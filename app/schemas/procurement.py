"""中台供应链 API 响应模型 — 申购/采购/发货"""
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════
# 申购计划 (purchase_plan + purchase_plan_item)
# ═══════════════════════════════════════════════════════════════

class PlanOverview(BaseModel):
    total: int = 0
    status_0_pending_submit: int = 0      # 待提交
    status_1_pending_approval: int = 0    # 待审批
    status_2_pending_create_po: int = 0   # 待创建采购单
    status_3_partial_create: int = 0      # 部分创建
    status_4_created: int = 0             # 已创建采购订单
    status_5_cancelled: int = 0           # 已作废
    status_6_approving: int = 0           # 审批中
    total_plan_qty: float = 0.0           # 计划总数量（来自明细行）


class PlanListItem(BaseModel):
    po_plan_no: str
    status: str | None = None
    status_label: str = ""
    plan_type: str | None = None
    plan_type_label: str = ""
    logistics_method: str | None = None
    stock_location_id: str | None = None
    location_id: str | None = None
    create_time: datetime | str | None = None
    memo: str | None = None
    item_count: int = 0
    total_plan_qty: float = 0.0
    return_reason: str | None = None


class PlanListResponse(BaseModel):
    items: list[PlanListItem]
    total: int
    page: int
    page_size: int


class PlanItemDetail(BaseModel):
    row_id: int = 0
    item_id: str | None = None            # SKU编码
    seller_sku: str | None = None
    plan_qty: float = 0.0                  # 计划采购数量
    already_qty: float = 0.0               # 已下单数量
    created_shipping_plan_qty: float = 0.0 # 已创建发货计划数量
    expect_date: str | None = None         # 期望交货日期
    expect_delivery_date: str | None = None
    store_id: str | None = None
    fn_sku: str | None = None
    marketplace: str | None = None
    new_flag: str | None = None
    order_type: str | None = None
    memo: str | None = None
    package_qty: float = 0.0
    wms_rec_qty: float = 0.0
    wms_check_qty: float = 0.0
    wms_onstock_qty: float = 0.0
    direct_ship_arrival_qty: float = 0.0
    direct_ship_arrival_time: str | None = None
    main_sku_id: str | None = None
    warehouse_item_code: str | None = None


class PlanDetail(BaseModel):
    po_plan_no: str
    status: str | None = None
    status_label: str = ""
    plan_type: str | None = None
    plan_type_label: str = ""
    logistics_method: str | None = None
    stock_location_id: str | None = None
    location_id: str | None = None
    create_time: datetime | str | None = None
    update_time: datetime | str | None = None
    memo: str | None = None
    return_reason: str | None = None
    plan_source: str | None = None
    is_urgent: str | None = None
    is_new_product: str | None = None
    is_year_stock: str | None = None
    is_group: str | None = None
    combo_flag: str | None = None
    wms_status: str | None = None
    task_status: str | None = None
    shipping_status: str | None = None
    cancel_reason: str | None = None
    tax_free_flag: str | None = None
    items: list[PlanItemDetail] = []


# ═══════════════════════════════════════════════════════════════
# 采购订单 (purchase_order + purchase_order_item)
# ═══════════════════════════════════════════════════════════════

class OrderOverview(BaseModel):
    total: int = 0
    status_0_pending_submit: int = 0       # 待提交
    status_1_submitted: int = 0            # 已提交
    status_2_pending_approval: int = 0     # 待审批
    status_3_pending_receipt: int = 0      # 待入库
    status_4_partial_receipt: int = 0      # 部分入库
    status_5_exception: int = 0            # 异常
    status_6_cancelled: int = 0            # 已作废
    status_7_completed: int = 0            # 完结
    total_amount: float = 0.0              # 采购总金额


class OrderListItem(BaseModel):
    po_no: str
    status: str | None = None
    status_label: str = ""
    vendor_id: str | None = None
    amount: float = 0.0
    currency_code: str | None = None
    create_time: datetime | str | None = None
    receipt_date: str | None = None
    item_count: int = 0
    total_qty: float = 0.0
    memo: str | None = None
    logistics_name: str | None = None
    logistics_num: str | None = None


