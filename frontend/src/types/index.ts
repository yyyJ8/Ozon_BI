export interface Store {
  id: number
  name: string
  is_active: boolean
}

export interface Product {
  sku_id: number
  name: string
  offer_id: string
  price: number
  status: string
  category_id: number
  primary_image: string | null
  commission_fbo_pct: number | null
  stock_present: number
  stock_reserved: number
}

export interface SummaryRow {
  date: string
  sku_id: number
  offer_id: string
  name: string | null
  primary_image: string | null
  stock_present: number
  stock_reserved: number
  ordered_units: number
  delivered_units: number
  cancelled_units: number
  revenue: number
  returns_amount: number
  returns_units: number
  commissions: number
  logistics_costs: number
  storage_fees: number
  advertising: number
  promotion_costs: number
  other_costs: number
  net_profit: number
  profit_margin: number
  data_quality: string
}

export interface SummaryStats {
  total_revenue: number
  total_net_profit: number
  avg_profit_margin: number
  total_ordered_units: number
  total_commissions: number
  total_logistics: number
  total_returns: number
  total_returns_units: number
  total_storage: number
  total_advertising: number
  total_promotion: number
  total_other_costs: number
  day_count: number
  sku_count: number
}

export interface SyncStatus {
  status: string
  last_sync: string | null
  details: Record<string, {
    status: string
    started_at: string
    records: number
    error: string | null
  }>
}

export interface StockStatus {
  last_updated: string | null
  stock_count: number
}

export interface StockRefreshResult {
  ok: boolean
  stock_count: number
  last_updated: string | null
  message: string
}

export interface DateRangeInfo {
  min_date: string
  max_date: string
}

export interface ProductSummary {
  sku_id: number
  offer_id: string
  name: string
  primary_image: string | null
  revenue: number
  net_profit: number
  profit_margin: number
  ordered_units: number
  delivered_units: number
  cancelled_units: number
  returns_amount: number
  returns_units: number
  commissions: number
  logistics_costs: number
  storage_fees: number
  advertising: number
  promotion_costs: number
  other_costs: number
  commission_rate: number | null
  stock_present: number
  stock_reserved: number
  day_count: number
}

export interface FinanceTransaction {
  operation_id: number
  operation_type_name: string | null
  type: string | null
  operation_date: string
  posting_number: string | null
  delivery_schema: string | null
  amount: number
  accruals_for_sale: number
  sale_commission: number
  delivery_charge: number
  return_delivery_charge: number
}

// ── 广告 API 类型 ──

export interface AdCampaignSummary {
  campaign_id: string
  title: string | null
  campaign_type: string
  state: string
  budget: number
  total_spend: number
  total_orders: number
  total_orders_sum: number
  total_impressions: number
  total_clicks: number
  mapped_sku_id: number | null
  mapped_offer_id: string | null
}

export interface AdDailyStat {
  stat_date: string
  impressions: number
  clicks: number
  spend: number
  orders_count: number
  orders_sum: number
}

export interface AdSkuDetail {
  stat_date: string
  campaign_id: string
  sku_name: string | null
  sku_price: number | null
  impressions: number
  clicks: number
  ctr: number | null
  add_to_cart: number
  avg_cpc: number | null
  spend: number
  sold_units: number
  sales_promotion: number | null
  drr_promotion: number | null
  drr_total: number | null
}

export interface AdTrendItem {
  date: string
  spend: number
  impressions: number
  clicks: number
  orders_count: number
  orders_sum: number
  mapped_spend: number
}

export interface AdSummary {
  total_spend: number
  total_orders_count: number
  total_orders_sum: number
  total_impressions: number
  total_clicks: number
  by_type: Record<string, { spend: number; count: number; orders_sum: number }>
  unmapped_spend: number
  mapped_spend: number
  campaign_count: number
  active_campaign_count: number
  mapped_sku_count: number
}

// ── 退货 API 类型 ──

