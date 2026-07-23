"""库存 API — 状态查询 + 实时刷新"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import get_ozon_client
from app.database import get_db
from app.models import Stock, Store

router = APIRouter(prefix="/stocks", tags=["stocks"])

STORE_ID = Query(default=1, description="店铺 ID")


class StockStatus(BaseModel):
    last_updated: datetime | None
    stock_count: int

    model_config = {"from_attributes": True}


class StockRefreshResult(BaseModel):
    ok: bool
    stock_count: int
    last_updated: datetime | None
    message: str

    model_config = {"from_attributes": True}


@router.get("/status", response_model=StockStatus)
def stock_status(
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """返回 stocks 表最后更新时间 + 记录数"""
    last = db.query(func.max(Stock.updated_at)).filter(
        Stock.store_id == store_id,
    ).scalar()
    count = db.query(func.count(Stock.sku_id)).filter(
        Stock.store_id == store_id,
    ).scalar()
    return StockStatus(last_updated=last, stock_count=count or 0)


@router.post("/refresh", response_model=StockRefreshResult)
def refresh_stocks(
    store_id: int = STORE_ID,
    db: Session = Depends(get_db),
):
    """实时从 Ozon v4 API 拉取库存并更新 stocks 表"""
    store = db.query(Store).filter_by(id=store_id).first()
    if not store:
        return StockRefreshResult(
            ok=False, stock_count=0, last_updated=None,
            message=f"店铺 {store_id} 不存在",
        )

    client = get_ozon_client(store.client_id, store.api_key)
    now = datetime.now()

    all_items: list[dict] = []
    cursor = ""
    try:
        while True:
            resp = client._request("/v4/product/info/stocks", {
                "filter": {"visibility": "ALL"},
                "limit": 1000,
                "cursor": cursor,
            })
            items = resp.get("items", [])
            all_items.extend(items)
            cursor = resp.get("cursor", "")
            if not cursor or not items:
                break
    except Exception as e:
        return StockRefreshResult(
            ok=False, stock_count=0, last_updated=None,
            message=f"Ozon API 调用失败: {e}",
        )

    upserted = 0
    for item in all_items:
        for s in item.get("stocks", []):
            sku_id = s.get("sku")
            if not sku_id:
                continue
            source = s.get("type", "fbo")
            s_data = {
                "store_id": store_id,
                "sku_id": int(sku_id),
                "source": source,
                "present": s.get("present", 0) or 0,
                "reserved": s.get("reserved", 0) or 0,
                "updated_at": now,
            }
            stmt = pg_insert(Stock).values(**s_data).on_conflict_do_update(
                index_elements=["store_id", "sku_id", "source"],
                set_={"present": s_data["present"], "reserved": s_data["reserved"], "updated_at": now},
            )
            db.execute(stmt)
            upserted += 1

    db.commit()

    return StockRefreshResult(
        ok=True, stock_count=upserted, last_updated=now,
        message=f"已从 Ozon 同步 {upserted} 条库存记录",
    )
