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
  avg_items_per_order: number | null
}

export interface OrderTrendItem {
  date: string
  ordered: number
  awaiting_deliver: number
  delivering: number
  delivered: number
  cancelled: number
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
