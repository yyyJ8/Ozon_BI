"""
汇总构建编排 — 协调费用计算 + 利润计算，并聚合履约指标

流程:
  1. 从 postings 聚合 revenue / ordered_units / delivered_units / cancelled_units
     revenue = SUM(price × quantity)，与 ordered_units 同源（posting.created_at）
  2. 从 returns 聚合 returns_units
  3. 写入库存快照（当天）
  4. 调用 cost_service.build_costs()  → 写入 7 类费用
  5. 调用 profit_service.build_profit() → 写入 net_profit / profit_margin

费用计算已独立到 app/services/cost_service.py。
利润计算已独立到 app/services/profit_service.py。

重要: revenue / ordered_units / costs 三者的日期维度统一为 posting.created_at。
"""
from datetime import date, timedelta
from decimal import Decimal

from loguru import logger
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.models import Posting, SkuDailySummary, Stock
from app.services.cost_service import build_costs
from app.services.profit_service import build_profit


def _parse_amount(val) -> Decimal:
    if val is None:
        return Decimal("0")
    return Decimal(str(val))


def build_summary(db: Session, start_date: date, end_date: date) -> dict:
    """
    构建/更新 sku_daily_summary:
      1. 聚合履约指标（postings → ordered/delivered/cancelled）
      2. 聚合退货件数（returns → returns_units）
      3. 库存快照
      4. 费用计算（cost_service）
      5. 利润计算（profit_service）
    """
    logger.info(f"=== 开始构建日汇总: {start_date} ~ {end_date} ===")

    all_groups: dict[tuple, dict] = {}

    def _get_group(key: tuple) -> dict:
        if key not in all_groups:
            all_groups[key] = {
                "revenue": Decimal("0"),
                "ordered_units": 0,
                "delivered_units": 0,
                "cancelled_units": 0,
                "returns_units": 0,
            }
        return all_groups[key]

    # ── 1. 从 postings 聚合 revenue + ordered_units（全部状态，以 posting.created_at 为准）──
    posting_agg_rows = db.execute(text("""
        SELECT
            created_at::date AS pdate,
            (prod->>'sku')::bigint AS sku_id,
            SUM((prod->>'quantity')::int) AS ordered_units,
            SUM((prod->>'quantity')::int * (prod->>'price')::numeric) AS revenue
        FROM ozon.postings,
             jsonb_array_elements(products) AS prod
        WHERE created_at >= :date_from
          AND created_at  < :date_to
        GROUP BY created_at::date, (prod->>'sku')::bigint
    """), {"date_from": start_date, "date_to": end_date + timedelta(days=1)}).fetchall()

    for pdate, sku_id, ordered_units, revenue in posting_agg_rows:
        if sku_id is None:
            continue
        g = _get_group((pdate, sku_id))
        if ordered_units is not None:
            g["ordered_units"] = int(ordered_units)
        if revenue is not None:
            g["revenue"] = Decimal(str(revenue))

    logger.info(f"posting 聚合（revenue + ordered_units）: {len(posting_agg_rows)} 个组合")

    # ── 2. 从 postings 聚合 delivered_units / cancelled_units ──
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

    for pdate, sku_id, qty, status in posting_rows:
        if sku_id is None or qty is None:
            continue
        g = _get_group((pdate, sku_id))
        if status == "delivered":
            g["delivered_units"] += int(qty)
        elif status == "cancelled":
            g["cancelled_units"] += int(qty)

    logger.info(f"posting 聚合（delivered/cancelled）: {len(posting_rows)} 条")

    # ── 3. 从 returns 表聚合退货件数 ──
    return_rows = db.execute(text("""
        SELECT
            p.created_at::date AS sale_date,
            r.sku,
            SUM(r.quantity) AS total_returns
        FROM ozon.returns r
        JOIN ozon.postings p ON r.posting_number = p.posting_number
        WHERE p.created_at >= :date_from
          AND p.created_at  < :date_to
        GROUP BY p.created_at::date, r.sku
    """), {"date_from": start_date, "date_to": end_date + timedelta(days=1)}).fetchall()

    for sale_date, sku_id, total_returns in return_rows:
        if sku_id is None:
            continue
        _get_group((sale_date, sku_id))["returns_units"] = int(total_returns)

    logger.info(f"returns 表退货件数: {len(return_rows)} 个组合")

    # ── 4. 写入履约指标 ──
    all_sku_ids = list({sid for _, sid in all_groups.keys()})
    stock_map: dict[int, tuple[int, int]] = {}
    if all_sku_ids:
        stock_rows = db.query(
            Stock.sku_id,
            func.coalesce(func.sum(Stock.present), 0).label("present"),
            func.coalesce(func.sum(Stock.reserved), 0).label("reserved"),
        ).filter(Stock.sku_id.in_(all_sku_ids)).group_by(Stock.sku_id).all()
        stock_map = {r.sku_id: (int(r.present), int(r.reserved)) for r in stock_rows}

    posting_updated = 0
    for (pdate, sku_id), vals in all_groups.items():
        summary = db.query(SkuDailySummary).filter(
            SkuDailySummary.record_date == pdate,
            SkuDailySummary.sku_id == sku_id,
        ).first()

        sp, sr = stock_map.get(sku_id, (0, 0))

        if not summary:
            is_today = (pdate == date.today())
            summary = SkuDailySummary(
                record_date=pdate,
                sku_id=sku_id,
                stock_present=sp if is_today else 0,
                stock_reserved=sr if is_today else 0,
            )
            db.add(summary)

        summary.ordered_units = vals["ordered_units"]
        summary.delivered_units = vals["delivered_units"]
        summary.cancelled_units = vals["cancelled_units"]
        summary.returns_units = vals["returns_units"]

        # revenue 从 postings 聚合，覆盖 analytics_sync 写入的值（统一日期维度）
        summary.revenue = vals["revenue"]

        posting_updated += 1

    db.commit()
    logger.info(f"履约指标写入: {posting_updated} 行")

    # ── 5. 费用计算 ──
    cost_result = build_costs(db, start_date, end_date)

    # ── 6. 利润计算 ──
    profit_result = build_profit(db, start_date, end_date)

    total_updated = posting_updated + cost_result["costs_updated"]
    logger.info(
        f"汇总构建完成: 履约 {posting_updated} + 费用 {cost_result['costs_updated']}"
        f"（新建 {cost_result['costs_created']}）+ 利润 {profit_result['profit_updated']}"
    )
    return {
        "summary_updated": total_updated,
        "costs": cost_result,
        "profit": profit_result,
    }
