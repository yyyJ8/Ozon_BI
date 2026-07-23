"""
定时同步调度 — 每天按 .env 配置的时间自动同步所有启用店铺

时间安排:
  5:00  (固定) — 广告 SKU 明细（异步报告极慢，凌晨 Ozon 队列空闲）
  9:00  (.env)  — 全量同步（商品/销售/财务/履约/退货/广告活动级）
  19:00 (.env)  — 全量同步（同上）
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
