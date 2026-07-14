"""商品响应模型"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductItem(BaseModel):
    """商品列表项（供筛选器使用）"""
    model_config = ConfigDict(from_attributes=True, ser_json_decimal='number')

    sku_id: int
    name: Optional[str] = None
    offer_id: Optional[str] = None
    price: Optional[Decimal] = None
    status: Optional[str] = None
    category_id: Optional[int] = None
