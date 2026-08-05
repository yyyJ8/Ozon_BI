"""供应链 SKU 聚合视图 — 申购→采购→发货 三阶段流水线"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SkuPipelineItem(BaseModel):
    """一行一个 SKU，聚合三阶段数据"""
    item_id: str                              # SKU编码
    seller_sku: str | None = None
    main_sku_id: str | None = None
    warehouse_item_code: str | None = None

    # 申购阶段
    plan_count: int = 0                       # 关联申购单数
    total_plan_qty: float = 0.0               # 计划总数
    total_ordered_qty: float = 0.0            # 已下单总数 (already_qty)
    plan_status_summary: str = ""             # 申购状态汇总
    latest_plan_no: str | None = None         # 最新申购单号

    # 采购阶段
    order_count: int = 0                      # 关联采购单数
    total_order_qty: float = 0.0              # 采购总数
    total_receipt_qty: float = 0.0            # 已收货总数
    order_status_summary: str = ""            # 采购状态汇总

    # 发货阶段
    shipping_count: int = 0                   # 关联发货单数
    total_shipped_qty: float = 0.0            # 已发货总数
    total_inbound_qty: float = 0.0            # 海外仓上架总数
    shipping_status_summary: str = ""         # 发货状态汇总

    # 元数据
    marketplace: str | None = None            # 站点
    expect_date: str | None = None            # 最早期望交期
    latest_update: str | None = None          # 最新更新时间


class SkuPipelineListResponse(BaseModel):
    items: list[SkuPipelineItem]
    total: int
    page: int
    page_size: int


# ── 详情：单个 SKU 展开三阶段明细 ──

class PlanStage(BaseModel):
    po_plan_no: str
    status: str | None = None
    status_label: str = ""
    plan_qty: float = 0.0
    already_qty: float = 0.0
    direct_ship_arrival_qty: float = 0.0
    expect_date: str | None = None
    wms_rec_qty: float = 0.0
    wms_onstock_qty: float = 0.0
    create_time: str | None = None


class OrderStage(BaseModel):
    po_no: str
    po_plan_no: str | None = None
    status: str | None = None
    status_label: str = ""
    qty: float = 0.0
    receipt_qty: float = 0.0
    price: float = 0.0
    untaxed_amount: float = 0.0
    expect_receipt_date: str | None = None
    create_time: str | None = None


class ShippingStage(BaseModel):
    order_code: str
    source_order_code: str | None = None
    po_no: str | None = None
    order_status: str | None = None
    status_label: str = ""
    final_shipping_num: float = 0.0
    planed_shipping_num: float = 0.0
    package_qty: float = 0.0
    channel_code: str | None = None
    create_time: str | None = None
    shipping_time: str | None = None
    arrived_time: str | None = None


class SkuPipelineDetail(BaseModel):
    item_id: str
    seller_sku: str | None = None
    main_sku_id: str | None = None
    plans: list[PlanStage] = []
    orders: list[OrderStage] = []
    shippings: list[ShippingStage] = []