class OrderListResponse(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    page_size: int


class OrderItemDetail(BaseModel):
    row_id: int = 0
    item_id: str | None = None             # SKU编码
    price: float = 0.0                     # 未税单价
    qty: float = 0.0                       # 采购数量
    untaxed_amount: float = 0.0            # 未税金额
    tax_rate: float = 0.0
    receipt_qty: float = 0.0               # 采购收货数量
    return_qty: float = 0.0
    expect_receipt_date: str | None = None
    expect_date: str | None = None
    po_plan_no: str | None = None          # 关联申购单号
    plan_row_id: int = 0
    memo: str | None = None
    package_qty: float = 0.0
    marketplace_code: str | None = None
    sale_platform: str | None = None
    main_sku_id: str | None = None
    track_status: str | None = None
    pending_shipment_qty: float = 0.0
    accepted_time: str | None = None
    check_date: str | None = None
    already_listed_time: str | None = None


class OrderDetail(BaseModel):
    po_no: str
    status: str | None = None
    status_label: str = ""
    vendor_id: str | None = None
    location_id: str | None = None
    subsidiary_id: str | None = None
    amount: float = 0.0
    untaxed_amount: float = 0.0
    tax_amount: float = 0.0
    currency_code: str | None = None
    create_time: datetime | str | None = None
    update_time: datetime | str | None = None
    receipt_date: str | None = None
    trandate: str | None = None
    memo: str | None = None
    sku_type: str | None = None
    purchase_platform: str | None = None
    logistics_name: str | None = None
    logistics_num: str | None = None
    payment_status: str | None = None
    is_year_stock: str | None = None
    cancel_reason: str | None = None
    tax_free_flag: str | None = None
    purchase_dept_type: str | None = None
    items: list[OrderItemDetail] = []


# ═══════════════════════════════════════════════════════════════
# 头程发货 (first_leg_shipping_order + first_leg_shipping_order_item)
# ═══════════════════════════════════════════════════════════════

class ShippingOverview(BaseModel):
    total: int = 0
    status_1_pending_push: int = 0         # 待推送
    status_2_pending_pick: int = 0         # 待拣货
    status_3_4_picked_packed: int = 0      # 拣货/装箱完成
    status_7_8_10_pending_ship: int = 0    # 待发货（复核阶段）
    status_11_shipped: int = 0             # 已发货
    status_12_13_arrived: int = 0          # 已到仓/部分到仓
    status_9_cancelled: int = 0            # 已作废
    total_item_qty: float = 0.0            # 总发货件数


class ShippingListItem(BaseModel):
    order_code: str
    order_status: str | None = None
    status_label: str = ""
    channel_code: str | None = None
    shipping_warehouse_id: str | None = None
    destination_warehouse_id: str | None = None
    destination_country_code: str | None = None
    create_time: datetime | str | None = None
    shipping_time: str | None = None
    arrived_time: str | None = None
    item_count: int = 0
    plan_code: str | None = None
    logistics_order: str | None = None
    is_direct_ship: str | None = None
    remark: str | None = None


class ShippingListResponse(BaseModel):
    items: list[ShippingListItem]
    total: int
    page: int
    page_size: int


class ShippingItemDetail(BaseModel):
    row_id: int = 0
    item_id: str | None = None             # 系统SKU
    seller_sku: str | None = None
    final_shipping_num: float = 0.0        # 最终发货数
    planed_shipping_num: float = 0.0       # 计划发货数量
    operation_shipping_num: float = 0.0    # 运营发货数量
    package_qty: float = 0.0               # 箱规-单箱数量
    package_volume: str | None = None
    package_weight: str | None = None
    source_order_code: str | None = None   # 来源申购单号
    source_order_type: str | None = None
    po_no: str | None = None               # 关联采购单号
    store_id: str | None = None
    fnsku: str | None = None
    material: str | None = None
    main_sku_id: str | None = None
    warehouse_item_code: str | None = None
    inbound_putaway_qty: float = 0.0
    qc_status: str | None = None
    memo: str | None = None


class ShippingDetail(BaseModel):
    order_code: str
    order_status: str | None = None
    status_label: str = ""
    plan_code: str | None = None
    plan_type: str | None = None
    channel_code: str | None = None
    shipping_warehouse_id: str | None = None
    destination_warehouse_id: str | None = None
    destination_country_code: str | None = None
    receiving_platform: str | None = None
    third_order_code: str | None = None
    create_time: datetime | str | None = None
    update_time: datetime | str | None = None
    shipping_time: str | None = None
    arrived_time: str | None = None
    shelving_time: str | None = None
    logistics_order: str | None = None
    remark: str | None = None
    merge_tag: str | None = None
    package_type: str | None = None
    is_agl: str | None = None
    is_official_provider: str | None = None
    is_direct_ship: str | None = None
    cancel_reason: str | None = None
    tax_free_flag: str | None = None
    shipping_plan_time: str | None = None
    ship_date: str | None = None
    form_id: str | None = None
    items: list[ShippingItemDetail] = []
