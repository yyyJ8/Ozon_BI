"""
定时同步调度 — 每天 5:00 和 16:00 自动同步最近 3 天数据
"""
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.clients.ozon import get_ozon_client
from app.database import SessionLocal
from app.services.sync_service import run_full_sync

scheduler = AsyncIOScheduler()


def sync_recent_data():
    """同步最近 3 天的数据（用于每日定时任务）"""
    db = SessionLocal()
    client = get_ozon_client()
    try:
        today = date.today()
        logger.info(f"[定时同步] 开始同步最近数据 ({today - timedelta(days=3)} ~ {today})")
        results = run_full_sync(db, client, days_back=3)
        logger.info(f"[定时同步] 完成: {results}")
    except Exception as e:
        logger.error(f"[定时同步] 失败: {e}")
    finally:
        client.close()
        db.close()


def start_scheduler():
    """启动定时调度，每天 5:00 和 16:00 执行同步"""
    scheduler.add_job(
        sync_recent_data,
        trigger="cron",
        hour=5,
        minute=0,
        id="daily_sync_at_5am",
        replace_existing=True,
        misfire_grace_time=600,
    )
    scheduler.add_job(
        sync_recent_data,
        trigger="cron",
        hour=16,
        minute=0,
        id="daily_sync_at_4pm",
        replace_existing=True,
        misfire_grace_time=600,
    )
    scheduler.start()
    logger.info("定时调度已启动: 每天 5:00、16:00 同步最近数据")


def stop_scheduler():
    """停止调度"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时调度已停止")
