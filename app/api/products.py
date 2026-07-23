"""商品 API"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, Stock
from app.schemas.product import ProductItem

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductItem])
def list_products(
    store_id: int = Query(default=1, description="店铺 ID"),
    db: Session = Depends(get_db),
):
    """获取所有商品（含当前库存快照，来自 stocks 表）"""
    stock_sub = (
        db.query(
            Stock.sku_id,
            func.coalesce(func.sum(Stock.present), 0).label("present"),
            func.coalesce(func.sum(Stock.reserved), 0).label("reserved"),
        )
        .filter(Stock.store_id == store_id)
        .group_by(Stock.sku_id)
        .subquery()
    )

    rows = (
        db.query(
            Product,
            func.coalesce(stock_sub.c.present, 0).label("stock_present"),
            func.coalesce(stock_sub.c.reserved, 0).label("stock_reserved"),
        )
        .filter(Product.store_id == store_id)
        .outerjoin(stock_sub, Product.sku_id == stock_sub.c.sku_id)
        .order_by(Product.name)
        .all()
    )

    result = []
    for p, sp, sr in rows:
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
        )
        result.append(item)
    return result
