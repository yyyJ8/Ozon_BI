"""
销售分析同步 — 从 Analytics API 拉取销量和收入，写入 sku_daily_summary

注意: Analytics API 有 30 天最大查询窗口限制，超过会自动拆分。
某些时间段可能无数据（API 返回 400），会自动跳过。
"""
from datetime import date, datetime, timedelta
from decimal import Decimal

import httpx
from loguru import logger
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import OzonClient
from app.models import SkuDailySummary


def _date_range_chunks(date_from: str, date_to: str, max_days: int = 30):
    """将日期范围拆成 max_days 一段的小窗口"""
    start = datetime.strptime(date_from[:10], "%Y-%m-%d").date()
    end = datetime.strptime(date_to[:10], "%Y-%m-%d").date()
    chunks = []
    cur = start
    while cur < end:
        chunk_end = min(cur + timedelta(days=max_days - 1), end)
        chunks.append((cur.isoformat(), chunk_end.isoformat()))
        cur = chunk_end + timedelta(days=1)
    return chunks


def sync_analytics(db: Session, client: OzonClient,
                   date_from: str, date_to: str, store_id: int) -> dict:
    """
    同步销售分析数据（revenue，ordered_units 改由 build_summary 从 postings 聚合）
    """
    logger.info(f"=== [store={store_id}] 开始同步销售分析: {date_from} ~ {date_to} ===")

    chunks = _date_range_chunks(date_from, date_to)
    logger.info(f"[store={store_id}] 已拆分为 {len(chunks)} 个时间窗口")

    updated = 0
    for i, (win_from, win_to) in enumerate(chunks, 1):
        try:
            logger.info(f"  [store={store_id}] 窗口 {i}/{len(chunks)}: {win_from} ~ {win_to}")
            rows = client.get_all_analytics(win_from, win_to)
            if not rows:
                logger.info(f"  窗口 {i}: 无数据")
                continue

            for row in rows:
                dims = row.get("dimensions", [])
                metrics = row.get("metrics", [])

                if len(dims) < 2 or len(metrics) < 2:
                    continue

                sku_id = int(dims[0]["id"])
                day_str = dims[1]["id"]  # "2026-06-21"
                revenue = Decimal(str(metrics[1])) if metrics[1] else Decimal("0")

                stmt = pg_insert(SkuDailySummary).values(
                    store_id=store_id,
                    record_date=day_str,
                    sku_id=sku_id,
                    revenue=revenue,
                ).on_conflict_do_update(
                    index_elements=["store_id", "date", "sku_id"],
                    set_={
                        "revenue": revenue,
                    },
                )
                db.execute(stmt)
                updated += 1

            db.commit()
            logger.info(f"  窗口 {i}: 处理 {len(rows)} 行")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                logger.warning(f"  窗口 {i}: 该时间段无数据 (400), 跳过")
                continue
            raise

    logger.info(f"[store={store_id}] 销售分析同步完成: {updated} 行")
    return {"analytics_updated": updated}
