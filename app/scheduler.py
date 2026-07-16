"""
定时同步调度 — 每天按 .env 配置的时间自动同步最近数据
"""
from datetime import date, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from app.clients.ozon import get_ozon_client
from app.config import settings
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
    """启动定时调度，从 .env 的 SYNC_CRON_HOURS 读取执行时间"""
    hours = [int(h.strip()) for h in settings.sync_cron_hours.split(",") if h.strip().isdigit()]
    if not hours:
        hours = [5, 16]

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
    logger.info(f"定时调度已启动: 每天 {hours} 点同步最近数据")


def stop_scheduler():
    """停止调度"""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("定时调度已停止")
