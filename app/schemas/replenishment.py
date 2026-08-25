"""补货提示 schema"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class ReplenishmentConfigItem(BaseModel):
    """补货配置行"""
    store_id: int
    offer_id: str
    product_name: Optional[str] = None
    safety_days: int = 5
    logistics_days: int = 45


class ReplenishmentRow(BaseModel):
    """补货提示完整行（含公式计算结果）"""
    store_id: int
    sku_id: int
    offer_id: str
    product_name: Optional[str] = None
    primary_image: Optional[str] = None

    # 基础信息
    store_name: Optional[str] = None
    product_status: Optional[str] = None
    sales_manager: Optional[str] = None

    # 输入数据
    stock_present: int = 0
    sales_3d: int = 0
    sales_7d: int = 0
    sales_14d: int = 0
    sales_30d: int = 0
    cross_border_sdk: int = 0
    cross_border_yunmeng: int = 0
    cross_border_kunlun: int = 0
    cross_border_cgs: int = 0
    domestic_in_transit: int = 0
    safety_days: int = 5
    logistics_days: int = 45

    # 公式中间结果
    weighted_daily_sales: float = 0.0
    cross_border_total: int = 0

    # 最终结果
    replenishment_qty_raw: float = 0.0
    suggested_replenishment: str = "♥☺♥"  # "♥☺♥" 或数字字符串
    available_days: Optional[float] = None
    alert_level: str = "normal"  # emergency / warning / normal
    configured: bool = False  # 是否已配置安全/物流天数

    model_config = {"from_attributes": True}
