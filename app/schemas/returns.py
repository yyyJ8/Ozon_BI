"""退货分析 API 响应模型"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ReturnsOverview(BaseModel):
    """退货总览"""
    model_config = ConfigDict(ser_json_decimal='number')

    total_returns: int
    cancellation_count: int
    client_return_count: int
    by_status: dict[str, int]
    return_rate: float
    avg_processing_days: float | None


class ReturnsTrendItem(BaseModel):
    """退货趋势 — 单日数据点"""
    date: date
    cancellation: int
    client_return: int
    total: int


class SkuReturnStats(BaseModel):
    """SKU 退货明细"""
    sku_id: int
    offer_id: str | None = None
    name: str | None = None
    primary_image: str | None = None
    total_returns: int
    cancellation_count: int            # 取消退回
    client_return_count: int           # 签收后退货
    fbo_count: int = 0                 # FBO 退货
    fbs_count: int = 0                 # FBS 退货
    completed_count: int = 0           # 已完结（有 finished_at）
    pending_count: int = 0             # 处理中（无 finished_at）
    total_return_price: float = 0.0    # 退货商品总价值 RUB
    ordered_units: int = 0             # 同期下单总件数（分母）
    return_rate: float
    main_reason: str | None = None
    avg_processing_days: float | None = None


class ReasonItem(BaseModel):
    """退货原因分布"""
    reason_name: str
    reason_cn: str
    type: str
    count: int


class ReturnDetailItem(BaseModel):
    """单条退货记录 — 用于 SKU 明细表的行展开"""
    model_config = ConfigDict(ser_json_decimal='number')

    id: int                              # 退货 ID
    posting_number: str                  # 订单号
    sku: int                             # SKU
    product_name: str | None = None      # 商品名（JOIN products）
    offer_id: str | None = None          # offer_id（JOIN products）
    primary_image: str | None = None     # 商品图（JOIN products）
    type: str                            # Cancellation / ClientReturn
    return_reason_name: str | None = None   # 俄文原因原文
    reason_cn: str | None = None         # 中文翻译
    quantity: int = 0                    # 退货件数
    price: float | None = None           # 退货金额 RUB
    visual_status: str                   # 状态
    delivery_schema: str                          # Fbo / Fbs
    returned_at: datetime | None = None  # 退货发起时间
    finished_at: datetime | None = None  # 完结时间
    status_changed_at: datetime | None = None  # 最后状态变更时间
    processing_days: float | None = None # 处理天数
