"""
广告数据同步 — 从 Performance API 拉取活动+每日统计, 建立 SKU 映射,
更新 sku_daily_summary.advertising
"""
import re
from datetime import date as date_type, datetime, timedelta
from decimal import Decimal
from typing import Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.perf import OzonPerfClient
from app.models import (
    AdCampaign, AdDailyStats, AdCampaignSkuMap, AdSkuDailyStats, Product,
)


# ── helpers ────────────────────────────────────────────────

def _date_range_chunks(date_from: str, date_to: str, max_days: int = 30) -> list[tuple[str, str]]:
    """将日期范围拆成 max_days 一段的小窗口"""
    start = datetime.strptime(date_from[:10], "%Y-%m-%d").date()
    end = datetime.strptime(date_to[:10], "%Y-%m-%d").date()
    chunks = []
    cur = start
    while cur <= end:
        chunk_end = min(cur + timedelta(days=max_days - 1), end)
        chunks.append((cur.isoformat(), chunk_end.isoformat()))
        cur = chunk_end + timedelta(days=1)
    return chunks


def _extract_offer_prefix(title: Optional[str]) -> Optional[str]:
    """从活动标题中提取 offer_id 前缀

    例: "33367-亚克力仓鼠笼" → "33367"
        "Оплата за заказ — все товары" → None
    """
    if not title:
        return None
    # 取第一个 - 之前的部分
    prefix = title.split("-")[0].strip()
    if not prefix:
        return None
    # 只取纯数字前缀（offer_id 的前半部分都是数字）
    prefix = re.sub(r"\D", "", prefix)
    return prefix if prefix else None


# ── 同步主函数 ─────────────────────────────────────────────

def sync_advertising(
    db: Session,
    client: OzonPerfClient,
    date_from: str,
    date_to: str,
    store_id: int,
    batch_id: Optional[str] = None,
) -> dict:
    """
    同步广告数据:
      1. 拉取活动列表 → upsert ad_campaigns
      2. 拉取每日统计 → upsert ad_daily_stats
      3. 构建 SKU 映射 → upsert ad_campaign_sku_map
      4. 广告费汇总已移至 build_summary
    """
    logger.info(f"=== [store={store_id}] 开始同步广告数据: {date_from} ~ {date_to} ===")

    if not batch_id:
        batch_id = f"adv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    campaigns_updated = 0
    daily_inserted = 0
    daily_updated = 0
    mappings_created = 0

    # ── 1. 拉取活动列表 ──────────────────────────────────
    try:
        campaigns = client.get_campaigns()
        logger.info(f"[store={store_id}] 获取到 {len(campaigns)} 个广告活动")

        for c in campaigns:
            stmt = pg_insert(AdCampaign).values(
                store_id=store_id,
                campaign_id=c["id"],
                title=c.get("title"),
                campaign_type=c.get("advObjectType", ""),
                state=c.get("state", ""),
                budget=Decimal(str(c.get("budget", 0))),
            ).on_conflict_do_update(
                index_elements=["store_id", "campaign_id"],
                set_={
                    "title": c.get("title"),
                    "campaign_type": c.get("advObjectType", ""),
                    "state": c.get("state", ""),
                    "budget": Decimal(str(c.get("budget", 0))),
                },
            )
            result = db.execute(stmt)
            if result.rowcount:
                campaigns_updated += 1
        db.commit()
        logger.info(f"活动列表同步: {campaigns_updated} 条 upsert")
    except Exception as e:
        logger.error(f"活动列表同步失败: {e}")
        raise

    # ── 2. 拉取每日统计（分片）────────────────────────────
    chunks = _date_range_chunks(date_from, date_to)
    logger.info(f"每日统计: 拆分为 {len(chunks)} 个窗口")

    for i, (chunk_from, chunk_to) in enumerate(chunks, 1):
        try:
            rows = client.get_daily_stats(chunk_from, chunk_to)
            if not rows:
                logger.info(f"  窗口 {i}/{len(chunks)}: 无数据")
                continue
            logger.info(f"  窗口 {i}/{len(chunks)}: {chunk_from[:10]}~{chunk_to[:10]}, {len(rows)} 行")
        except Exception as e:
            logger.error(f"  窗口 {i}/{len(chunks)} 拉取失败: {e}")
            raise

        for row in rows:
            stmt = pg_insert(AdDailyStats).values(
                store_id=store_id,
                campaign_id=row["campaign_id"],
                stat_date=date_type.fromisoformat(row["date"]),
                impressions=row.get("impressions", 0),
                clicks=row.get("clicks", 0),
                spend=Decimal(str(row.get("spend", 0))),
                orders_count=row.get("orders_count", 0),
                orders_sum=Decimal(str(row.get("orders_sum", 0))),
            ).on_conflict_do_update(
                index_elements=["store_id", "campaign_id", "stat_date"],
                set_={
                    "impressions": row.get("impressions", 0),
                    "clicks": row.get("clicks", 0),
                    "spend": Decimal(str(row.get("spend", 0))),
                    "orders_count": row.get("orders_count", 0),
                    "orders_sum": Decimal(str(row.get("orders_sum", 0))),
                },
            )
            result = db.execute(stmt)
            if result.rowcount:
                daily_inserted += 1
            else:
                daily_updated += 1
        db.commit()

    logger.info(f"每日统计同步: {daily_inserted} 新增, {daily_updated} 更新")

    # ── 3. 构建 SKU 映射 ─────────────────────────────────
    try:
        sku_campaigns = db.query(AdCampaign).filter(
            AdCampaign.store_id == store_id,
            AdCampaign.campaign_type == "SKU"
        ).all()
        logger.info(f"SKU 类型活动: {len(sku_campaigns)} 个")

        for campaign in sku_campaigns:
            prefix = _extract_offer_prefix(campaign.title)
            if not prefix:
                logger.warning(f"  无法提取前缀: id={campaign.campaign_id} title={campaign.title!r}")
                continue

            products = db.query(Product).filter(
                Product.store_id == store_id,
                Product.offer_id.like(f"{prefix}-%")
            ).all()

            if not products:
                logger.warning(f"  未匹配到商品: prefix={prefix} campaign_id={campaign.campaign_id}")
                continue

            for p in products:
                stmt = pg_insert(AdCampaignSkuMap).values(
                    store_id=store_id,
                    campaign_id=campaign.campaign_id,
                    sku_id=p.sku_id,
                    offer_id=p.offer_id,
                    mapping_method="auto",
                ).on_conflict_do_nothing(
                    index_elements=["store_id", "campaign_id", "sku_id"],
                )
                result = db.execute(stmt)
                if result.rowcount:
                    mappings_created += 1
        db.commit()
        logger.info(f"SKU 映射创建: {mappings_created} 条")
    except Exception as e:
        logger.error(f"SKU 映射构建失败: {e}")
        raise

    logger.info(
        f"[store={store_id}] 广告同步完成: campaigns={campaigns_updated}, "
        f"daily_inserted={daily_inserted}, daily_updated={daily_updated}, "
        f"mappings={mappings_created}"
    )
    return {
        "campaigns_updated": campaigns_updated,
        "daily_stats_inserted": daily_inserted,
        "daily_stats_updated": daily_updated,
        "sku_mappings_created": mappings_created,
    }


