import type {
  Product, SummaryRow, SummaryStats, SyncStatus, DateRangeInfo, FinanceTransaction,
  AdCampaignSummary, AdDailyStat, AdSkuDetail, AdSummary, AdTrendItem,
  ReturnsOverview, ReturnsTrendItem, SkuReturnStats, ReasonItem, ReturnDetailItem,
  OrderOverview, OrderTrendItem, OrderListResponse, OrderDetail,
  StockStatus, StockRefreshResult,
  Store,
} from '@/types'

const BASE = '/api/v1'

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json()
}

// ── 店铺 ──

export async function getStores(): Promise<Store[]> {
  return fetchJson<Store[]>(`${BASE}/stores`)
}

// ── 商品 ──

export async function getProducts(storeId: number = 1): Promise<Product[]> {
  return fetchJson<Product[]>(`${BASE}/products?store_id=${storeId}`)
}

// ── 汇总 ──

export async function getSummary(
  dateFrom?: string,
  dateTo?: string,
  skuId?: number,
  storeId: number = 1,
): Promise<SummaryRow[]> {
  const params = new URLSearchParams()
  params.set('store_id', String(storeId))
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (skuId) params.set('sku_id', String(skuId))
  return fetchJson<SummaryRow[]>(`${BASE}/summary?${params.toString()}`)
}

export async function getSummaryStats(
  dateFrom?: string,
  dateTo?: string,
  skuId?: number,
  storeId: number = 1,
): Promise<SummaryStats> {
  const params = new URLSearchParams()
  params.set('store_id', String(storeId))
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (skuId) params.set('sku_id', String(skuId))
  return fetchJson<SummaryStats>(`${BASE}/summary/stats?${params.toString()}`)
}

export async function triggerSync(storeId?: number): Promise<{ status: string; results: Record<string, unknown> }> {
  const url = storeId ? `${BASE}/sync?store_id=${storeId}` : `${BASE}/sync`
  return fetchJson(url, { method: 'POST' })
}

export async function getSyncStatus(storeId: number = 1): Promise<SyncStatus> {
  return fetchJson<SyncStatus>(`${BASE}/sync/status?store_id=${storeId}`)
}

export async function getDateRange(storeId: number = 1): Promise<DateRangeInfo> {
  return fetchJson<DateRangeInfo>(`${BASE}/summary/date-range?store_id=${storeId}`)
}

export async function getFinanceTransactions(
  skuId: number,
  date: string,
  storeId: number = 1,
): Promise<FinanceTransaction[]> {
  return fetchJson<FinanceTransaction[]>(
    `${BASE}/finance/transactions?sku_id=${skuId}&date=${date}&store_id=${storeId}`,
  )
}

export async function getReturnsByPostings(
  postingNumbers: string[],
  storeId: number = 1,
): Promise<FinanceTransaction[]> {
  if (!postingNumbers.length) return []
  return fetchJson<FinanceTransaction[]>(
    `${BASE}/finance/returns-by-postings?store_id=${storeId}&posting_numbers=${postingNumbers.join(',')}`,
  )
}

export async function getTransactionsByPostings(
  postingNumbers: string[],
  storeId: number = 1,
): Promise<FinanceTransaction[]> {
  if (!postingNumbers.length) return []
  return fetchJson<FinanceTransaction[]>(
    `${BASE}/finance/by-postings?store_id=${storeId}&posting_numbers=${postingNumbers.join(',')}`,
  )
}

// ── 广告 API ──

