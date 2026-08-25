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


# ── 真实利润（含采购成本 + 头程费用）────────────────────────────


class RealProfitOverview(BaseModel):
    """含采购成本 + 头程费用的真实利润总览"""
    model_config = ConfigDict(ser_json_decimal='number')

    # Ozon 平台 P&L（继承自 ProfitOverview）
    revenue: float
    net_profit: float                    # 平台毛利
    profit_margin: float                 # 平台利润率
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
    # 采购成本（单价 × 销量）
    total_purchase_cost_rmb: float       # 采购总成本 (RMB)
    total_purchase_cost_rub: float       # 采购总成本 (₽)
    sku_with_purchase_cost: int          # 有采购单价的 SKU 数
    # 头程费用（单价 × 销量）
    total_first_leg_cost_rmb: float      # 头程总成本 (RMB)
    total_first_leg_cost_rub: float      # 头程总成本 (₽)
    sku_with_first_leg_cost: int         # 有头程单价的 SKU 数
    # 真实利润
    real_net_profit: float               # 真实净利润 = 平台净利 - 采购₽ - 头程₽
    real_profit_margin: float            # 真实利润率


class RealProfitSkuItem(BaseModel):
    """含采购成本 + 头程费用的 SKU 利润排行"""
    sku_id: int
    offer_id: Optional[str] = None
    name: Optional[str] = None
    primary_image: Optional[str] = None
    # 平台 P&L
    revenue: float = 0
    costs: float = 0
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
    stock_present: int = 0
    stock_reserved: int = 0
    # 采购成本（单价）
    purchase_cost_rmb: float = 0         # 采购单价 (RMB/件)
    exchange_rate: float = 0             # 使用的汇率
    has_purchase_cost: bool = False      # 是否已有采购单价
    # 头程费用（单价）
    first_leg_cost_rmb: float = 0        # 头程单价 (RMB/件)
    has_first_leg_cost: bool = False     # 是否已有头程单价
    # 真实利润
    real_net_profit: float = 0           # 真实净利润 = 平台净利 - (采购+头程)单价×销量×汇率
    real_profit_margin: float = 0        # 真实利润率


class RealProfitDailyItem(BaseModel):
    """含采购成本 + 头程费用的单 SKU 每日利润明细"""
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
    # 采购成本 + 头程（按收入占比分摊到日）
    purchase_cost_rub: float = 0         # 当日摊采购成本 (₽)
    first_leg_cost_rub: float = 0        # 当日摊头程成本 (₽)
    has_purchase_cost: bool = False
    has_first_leg_cost: bool = False
    real_net_profit: float = 0
    real_profit_margin: float = 0