def sync_sku_advertising(
    db: Session,
    client: OzonPerfClient,
    date_from: str,
    date_to: str,
    store_id: int,
) -> dict:
    """同步广告 SKU 日明细（异步报告模式）

    按天请求异步报告（dateFrom=dateTo=当天），获取每个活动的 SKU 级数据:
      展示 / 点击 / CTR / 加购 / CPC / 花费 / 售出 / 销售额 / DRR

    存入 ad_sku_daily_stats，用 on_conflict_do_update 覆写已有数据。
    """
    logger.info(f"=== [store={store_id}] 开始同步广告 SKU 明细: {date_from} ~ {date_to} ===")

    start = datetime.strptime(date_from[:10], "%Y-%m-%d").date()
    end = datetime.strptime(date_to[:10], "%Y-%m-%d").date()
    day_count = (end - start).days + 1
    if day_count > 7:
        logger.warning(f"日期范围 {day_count} 天, 异步报告逐天请求较慢, 建议分批")

    total_inserted = 0
    total_updated = 0

    cur = start
    while cur <= end:
        day_str = cur.isoformat()
        try:
            rows = client.get_sku_daily_stats(day_str, day_str)
            if not rows:
                logger.info(f"  {day_str}: 无 SKU 数据")
                cur += timedelta(days=1)
                continue
            logger.info(f"  {day_str}: {len(rows)} 行 SKU 数据")
        except Exception as e:
            logger.error(f"  {day_str}: 拉取失败 - {e}")
            cur += timedelta(days=1)
            continue

        for row in rows:
            vals = {
                "store_id": store_id,
                "campaign_id": row["campaign_id"],
                "sku_id": row["sku_id"],
                "stat_date": cur,
                "sku_name": row.get("sku_name"),
                "sku_price": _decimal(row.get("sku_price")),
                "impressions": row.get("impressions", 0),
                "clicks": row.get("clicks", 0),
                "ctr": _decimal(row.get("ctr")),
                "add_to_cart": row.get("add_to_cart", 0),
                "avg_cpc": _decimal(row.get("avg_cpc")),
                "spend": _decimal(row.get("spend")),
                "sold_units": row.get("sold_units", 0),
                "sales_promotion": _decimal(row.get("sales_promotion")),
                "total_ordered": _decimal(row.get("total_ordered")),
                "drr_promotion": _decimal(row.get("drr_promotion")),
                "drr_total": _decimal(row.get("drr_total")),
            }
            if row.get("date_added"):
                try:
                    vals["date_added"] = date_type.fromisoformat(row["date_added"])
                except (ValueError, TypeError):
                    pass

            stmt = pg_insert(AdSkuDailyStats).values(**vals).on_conflict_do_update(
                index_elements=["store_id", "campaign_id", "sku_id", "stat_date"],
                set_={
                    "sku_name": vals["sku_name"],
                    "sku_price": vals["sku_price"],
                    "impressions": vals["impressions"],
                    "clicks": vals["clicks"],
                    "ctr": vals["ctr"],
                    "add_to_cart": vals["add_to_cart"],
                    "avg_cpc": vals["avg_cpc"],
                    "spend": vals["spend"],
                    "sold_units": vals["sold_units"],
                    "sales_promotion": vals["sales_promotion"],
                    "total_ordered": vals["total_ordered"],
                    "drr_promotion": vals["drr_promotion"],
                    "drr_total": vals["drr_total"],
                },
            )
            result = db.execute(stmt)
            if result.rowcount:
                total_inserted += 1
            else:
                total_updated += 1

        db.commit()
        cur += timedelta(days=1)

    logger.info(f"[store={store_id}] SKU 明细同步完成: {total_inserted} 新增, {total_updated} 更新")
    return {
        "sku_inserted": total_inserted,
        "sku_updated": total_updated,
    }


def _decimal(val) -> Decimal:
    """安全转为 Decimal, None → 0"""
    if val is None:
        return Decimal("0")
    return Decimal(str(val))
