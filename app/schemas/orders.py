"""订单分析 API 响应模型"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class OrderOverview(BaseModel):
    """订单总览"""
    model_config = ConfigDict(ser_json_decimal='number')

    total_orders: int
    fbo_count: int
    fbs_count: int
    delivered_count: int
    cancelled_count: int
    in_progress_count: int
    total_ordered_units: int
    cancellation_rate: float
    avg_items_per_order: float | None


class OrderTrendItem(BaseModel):
    """订单趋势 — 单日数据点"""
    date: date
    ordered: int
    delivered: int
    cancelled: int


class OrderListItem(BaseModel):
    """订单列表项 — 一行一个 posting"""
    posting_number: str
    order_number: str | None = None
    delivery_schema: str | None = None
    status: str | None = None
    created_at: datetime | None = None
    delivered_at: datetime | None = None
    in_process_at: datetime | None = None
    product_count: int = 0
    total_quantity: int = 0
    total_price: float = 0.0


class OrderListResponse(BaseModel):
    """订单列表分页响应"""
    items: list[OrderListItem]
    total: int
    page: int
    page_size: int


class OrderProduct(BaseModel):
    """订单中的单个商品"""
    sku: int | None = None
    name: str | None = None
    quantity: int = 0
    offer_id: str | None = None
    price: float = 0.0


class OrderReturn(BaseModel):
    """关联的退货记录"""
    id: int
    sku: int
    type: str
    return_reason_name: str | None = None
    quantity: int = 0
    visual_status: str
    returned_at: datetime | None = None
    finished_at: datetime | None = None


class OrderFinance(BaseModel):
    """关联的财务流水"""
    operation_id: int
    operation_type_name: str | None = None
    type: str | None = None
    operation_date: date
    amount: float = 0.0


class OrderDetail(BaseModel):
    """订单详情"""
    posting_number: str
    order_number: str | None = None
    delivery_schema: str | None = None
    status: str | None = None
    cancel_reason_id: int = 0
    created_at: datetime | None = None
    in_process_at: datetime | None = None
    delivered_at: datetime | None = None
    products: list[OrderProduct] = []
    returns: list[OrderReturn] = []
    finance_transactions: list[OrderFinance] = []
