"""库存 API — 状态查询 + 实时刷新"""
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.clients.ozon import get_ozon_client
from app.database import get_db
from app.models import Stock

router = APIRouter(prefix="/stocks", tags=["stocks"])


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
def stock_status(db: Session = Depends(get_db)):
    """返回 stocks 表最后更新时间 + 记录数"""
    last = db.query(func.max(Stock.updated_at)).scalar()
    count = db.query(func.count(Stock.sku_id)).scalar()
    return StockStatus(last_updated=last, stock_count=count or 0)


@router.post("/refresh", response_model=StockRefreshResult)
def refresh_stocks(db: Session = Depends(get_db)):
    """实时从 Ozon v4 API 拉取库存并更新 stocks 表"""
    client = get_ozon_client()
    now = datetime.now()

    # 全量拉取 /v4/product/info/stocks
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

    # Upsert stocks 表: v4 返回 stocks[].sku 是真正的 SKU ID
    upserted = 0
    for item in all_items:
        for s in item.get("stocks", []):
            sku_id = s.get("sku")
            if not sku_id:
                continue
            source = s.get("type", "fbo")
            s_data = {
                "sku_id": int(sku_id),
                "source": source,
                "present": s.get("present", 0) or 0,
                "reserved": s.get("reserved", 0) or 0,
                "updated_at": now,
            }
            stmt = pg_insert(Stock).values(**s_data).on_conflict_do_update(
                index_elements=["sku_id", "source"],
                set_={"present": s_data["present"], "reserved": s_data["reserved"], "updated_at": now},
            )
            db.execute(stmt)
            upserted += 1

    db.commit()

    return StockRefreshResult(
        ok=True, stock_count=upserted, last_updated=now,
        message=f"已从 Ozon 同步 {upserted} 条库存记录",
    )
