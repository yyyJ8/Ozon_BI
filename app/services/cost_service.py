"""
费用计算模块 — 从 finance_transactions + 广告数据计算 7 类费用，写入 sku_daily_summary

核心改动（相比旧 summary_service）：
  费用日期归因统一使用 posting.created_at（下单日），而非 finance.operation_date（结算日）。
  通过 posting_number 关联 postings 表拿到 created_at，解决 revenue 和 costs 日期错配问题。

7 类费用（与前端 CostAnalysis.vue 一致）:
  commissions      ← OperationAgentDeliveredToCustomer.sale_commission
  logistics_costs  ← services JSON 中含 "Logistic" 的条目（Ozon API 不填充 delivery_charge 字段）
  storage_fees     ← TemporaryStorage amount
  advertising      ← ad_sku_daily_stats.spend（SKU 活动，按点击付费）
  promotion_costs  ← OperationPromotionWithCostPerOrder（按订单付费）
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
from app.services.ad_spend_adjustment import apply_adjustments, load_active_adjustments


def _parse_amount(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def _extract_logistics_from_services(services: Optional[list]) -> Decimal:
    """从 services JSON 中提取物流费用（Ozon API 的 delivery_charge 字段始终为 0，
    实际物流费在 services 数组里，name 包含 'Logistic' 的条目）"""
    if not services:
        return Decimal("0")
    total = Decimal("0")
    for svc in services:
        name = svc.get("name", "")
        if "Logistic" in name or "logistic" in name:
            total += _parse_amount(svc.get("price"))
    return total


def build_costs(db: Session, start_date: date, end_date: date, store_id: int) -> dict:
    """
    按日期范围构建费用字段，写入 sku_daily_summary。
    有 posting_number 的费用 → 按 posting.created_at 归因；无 posting_number → 按 operation_date。
    """
    logger.info(f"=== [store={store_id}] 费用计算: {start_date} ~ {end_date} ===")

    # ── 1. 获取日期范围内的所有 postings ──
    postings_in_range = db.query(Posting).filter(
        Posting.store_id == store_id,
        Posting.created_at >= start_date,
        Posting.created_at < end_date + timedelta(days=1),
    ).all()
    posting_numbers_in_range = {p.posting_number for p in postings_in_range if p.posting_number}

    posting_date_map: dict[str, date] = {}
    for p in postings_in_range:
        if p.posting_number and p.created_at:
            posting_date_map[p.posting_number] = p.created_at.date()

    logger.info(f"日期范围内 postings: {len(postings_in_range)} 个")

    # ── 2. 加载 finance_transactions ──
    txs: list[FinanceTransaction] = []

    # 2a: 按 operation_date 加载
    txs_by_date = db.query(FinanceTransaction).filter(
        FinanceTransaction.store_id == store_id,
        FinanceTransaction.operation_date.between(start_date, end_date),
        FinanceTransaction.sku_id.isnot(None),
    ).all()
    txs.extend(txs_by_date)
    logger.info(f"finance（按 operation_date）: {len(txs_by_date)} 条")

    # 2b: 按 posting_number 加载（覆盖结算日滞后于下单日的情况）
    if posting_numbers_in_range:
        existing_ids = {tx.operation_id for tx in txs}
        txs_by_posting = db.query(FinanceTransaction).filter(
            FinanceTransaction.store_id == store_id,
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
    extra_posting_numbers = set()
    for tx in txs:
        if tx.posting_number and tx.posting_number not in posting_date_map:
            extra_posting_numbers.add(tx.posting_number)

    if extra_posting_numbers:
        extra_postings = db.query(Posting).filter(
            Posting.store_id == store_id,
            Posting.posting_number.in_(extra_posting_numbers),
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
            # 物流费从 services JSON 提取（Ozon API 的 delivery_charge 字段始终为 0）
            g["logistics_costs"] += _extract_logistics_from_services(tx.services)

        elif optype in ("OperationItemReturn", "ClientReturnAgentOperation"):
            g["returns_amount"] += amt
            # 退货物流费也从 services JSON 提取（return_delivery_charge 字段始终为 0）
            g["logistics_costs"] += _extract_logistics_from_services(tx.services)

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

    # ── 3.5 推广费（OperationPromotionWithCostPerOrder，全部 sku_id=NULL，需通过 posting 归因）──
    promo_txs = db.query(FinanceTransaction).filter(
        FinanceTransaction.store_id == store_id,
        FinanceTransaction.operation_type == "OperationPromotionWithCostPerOrder",
        FinanceTransaction.operation_date.between(start_date, end_date),
    ).all()
    if promo_txs:
        promo_posting_numbers = {tx.posting_number for tx in promo_txs if tx.posting_number}
        posting_skus: dict[str, list[int]] = {}
        if promo_posting_numbers:
            promo_postings = db.query(Posting).filter(
                Posting.store_id == store_id,
                Posting.posting_number.in_(promo_posting_numbers),
            ).all()
            for p in promo_postings:
                if p.products:
                    skus = [
                        prod.get("sku") for prod in p.products
                        if prod.get("sku") is not None
                    ]
                    if skus:
                        posting_skus[p.posting_number] = skus
            logger.info(f"推广费 posting 匹配: {len(posting_skus)}/{len(promo_posting_numbers)}")

        # 有 posting → 按 SKU 数均摊
        has_posting_txs = [tx for tx in promo_txs if tx.posting_number in posting_skus]
        for tx in has_posting_txs:
            skus = posting_skus.get(tx.posting_number)
            if not skus:
                continue
            amt = _parse_amount(tx.amount)
            per_sku = amt / Decimal(str(len(skus)))
            attr_date = posting_date_map.get(tx.posting_number, tx.operation_date)
            is_cross = attr_date < start_date or attr_date > end_date
            for sid in skus:
                g = _get_group((attr_date, sid))
                g["promotion_costs"] += per_sku
                if is_cross:
                    g["is_cross_period"] = True

        # 无 posting → 按当天 revenue 占比分摊
        unmatched_txs = [tx for tx in promo_txs if tx.posting_number not in posting_skus]
        if unmatched_txs:
            daily_promo: dict[date, Decimal] = {}
            for tx in unmatched_txs:
                d = daily_promo.get(tx.operation_date, Decimal("0"))
                daily_promo[tx.operation_date] = d + _parse_amount(tx.amount)

            revenue_rows = db.execute(text("""
                SELECT "date", sku_id, revenue
                FROM ozon.sku_daily_summary
                WHERE store_id = :store_id
                  AND "date" BETWEEN :from_date AND :to_date
                  AND revenue > 0
            """), {"store_id": store_id, "from_date": start_date, "to_date": end_date}).fetchall()

            daily_revenue: dict[date, dict[int, Decimal]] = {}
            daily_revenue_total: dict[date, Decimal] = {}
            for rdate, sid, rev in revenue_rows:
                rev_d = Decimal(str(rev or 0))
                if rdate not in daily_revenue:
                    daily_revenue[rdate] = {}
                daily_revenue[rdate][sid] = rev_d
                daily_revenue_total[rdate] = daily_revenue_total.get(rdate, Decimal("0")) + rev_d

            rev_attributed = 0
            for rdate, total_promo in daily_promo.items():
                rev_map = daily_revenue.get(rdate, {})
                day_total_rev = daily_revenue_total.get(rdate, Decimal("0"))
                if day_total_rev <= 0 or total_promo == 0:
                    continue
                for sid, rev in rev_map.items():
                    share = rev / day_total_rev
                    g = _get_group((rdate, sid))
                    g["promotion_costs"] += total_promo * share
                    rev_attributed += 1
            logger.info(f"推广费 revenue 分摊: {len(daily_promo)} 天, {rev_attributed} 个组合")

        logger.info(
            f"推广费归因: {len(promo_txs)} 条, "
            f"posting={len(has_posting_txs)} + revenue={len(unmatched_txs)}"
        )
    else:
        logger.info("promotion 记录: 0 条")

    # ── 4. 广告费聚合 ──

    # 4a: ad_sku_daily_stats（SKU 级精确数据）
    ad_rows = db.execute(text("""
        SELECT sku_id, stat_date, SUM(spend) AS total_spend
        FROM ozon.ad_sku_daily_stats
        WHERE store_id = :store_id
          AND stat_date BETWEEN :from_date AND :to_date
          AND sku_id > 0
        GROUP BY sku_id, stat_date
    """), {"store_id": store_id, "from_date": start_date, "to_date": end_date}).fetchall()

    for sku_id, stat_date, total_spend in ad_rows:
        key = (stat_date, sku_id)
        g = _get_group(key)
        g["advertising"] += Decimal(str(total_spend)) * -1

    logger.info(f"ad_sku_daily_stats 广告费: {len(ad_rows)} 个组合")

    # 4b 已移除: SEARCH_PROMO 按单付费统一走 promotion_costs
    # （OperationPromotionWithCostPerOrder，Finance API 实际结算口径 + posting 级归因），
    # 不再按 revenue 分摊进 advertising，避免同一笔钱重复计费。

    # 4c: 广告花费归因调整（A→B 转移规则，实时应用）
    adjustments = load_active_adjustments(db, store_id)
    apply_adjustments(groups, adjustments, _get_group)

    # ── 5. 写入 sku_daily_summary ──
    updated = 0
    created = 0

    for (op_date, sku_id), vals in groups.items():
        summary = db.query(SkuDailySummary).filter(
            SkuDailySummary.store_id == store_id,
            SkuDailySummary.record_date == op_date,
            SkuDailySummary.sku_id == sku_id,
        ).first()

        if not summary:
            summary = SkuDailySummary(
                store_id=store_id,
                record_date=op_date,
                sku_id=sku_id,
            )
            db.add(summary)
            created += 1

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
