"""商品响应模型"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class ProductItem(BaseModel):
    """商品列表项（供筛选器使用）"""
    sku_id: int
    name: Optional[str] = None
    offer_id: Optional[str] = None
    price: Optional[Decimal] = None
    status: Optional[str] = None
    category_id: Optional[int] = None

    class Config:
        from_attributes = True