function adParams(storeId: number, dateFrom?: string, dateTo?: string, extra?: Record<string, string>): string {
  const p = new URLSearchParams(extra)
  p.set('store_id', String(storeId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return p.toString()
}

export async function getAdCampaigns(
  dateFrom?: string, dateTo?: string, type?: string, state?: string,
  storeId: number = 1,
): Promise<AdCampaignSummary[]> {
  const extra: Record<string, string> = {}
  if (type) extra['campaign_type'] = type
  if (state) extra['state'] = state
  return fetchJson<AdCampaignSummary[]>(`${BASE}/advertising/campaigns?${adParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getAdCampaignDaily(
  campaignId: string, dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<AdDailyStat[]> {
  return fetchJson<AdDailyStat[]>(
    `${BASE}/advertising/campaigns/${campaignId}/daily?${adParams(storeId, dateFrom, dateTo)}`)
}

export async function getAdSkuDetail(
  skuId: number, dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<AdSkuDetail[]> {
  return fetchJson<AdSkuDetail[]>(
    `${BASE}/advertising/sku/${skuId}/detail?${adParams(storeId, dateFrom, dateTo)}`)
}

export async function getAdTrend(
  dateFrom?: string, dateTo?: string, campaignType?: string, storeId: number = 1,
): Promise<AdTrendItem[]> {
  const extra: Record<string, string> = {}
  if (campaignType) extra['campaign_type'] = campaignType
  return fetchJson<AdTrendItem[]>(
    `${BASE}/advertising/trend?${adParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getAdSummary(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<AdSummary> {
  return fetchJson<AdSummary>(`${BASE}/advertising/summary?${adParams(storeId, dateFrom, dateTo)}`)
}

// ── 退货 API ──

function returnsParams(storeId: number, dateFrom?: string, dateTo?: string, extra?: Record<string, string>): string {
  const p = new URLSearchParams(extra)
  p.set('store_id', String(storeId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return p.toString()
}

export async function getReturnsOverview(
  dateFrom?: string, dateTo?: string, skuId?: number, storeId: number = 1,
): Promise<ReturnsOverview> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<ReturnsOverview>(
    `${BASE}/returns/overview?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getReturnsTrend(
  dateFrom?: string, dateTo?: string, skuId?: number, storeId: number = 1,
): Promise<ReturnsTrendItem[]> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<ReturnsTrendItem[]>(
    `${BASE}/returns/trend?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getSkuReturnStats(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<SkuReturnStats[]> {
  return fetchJson<SkuReturnStats[]>(
    `${BASE}/returns/sku-stats?${returnsParams(storeId, dateFrom, dateTo)}`)
}

export async function getReturnsReasons(
  dateFrom?: string, dateTo?: string, type?: string, skuId?: number, storeId: number = 1,
): Promise<ReasonItem[]> {
  const extra: Record<string, string> = {}
  if (type) extra['type'] = type
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<ReasonItem[]>(
    `${BASE}/returns/reasons?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getReturnsDetails(
  skuId: number, dateFrom?: string, dateTo?: string,
  limit?: number, offset?: number, storeId: number = 1,
): Promise<ReturnDetailItem[]> {
  const p = new URLSearchParams()
  p.set('store_id', String(storeId))
  p.set('sku_id', String(skuId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  if (limit !== undefined) p.set('limit', String(limit))
  if (offset !== undefined) p.set('offset', String(offset))
  return fetchJson<ReturnDetailItem[]>(`${BASE}/returns/details?${p.toString()}`)
}

// ── 订单 API ──

export async function getOrdersOverview(
  dateFrom?: string, dateTo?: string, skuId?: number, storeId: number = 1,
): Promise<OrderOverview> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<OrderOverview>(
    `${BASE}/orders/overview?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getOrdersTrend(
  dateFrom?: string, dateTo?: string, skuId?: number, storeId: number = 1,
): Promise<OrderTrendItem[]> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<OrderTrendItem[]>(
    `${BASE}/orders/trend?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getOrdersList(
  dateFrom?: string, dateTo?: string, status?: string,
  schema?: string, skuId?: number, search?: string,
  page?: number, pageSize?: number, storeId: number = 1,
): Promise<OrderListResponse> {
  const extra: Record<string, string> = {}
  if (status) extra['status'] = status
  if (schema) extra['schema'] = schema
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  if (search) extra['search'] = search
  if (page !== undefined) extra['page'] = String(page)
  if (pageSize !== undefined) extra['page_size'] = String(pageSize)
  return fetchJson<OrderListResponse>(
    `${BASE}/orders/list?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

export async function getOrderDetail(
  postingNumber: string, storeId: number = 1,
): Promise<OrderDetail> {
  return fetchJson<OrderDetail>(`${BASE}/orders/${encodeURIComponent(postingNumber)}?store_id=${storeId}`)
}

// ── 库存 API ──

export async function getStockStatus(storeId: number = 1): Promise<StockStatus> {
  return fetchJson<StockStatus>(`${BASE}/stocks/status?store_id=${storeId}`)
}

export async function refreshStocks(storeId: number = 1): Promise<StockRefreshResult> {
  return fetchJson<StockRefreshResult>(`${BASE}/stocks/refresh?store_id=${storeId}`, { method: 'POST' })
}