export interface ReturnsOverview {
  total_returns: number
  cancellation_count: number
  client_return_count: number
  by_status: Record<string, number>
  return_rate: number
  avg_processing_days: number | null
  unmatched_count: number
}

export interface ReturnsTrendItem {
  date: string
  cancellation: number
  client_return: number
  total: number
}

export interface SkuReturnStats {
  sku_id: number
  offer_id: string | null
  name: string | null
  primary_image: string | null
  total_returns: number
  cancellation_count: number
  client_return_count: number
  fbo_count: number
  fbs_count: number
  completed_count: number
  pending_count: number
  total_return_price: number
  ordered_units: number
  return_rate: number
  main_reason: string | null
  avg_processing_days: number | null
}

export interface ReasonItem {
  reason_name: string
  reason_cn: string
  type: string
  count: number
}

export interface ReturnDetailItem {
  id: number
  posting_number: string
  sku: number
  product_name: string | null
  offer_id: string | null
  primary_image: string | null
  type: string
  return_reason_name: string | null
  reason_cn: string | null
  quantity: number
  price: number | null
  visual_status: string
  delivery_schema: string
  returned_at: string | null
  finished_at: string | null
  status_changed_at: string | null
  processing_days: number | null
}

// ── 订单 API 类型 ──

export interface OrderOverview {
  total_orders: number
  fbo_count: number
  fbs_count: number
  delivered_count: number
  cancelled_count: number
  in_progress_count: number
  total_ordered_units: number
  cancellation_rate: number
  client_return_count: number
  avg_items_per_order: number | null
}

export interface OrderTrendItem {
  date: string
  ordered: number
  awaiting_deliver: number
  delivering: number
  delivered: number
  cancelled: number
  client_return: number
  price: number | null
}

export interface OrderListItem {
  posting_number: string
  order_number: string | null
  delivery_schema: string | null
  status: string | null
  created_at: string | null
  delivered_at: string | null
  in_process_at: string | null
  sku: number | null
  offer_id: string | null
  product_count: number
  total_quantity: number
  total_price: number
  actual_revenue: number
}

export interface OrderListResponse {
  items: OrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface OrderProduct {
  sku: number | null
  name: string | null
  quantity: number
  offer_id: string | null
  price: number
  image: string | null
}

export interface OrderReturn {
  id: number
  sku: number
  type: string
  return_reason_name: string | null
  quantity: number
  visual_status: string
  returned_at: string | null
  finished_at: string | null
}

export interface OrderFinance {
  operation_id: number
  operation_type_name: string | null
  type: string | null
  operation_date: string
  amount: number
  accruals_for_sale: number
  sale_commission: number
  delivery_charge: number
  return_delivery_charge: number
}

export interface OrderDetail {
  posting_number: string
  order_number: string | null
  delivery_schema: string | null
  status: string | null
  cancel_reason_id: number
  created_at: string | null
  in_process_at: string | null
  delivered_at: string | null
  products: OrderProduct[]
  returns: OrderReturn[]
  finance_transactions: OrderFinance[]
}

export interface OrderSkuStats {
  sku_id: number
  offer_id: string | null
  name: string | null
  primary_image: string | null
  order_count: number
  total_quantity: number
  total_revenue: number
  actual_revenue: number
  current_price: number
  delivered_count: number
  cancelled_count: number
  return_count: number
  profit_rmb: number | null
  profit_margin_pct: number | null
  stock: number
  fbo_count: number
  fbs_count: number
}

// ── 利润 API 类型 ──

export interface ProfitOverview {
  revenue: number
  net_profit: number
  profit_margin: number
  total_costs: number
  total_commissions: number
  total_logistics: number
  total_storage: number
  total_advertising: number
  total_promotion: number
  total_returns: number
  total_other: number
  ordered_units: number
  sku_count: number
  day_count: number
}

export interface ProfitTrendItem {
  date: string
  revenue: number
  costs: number
  net_profit: number
  profit_margin: number
  commissions: number
  logistics_costs: number
  storage_fees: number
  advertising: number
  promotion_costs: number
  returns_amount: number
  other_costs: number
}

export interface ProfitSkuItem {
  sku_id: number
  offer_id: string | null
  name: string | null
  primary_image: string | null
  revenue: number
  costs: number
  net_profit: number
  profit_margin: number
  ordered_units: number
  commissions: number
  logistics_costs: number
  storage_fees: number
  advertising: number
  promotion_costs: number
  returns_amount: number
  other_costs: number
  stock_present: number
  stock_reserved: number
}

// ── 异常检测 API 类型 ──

export interface AnomalyItem {
  sku_id: number
  offer_id: string | null
  name: string | null
  primary_image: string | null
  anomaly_type: string
  severity: 'critical' | 'warning' | 'info'
  description: string
  metrics: Record<string, number>
  triggered_conditions: string[]
}

export interface AnomalySummary {
  total_anomalies: number
  by_type: Record<string, number>
}

export interface AnomalyResponse {
  summary: AnomalySummary
  items: AnomalyItem[]
}

export interface ProfitDailyItem {
  date: string
  revenue: number
  costs: number
  net_profit: number
  profit_margin: number
  commissions: number
  logistics_costs: number
  storage_fees: number
  advertising: number
  promotion_costs: number
  returns_amount: number
  other_costs: number
}

// ── SKU 管理（可编辑表格）──

export interface SkuManagementRow {
  store_id: number
  sku_id: number

