"""商品 API"""
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Stock, SkuDailySnapshot
from app.schemas.product import ProductItem

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductItem])
def list_products(
    store_id: int = Query(default=1, description="店铺 ID，0=全部店铺"),
    db: Session = Depends(get_db),
):
    """获取所有商品（含当前库存快照，来自 stocks 表）

    stock_month_start: 月初库存，取当月 1 号的 sku_daily_snapshot.stock_present；
    该 SKU 月初无快照（如月初尚未上架）时为 NULL（前端显示空值）。
    """
    stock_q = (
        db.query(
            Stock.sku_id,
            func.coalesce(func.sum(Stock.present), 0).label("present"),
            func.coalesce(func.sum(Stock.reserved), 0).label("reserved"),
        )
    )
    if store_id != 0:
        stock_q = stock_q.filter(Stock.store_id == store_id)
    stock_sub = stock_q.group_by(Stock.sku_id).subquery()

    # 月初库存 = 当月 1 号的每日快照 stock_present（莫斯科日口径）
    month_start = date.today().replace(day=1)
    month_q = db.query(
        SkuDailySnapshot.sku_id,
        func.sum(SkuDailySnapshot.stock_present).label("stock_month_start"),
    )
    if store_id != 0:
        month_q = month_q.filter(SkuDailySnapshot.store_id == store_id)
    month_q = month_q.filter(SkuDailySnapshot.record_date == month_start).group_by(SkuDailySnapshot.sku_id)
    month_sub = month_q.subquery()

    prod_q = db.query(
        Product,
        func.coalesce(stock_sub.c.present, 0).label("stock_present"),
        func.coalesce(stock_sub.c.reserved, 0).label("stock_reserved"),
        month_sub.c.stock_month_start,
    )
    if store_id != 0:
        prod_q = prod_q.filter(Product.store_id == store_id)
    rows = (
        prod_q.outerjoin(stock_sub, Product.sku_id == stock_sub.c.sku_id)
        .outerjoin(month_sub, Product.sku_id == month_sub.c.sku_id)
        .order_by(Product.name)
        .all()
    )

    result = []
    for p, sp, sr, sms in rows:
        item = ProductItem(
            sku_id=p.sku_id,
            name=p.name,
            offer_id=p.offer_id,
            price=p.price,
            status=p.status,
            category_id=p.category_id,
            primary_image=p.primary_image,
            commission_fbo_pct=p.commission_fbo_pct,
            stock_present=int(sp),
            stock_reserved=int(sr),
            stock_month_start=int(sms) if sms is not None else None,
        )
        result.append(item)
    return result
