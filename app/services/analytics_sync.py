"""
销售分析同步 — 从 Analytics API 拉取销量和收入，写入 sku_daily_summary
"""
from datetime import date
from decimal import Decimal

from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import SkuDailySummary


def sync_analytics(db: Session, client: OzonClient,
                   date_from: str, date_to: str) -> dict:
    """
    同步销售分析数据（ordered_units, revenue）
    注意: analytics API 只返回这 2 个有效指标，其他均已废弃
    """
    logger.info(f"=== 开始同步销售分析: {date_from} ~ {date_to} ===")

    rows = client.get_all_analytics(date_from, date_to)
    logger.info(f"analytics 返回 {len(rows)} 行")

    updated = 0
    for row in rows:
        dims = row.get("dimensions", [])
        metrics = row.get("metrics", [])

        if len(dims) < 2 or len(metrics) < 2:
            continue

        sku_id = int(dims[0]["id"])
        day_str = dims[1]["id"]  # "2026-06-21"
        ordered_units = int(metrics[0] or 0)
        revenue = Decimal(str(metrics[1])) if metrics[1] else Decimal("0")

        stmt = pg_insert(SkuDailySummary).values(
            record_date=day_str,
            sku_id=sku_id,
            ordered_units=ordered_units,
            revenue=revenue,
        ).on_conflict_do_update(
            index_elements=["date", "sku_id"],
            set_={
                "ordered_units": ordered_units,
                "revenue": revenue,
            },
        )
        db.execute(stmt)
        updated += 1

    db.commit()
    logger.info(f"销售分析同步完成: {updated} 行")
    return {"analytics_updated": updated}
