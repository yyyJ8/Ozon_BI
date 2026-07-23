"""
定时同步调度 — 每天按 .env 配置的时间自动同步最近数据

时间安排:
  5:00  (固定) — 广告 SKU 明细（异步报告极慢，凌晨 Ozon 队列空闲）
  9:00  (.env)  — 全量同步（商品/销售/财务/履约/退货/广告活动级）
  16:00 (.env)  — 全量同步（同上）
"""
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.clients.ozon import get_ozon_client
from app.clients.perf import get_perf_client
from app.config import settings
from app.database import SessionLocal
from app.services.sync_service import run_full_sync
from app.services.advertising_sync import sync_sku_advertising

scheduler = AsyncIOScheduler()


def sync_sku_detail():
    """凌晨专用: 只拉昨天的 SKU 广告明细"""
    db = SessionLocal()
    client = get_perf_client()
    try:
        yesterday = date.today() - timedelta(days=1)
        logger.info(f"[SKU明细] 开始同步: {yesterday}")
        result = sync_sku_advertising(db, client,
                                      date_from=yesterday.isoformat(),
                                      date_to=yesterday.isoformat())
        logger.info(f"[SKU明细] 完成: {result}")
    except Exception as e:
        logger.error(f"[SKU明细] 失败: {e}")
    finally:
        client.close()
        db.close()


def sync_recent_data():
    """全量同步最近 3 天数据（不含 SKU 广告明细，那部分凌晨已跑）"""
    db = SessionLocal()
    client = get_ozon_client()
    try:
        today = date.today()
        logger.info(f"[定时同步] 开始 ({today - timedelta(days=3)} ~ {today})")
        results = run_full_sync(db, client, days_back=3)
        logger.info(f"[定时同步] 完成: {results}")
    except Exception as e:
        logger.error(f"[定时同步] 失败: {e}")
    finally:
        client.close()
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

    # 白天同步时间点 — 从 .env 读取（默认 9:00 和 16:00）
    hours = [int(h.strip()) for h in settings.sync_cron_hours.split(",") if h.strip().isdigit()]
    if not hours:
        hours = [9, 16]

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
    logger.info(f"定时调度已启动: SKU明细=5:00, 全量同步={hours}")


def stop_scheduler():
    """停止调度"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时调度已停止")
