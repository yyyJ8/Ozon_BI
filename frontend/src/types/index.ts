export interface Product {
  sku_id: number
  name: string
  offer_id: string
  price: number
  status: string
  category_id: number
  primary_image: string | null
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
  revenue: number
  returns_amount: number
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
  returns_amount: number
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
