"""同步控制 API"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SyncLog
from app.services.sync_service import sync_all_stores

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("")
def trigger_sync(
    store_id: Optional[int] = Query(default=None, description="指定店铺 ID，不传则同步全部"),
    skip_sku_detail: bool = Query(default=True, description="跳过广告 SKU 明细（避免 429，凌晨 5 点定时跑）"),
    db: Session = Depends(get_db),
):
    """触发全量同步"""
    if store_id is not None:
        from app.clients.ozon import get_ozon_client
        from app.models import Store
        from app.services.sync_service import run_full_sync
        store = db.query(Store).filter_by(id=store_id).first()
        if not store:
            return {"status": "error", "message": f"店铺 {store_id} 不存在"}
        client = get_ozon_client(store.client_id, store.api_key)
        try:
            results = run_full_sync(db, client, store_id, skip_sku_detail=skip_sku_detail)
            return {"status": "completed", "store_id": store_id, "results": results}
        finally:
            client.close()
    else:
        results = sync_all_stores(db, skip_sku_detail=skip_sku_detail)
        return {"status": "completed", "results": results}


@router.get("/status")
def sync_status(
    store_id: int = Query(default=1, description="店铺 ID"),
    db: Session = Depends(get_db),
):
    """最近一次同步状态"""
    last = db.query(SyncLog).filter(
        SyncLog.store_id == store_id,
    ).order_by(SyncLog.started_at.desc()).first()
    if not last:
        return {"status": "never_run"}

    latest_per_type = {}
    for st in ["products", "analytics", "finance", "postings", "returns", "advertising", "ad_sku_daily", "summary"]:
        row = db.query(SyncLog).filter(
            SyncLog.store_id == store_id,
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
