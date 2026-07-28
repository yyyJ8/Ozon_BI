"""异常检测 API 响应模型"""
from typing import Optional

from pydantic import BaseModel


class AnomalyItem(BaseModel):
    """单条异常记录"""
    sku_id: int
    offer_id: Optional[str] = None
    name: Optional[str] = None
    primary_image: Optional[str] = None
    anomaly_type: str              # 规则名称，如 "SKU退货异常"
    severity: str                  # "critical" | "warning" | "info"
    description: str               # 规则描述，如 "退货≥4件 且 月订单≥20单"
    metrics: dict[str, float]      # 触发时的实际指标值 {"returns_units": 5, "ordered_units": 25}
    triggered_conditions: list[str]  # 命中的条件表达式 ["returns_units >= 4", "ordered_units >= 20"]


class AnomalySummary(BaseModel):
    """异常汇总统计"""
    total_anomalies: int
    by_type: dict[str, int]        # {"SKU退货异常": 3, ...}


class AnomalyResponse(BaseModel):
    """完整异常检测响应"""
    summary: AnomalySummary
    items: list[AnomalyItem]
