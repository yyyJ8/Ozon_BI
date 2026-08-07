"""供应链 SKU 宽表 — 申购→采购→发货 扁平聚合"""
from typing import Optional
from pydantic import BaseModel


class SkuTableRow(BaseModel):
    """一行一个 SKU（对应 products.offer_id），扁平宽表"""
    item_id: str                                    # 货号 = omsprod purchase_plan_item.item_id
    sku_id: int = 0                                 # products 表的 SKU ID
    product_name: str | None = None                 # products 表的商品名

    # ── 申购阶段 ──
    plan_no: str | None = None                      # 最新申购单号
    plan_status: str | None = None                  # 申购单状态码
    plan_status_label: str = ""                     # 申购单状态中文
    plan_type: str | None = None                    # 申购类型码
    plan_type_label: str = ""                       # 申购类型中文
    plan_qty: float = 0.0                           # 计划数量（汇总）
    already_qty: float = 0.0                        # 已下单数量（汇总）
    plan_count: int = 0                             # 申购单数
    expect_date: str | None = None                  # 最早期望交期
    wms_rec_qty: float = 0.0                        # WMS收货总数
    wms_onstock_qty: float = 0.0                    # WMS上架总数
    direct_ship_arrival_qty: float = 0.0            # 直发到货总数

    # ── 采购阶段 ──
    order_no: str | None = None                     # 最新采购单号
    order_status: str | None = None                 # 采购单状态码
    order_status_label: str = ""                    # 采购单状态中文
    order_qty: float = 0.0                          # 采购数量（汇总）
    receipt_qty: float = 0.0                        # 已收货数量（汇总）
    order_count: int = 0                            # 采购单数
    order_price: float = 0.0                        # 最新采购单价
    order_amount: float = 0.0                       # 采购总金额（汇总）
    expect_receipt_date: str | None = None          # 最早采购预计交期

    # ── 发货阶段 ──
    shipping_no: str | None = None                  # 最新发货单号
    shipping_status: str | None = None              # 发货单状态码
    shipping_status_label: str = ""                 # 发货单状态中文
    planed_shipping_qty: float = 0.0                # 计划发货数（汇总）
    final_shipping_qty: float = 0.0                 # 最终发货数（汇总）
    inbound_qty: float = 0.0                        # 已到仓上架数（汇总）
    shipping_count: int = 0                         # 发货单数
    channel_code: str | None = None                 # 物流方式
    logistics_order: str | None = None              # 物流单号
    shipping_time: str | None = None                # 发货时间
    arrived_time: str | None = None                 # 到仓时间

    # ── 元数据 ──
    marketplace: str | None = None                  # 站点
    latest_update: str | None = None                # 最新更新时间
    logistics_method: str | None = None             # 申购单物流方式

    # ── 货件追踪 (cargo_shipments) ──
    cargo_status: str | None = None                 # 货物状态
    transit_warehouse: str | None = None            # 中转仓
    logistics_inbound_no: str | None = None         # 物流商入库单号
    cargo_box_count: float = 0.0                    # 箱数（总箱数）
    cargo_cbm: float = 0.0                          # 总方数
    cargo_weight: float = 0.0                       # 总重量 kg
    actual_listing_qty: float = 0.0                 # 实际上架数量
    fbo_warehouse_name: str | None = None           # FBO仓名称
    fbo_listing_time: str | None = None             # FBO上架时间
    product_status: str | None = None               # 产品状态（新品/热卖/滞销等）
    info_remarks: str | None = None                 # 信息备注
    requisitioner: str | None = None                # 申购人
    replenishment_qty: float = 0.0                  # 补货数量

    # ── 直发跟进 (ozon_direct_shipment) ──
    direct_receiving_status: str | None = None      # 收货状态
    direct_total_qty: float = 0.0                   # 直发总数量
    direct_shipment_count: int = 0                  # 直发跟进单数
    direct_latest_pr_no: str | None = None          # 最新申购单号
    direct_logistics_provider: str | None = None    # 物流商
    direct_tracking_no: str | None = None           # 物流单号
    direct_ship_date: str | None = None             # 发货日期


class SkuTableResponse(BaseModel):
    items: list[SkuTableRow]
    total: int
    page: int
    page_size: int


# ── 详情（展开行用，保持不变）──

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
    # 关联货件追踪（通过 pr_no 匹配 cargo_shipments）
    cs_product_name: str | None = None
    cs_store: str | None = None
    cs_requisitioner: str | None = None
    cs_replenishment_qty: float = 0.0
    cs_carton_qty: float = 0.0
    cs_carton_volume: float = 0.0
    cs_carton_gross_weight: float = 0.0
    cs_weight: float = 0.0
    cs_cbm: float = 0.0
    cs_density: float = 0.0
    cs_box_count: float = 0.0
    cs_transit_warehouse: str | None = None
    cs_logistics_inbound_no: str | None = None
    cs_cargo_status: str | None = None
    cs_fbo_warehouse_name: str | None = None
    cs_booking_code: str | None = None
    cs_fbo_listing_time: str | None = None
    cs_warehouse_rent_start: str | None = None
    cs_actual_listing_qty: float = 0.0
    cs_info_remarks: str | None = None
    cs_batch_quotation: str | None = None
    cs_product_status: str | None = None
    cs_stocking_opinion: str | None = None
    cs_parent_record: str | None = None


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
