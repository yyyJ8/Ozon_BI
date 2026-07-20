"""同步控制 API"""
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.clients.ozon import get_ozon_client
from app.database import get_db
from app.models import SyncLog
from app.services.sync_service import run_full_sync

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("")
def trigger_sync(db: Session = Depends(get_db)):
    """触发全量同步"""
    client = get_ozon_client()
    try:
        results = run_full_sync(db, client)
        return {"status": "completed", "results": results}
    finally:
        client.close()


@router.get("/status")
def sync_status(db: Session = Depends(get_db)):
    """最近一次同步状态"""
    last = db.query(SyncLog).order_by(SyncLog.started_at.desc()).first()
    if not last:
        return {"status": "never_run"}

    # 每个 sync_type 的最新一条
    latest_per_type = {}
    for st in ["products", "analytics", "finance", "postings", "returns", "advertising", "ad_sku_daily", "summary"]:
        row = db.query(SyncLog).filter(
            SyncLog.sync_type == st,
        ).order_by(SyncLog.started_at.desc()).first()
        if row:
            latest_per_type[st] = {
                "status": row.status,
                "started_at": row.started_at.isoformat(),
                "records": row.records_processed,
                "error": row.error_message,
            }

    return {
        "status": last.status,
        "last_sync": last.started_at.isoformat() if last.started_at else None,
        "details": latest_per_type,
    }
