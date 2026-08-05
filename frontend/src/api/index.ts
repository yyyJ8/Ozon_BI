import type {
  Product, SummaryRow, SummaryStats, SyncStatus, DateRangeInfo, FinanceTransaction,
  AdCampaignSummary, AdDailyStat, AdSkuDetail, AdSummary, AdTrendItem,
  ReturnsOverview, ReturnsTrendItem, SkuReturnStats, ReasonItem, ReturnDetailItem,
  OrderOverview, OrderTrendItem, OrderListResponse, OrderDetail, OrderSkuStats,
  StockStatus, StockRefreshResult,
  Store,
  ProfitOverview, ProfitTrendItem, ProfitSkuItem, ProfitDailyItem,
  AnomalyResponse,
  SkuManagementRow, SkuManagementUpdate,
  PlanOverview, PlanListItem, PlanListResponse, PlanDetail,
  PurOrderOverview, PurOrderListItem, PurOrderListResponse, PurOrderDetail,
  ShippingOverview, ShippingListItem, ShippingListResponse, ShippingDetail,
  DirectSkuItem, DirectSkuUpdate, DirectShipmentItem, DirectShipmentUpdate,
  DirectFileItem, DirectListResponse,
  SkuPipelineItem, SkuPipelineListResponse, SkuPipelineDetail,
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

export async function getOrdersSkuStats(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<OrderSkuStats[]> {
  const extra: Record<string, string> = {}
  return fetchJson<OrderSkuStats[]>(
    `${BASE}/orders/sku-stats?${returnsParams(storeId, dateFrom, dateTo, extra)}`)
}

// ── 库存 API ──

export async function getStockStatus(storeId: number = 1): Promise<StockStatus> {
  return fetchJson<StockStatus>(`${BASE}/stocks/status?store_id=${storeId}`)
}

export async function refreshStocks(storeId: number = 1): Promise<StockRefreshResult> {
  return fetchJson<StockRefreshResult>(`${BASE}/stocks/refresh?store_id=${storeId}`, { method: 'POST' })
}

// ── 利润 API ──

function profitParams(storeId: number, dateFrom?: string, dateTo?: string, extra?: Record<string, string>): string {
  const p = new URLSearchParams(extra)
  p.set('store_id', String(storeId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return p.toString()
}

export async function getProfitOverview(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<ProfitOverview> {
  return fetchJson<ProfitOverview>(`${BASE}/profit/overview?${profitParams(storeId, dateFrom, dateTo)}`)
}

export async function getProfitTrend(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<ProfitTrendItem[]> {
  return fetchJson<ProfitTrendItem[]>(`${BASE}/profit/trend?${profitParams(storeId, dateFrom, dateTo)}`)
}

export async function getProfitSkuRanking(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<ProfitSkuItem[]> {
  return fetchJson<ProfitSkuItem[]>(`${BASE}/profit/sku-ranking?${profitParams(storeId, dateFrom, dateTo)}`)
}

export async function getProfitSkuDaily(
  skuId: number, dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<ProfitDailyItem[]> {
  const p = new URLSearchParams()
  p.set('store_id', String(storeId))
  p.set('sku_id', String(skuId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return fetchJson<ProfitDailyItem[]>(`${BASE}/profit/sku-daily?${p.toString()}`)
}

// ── 异常检测 API ──

export async function getAnomalies(
  dateFrom?: string, dateTo?: string, storeId: number = 1,
): Promise<AnomalyResponse> {
  const p = new URLSearchParams()
  p.set('store_id', String(storeId))
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return fetchJson<AnomalyResponse>(`${BASE}/anomalies?${p.toString()}`)
}

// ── SKU 管理 API ──

export async function getSkuManagement(storeId: number = 1): Promise<SkuManagementRow[]> {
  return fetchJson<SkuManagementRow[]>(`${BASE}/sku-management?store_id=${storeId}`)
}

export async function batchUpdateSkuManagement(
  items: SkuManagementUpdate[],
  storeId: number = 1,
): Promise<SkuManagementRow[]> {
  return fetchJson<SkuManagementRow[]>(
    `${BASE}/sku-management/batch?store_id=${storeId}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ items }),
    },
  )
}

// ── 供应链 API（中台数据）──

function procurementParams(dateFrom?: string, dateTo?: string): string {
  const p = new URLSearchParams()
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  return p.toString()
}

// 申购计划
export async function getPlanOverview(dateFrom?: string, dateTo?: string): Promise<PlanOverview> {
  return fetchJson<PlanOverview>(`${BASE}/procurement/plan/overview?${procurementParams(dateFrom, dateTo)}`)
}
export async function getPlanList(
  dateFrom?: string, dateTo?: string, page?: number, pageSize?: number,
): Promise<PlanListResponse> {
  const p = new URLSearchParams()
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  if (page) p.set('page', String(page))
  if (pageSize) p.set('page_size', String(pageSize))
  return fetchJson<PlanListResponse>(`${BASE}/procurement/plan/list?${p.toString()}`)
}
export async function getPlanDetail(poPlanNo: string): Promise<PlanDetail> {
  return fetchJson<PlanDetail>(`${BASE}/procurement/plan/${encodeURIComponent(poPlanNo)}`)
}

// 采购订单
export async function getPurOrderOverview(dateFrom?: string, dateTo?: string): Promise<PurOrderOverview> {
  return fetchJson<PurOrderOverview>(`${BASE}/procurement/order/overview?${procurementParams(dateFrom, dateTo)}`)
}
export async function getPurOrderList(
  dateFrom?: string, dateTo?: string, page?: number, pageSize?: number,
): Promise<PurOrderListResponse> {
  const p = new URLSearchParams()
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  if (page) p.set('page', String(page))
  if (pageSize) p.set('page_size', String(pageSize))
  return fetchJson<PurOrderListResponse>(`${BASE}/procurement/order/list?${p.toString()}`)
}
export async function getPurOrderDetail(poNo: string): Promise<PurOrderDetail> {
  return fetchJson<PurOrderDetail>(`${BASE}/procurement/order/${encodeURIComponent(poNo)}`)
}

// 头程发货
export async function getShippingOverview(dateFrom?: string, dateTo?: string): Promise<ShippingOverview> {
  return fetchJson<ShippingOverview>(`${BASE}/procurement/shipping/overview?${procurementParams(dateFrom, dateTo)}`)
}
export async function getShippingList(
  dateFrom?: string, dateTo?: string, page?: number, pageSize?: number,
): Promise<ShippingListResponse> {
  const p = new URLSearchParams()
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  if (page) p.set('page', String(page))
  if (pageSize) p.set('page_size', String(pageSize))
  return fetchJson<ShippingListResponse>(`${BASE}/procurement/shipping/list?${p.toString()}`)
}
export async function getShippingDetail(orderCode: string): Promise<ShippingDetail> {
  return fetchJson<ShippingDetail>(`${BASE}/procurement/shipping/${encodeURIComponent(orderCode)}`)
}

// ============================================================
// OZON 直发信息
// ============================================================

// SKU 基础数据
export async function getDirectSkuList(
  page?: number, pageSize?: number, search?: string, storeName?: string,
): Promise<DirectListResponse<DirectSkuItem>> {
  const p = new URLSearchParams()
  if (page) p.set('page', String(page))
  if (pageSize) p.set('page_size', String(pageSize))
  if (search) p.set('search', search)
  if (storeName) p.set('store_name', storeName)
  return fetchJson<DirectListResponse<DirectSkuItem>>(`${BASE}/ozon-direct/sku?${p.toString()}`)
}
export async function getDirectSku(id: number): Promise<DirectSkuItem> {
  return fetchJson<DirectSkuItem>(`${BASE}/ozon-direct/sku/${id}`)
}
export async function createDirectSku(body: DirectSkuUpdate): Promise<DirectSkuItem> {
  return fetchJson<DirectSkuItem>(`${BASE}/ozon-direct/sku`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
}
export async function updateDirectSku(id: number, body: DirectSkuUpdate): Promise<DirectSkuItem> {
  return fetchJson<DirectSkuItem>(`${BASE}/ozon-direct/sku/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
}
export async function deleteDirectSku(id: number): Promise<{ ok: boolean }> {
  return fetchJson<{ ok: boolean }>(`${BASE}/ozon-direct/sku/${id}`, { method: 'DELETE' })
}

// 直发跟进表
export async function getDirectShipmentList(
  page?: number, pageSize?: number, search?: string, dateFrom?: string, dateTo?: string, receivingStatus?: string,
): Promise<DirectListResponse<DirectShipmentItem>> {
  const p = new URLSearchParams()
  if (page) p.set('page', String(page))
  if (pageSize) p.set('page_size', String(pageSize))
  if (search) p.set('search', search)
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  if (receivingStatus) p.set('receiving_status', receivingStatus)
  return fetchJson<DirectListResponse<DirectShipmentItem>>(`${BASE}/ozon-direct/shipment?${p.toString()}`)
}
export async function getDirectShipment(id: number): Promise<DirectShipmentItem> {
  return fetchJson<DirectShipmentItem>(`${BASE}/ozon-direct/shipment/${id}`)
}
export async function createDirectShipment(body: DirectShipmentUpdate): Promise<DirectShipmentItem> {
  return fetchJson<DirectShipmentItem>(`${BASE}/ozon-direct/shipment`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
}
export async function updateDirectShipment(id: number, body: DirectShipmentUpdate): Promise<DirectShipmentItem> {
  return fetchJson<DirectShipmentItem>(`${BASE}/ozon-direct/shipment/${id}`, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  })
}
export async function deleteDirectShipment(id: number): Promise<{ ok: boolean }> {
  return fetchJson<{ ok: boolean }>(`${BASE}/ozon-direct/shipment/${id}`, { method: 'DELETE' })
}

// 文件
export async function getDirectFiles(sourceTable: string, sku: string, prNo?: string): Promise<DirectFileItem[]> {
  let url = `${BASE}/ozon-direct/files/by-source?source_table=${sourceTable}&sku=${encodeURIComponent(sku)}`
  if (prNo) url += `&pr_no=${encodeURIComponent(prNo)}`
  return fetchJson<DirectFileItem[]>(url)
}
export async function uploadDirectFile(file: File, sourceTable: string, sku: string, prNo?: string): Promise<DirectFileItem> {
  const formData = new FormData()
  formData.append('file', file)
  let url = `${BASE}/ozon-direct/files/upload?source_table=${sourceTable}&sku=${encodeURIComponent(sku)}`
  if (prNo) url += `&pr_no=${encodeURIComponent(prNo)}`
  return fetchJson<DirectFileItem>(url, { method: 'POST', body: formData })
}
export async function deleteDirectFile(id: number): Promise<{ ok: boolean }> {
  return fetchJson<{ ok: boolean }>(`${BASE}/ozon-direct/files/${id}`, { method: 'DELETE' })
}
export function getDirectFileUrl(fileId: number): string {
  return `${BASE}/ozon-direct/files/${fileId}`
}

// 导入导出
export async function importDirectExcel(file: File): Promise<{ ok: boolean; sku_count: number; shipment_count: number }> {
  const formData = new FormData()
  formData.append('file', file)
  return fetchJson(`${BASE}/ozon-direct/import`, { method: 'POST', body: formData })
}
export function getExportUrl(): string {
  return `${BASE}/ozon-direct/export`
}

// ── 供应链 SKU 聚合 ──

export async function getSkuPipelineList(
  dateFrom?: string, dateTo?: string, page?: number, pageSize?: number,
): Promise<SkuPipelineListResponse> {
  const p = new URLSearchParams()
  if (dateFrom) p.set('date_from', dateFrom)
  if (dateTo) p.set('date_to', dateTo)
  if (page) p.set('page', String(page))
  if (pageSize) p.set('page_size', String(pageSize))
  return fetchJson<SkuPipelineListResponse>(`${BASE}/procurement/sku-pipeline?${p.toString()}`)
}

export async function getSkuPipelineDetail(itemId: string): Promise<SkuPipelineDetail> {
  return fetchJson<SkuPipelineDetail>(`${BASE}/procurement/sku-pipeline/${encodeURIComponent(itemId)}`)
}
