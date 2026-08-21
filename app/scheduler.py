"""
定时同步调度 — 每天按 .env 配置的时间自动同步所有启用店铺

时间安排:
  5:00  (固定) — 广告 SKU 明细（异步报告极慢，凌晨 Ozon 队列空闲）
  9:00  (.env)  — 全量同步（商品/销售/财务/履约/退货/广告活动级）
  19:00 (.env)  — 全量同步（同上）
  5:00  (固定) — 每日快照（价格+库存 → sku_daily_snapshot，Ozon 莫斯科 24:00 = 北京 5:00）
"""
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.clients.ozon import get_ozon_client
from app.clients.perf import get_perf_client
from app.config import settings
from app.database import SessionLocal
from app.models import Store
from app.services.sync_service import run_full_sync
from app.services.advertising_sync import sync_sku_advertising

scheduler = AsyncIOScheduler()


def daily_snapshot():
    """每日快照: 遍历所有启用店铺，将 products + stocks 快照写入 sku_daily_snapshot
    运行时间: 北京时间 5:00（= 莫斯科 0:00），记录日期 = 莫斯科日期（北京时间 -1 天）"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        stores = db.query(Store).filter_by(is_active=True).all()
        today = date.today() - timedelta(days=1)  # Ozon 莫斯科日期
        for store in stores:
            try:
                result = db.execute(text("""
                    INSERT INTO ozon.sku_daily_snapshot
                        (store_id, sku_id, record_date, offer_id,
                         price, old_price, marketing_seller_price, min_price,
                         green_price, discount_pct,
                         stock_present, stock_reserved, synced_at)
                    SELECT
                        p.store_id, p.sku_id, :today, p.offer_id,
                        p.price, p.old_price, p.marketing_seller_price, p.min_price,
                        m.green_price_rub, m.discount_pct,
                        COALESCE(s.present, 0), COALESCE(s.reserved, 0), now()
                    FROM ozon.products p
                    LEFT JOIN (
                        SELECT store_id, sku_id, SUM(present) AS present, SUM(reserved) AS reserved
                        FROM ozon.stocks GROUP BY store_id, sku_id
                    ) s ON p.store_id = s.store_id AND p.sku_id = s.sku_id
                    LEFT JOIN ozon.sku_management m ON p.store_id = m.store_id AND p.sku_id = m.sku_id
                    WHERE p.store_id = :sid
                    ON CONFLICT (store_id, sku_id, record_date) DO NOTHING
                """), {"today": today, "sid": store.id})
                db.commit()
                logger.info(f"[快照] 店铺 {store.id} ({store.name}): 日期={today} 记录={result.rowcount}")
            except Exception as e:
                logger.error(f"[快照] 店铺 {store.id} 失败: {e}")
                db.rollback()
    except Exception as e:
        logger.error(f"[快照] 调度失败: {e}")
    finally:
        db.close()


def sync_sku_detail():
    """凌晨专用: 遍历所有启用店铺，只拉昨天的 SKU 广告明细"""
    db = SessionLocal()
    try:
        stores = db.query(Store).filter_by(is_active=True).all()
        yesterday = date.today() - timedelta(days=1)
        for store in stores:
            if not store.perf_client_id or not store.perf_client_secret:
                logger.warning(f"店铺 {store.id} ({store.name}) 未配置广告 API，跳过 SKU 明细")
                continue
            try:
                client = get_perf_client(store.perf_client_id, store.perf_client_secret)
                logger.info(f"[SKU明细] 店铺 {store.id} ({store.name}): {yesterday}")
                result = sync_sku_advertising(db, client,
                                              date_from=yesterday.isoformat(),
                                              date_to=yesterday.isoformat(),
                                              store_id=store.id)
                logger.info(f"[SKU明细] 店铺 {store.id}: 完成 {result}")
            except Exception as e:
                logger.error(f"[SKU明细] 店铺 {store.id} 失败: {e}")
            finally:
                client.close()
    except Exception as e:
        logger.error(f"[SKU明细] 调度失败: {e}")
    finally:
        db.close()


def sync_recent_data():
    """全量同步最近 3 天数据（遍历所有启用店铺）"""
    db = SessionLocal()
    try:
        stores = db.query(Store).filter_by(is_active=True).all()
        today = date.today()
        for store in stores:
            try:
                client = get_ozon_client(store.client_id, store.api_key)
                logger.info(f"[定时同步] 店铺 {store.id} ({store.name}): {today - timedelta(days=3)} ~ {today}")
                results = run_full_sync(db, client, store.id, days_back=3)
                logger.info(f"[定时同步] 店铺 {store.id}: 完成 {results}")
            except Exception as e:
                logger.error(f"[定时同步] 店铺 {store.id} 失败: {e}")
            finally:
                client.close()
    except Exception as e:
        logger.error(f"[定时同步] 调度失败: {e}")
    finally:
        db.close()


def start_scheduler():
    """启动定时调度"""
    # 凌晨 5:00 — SKU 广告明细（固定，不通过 .env 配置）
    scheduler.add_job(
        sync_sku_detail,
        trigger="cron",
        hour=5,
        minute=0,
        id="sku_detail_at_05h",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # 每天 5:00 — 价格+库存每日快照（Ozon 莫斯科 24:00 = 北京 5:00）
    scheduler.add_job(
        daily_snapshot,
        trigger="cron",
        hour=5,
        minute=0,
        id="daily_snapshot_at_05h",
        replace_existing=True,
        misfire_grace_time=600,
    )

    # 白天同步时间点 — 从 .env 读取（默认 9:00 和 19:00）
    hours = [int(h.strip()) for h in settings.sync_cron_hours.split(",") if h.strip().isdigit()]
    if not hours:
        hours = [9, 19]

    for hour in hours:
        scheduler.add_job(
            sync_recent_data,
            trigger="cron",
            hour=hour,
            minute=0,
            id=f"daily_sync_at_{hour:02d}h",
            replace_existing=True,
            misfire_grace_time=600,
        )

    scheduler.start()
    logger.info(f"定时调度已启动: SKU明细=5:00, 全量同步={hours}，覆盖所有启用店铺")


def stop_scheduler():
    """停止调度"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时调度已停止")
