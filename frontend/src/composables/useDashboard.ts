import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { Product, SummaryRow, SummaryStats, DateRangeInfo } from '@/types'
import { getProducts, getSummary, getSummaryStats, getDateRange } from '@/api'

export function useDashboard() {
  // 筛选条件
  const dateRange = ref<[string, string] | null>(null)
  const selectedSkuId = ref<number | undefined>(undefined)

  // 数据
  const products = ref<Product[]>([])
  const summaryRows = ref<SummaryRow[]>([])
  const stats = ref<SummaryStats | null>(null)
  const availableRange = ref<DateRangeInfo | null>(null)
  const loading = ref(false)

  // 按日期聚合 — 趋势图使用
  const dailyAggregation = computed(() => {
    const map = new Map<string, { revenue: number; net_profit: number; ordered_units: number; delivered_units: number; returns_units: number }>()
    for (const row of summaryRows.value) {
      const d = map.get(row.date) || { revenue: 0, net_profit: 0, ordered_units: 0, returns_units: 0 }
      d.revenue += row.revenue
      d.net_profit += row.net_profit
      d.ordered_units += row.ordered_units
      d.delivered_units += row.delivered_units
      d.returns_units += row.returns_units
      map.set(row.date, d)
    }
    return Array.from(map.entries())
      .map(([date, v]) => ({ date, ...v }))
      .sort((a, b) => a.date.localeCompare(b.date))
  })

  // 按 SKU 聚合 — 商品汇总表（基于全量商品列表，缺失商品填 0）
  const productSummary = computed(() => {
    const map = new Map<number, {
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
    }>()

    // 先填充全量商品（兜底值，stock 用 products 表的真实库存）
    for (const p of products.value) {
      map.set(p.sku_id, {
        sku_id: p.sku_id,
        offer_id: p.offer_id,
        name: p.name,
        primary_image: p.primary_image,
        revenue: 0,
        net_profit: 0,
        profit_margin: 0,
        ordered_units: 0,
        delivered_units: 0,
        cancelled_units: 0,
        returns_amount: 0,
        returns_units: 0,
        commissions: 0,
        logistics_costs: 0,
        storage_fees: 0,
        advertising: 0,
        promotion_costs: 0,
        other_costs: 0,
        commission_rate: p.commission_fbo_pct != null ? Number(p.commission_fbo_pct) * 100 : null,
        stock_present: p.stock_present,
        stock_reserved: p.stock_reserved,
        day_count: 0,
      })
    }

    // 用汇总数据覆盖（不覆盖 stock，stock 始终用 products 表的真实库存）
    for (const row of summaryRows.value) {
      const d = map.get(row.sku_id)
      if (d) {
        d.revenue += row.revenue
        d.net_profit += row.net_profit
        d.ordered_units += row.ordered_units
        d.delivered_units += row.delivered_units
        d.cancelled_units += row.cancelled_units
        d.returns_amount += row.returns_amount
        d.returns_units += row.returns_units
        d.commissions += row.commissions
        d.logistics_costs += row.logistics_costs
        d.storage_fees += row.storage_fees
        d.advertising += row.advertising
        d.promotion_costs += row.promotion_costs
        d.other_costs += row.other_costs
        d.day_count += 1
        if (row.primary_image) d.primary_image = row.primary_image
      }
    }

    const arr = Array.from(map.values())
    for (const p of arr) {
      p.profit_margin = p.revenue > 0 ? (p.net_profit / p.revenue) * 100 : 0
    }
    return arr.sort((a, b) => b.revenue - a.revenue)
  })

  // 日期禁用函数：只能选有数据的日期范围
  function disabledDate(time: Date): boolean {
    if (!availableRange.value) return false
    const d = time.toISOString().split('T')[0]
    const today = new Date().toISOString().split('T')[0]
    return d < availableRange.value.min_date || d > today  // 不能选未来
  }

  // 获取可用日期范围
  async function fetchDateRange() {
    try {
      availableRange.value = await getDateRange()
      // 初始化日期范围：默认到今天
      const today = new Date().toISOString().split('T')[0]
      dateRange.value = [
        availableRange.value.min_date,
        availableRange.value.max_date,
      ]
    } catch {
      // 如果失败，退回到最近 30 天
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 30)
      dateRange.value = [
        start.toISOString().split('T')[0],
        end.toISOString().split('T')[0],
      ]
    }
  }

  // 加载商品列表
  async function fetchProducts() {
    try {
      products.value = await getProducts()
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载商品列表失败: ' + msg)
    }
  }

    // 将 API 返回的字符串数字转为真正的数字
  function toNum(v: unknown): number {
    if (typeof v === 'number') return v
    if (typeof v === 'string') return Number(v)
    return 0
  }

  function normalizeRow(r: SummaryRow): SummaryRow {
    return {
      ...r,
      revenue: toNum(r.revenue),
      stock_present: toNum(r.stock_present),
      stock_reserved: toNum(r.stock_reserved),
      ordered_units: toNum(r.ordered_units),
      delivered_units: toNum(r.delivered_units),
      cancelled_units: toNum(r.cancelled_units),
      returns_amount: toNum(r.returns_amount),
      returns_units: toNum(r.returns_units),
      commissions: toNum(r.commissions),
      logistics_costs: toNum(r.logistics_costs),
      storage_fees: toNum(r.storage_fees),
      advertising: toNum(r.advertising),
      promotion_costs: toNum(r.promotion_costs),
      other_costs: toNum(r.other_costs),
      net_profit: toNum(r.net_profit),
      profit_margin: toNum(r.profit_margin),
    }
  }

  function normalizeStats(s: SummaryStats): SummaryStats {
    return {
      ...s,
      total_revenue: toNum(s.total_revenue),
      total_net_profit: toNum(s.total_net_profit),
      avg_profit_margin: toNum(s.avg_profit_margin),
      total_ordered_units: toNum(s.total_ordered_units),
      total_commissions: toNum(s.total_commissions),
      total_logistics: toNum(s.total_logistics),
      total_returns: toNum(s.total_returns),
      total_returns_units: toNum(s.total_returns_units),
      total_storage: toNum(s.total_storage),
      total_advertising: toNum(s.total_advertising),
      total_promotion: toNum(s.total_promotion),
      total_other_costs: toNum(s.total_other_costs),
    }
  }

  // 加载看板数据
  async function fetchData() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [rows, st] = await Promise.all([
        getSummary(dateRange.value[0], dateRange.value[1], selectedSkuId.value),
        getSummaryStats(dateRange.value[0], dateRange.value[1], selectedSkuId.value),
      ])
      summaryRows.value = rows.map(normalizeRow)
      stats.value = normalizeStats(st)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载看板数据失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  // 当筛选条件变化时重新加载
  watch(dateRange, () => {
    if (dateRange.value) fetchData()
  })

  watch(selectedSkuId, () => {
    if (dateRange.value) fetchData()
  })

  fetchDateRange()

  return {
    dateRange,
    selectedSkuId,
    products,
    summaryRows,
    stats,
    loading,
    dailyAggregation,
    productSummary,
    disabledDate,
    availableRange,
    fetchProducts,
    fetchData,
  }
}
