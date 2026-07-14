"""商品 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.product import ProductItem

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=list[ProductItem])
def list_products(db: Session = Depends(get_db)):
    """获取所有商品（用于 SKU 筛选器）"""
    products = db.query(Product).order_by(Product.name).all()
    return products