  // products 表（只读）
  name: string | null
  offer_id: string | null
  primary_image: string | null
  category_name: string | null
  price: number | null
  stock_present: number | null

  // sku_management 表（可编辑）
  main_sku: string | null
  source_url_1688: string | null
  specification: string | null
  sales_manager: string | null
  listed_stores: string | null
  product_status: string | null
  key_notes: string | null

  length_cm: number | null
  width_cm: number | null
  height_cm: number | null
  actual_weight_kg: number | null
  volume_cbm: number | null
  density: number | null

  first_leg_unit_price: number | null
  units_per_carton: number | null
  carton_length_cm: number | null
  carton_width_cm: number | null
  carton_height_cm: number | null
  gross_weight_kg: number | null
  volume_liters: number | null

  purchase_cost_rmb: number | null
  warehousing_fee_rmb: number | null
  fbo_delivery_fee_rmb: number | null
  first_leg_cost_rmb: number | null

  acquiring_fee_pct: number | null
  fbo_commission_pct: number | null
  logistics_rub: number | null
  delivery_pickup_rub: number | null
  advertising_rate_pct: number | null
  return_rate_pct: number | null
  tax_and_fee_pct: number | null
  risk_reserve_rub: number | null

  exchange_rate: number | null
  green_price_rub: number | null

  competitor_1: string | null
  competitor_2: string | null
  competitor_sales: number | null

  purchase_cost_pct: number | null
  first_leg_pct: number | null
  last_mile_pct: number | null
  product_cost_rmb: number | null
  discount_pct: number | null
  platform_payout_rub: number | null
  actual_payout_rub: number | null
  profit_rmb: number | null
  profit_rub: number | null
  profit_margin_pct: number | null

