"""广告 API 响应模型"""
from datetime import date
from decimal import Decimal
from typing import Annotated, Optional, Union

from pydantic import BaseModel, BeforeValidator, ConfigDict, PlainSerializer


def _to_float(v: object) -> float:
    """Decimal / str → float"""
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, str):
        return float(v)
    return float(v)  # type: ignore[arg-type]


# 前端需要 JSON number，所以响应中将 Decimal 序列化为 float
Money = Annotated[
    float,
    BeforeValidator(_to_float),
    PlainSerializer(lambda v: float(v) if isinstance(v, Decimal) else v, return_type=float),
]


class AdCampaignItem(BaseModel):
    """广告活动 + 汇总统计"""
    model_config = ConfigDict(from_attributes=True)

    campaign_id: str
    title: Optional[str] = None
    campaign_type: str
    state: str
    budget: Money = 0.0
    total_spend: Money = 0.0               # 期内总花费（正数）
    total_orders: int = 0                   # 期内总订单数
    total_orders_sum: Money = 0.0           # 期内订单总额
    total_impressions: int = 0              # 期内总展示量
    total_clicks: int = 0                   # 期内总点击量
    mapped_sku_id: Optional[int] = None     # 关联的 SKU（如有）
    mapped_offer_id: Optional[str] = None   # 关联的 offer_id（如有）


class AdDailyStatItem(BaseModel):
    """某活动单日统计"""
    model_config = ConfigDict(from_attributes=True)

    stat_date: date
    impressions: int = 0
    clicks: int = 0
    spend: Money = 0.0               # 当日花费
    orders_count: int = 0
    orders_sum: Money = 0.0


class AdSkuDailyItem(BaseModel):
    """某 SKU 每日广告费"""
    model_config = ConfigDict(from_attributes=True)

    stat_date: date
    spend: Money = 0.0               # 当日广告费（正数）
    campaign_count: int = 0           # 有几个活动为该 SKU 贡献


class AdSummary(BaseModel):
    """广告总览"""
    model_config = ConfigDict(from_attributes=True)

    total_spend: Money = 0.0                  # 总花费
    total_orders_count: int = 0                # 总广告订单数
    total_orders_sum: Money = 0.0              # 总广告订单金额
    total_impressions: int = 0                 # 总展示量
    total_clicks: int = 0                      # 总点击量
    by_type: dict = {}                         # {"SKU": {"spend": X, "count": N, "orders_sum": Y}, ...}
    unmapped_spend: Money = 0.0                # SEARCH_PROMO 等无法关联 SKU 的花费
    mapped_spend: Money = 0.0                  # 已关联到 SKU 的花费
    campaign_count: int = 0                    # 活动总数
    active_campaign_count: int = 0             # 运行中活动数
    mapped_sku_count: int = 0                  # 已关联的 SKU 数量


class AdSkuDetailItem(BaseModel):
    """某 SKU 单日广告明细（含 CTR / CPC / 加购等）"""
    model_config = ConfigDict(from_attributes=True)

    stat_date: date
    campaign_id: str
    sku_name: Optional[str] = None
    sku_price: Optional[Money] = None
    impressions: int = 0
    clicks: int = 0
    ctr: Optional[float] = None
    add_to_cart: int = 0
    avg_cpc: Optional[float] = None
    spend: Money = 0.0
    sold_units: int = 0
    sales_promotion: Optional[Money] = None
    drr_promotion: Optional[float] = None
    drr_total: Optional[float] = None


class AdTrendItem(BaseModel):
    """广告每日趋势"""
    date: date
    spend: Money = 0.0
    impressions: int = 0
    clicks: int = 0
    orders_count: int = 0
    orders_sum: Money = 0.0
    mapped_spend: Money = 0.0
