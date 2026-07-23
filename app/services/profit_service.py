"""
利润计算模块 — 基于 revenue + 7 类费用计算 net_profit / profit_margin

前置条件: cost_service.build_costs() 已写入费用字段，analytics_sync 已写入 revenue。

利润公式:
  net_profit = revenue + commissions + returns_amount + logistics_costs
             + storage_fees + advertising + promotion_costs + other_costs
  profit_margin = net_profit / revenue * 100

data_quality:
  "complete" — 费用数据完整（至少有一项费用非零，或 revenue=0 且费用也=0）
  "partial"  — revenue > 0 但所有费用 = 0（费用数据尚未到位）
"""
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import SkuDailySummary


def _parse_amount(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def build_profit(db: Session, start_date: date, end_date: date, store_id: int) -> dict:
    """
    计算日期范围内所有 sku_daily_summary 行的 net_profit 和 profit_margin。
    """
    logger.info(f"=== [store={store_id}] 利润计算: {start_date} ~ {end_date} ===")

    rows = db.query(SkuDailySummary).filter(
        SkuDailySummary.store_id == store_id,
        SkuDailySummary.record_date.between(start_date, end_date),
    ).all()

    updated = 0
    partial_count = 0

    for s in rows:
        revenue = _parse_amount(s.revenue)
        commissions = _parse_amount(s.commissions)
        returns_amount = _parse_amount(s.returns_amount)
        logistics_costs = _parse_amount(s.logistics_costs)
        storage_fees = _parse_amount(s.storage_fees)
        advertising = _parse_amount(s.advertising)
        promotion_costs = _parse_amount(s.promotion_costs)
        other_costs = _parse_amount(s.other_costs)

        total_costs = (
            commissions + returns_amount + logistics_costs
            + storage_fees + advertising + promotion_costs + other_costs
        )

        s.net_profit = revenue + total_costs

        if revenue > 0:
            s.profit_margin = (s.net_profit / revenue * 100).quantize(Decimal("0.01"))
        else:
            s.profit_margin = Decimal("0")

        # data_quality: 有收入但全部费用为 0 → partial
        if revenue > 0 and total_costs == 0:
            s.data_quality = "partial"
            partial_count += 1
        else:
            s.data_quality = "complete"

        updated += 1

    db.commit()

    logger.info(
        f"[store={store_id}] 利润计算完成: {updated} 行, "
        f"其中 {partial_count} 行标记 partial（有收入无费用）"
    )
    return {
        "profit_updated": updated,
        "profit_partial": partial_count,
    }
