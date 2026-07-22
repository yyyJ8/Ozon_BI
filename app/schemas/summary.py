"""SKU 日汇总响应模型"""
from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class SummaryItem(BaseModel):
    """单条日汇总"""
    model_config = ConfigDict(from_attributes=True, ser_json_decimal='number')

    date: date
    sku_id: int
    offer_id: Optional[str] = None
    name: Optional[str] = None          # 来自 products 表
    primary_image: Optional[str] = None # 主图 URL
    stock_present: int = 0              # 当前库存总量（FBO+FBS）
    stock_reserved: int = 0             # 已预留库存
    ordered_units: int = 0
    delivered_units: int = 0
    cancelled_units: int = 0
    revenue: Decimal = Decimal("0")
    returns_amount: Decimal = Decimal("0")
    returns_units: int = 0
    commissions: Decimal = Decimal("0")
    logistics_costs: Decimal = Decimal("0")
    storage_fees: Decimal = Decimal("0")
    advertising: Decimal = Decimal("0")
    promotion_costs: Decimal = Decimal("0")
    other_costs: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    profit_margin: Decimal = Decimal("0")
    data_quality: str = "partial"


class SummaryStats(BaseModel):
    """看板顶部汇总卡"""
    model_config = ConfigDict(ser_json_decimal='number')

    total_revenue: Decimal = Decimal("0")
    total_net_profit: Decimal = Decimal("0")
    avg_profit_margin: Decimal = Decimal("0")
    total_ordered_units: int = 0
    total_delivered_units: int = 0
    total_cancelled_units: int = 0
    total_commissions: Decimal = Decimal("0")
    total_logistics: Decimal = Decimal("0")
    total_returns: Decimal = Decimal("0")
    total_returns_units: int = 0
    total_storage: Decimal = Decimal("0")
    total_advertising: Decimal = Decimal("0")
    total_promotion: Decimal = Decimal("0")
    total_other_costs: Decimal = Decimal("0")
    day_count: int = 0
    sku_count: int = 0


class DateRange(BaseModel):
    """数据可用日期范围"""
    min_date: date
    max_date: date
