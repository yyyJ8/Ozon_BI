"""
汇总构建服务 — 从 finance_transactions 聚合，更新 sku_daily_summary 的费用字段

聚合逻辑:
  commissions     ← sale_commission WHERE operation_type = 'OperationAgentDeliveredToCustomer'
  returns_amount  ← amount WHERE operation_type IN ('OperationItemReturn', 'ClientReturnAgentOperation')
                    **退货按 posting_number → postings.created_at 归因到原销售日期**
  logistics_costs ← services[].price (where name contains Logistic)
                   仅从销售单（OperationAgentDeliveredToCustomer）提取，因为 amount 是净额不包含物流
                   其他类型的 amount 已含物流费，提取会重复计算
  storage_fees    ← amount WHERE operation_type LIKE '%TemporaryStorage%'
  advertising     ← amount WHERE operation_type = 'OperationMarketplaceCostPerClick'
  promotion_costs ← amount WHERE operation_type = 'OperationPromotionWithCostPerOrder'
  other_costs     ← 剩余所有负 amount（银行手续费、转运、包装、销毁等）

  net_profit    = revenue + commissions + returns + logistics + storage + advertising + promotion + other
  profit_margin = net_profit / revenue * 100

关键设计:
  - 退货按 postings.created_at（原订单日期）归因，而非 finance_transactions.operation_date（退货发生日）
  - 归因到日期范围外的退货：只更新 returns_amount/returns_units/net_profit，不覆盖其他费用字段
  - 按 posting_number 去重，每条退货单只计 1 件 returns_units
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy import BigInteger, func, text
from sqlalchemy.orm import Session

from app.models import FinanceTransaction, Posting, SkuDailySummary, Stock


def _parse_amount(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _get_logistics_from_services(services: Optional[list]) -> Decimal:
    """从 services JSONB 中提取物流费用（已在 API 中为负数）"""
    if not services:
        return Decimal("0")
    total = Decimal("0")
    for s in services:
        if "Logistic" in s.get("name", ""):
            total += _parse_amount(s.get("price"))
    return total


def build_summary(db: Session, start_date: date, end_date: date) -> dict:
    """
    按日期范围构建/更新 sku_daily_summary 的费用字段。
    保留 ordered_units 和 revenue（来自 analytics_sync）。
    退货按 postings.created_at 归因到原销售日期。
    """
    logger.info(f"=== 开始构建日汇总: {start_date} ~ {end_date} ===")

    # 1. 拉取有 SKU 关联的财务记录
    txs = db.query(FinanceTransaction).filter(
        FinanceTransaction.operation_date.between(start_date, end_date),
        FinanceTransaction.sku_id.isnot(None),
    ).all()
    logger.info(f"finance_records（有 SKU）: {len(txs)} 条")

    # 2. 构建 posting_number → 原销售日期 映射（退货归因用）
    return_posting_numbers = set()
    for tx in txs:
        if tx.operation_type in ("OperationItemReturn", "ClientReturnAgentOperation"):
            if tx.posting_number:
                return_posting_numbers.add(tx.posting_number)

    posting_sale_date: dict[str, date] = {}
    posting_status: dict[str, str] = {}  # 用于区分真退货 vs 取消退款
    if return_posting_numbers:
        postings = db.query(Posting).filter(
            Posting.posting_number.in_(return_posting_numbers)
        ).all()
        for p in postings:
            if p.created_at:
                posting_sale_date[p.posting_number] = p.created_at.date()
            if p.status:
                posting_status[p.posting_number] = p.status
        matched = len(posting_sale_date)
        total = len(return_posting_numbers)
        logger.info(f"退货归因映射: {matched}/{total} 个 posting 匹配到原销售日期"
                     + (f" ({total - matched} 未匹配，退回 operation_date)" if total > matched else ""))

    # 3. 按 (date, sku_id) 分组，逐条分类
    #    退货使用 sale_date（原订单日期），其他费用使用 operation_date
    #    注：returns_units 不再从 finance 取（仅覆盖 ClientReturn），
    #        改由第 3.5c 步从 returns 表聚合（覆盖 Cancellation + ClientReturn）
    groups: dict[tuple, dict] = {}

    def _get(key):
        if key not in groups:
            groups[key] = {
                "commissions": Decimal("0"),
                "returns_amount": Decimal("0"),
                "returns_units": 0,
                "delivered_units": 0,
                "cancelled_units": 0,
                "logistics_costs": Decimal("0"),
                "storage_fees": Decimal("0"),
                "advertising": Decimal("0"),
                "promotion_costs": Decimal("0"),
                "other_costs": Decimal("0"),
                "is_return_only": False,  # 标记：是否只有退货归因（无同期其他费用）
            }
        return groups[key]

    for tx in txs:
        amt = _parse_amount(tx.amount)
        optype = tx.operation_type or ""

        if optype == "OperationAgentDeliveredToCustomer":
            key = (tx.operation_date, tx.sku_id)
            g = _get(key)
            g["commissions"] += _parse_amount(tx.sale_commission)
            g["logistics_costs"] += _get_logistics_from_services(tx.services)

        elif optype in ("OperationItemReturn", "ClientReturnAgentOperation"):
            # 退货归因：用 posting.created_at 作为原销售日期
            sale_date = posting_sale_date.get(tx.posting_number, tx.operation_date)
            key = (sale_date, tx.sku_id)
            g = _get(key)
            # returns_amount 始终计入（取消退款也是真实财务流水）
            g["returns_amount"] += amt
            # 标记此 group 的退货是否来自其他日期（跨期归因）
            if sale_date != tx.operation_date and (sale_date < start_date or sale_date > end_date):
                g["is_return_only"] = True
            # returns_units 改由第 3.5c 步从 returns 表聚合（覆盖全部 363 条）

        elif "TemporaryStorage" in optype:
            key = (tx.operation_date, tx.sku_id)
            g = _get(key)
            g["storage_fees"] += amt

        elif optype == "OperationPromotionWithCostPerOrder":
            key = (tx.operation_date, tx.sku_id)
            g = _get(key)
            g["promotion_costs"] += amt

        else:
            if amt < 0:
                key = (tx.operation_date, tx.sku_id)
                g = _get(key)
                g["other_costs"] += amt

    logger.info(f"分组聚合: {len(groups)} 个 (date, sku) 组合"
                 + f"（含 {sum(1 for v in groups.values() if v['is_return_only'])} 个跨期退货归因）")

    # 3.5 从 postings 聚合 delivered_units / cancelled_units（raw SQL — JSONB 展开）
    posting_rows = db.execute(text("""
        SELECT
            created_at::date AS pdate,
            (prod->>'sku')::bigint AS sku_id,
            (prod->>'quantity')::int AS qty,
            status
        FROM ozon.postings,
             jsonb_array_elements(products) AS prod
        WHERE created_at >= :date_from
          AND created_at  < :date_to
          AND status IN ('delivered', 'cancelled')
    """), {"date_from": start_date, "date_to": end_date + timedelta(days=1)}).fetchall()

    posting_agg: dict[tuple, dict] = {}
    for pdate, sku_id, qty, status in posting_rows:
        if sku_id is None or qty is None:
            continue
        key = (pdate, sku_id)
        if key not in posting_agg:
            posting_agg[key] = {"delivered_units": 0, "cancelled_units": 0}
        if status == "delivered":
            posting_agg[key]["delivered_units"] += int(qty)
        elif status == "cancelled":
            posting_agg[key]["cancelled_units"] += int(qty)

    for key, agg in posting_agg.items():
        g = _get(key)
        g["delivered_units"] = agg["delivered_units"]
        g["cancelled_units"] = agg["cancelled_units"]

    logger.info(f"posting 聚合: {len(posting_agg)} 个 (date, sku) 组合")

    # 3.5b 从 returns 表聚合退货件数（替代 finance 的 returns_units）
    #      覆盖 Cancellation + ClientReturn（finance 只能覆盖 delivered posting 的 ClientReturn）
    return_rows = db.execute(text("""
        SELECT
            p.created_at::date AS sale_date,
            r.sku,
            COUNT(*) AS total_returns
        FROM ozon.returns r
        JOIN ozon.postings p ON r.posting_number = p.posting_number
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to
        GROUP BY p.created_at::date, r.sku
    """), {"date_from": start_date, "date_to": end_date + timedelta(days=1)}).fetchall()

    for sale_date, sku_id, total_returns in return_rows:
        if sku_id is None:
            continue
        g = _get((sale_date, sku_id))
        g["returns_units"] = int(total_returns)

    logger.info(f"returns 表退货件数: {len(return_rows)} 个 (date, sku) 组合"
                 + f"（覆盖全部 Cancellation + ClientReturn）")

    # 3.5c 从 Performance API 聚合广告费（替代 Finance API OperationMarketplaceCostPerClick）
    #      因为 Finance API 的广告记录全部 sku_id=None，无法关联到 SKU
    ad_rows = db.execute(text("""
        SELECT m.sku_id, ds.stat_date, SUM(ds.spend) AS total_spend
        FROM ozon.ad_daily_stats ds
        JOIN ozon.ad_campaign_sku_map m ON ds.campaign_id = m.campaign_id
        WHERE ds.stat_date BETWEEN :from_date AND :to_date
        GROUP BY m.sku_id, ds.stat_date
    """), {"from_date": start_date, "to_date": end_date}).fetchall()

    for sku_id, stat_date, total_spend in ad_rows:
        key = (stat_date, sku_id)
        g = _get(key)
        g["advertising"] = Decimal(str(total_spend)) * -1  # 取负：spend 为正数，费用需为负数

    logger.info(f"Performance API 广告费聚合: {len(ad_rows)} 个 (date, sku) 组合")

    # 4. 预加载库存（所有涉及 SKU 的当前库存）
    all_sku_ids = list(set(sid for _, sid in groups.keys()))
    stock_map: dict[int, tuple[int, int]] = {}
    if all_sku_ids:
        stock_rows = db.query(
            Stock.sku_id,
            func.coalesce(func.sum(Stock.present), 0).label("present"),
            func.coalesce(func.sum(Stock.reserved), 0).label("reserved"),
        ).filter(Stock.sku_id.in_(all_sku_ids)).group_by(Stock.sku_id).all()
        stock_map = {r.sku_id: (int(r.present), int(r.reserved)) for r in stock_rows}

    # 5. 更新 sku_daily_summary
    updated = 0
    for (op_date, sku_id), vals in groups.items():
        summary = db.query(SkuDailySummary).filter(
            SkuDailySummary.record_date == op_date,
            SkuDailySummary.sku_id == sku_id,
        ).first()

        sp, sr = stock_map.get(sku_id, (0, 0))

        if not summary:
            summary = SkuDailySummary(
                record_date=op_date,
                sku_id=sku_id,
                stock_present=sp,
                stock_reserved=sr,
            )
            db.add(summary)

        # 退货字段：始终 SET（包括跨期归因）
        summary.returns_amount = vals["returns_amount"]
        summary.returns_units = vals["returns_units"]

        # 履约字段：始终 SET（posting 数据不依赖 finance 范围）
        summary.delivered_units = vals["delivered_units"]
        summary.cancelled_units = vals["cancelled_units"]

        # 非退货字段：仅当日期在本次处理范围内才 SET
        # 跨期归因的 group（is_return_only=True）不覆盖其他费用字段，
        # 因为这些字段在上次处理该日期时已经被正确设定了
        if not vals["is_return_only"]:
            summary.commissions = vals["commissions"]
            summary.logistics_costs = vals["logistics_costs"]
            summary.storage_fees = vals["storage_fees"]
            summary.advertising = vals["advertising"]
            summary.other_costs = vals["other_costs"]
            # promotion_costs 在 vals 中有但模型中无单独字段，这里跳过

        # 净利润 = revenue + 所有费用（费用已经是负数）
        # 使用 summary 上的当前值（含跨期归因的 returns）
        total_costs = (
            _parse_amount(summary.commissions)
            + _parse_amount(summary.returns_amount)
            + _parse_amount(summary.logistics_costs)
            + _parse_amount(summary.storage_fees)
            + _parse_amount(summary.advertising)
            + vals["promotion_costs"]  # promotion_costs 无独立持久化，直接从本次 vals 取
            + _parse_amount(summary.other_costs)
        )
        rev = _parse_amount(summary.revenue)
        summary.net_profit = rev + total_costs

        # 利润率
        if rev > 0:
            summary.profit_margin = (summary.net_profit / rev * 100).quantize(Decimal("0.01"))
        else:
            summary.profit_margin = Decimal("0")

        summary.data_quality = "complete"
        updated += 1

    db.commit()

    # 标记日期范围内所有剩余行也为 complete
    # 这些行只有 Analytics 数据（无 finance/postings），但已经处理过所有可用的数据源
    remained = db.execute(text("""
        UPDATE ozon.sku_daily_summary
        SET data_quality = 'complete'
        WHERE "date" >= :date_from
          AND "date" <= :date_to
          AND data_quality = 'partial'
    """), {"date_from": start_date, "date_to": end_date}).rowcount

    logger.info(f"汇总构建完成: 更新 {updated} 行 + {remained} 行补标 complete")
    return {"summary_updated": updated + remained}
