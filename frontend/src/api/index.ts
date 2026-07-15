import type { Product, SummaryRow, SummaryStats, SyncStatus, DateRangeInfo, FinanceTransaction } from '@/types'

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