  created_at: string | null
  updated_at: string | null
}

export interface SkuManagementUpdate {
  sku_id: number
  [key: string]: any
}

export interface SkuManagementBatchUpdate {
  items: SkuManagementUpdate[]
}

// ── 供应链：申购计划 ──

export interface PlanOverview {
  total: number
  status_0_pending_submit: number
  status_1_pending_approval: number
  status_2_pending_create_po: number
  status_3_partial_create: number
  status_4_created: number
  status_5_cancelled: number
  status_6_approving: number
  total_plan_qty: number
}

export interface PlanListItem {
  po_plan_no: string
  status: string | null
  status_label: string
  plan_type: string | null
  plan_type_label: string
  logistics_method: string | null
  stock_location_id: string | null
  location_id: string | null
  create_time: string | null
  memo: string | null
  item_count: number
  total_plan_qty: number
  return_reason: string | null
}

export interface PlanListResponse {
  items: PlanListItem[]
  total: number
  page: number
  page_size: number
}

export interface PlanItemDetail {
  row_id: number
  item_id: string | null
  seller_sku: string | null
  plan_qty: number
  already_qty: number
  created_shipping_plan_qty: number
  expect_date: string | null
  expect_delivery_date: string | null
  store_id: string | null
  fn_sku: string | null
  marketplace: string | null
  new_flag: string | null
  order_type: string | null
  memo: string | null
  package_qty: number
  wms_rec_qty: number
  wms_check_qty: number
  wms_onstock_qty: number
  direct_ship_arrival_qty: number
  direct_ship_arrival_time: string | null
  main_sku_id: string | null
  warehouse_item_code: string | null
}

export interface PlanDetail {
  po_plan_no: string
  status: string | null
  status_label: string
  plan_type: string | null
  plan_type_label: string
  logistics_method: string | null
  stock_location_id: string | null
  location_id: string | null
  create_time: string | null
  update_time: string | null
  memo: string | null
  return_reason: string | null
  plan_source: string | null
  is_urgent: string | null
  is_new_product: string | null
  is_year_stock: string | null
  is_group: string | null
  combo_flag: string | null
  wms_status: string | null
  task_status: string | null
  shipping_status: string | null
  cancel_reason: string | null
  tax_free_flag: string | null
  items: PlanItemDetail[]
}

// ── 供应链：采购订单 ──

export interface PurOrderOverview {
  total: number
  status_0_pending_submit: number
  status_1_submitted: number
  status_2_pending_approval: number
  status_3_pending_receipt: number
  status_4_partial_receipt: number
  status_5_exception: number
  status_6_cancelled: number
  status_7_completed: number
  total_amount: number
}

export interface PurOrderListItem {
  po_no: string
  status: string | null
  status_label: string
  vendor_id: string | null
  amount: number
  currency_code: string | null
  create_time: string | null
  receipt_date: string | null
  item_count: number
  total_qty: number
  memo: string | null
  logistics_name: string | null
  logistics_num: string | null
}

export interface PurOrderListResponse {
  items: PurOrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface PurOrderItemDetail {
  row_id: number
  item_id: string | null
  price: number
  qty: number
  untaxed_amount: number
  tax_rate: number
  receipt_qty: number
  return_qty: number
  expect_receipt_date: string | null
  expect_date: string | null
  po_plan_no: string | null
  plan_row_id: number
  memo: string | null
  package_qty: number
  marketplace_code: string | null
  sale_platform: string | null
  main_sku_id: string | null
  track_status: string | null
  pending_shipment_qty: number
  accepted_time: string | null
  check_date: string | null
  already_listed_time: string | null
}

export interface PurOrderDetail {
  po_no: string
  status: string | null
  status_label: string
  vendor_id: string | null
  location_id: string | null
  subsidiary_id: string | null
  amount: number
  untaxed_amount: number
  tax_amount: number
  currency_code: string | null
  create_time: string | null
  update_time: string | null
  receipt_date: string | null
  trandate: string | null
  memo: string | null
  sku_type: string | null
  purchase_platform: string | null
  logistics_name: string | null
  logistics_num: string | null
  payment_status: string | null
  is_year_stock: string | null
  cancel_reason: string | null
  tax_free_flag: string | null
  purchase_dept_type: string | null
  items: PurOrderItemDetail[]
}

// ── 供应链：头程发货 ──

export interface ShippingOverview {
  total: number
  status_1_pending_push: number
  status_2_pending_pick: number
  status_3_4_picked_packed: number
  status_7_8_10_pending_ship: number
  status_11_shipped: number
  status_12_13_arrived: number
  status_9_cancelled: number
  total_item_qty: number
}

export interface ShippingListItem {
  order_code: string
  order_status: string | null
  status_label: string
  channel_code: string | null
  shipping_warehouse_id: string | null
  destination_warehouse_id: string | null
  destination_country_code: string | null
  create_time: string | null
  shipping_time: string | null
  arrived_time: string | null
  item_count: number
  plan_code: string | null
  logistics_order: string | null
  is_direct_ship: string | null
  remark: string | null
}

export interface ShippingListResponse {
  items: ShippingListItem[]
  total: number
  page: number
  page_size: number
}

export interface ShippingItemDetail {
  row_id: number
  item_id: string | null
  seller_sku: string | null
  final_shipping_num: number
  planed_shipping_num: number
  operation_shipping_num: number
  package_qty: number
  package_volume: string | null
  package_weight: string | null
  source_order_code: string | null
  source_order_type: string | null
  po_no: string | null
  store_id: string | null
  fnsku: string | null
  material: string | null
  main_sku_id: string | null
  warehouse_item_code: string | null
  inbound_putaway_qty: number
  qc_status: string | null
}

export interface ShippingDetail {
  order_code: string
  order_status: string | null
  status_label: string
  plan_code: string | null
  plan_type: string | null
  channel_code: string | null
  shipping_warehouse_id: string | null
  destination_warehouse_id: string | null
  destination_country_code: string | null
  receiving_platform: string | null
  third_order_code: string | null
  create_time: string | null
  update_time: string | null
  shipping_time: string | null
  arrived_time: string | null
  shelving_time: string | null
  logistics_order: string | null
  remark: string | null
  merge_tag: string | null
  package_type: string | null
  is_agl: string | null
  is_official_provider: string | null
  is_direct_ship: string | null
  cancel_reason: string | null
  tax_free_flag: string | null
  shipping_plan_time: string | null
  ship_date: string | null
  form_id: string | null
  items: ShippingItemDetail[]
}

// ── 供应链 SKU 宽表 ──

export interface SkuTableRow {
  item_id: string
  sku_id: number
  product_name: string | null
  plan_no: string | null
  plan_status: string | null
  plan_status_label: string
  plan_type: string | null
  plan_type_label: string
  plan_qty: number
  already_qty: number
  plan_count: number
  expect_date: string | null
  wms_rec_qty: number
  wms_onstock_qty: number
  direct_ship_arrival_qty: number
  order_no: string | null
  order_status: string | null
  order_status_label: string
  order_qty: number
  receipt_qty: number
  order_count: number
  order_price: number
  order_amount: number
  expect_receipt_date: string | null
  shipping_no: string | null
  shipping_status: string | null
  shipping_status_label: string
  planed_shipping_qty: number
  final_shipping_qty: number
  inbound_qty: number
  shipping_count: number
  channel_code: string | null
  logistics_order: string | null
  shipping_time: string | null
  arrived_time: string | null
  marketplace: string | null
  latest_update: string | null
  logistics_method: string | null
  // 货件追踪
  cargo_status: string | null
  transit_warehouse: string | null
  logistics_inbound_no: string | null
  cargo_box_count: number
  cargo_cbm: number
  cargo_weight: number
  actual_listing_qty: number
  fbo_warehouse_name: string | null
  fbo_listing_time: string | null
  product_status: string | null
  info_remarks: string | null
  requisitioner: string | null
  replenishment_qty: number
  // 直发跟进
  direct_receiving_status: string | null
  direct_total_qty: number
  direct_shipment_count: number
  direct_latest_pr_no: string | null
  direct_logistics_provider: string | null
  direct_tracking_no: string | null
  direct_ship_date: string | null
}

export interface SkuTableResponse {
  items: SkuTableRow[]
  total: number
  page: number
  page_size: number
}

export interface PlanStage {
  po_plan_no: string
  status: string | null
  status_label: string
  plan_qty: number
  already_qty: number
  direct_ship_arrival_qty: number
  expect_date: string | null
  wms_rec_qty: number
  wms_onstock_qty: number
  create_time: string | null
  cargo_status: string | null
  cargo_transit_warehouse: string | null
  cargo_box_count: number
  cargo_cbm: number
  cargo_weight: number
  cargo_logistics_inbound_no: string | null
}

export interface OrderStage {
  po_no: string
  po_plan_no: string | null
  status: string | null
  status_label: string
  qty: number
  receipt_qty: number
  price: number
  untaxed_amount: number
  expect_receipt_date: string | null
  create_time: string | null
}

export interface ShippingStage {
  order_code: string
  source_order_code: string | null
  po_no: string | null
  order_status: string | null
  status_label: string
  final_shipping_num: number
  planed_shipping_num: number
  package_qty: number
  channel_code: string | null
  create_time: string | null
  shipping_time: string | null
  arrived_time: string | null
}

export interface SkuPipelineDetail {
  item_id: string
  seller_sku: string | null
  main_sku_id: string | null
  plans: PlanStage[]
  orders: OrderStage[]
  shippings: ShippingStage[]
}

// ============================================================
// OZON 直发信息
// ============================================================

export interface DirectSkuItem {
  id: number
  sku: string
  product_name: string | null
  supplier: string | null
  store_name: string | null
  sales_manager: string | null
  label_file: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DirectSkuUpdate {
  sku?: string
  product_name?: string | null
  supplier?: string | null
  store_name?: string | null
  sales_manager?: string | null
  label_file?: string | null
}

export interface DirectShipmentItem {
  id: number
  pr_date: string | null
  pr_no: string | null
  sku: string | null
  pr_person: string | null
  product_cn_name: string | null
  previous_aftersales: string | null
  supplier: string | null
  logistics_provider: string | null
  first_leg_tracking: string | null
  total_qty: number | null
  total_boxes: number | null
  receiving_address: string | null
  labeling_notes: string | null
  product_label: string | null
  carton_mark: string | null
  warehouse_receipt: string | null
  po_no: string | null
  online_po_no: string | null
  is_received: string | null
  ship_date: string | null
  special_notes: string | null
  plan_no: string | null
  tracking_no: string | null
  receiving_status: string | null
  receiving_date: string | null
  length_cm: number | null
  width_cm: number | null
  height_cm: number | null
  gross_weight: number | null
  total_cbm: number | null
  density: number | null
  logistics_company: string | null
  shipment_no: string | null
  created_at: string | null
  updated_at: string | null
}

export interface DirectShipmentUpdate {
  pr_date?: string | null
  pr_no?: string | null
  sku?: string | null
  pr_person?: string | null
  product_cn_name?: string | null
  previous_aftersales?: string | null
  supplier?: string | null
  logistics_provider?: string | null
  first_leg_tracking?: string | null
  total_qty?: number | null
  total_boxes?: number | null
  receiving_address?: string | null
  labeling_notes?: string | null
  product_label?: string | null
  carton_mark?: string | null
  warehouse_receipt?: string | null
  po_no?: string | null
  online_po_no?: string | null
  is_received?: string | null
  ship_date?: string | null
  special_notes?: string | null
  plan_no?: string | null
  tracking_no?: string | null
  receiving_status?: string | null
  receiving_date?: string | null
  length_cm?: number | null
  width_cm?: number | null
  height_cm?: number | null
  gross_weight?: number | null
  total_cbm?: number | null
  density?: number | null
  logistics_company?: string | null
  shipment_no?: string | null
}

export interface DirectFileItem {
  id: number
  source_table: string
  sku: string | null
  pr_no: string | null
  file_name: string
  file_size: number | null
  file_type: string | null
  uploaded_at: string | null
}

export interface DirectListResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
