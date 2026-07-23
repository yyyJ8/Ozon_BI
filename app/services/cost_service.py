"""
费用计算模块 — 从 finance_transactions + 广告数据计算 7 类费用，写入 sku_daily_summary

核心改动（相比旧 summary_service）：
  费用日期归因统一使用 posting.created_at（下单日），而非 finance.operation_date（结算日）。
  通过 posting_number 关联 postings 表拿到 created_at，解决 revenue 和 costs 日期错配问题。

7 类费用（与前端 CostAnalysis.vue 一致）:
  commissions      ← OperationAgentDeliveredToCustomer.sale_commission
  logistics_costs  ← delivery_charge + return_delivery_charge
  storage_fees     ← TemporaryStorage amount
  advertising      ← ad_sku_daily_stats.spend + SEARCH_PROMO revenue 分摊
  promotion_costs  ← OperationPromotionWithCostPerOrder
  returns_amount   ← OperationItemReturn / ClientReturnAgentOperation
  other_costs      ← 剩余负 amount
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import FinanceTransaction, Posting, SkuDailySummary


def _parse_amount(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def build_costs(db: Session, start_date: date, end_date: date) -> dict:
    """
    按日期范围构建费用字段，写入 sku_daily_summary。
    有 posting_number 的费用 → 按 posting.created_at 归因；无 posting_number → 按 operation_date。
    """
    logger.info(f"=== 费用计算: {start_date} ~ {end_date} ===")

    # ── 1. 获取日期范围内的所有 postings ──
    #    用于两个目的：
    #    a) 扩展 finance 查询范围（捞取 posting.created_at 在范围内但 operation_date 在范围外的记录）
    #    b) posting_number → created_at 映射
    postings_in_range = db.query(Posting).filter(
        Posting.created_at >= start_date,
        Posting.created_at < end_date + timedelta(days=1),
    ).all()
    posting_numbers_in_range = {p.posting_number for p in postings_in_range if p.posting_number}

    posting_date_map: dict[str, date] = {}
    for p in postings_in_range:
        if p.posting_number and p.created_at:
            posting_date_map[p.posting_number] = p.created_at.date()

    logger.info(f"日期范围内 postings: {len(postings_in_range)} 个, posting_numbers: {len(posting_numbers_in_range)}")

    # ── 2. 加载 finance_transactions ──
    #    两类都需要：
    #    a) operation_date 在范围内（覆盖无 posting_number 的费用：仓储、推广、其他）
    #    b) posting_number 指向范围内的 posting（覆盖佣金/物流，即使结算日不在范围内）
    txs: list[FinanceTransaction] = []
    total_finance = 0

    # 2a: 按 operation_date 加载
    txs_by_date = db.query(FinanceTransaction).filter(
        FinanceTransaction.operation_date.between(start_date, end_date),
        FinanceTransaction.sku_id.isnot(None),
    ).all()
    txs.extend(txs_by_date)
    total_finance += len(txs_by_date)
    logger.info(f"finance（按 operation_date）: {len(txs_by_date)} 条")

    # 2b: 按 posting_number 加载（覆盖结算日滞后于下单日的情况）
    if posting_numbers_in_range:
        # 排除已经在 2a 中加载的 operation_id
        existing_ids = {tx.operation_id for tx in txs}
        txs_by_posting = db.query(FinanceTransaction).filter(
            FinanceTransaction.posting_number.in_(posting_numbers_in_range),
            FinanceTransaction.sku_id.isnot(None),
        ).all()
        for tx in txs_by_posting:
            if tx.operation_id not in existing_ids:
                txs.append(tx)
                existing_ids.add(tx.operation_id)
        logger.info(f"finance（按 posting_number 补充）: {len(txs) - len(txs_by_date)} 条")

    total_finance = len(txs)
    logger.info(f"finance 总计: {total_finance} 条")

    # ── 2.5 补充 posting_date_map ──
    #    有些 finance 的 posting_number 可能不在我们的日期范围内（如旧订单的退货），
    #    需要额外查询这些 posting 的 created_at
    extra_posting_numbers = set()
    for tx in txs:
        if tx.posting_number and tx.posting_number not in posting_date_map:
            extra_posting_numbers.add(tx.posting_number)

    if extra_posting_numbers:
        extra_postings = db.query(Posting).filter(
            Posting.posting_number.in_(extra_posting_numbers)
        ).all()
        for p in extra_postings:
            if p.created_at:
                posting_date_map[p.posting_number] = p.created_at.date()
        logger.info(f"补充 posting 映射: {len(extra_postings)}/{len(extra_posting_numbers)} 匹配")

    # ── 3. 按 (date, sku_id) 分组，分类费用 ──
    groups: dict[tuple, dict] = {}

    def _get_group(key: tuple) -> dict:
        if key not in groups:
            groups[key] = {
                "commissions": Decimal("0"),
                "returns_amount": Decimal("0"),
                "logistics_costs": Decimal("0"),
                "storage_fees": Decimal("0"),
                "advertising": Decimal("0"),
                "promotion_costs": Decimal("0"),
                "other_costs": Decimal("0"),
                "is_cross_period": False,
            }
        return groups[key]

    for tx in txs:
        amt = _parse_amount(tx.amount)
        optype = tx.operation_type or ""

        # 确定归因日期：有 posting_number → posting.created_at，否则 → operation_date
        if tx.posting_number and tx.posting_number in posting_date_map:
            attr_date = posting_date_map[tx.posting_number]
        else:
            attr_date = tx.operation_date

        key = (attr_date, tx.sku_id)
        g = _get_group(key)

        # 标记跨期：归因日期不在本次处理范围内
        if attr_date < start_date or attr_date > end_date:
            g["is_cross_period"] = True

        if optype == "OperationAgentDeliveredToCustomer":
            g["commissions"] += _parse_amount(tx.sale_commission)
            g["logistics_costs"] += _parse_amount(tx.delivery_charge)

        elif optype in ("OperationItemReturn", "ClientReturnAgentOperation"):
            g["returns_amount"] += amt
            g["logistics_costs"] += _parse_amount(tx.return_delivery_charge)

        elif "TemporaryStorage" in optype:
            g["storage_fees"] += amt

        elif optype == "OperationPromotionWithCostPerOrder":
            g["promotion_costs"] += amt

        else:
            if amt < 0:
                g["other_costs"] += amt

    logger.info(
        f"分组聚合: {len(groups)} 个 (date, sku) 组合"
        f"（含 {sum(1 for v in groups.values() if v['is_cross_period'])} 个跨期归因）"
    )

    # ── 4. 广告费聚合 ──

    # 4a: ad_sku_daily_stats（SKU 级精确数据）
    ad_rows = db.execute(text("""
        SELECT sku_id, stat_date, SUM(spend) AS total_spend
        FROM ozon.ad_sku_daily_stats
        WHERE stat_date BETWEEN :from_date AND :to_date
          AND sku_id > 0
        GROUP BY sku_id, stat_date
    """), {"from_date": start_date, "to_date": end_date}).fetchall()

    for sku_id, stat_date, total_spend in ad_rows:
        key = (stat_date, sku_id)
        g = _get_group(key)
        g["advertising"] += Decimal(str(total_spend)) * -1

    logger.info(f"ad_sku_daily_stats 广告费: {len(ad_rows)} 个组合")

    # 4b: SEARCH_PROMO 按当日 revenue 占比分摊
    search_promo_rows = db.execute(text("""
        SELECT ads.stat_date, SUM(ads.spend) AS total_spend
        FROM ozon.ad_daily_stats ads
        JOIN ozon.ad_campaigns ac ON ads.campaign_id = ac.campaign_id
        WHERE ads.stat_date BETWEEN :from_date AND :to_date
          AND ac.campaign_type = 'SEARCH_PROMO'
        GROUP BY ads.stat_date
    """), {"from_date": start_date, "to_date": end_date}).fetchall()

    if search_promo_rows:
        daily_spend = {r.stat_date: Decimal(str(r.total_spend or 0)) for r in search_promo_rows}
        revenue_rows = db.execute(text("""
            SELECT "date", sku_id, revenue
            FROM ozon.sku_daily_summary
            WHERE "date" BETWEEN :from_date AND :to_date
              AND revenue > 0
        """), {"from_date": start_date, "to_date": end_date}).fetchall()

        daily_revenue: dict[date, dict[int, Decimal]] = {}
        daily_revenue_total: dict[date, Decimal] = {}
        for rdate, sid, rev in revenue_rows:
            rev_d = Decimal(str(rev or 0))
            if rdate not in daily_revenue:
                daily_revenue[rdate] = {}
            daily_revenue[rdate][sid] = rev_d
            daily_revenue_total[rdate] = daily_revenue_total.get(rdate, Decimal("0")) + rev_d

        promo_attributed = 0
        for rdate, total_spend in daily_spend.items():
            if total_spend == 0:
                continue
            rev_map = daily_revenue.get(rdate, {})
            day_total_rev = daily_revenue_total.get(rdate, Decimal("0"))
            if day_total_rev <= 0:
                continue
            for sid, rev in rev_map.items():
                share = rev / day_total_rev
                attributed = total_spend * share
                g = _get_group((rdate, sid))
                g["advertising"] += attributed * -1
                promo_attributed += 1

        logger.info(f"SEARCH_PROMO 分摊: {len(daily_spend)} 天, {promo_attributed} 个组合")

    # ── 5. 写入 sku_daily_summary ──
    updated = 0
    created = 0

    for (op_date, sku_id), vals in groups.items():
        summary = db.query(SkuDailySummary).filter(
            SkuDailySummary.record_date == op_date,
            SkuDailySummary.sku_id == sku_id,
        ).first()

        if not summary:
            summary = SkuDailySummary(
                record_date=op_date,
                sku_id=sku_id,
            )
            db.add(summary)
            created += 1

        # 跨期归因：只更新费用字段，不覆盖其他字段
        # （非跨期的正常记录可以全量更新费用）
        summary.commissions = vals["commissions"]
        summary.returns_amount = vals["returns_amount"]
        summary.logistics_costs = vals["logistics_costs"]
        summary.storage_fees = vals["storage_fees"]
        summary.advertising = vals["advertising"]
        summary.promotion_costs = vals["promotion_costs"]
        summary.other_costs = vals["other_costs"]

        updated += 1

    db.commit()

    logger.info(f"费用写入完成: 更新 {updated} 行（新建 {created} 行）")
    return {"costs_updated": updated, "costs_created": created}
