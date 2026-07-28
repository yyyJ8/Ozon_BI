"""利润分析 API 响应模型 — 从原始表直接聚合，独立于 sku_daily_summary"""
from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProfitOverview(BaseModel):
    """利润总览 KPI"""
    model_config = ConfigDict(ser_json_decimal='number')

    revenue: float
    net_profit: float
    profit_margin: float
    total_costs: float
    total_commissions: float
    total_logistics: float
    total_storage: float
    total_advertising: float
    total_promotion: float
    total_returns: float
    total_other: float
    ordered_units: int
    sku_count: int
    day_count: int


class ProfitTrendItem(BaseModel):
    """利润趋势 — 单日数据点"""
    date: date
    revenue: float
    costs: float               # 总费用（正数，方便图表展示）
    net_profit: float
    profit_margin: float
    commissions: float = 0
    logistics_costs: float = 0
    storage_fees: float = 0
    advertising: float = 0
    promotion_costs: float = 0
    returns_amount: float = 0
    other_costs: float = 0


class ProfitSkuItem(BaseModel):
    """SKU 利润排行 — 单商品聚合"""
    sku_id: int
    offer_id: Optional[str] = None
    name: Optional[str] = None
    primary_image: Optional[str] = None
    revenue: float = 0
    costs: float = 0             # 总费用（正数）
    net_profit: float = 0
    profit_margin: float = 0
    ordered_units: int = 0
    commissions: float = 0
    logistics_costs: float = 0
    storage_fees: float = 0
    advertising: float = 0
    promotion_costs: float = 0
    returns_amount: float = 0
    other_costs: float = 0
    stock_present: int = 0       # 从 products 表取
    stock_reserved: int = 0


class ProfitDailyItem(BaseModel):
    """单 SKU 每日利润明细（下钻用）"""
    date: date
    revenue: float = 0
    costs: float = 0
    net_profit: float = 0
    profit_margin: float = 0
    commissions: float = 0
    logistics_costs: float = 0
    storage_fees: float = 0
    advertising: float = 0
    promotion_costs: float = 0
    returns_amount: float = 0
    other_costs: float = 0
