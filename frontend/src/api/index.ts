import type {
  Product, SummaryRow, SummaryStats, SyncStatus, DateRangeInfo, FinanceTransaction,
  AdCampaignSummary, AdDailyStat, AdSkuDetail, AdSummary,
  ReturnsOverview, ReturnsTrendItem, SkuReturnStats, ReasonItem,
  OrderOverview, OrderTrendItem, OrderListResponse, OrderDetail,
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

export async function getProducts(): Promise<Product[]> {
  return fetchJson<Product[]>(`${BASE}/products`)
}

export async function getSummary(
  dateFrom?: string,
  dateTo?: string,
  skuId?: number,
): Promise<SummaryRow[]> {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (skuId) params.set('sku_id', String(skuId))
  const qs = params.toString()
  return fetchJson<SummaryRow[]>(`${BASE}/summary${qs ? '?' + qs : ''}`)
}

export async function getSummaryStats(
  dateFrom?: string,
  dateTo?: string,
  skuId?: number,
): Promise<SummaryStats> {
  const params = new URLSearchParams()
  if (dateFrom) params.set('date_from', dateFrom)
  if (dateTo) params.set('date_to', dateTo)
  if (skuId) params.set('sku_id', String(skuId))
  const qs = params.toString()
  return fetchJson<SummaryStats>(`${BASE}/summary/stats${qs ? '?' + qs : ''}`)
}

export async function triggerSync(): Promise<{ status: string; results: Record<string, unknown> }> {
  return fetchJson(`${BASE}/sync`, { method: 'POST' })
}

export async function getSyncStatus(): Promise<SyncStatus> {
  return fetchJson<SyncStatus>(`${BASE}/sync/status`)
}

export async function getDateRange(): Promise<DateRangeInfo> {
  return fetchJson<DateRangeInfo>(`${BASE}/summary/date-range`)
}

export async function getFinanceTransactions(
  skuId: number,
  date: string,
): Promise<FinanceTransaction[]> {
  return fetchJson<FinanceTransaction[]>(
    `${BASE}/finance/transactions?sku_id=${skuId}&date=${date}`,
  )
}

export async function getReturnsByPostings(
  postingNumbers: string[],
): Promise<FinanceTransaction[]> {
  if (!postingNumbers.length) return []
  return fetchJson<FinanceTransaction[]>(
    `${BASE}/finance/returns-by-postings?posting_numbers=${postingNumbers.join(',')}`,
  )
}

export async function getTransactionsByPostings(
  postingNumbers: string[],
): Promise<FinanceTransaction[]> {
  if (!postingNumbers.length) return []
  return fetchJson<FinanceTransaction[]>(
    `${BASE}/finance/by-postings?posting_numbers=${postingNumbers.join(',')}`,
  )
}

// ── 广告 API ──

function adParams(dateFrom?: string, dateTo?: string, extra?: Record<string, string>): string {
  const p = new URLSearchParams(extra)
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  const qs = p.toString()
  return qs ? '?' + qs : ''
}

export async function getAdCampaigns(
  dateFrom?: string, dateTo?: string, type?: string, state?: string,
): Promise<AdCampaignSummary[]> {
  const extra: Record<string, string> = {}
  if (type) extra['campaign_type'] = type
  if (state) extra['state'] = state
  return fetchJson<AdCampaignSummary[]>(`${BASE}/advertising/campaigns${adParams(dateFrom, dateTo, extra)}`)
}

export async function getAdCampaignDaily(
  campaignId: string, dateFrom?: string, dateTo?: string,
): Promise<AdDailyStat[]> {
  return fetchJson<AdDailyStat[]>(
    `${BASE}/advertising/campaigns/${campaignId}/daily${adParams(dateFrom, dateTo)}`)
}

export async function getAdSkuDetail(
  skuId: number, dateFrom?: string, dateTo?: string,
): Promise<AdSkuDetail[]> {
  return fetchJson<AdSkuDetail[]>(
    `${BASE}/advertising/sku/${skuId}/detail${adParams(dateFrom, dateTo)}`)
}

export async function getAdSummary(
  dateFrom?: string, dateTo?: string,
): Promise<AdSummary> {
  return fetchJson<AdSummary>(`${BASE}/advertising/summary${adParams(dateFrom, dateTo)}`)
}

// ── 退货 API ──

function returnsParams(dateFrom?: string, dateTo?: string, extra?: Record<string, string>): string {
  const p = new URLSearchParams(extra)
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  const qs = p.toString()
  return qs ? '?' + qs : ''
}

export async function getReturnsOverview(
  dateFrom?: string, dateTo?: string, skuId?: number,
): Promise<ReturnsOverview> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<ReturnsOverview>(
    `${BASE}/returns/overview${returnsParams(dateFrom, dateTo, extra)}`)
}

export async function getReturnsTrend(
  dateFrom?: string, dateTo?: string, skuId?: number,
): Promise<ReturnsTrendItem[]> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<ReturnsTrendItem[]>(
    `${BASE}/returns/trend${returnsParams(dateFrom, dateTo, extra)}`)
}

export async function getSkuReturnStats(
  dateFrom?: string, dateTo?: string,
): Promise<SkuReturnStats[]> {
  return fetchJson<SkuReturnStats[]>(
    `${BASE}/returns/sku-stats${returnsParams(dateFrom, dateTo)}`)
}

export async function getReturnsReasons(
  dateFrom?: string, dateTo?: string, type?: string, skuId?: number,
): Promise<ReasonItem[]> {
  const extra: Record<string, string> = {}
  if (type) extra['type'] = type
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<ReasonItem[]>(
    `${BASE}/returns/reasons${returnsParams(dateFrom, dateTo, extra)}`)
}

// ── 订单 API ──

export async function getOrdersOverview(
  dateFrom?: string, dateTo?: string, skuId?: number,
): Promise<OrderOverview> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<OrderOverview>(
    `${BASE}/orders/overview${returnsParams(dateFrom, dateTo, extra)}`)
}

export async function getOrdersTrend(
  dateFrom?: string, dateTo?: string, skuId?: number,
): Promise<OrderTrendItem[]> {
  const extra: Record<string, string> = {}
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  return fetchJson<OrderTrendItem[]>(
    `${BASE}/orders/trend${returnsParams(dateFrom, dateTo, extra)}`)
}

export async function getOrdersList(
  dateFrom?: string, dateTo?: string, status?: string,
  schema?: string, skuId?: number, page?: number, pageSize?: number,
): Promise<OrderListResponse> {
  const extra: Record<string, string> = {}
  if (status) extra['status'] = status
  if (schema) extra['schema'] = schema
  if (skuId !== undefined) extra['sku_id'] = String(skuId)
  if (page !== undefined) extra['page'] = String(page)
  if (pageSize !== undefined) extra['page_size'] = String(pageSize)
  return fetchJson<OrderListResponse>(
    `${BASE}/orders/list${returnsParams(dateFrom, dateTo, extra)}`)
}

export async function getOrderDetail(
  postingNumber: string,
): Promise<OrderDetail> {
  return fetchJson<OrderDetail>(`${BASE}/orders/${encodeURIComponent(postingNumber)}`)
}
