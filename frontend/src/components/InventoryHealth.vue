<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import type { ProductSummary, SummaryRow, ReplenishmentRow } from '@/types'
import { getStockStatus, refreshStocks, getReplenishment, getSummary } from '@/api'
import { useLocalDateRange } from '@/composables/useLocalDateRange'
import { useStore } from '@/composables/useStore'

const props = defineProps<{
  products: ProductSummary[]
  summaryRows: SummaryRow[]
  activeTab: string
}>()

const emit = defineEmits<{
  (e: 'row-click', product: ProductSummary): void
  (e: 'refresh-products'): void
}>()

// 库存状态
const stockStatus = ref<{ last_updated: string | null; stock_count: number }>({ last_updated: null, stock_count: 0 })
const refreshing = ref(false)

// 成交量的独立日期筛选（与退货/订单 Tab 一致）
const { selectedStoreId } = useStore()
const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

const salesSummaryRows = ref<SummaryRow[]>([])
const salesLoading = ref(false)

async function fetchSalesData() {
  if (!localDateRange.value) return
  salesLoading.value = true
  try {
    salesSummaryRows.value = await getSummary(
      localDateRange.value[0], localDateRange.value[1],
      undefined, selectedStoreId.value,
    )
  } catch { /* ignore */ }
  finally { salesLoading.value = false }
}

watch(localDateRange, () => { fetchSalesData() }, { immediate: true })
watch(selectedStoreId, () => { fetchSalesData() })

// 实际成交 = ordered - cancelled - returns，按独立日期范围聚合
const actualSalesMap = computed(() => {
  const map = new Map<number, number>()
  for (const r of salesSummaryRows.value) {
    const v = (Number(r.ordered_units) || 0) - (Number(r.cancelled_units) || 0) - (Number(r.returns_units) || 0)
    map.set(r.sku_id, (map.get(r.sku_id) || 0) + v)
  }
  return map
})

const replenishmentMap = ref<Map<number, { available_days: number | null; alert_level: string; actual_sales_3d: number; actual_sales_7d: number; actual_sales_14d: number; actual_sales_30d: number }>>(new Map())

async function fetchStockStatus() {
  try {
    stockStatus.value = await getStockStatus()
  } catch { /* ignore */ }
}

async function fetchReplenishmentData() {
  try {
    const data = await getReplenishment(0)
    const map = new Map<number, { available_days: number | null; alert_level: string; actual_sales_3d: number; actual_sales_7d: number; actual_sales_14d: number; actual_sales_30d: number }>()
    for (const r of data) {
      map.set(r.sku_id, {
        available_days: r.available_days,
        alert_level: r.alert_level,
        actual_sales_3d: r.sales_3d,
        actual_sales_7d: r.sales_7d,
        actual_sales_14d: r.sales_14d,
        actual_sales_30d: r.sales_30d,
      })
    }
    replenishmentMap.value = map
  } catch { /* ignore */ }
}

async function handleRefresh() {
  refreshing.value = true
  try {
    const res = await refreshStocks()
    if (res.ok) {
      ElMessage.success(res.message || '库存已刷新')
      await fetchStockStatus()
      emit('refresh-products')
    } else {
      ElMessage.error(res.message || '刷新失败')
    }
  } catch (e: unknown) {
    ElMessage.error('刷新库存失败: ' + (e instanceof Error ? e.message : '未知错误'))
  } finally {
    refreshing.value = false
  }
}

function formatUpdateTime(t: string | null): string {
  if (!t) return '未知'
  // t is ISO format like '2026-07-21T11:39:14'
  const d = new Date(t + (t.endsWith('Z') ? '' : 'Z'))
  const now = new Date()
  const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000)
  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH} 小时前`
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

const selectedSkuId = ref<number | null>(null)
const selectedSkuLabel = computed(() => {
  if (selectedSkuId.value === null) return '全部商品'
  const p = props.products.find(x => x.sku_id === selectedSkuId.value)
  const oid = p?.offer_id || '—'
  return `SKU ${selectedSkuId.value} / ${oid}`
})

// 当前真实总库存（从 products/stocks 表读取）
const realTotalStock = computed(() =>
  props.products.reduce((s, p) => s + p.stock_present, 0)
)

const selectedSkuStock = computed(() => {
  if (selectedSkuId.value === null) return null
  return props.products.find(p => p.sku_id === selectedSkuId.value)?.stock_present ?? 0
})

// ─── 按日期聚合 ──────────────────────────────────────────

function dailyAgg(field: 'ordered_units' | 'delivered_units' | 'returns_units') {
  const rows = selectedSkuId.value === null
    ? props.summaryRows
    : props.summaryRows.filter(r => r.sku_id === selectedSkuId.value)
  const map = new Map<string, number>()
  for (const row of rows) {
    const v = Number(row[field]) || 0
    map.set(row.date, (map.get(row.date) || 0) + v)
  }
  return Array.from(map.entries())
    .map(([date, units]) => ({ date, units }))
    .sort((a, b) => a.date.localeCompare(b.date))
}

const dailyOrders = computed(() => dailyAgg('ordered_units'))
const dailyDelivered = computed(() => dailyAgg('delivered_units'))
const dailyReturns = computed(() => dailyAgg('returns_units'))

// ─── 库存历史：从当前真实库存往回推算 ──

const estimatedStockHistory = computed(() => {
  const byDate = new Map<string, { delivered: number; returns: number }>()
  for (const d of dailyDelivered.value) {
    const entry = byDate.get(d.date) || { delivered: 0, returns: 0 }
    entry.delivered = d.units
    byDate.set(d.date, entry)
  }
  for (const d of dailyReturns.value) {
    const entry = byDate.get(d.date) || { delivered: 0, returns: 0 }
    entry.returns = d.units
    byDate.set(d.date, entry)
  }

  // 用 dailyOrders 的日期作为时间轴
  const sorted = dailyOrders.value
  if (sorted.length === 0) return []

  const currentStock = selectedSkuId.value === null
    ? realTotalStock.value
    : (selectedSkuStock.value ?? 0)

  // 从最晚日期往回推算: stock[prev] = stock[cur] + delivered[prev] - returns[prev]
  // stock[t-1] = stock[t] + delivered[t] - returns[t]
  const result = new Array<{ date: string; stock: number }>(sorted.length)
  let running = currentStock
  for (let i = sorted.length - 1; i >= 0; i--) {
    const d = sorted[i].date
    const flow = byDate.get(d) || { delivered: 0, returns: 0 }
    result[i] = { date: d, stock: Math.max(0, Math.round(running)) }
    running = running + flow.delivered - flow.returns
  }

  return result
})

// ─── 库存列表 ─────────────────────────────────────────

interface InventoryItem {
  sku_id: number
  offer_id: string
  name: string
  primary_image: string | null
  stock_present: number
  stock_month_start: number | null
  actual_sales: number
  status: 'danger' | 'warning' | 'success'
  status_label: string
  available_days: number | null
  alert_level: string
}



const ALERT_LABELS: Record<string, string> = {
  emergency: '紧急',
  warning: '预警',
  normal: '正常',
}

const items = computed<InventoryItem[]>(() => {
  return props.products
    .map(p => {
      let status: 'danger' | 'warning' | 'success'
      let status_label: string
      if (p.stock_present <= 0) {
        status = 'danger'; status_label = '缺货'
      } else if (p.stock_present < 10) {
        status = 'warning'; status_label = '低库存'
      } else {
        status = 'success'; status_label = '健康'
      }
      const rp = replenishmentMap.value.get(p.sku_id)
      return {
        sku_id: p.sku_id, offer_id: p.offer_id, name: p.name,
        primary_image: p.primary_image, stock_present: p.stock_present,
        stock_month_start: p.stock_month_start ?? null,
        actual_sales: actualSalesMap.value.get(p.sku_id) ?? 0,
        status, status_label,
        available_days: rp?.available_days ?? null,
        alert_level: rp?.alert_level ?? 'normal',
      }
    })
    .sort((a, b) => {
      const rank = { emergency: 0, warning: 1, normal: 2 }
      const ar = rank[a.alert_level as keyof typeof rank] ?? 2
      const br = rank[b.alert_level as keyof typeof rank] ?? 2
      return ar - br || a.stock_present - b.stock_present
    })
})

const searchInput = ref('')
const searchKeyword = ref('')
const statusInput = ref('')
const statusFilter = ref('')
function applySearch() { searchKeyword.value = searchInput.value; statusFilter.value = statusInput.value }
function handleClear() { searchInput.value = ''; statusInput.value = ''; searchKeyword.value = ''; statusFilter.value = '' }

const filteredItems = computed(() => {
  const kw = searchKeyword.value.trim().toLowerCase()
  const sf = statusFilter.value
  return items.value.filter(i => {
    if (sf && i.status !== sf) return false
    if (kw && !(i.name || '').toLowerCase().includes(kw) && !(i.offer_id || '').toLowerCase().includes(kw) && !String(i.sku_id).includes(kw)) return false
    return true
  })
})

const overview = computed(() => {
  const total = items.value.length
  const total_stock = items.value.reduce((s, i) => s + i.stock_present, 0)
  const danger = items.value.filter(i => i.status === 'danger').length
  const warning = items.value.filter(i => i.status === 'warning').length
  return { total, total_stock, danger, warning }
})

// ─── 图表 ──────────────────────────────────────────────

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

const COLOR: Record<string, string> = { '库存': '#409eff', '下单': '#e6a23c' }

function renderChart() {
  if (!chart || estimatedStockHistory.value.length === 0) return

  const dates = estimatedStockHistory.value.map(d => d.date.slice(5))
  const stockData = estimatedStockHistory.value.map(d => d.stock)
  const orderData = dailyOrders.value.map(d => d.units)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const items = Array.isArray(params) ? params : [params]
        let h = `<div style="font-size:13px;line-height:1.8"><strong>${items[0].axisValue}</strong>`
        for (const p of items) {
          const c = COLOR[p.seriesName] || '#909399'
          const suffix = p.seriesName === '库存' ? ' 件（推算）' : ' 件'
          h += `<br/><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${c};margin-right:4px"></span>${p.seriesName}: <strong>${Number(p.value).toLocaleString()}${suffix}</strong>`
        }
        return h + '</div>'
      },
    },
    grid: { left: 60, right: 30, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 }, min: 0 },
    legend: { data: ['库存', '下单'], bottom: 0 },
    series: [
      {
        name: '库存', type: 'line', data: stockData,
        smooth: true, symbol: 'circle', symbolSize: 5,
        lineStyle: { width: 2, color: '#409eff' },
        itemStyle: { color: '#409eff' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.2)' },
          { offset: 1, color: 'rgba(64,158,255,0.02)' },
        ])},
      },
      {
        name: '下单', type: 'line', data: orderData,
        smooth: true, symbol: 'circle', symbolSize: 4,
        lineStyle: { width: 2, color: '#e6a23c' },
        itemStyle: { color: '#e6a23c' },
      },
    ],
  }, true)
}

let initialized = false
function initIfNeeded() {
  if (initialized) return
  chart = echarts.init(chartRef.value!)
  initialized = true
  renderChart()
}

function selectSku(skuId: number) {
  selectedSkuId.value = selectedSkuId.value === skuId ? null : skuId
}

onMounted(() => { if (props.activeTab === 'inventory') { initIfNeeded(); fetchStockStatus(); fetchReplenishmentData() } })
watch(() => props.activeTab, (tab) => {
  if (tab === 'inventory') { nextTick(() => { initIfNeeded(); chart?.resize() }); fetchReplenishmentData() }
})
watch(() => [estimatedStockHistory.value, dailyOrders.value], () => { if (initialized) renderChart() })
onUnmounted(() => { chart?.dispose() })

function statusTagType(s: string) { return s === 'danger' ? 'danger' : s === 'warning' ? 'warning' : 'success' }
</script>

<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-weight: 600">
                📈 {{ selectedSkuId === null ? '库存趋势 + 下单' : selectedSkuLabel + ' 趋势' }}
              </span>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-tooltip content="库存 = 从当前实时库存往回推算：stock[t-1] ≈ stock[t] + delivered[t] - returns[t]。每日 5:00 自动同步 stocks 表" placement="top">
                  <span style="font-size: 11px; color: #909399; cursor: help; border-bottom: 1px dashed #c0c4cc;">推算规则</span>
                </el-tooltip>
                <el-button size="small" :loading="refreshing" @click="handleRefresh">
                  刷新库存 · {{ formatUpdateTime(stockStatus.last_updated) }}
                </el-button>
                <el-button v-if="selectedSkuId !== null" size="small" @click="selectSku(selectedSkuId!)">显示全部</el-button>
                <el-tag type="info" size="small">{{ estimatedStockHistory.length }} 天</el-tag>
              </div>
            </div>
          </template>
          <div ref="chartRef" style="width: 100%; height: 360px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span style="font-weight: 600">📋 库存概况</span></template>
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0;">
              <span style="color: #909399;">商品总数</span><span style="font-weight: 600;">{{ overview.total }} 个</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0;">
              <span style="color: #909399;">总库存</span><span style="font-weight: 600;">{{ overview.total_stock.toLocaleString() }} 件</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0;">
              <span style="color: #909399;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #f56c6c; margin-right: 4px;" />缺货</span>
              <el-tag size="small" :type="overview.danger > 0 ? 'danger' : 'info'">{{ overview.danger }}</el-tag>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 6px 0;">
              <span style="color: #909399;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #e6a23c; margin-right: 4px;" />低库存</span>
              <el-tag size="small" :type="overview.warning > 0 ? 'warning' : 'info'">{{ overview.warning }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
          <span style="font-weight: 600; white-space: nowrap;">库存列表</span>
          <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
            <span style="font-size: 11px; color: #909399;">成交</span>
            <el-select v-model="periodPreset" style="width: 90px" size="small" @change="applyPreset">
              <el-option label="昨天" value="yesterday" />
              <el-option label="近7天" value="7days" />
              <el-option label="近30天" value="30days" />
              <el-option label="本月" value="thisMonth" />
              <el-option label="全部" value="all" />
              <el-option label="自定义" value="custom" />
            </el-select>
            <el-date-picker
              v-if="showCustomDate"
              v-model="localDateRange"
              type="daterange"
              size="small"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 220px"
              :disabled-date="disabledDate"
            />
            <el-input v-model="searchInput" placeholder="搜索名称 / 货号 / SKU" clearable style="width: 190px;" size="small" @clear="handleClear" @keyup.enter="applySearch" />
            <el-select v-model="statusInput" placeholder="库存状态" style="width: 105px;" size="small" @change="applySearch">
              <el-option label="全部" value="" /><el-option label="缺货" value="danger" /><el-option label="低库存" value="warning" /><el-option label="健康" value="success" />
            </el-select>
            <el-tag type="info" size="small">{{ filteredItems.length }} / {{ items.length }}</el-tag>
          </div>
        </div>
      </template>
      <el-table :data="filteredItems" stripe size="small" style="width: 100%" max-height="480" highlight-current-row @row-click="(row: InventoryItem) => selectSku(row.sku_id)">
        <el-table-column prop="sku_id" label="SKU" width="100" sortable>
          <template #default="{ row }"><span style="font-family: monospace; font-size: 12px;">{{ row.sku_id }}</span></template>
        </el-table-column>
        <el-table-column prop="offer_id" label="货号" width="200" sortable>
          <template #default="{ row }"><span style="font-family: monospace; font-size: 12px; color: #909399;">{{ row.offer_id }}</span></template>
        </el-table-column>
        <el-table-column label="图片" width="56" align="center">
          <template #default="{ row }">
            <el-image v-if="row.primary_image" :src="row.primary_image" style="width: 36px; height: 36px; border-radius: 4px;" fit="cover" lazy>
              <template #error><div style="width: 36px; height: 36px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #c0c4cc;">无</div></template>
            </el-image>
            <div v-else style="width: 36px; height: 36px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #c0c4cc;">无</div>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商品名称" min-width="140" show-overflow-tooltip />
        <el-table-column prop="stock_present" label="现有库存" width="80" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.stock_present <= 0 ? '#f56c6c' : row.stock_present < 10 ? '#e6a23c' : '#303133', fontWeight: row.stock_present <= 0 ? 700 : 400 }">{{ row.stock_present }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="stock_month_start" label="月初库存" width="80" align="right" sortable>
          <template #header>
            <el-tooltip content="当月1号的每日快照库存（莫斯科日口径）；该SKU月初无快照则显示 —" placement="top">
              <span>月初库存</span>
            </el-tooltip>
          </template>
          <template #default="{ row }">
            <span v-if="row.stock_month_start === null">—</span>
            <span v-else>{{ row.stock_month_start }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="actual_sales" label="实际成交" width="80" align="right" sortable />
        <el-table-column label="可售天数" width="80" align="right" sortable prop="available_days">
          <template #default="{ row }">
            <el-tag v-if="row.available_days === null" type="info" size="small" effect="plain">∞</el-tag>
            <el-tag v-else-if="row.alert_level === 'emergency'" type="danger" size="small" effect="dark">{{ row.available_days }}</el-tag>
            <el-tag v-else-if="row.alert_level === 'warning'" type="warning" size="small" effect="dark">{{ row.available_days }}</el-tag>
            <el-tag v-else type="success" size="small" effect="plain">{{ row.available_days }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预警" width="70" align="center" sortable prop="alert_level">
          <template #default="{ row }">
            <el-tag v-if="row.alert_level === 'emergency'" type="danger" size="small" effect="dark">紧急</el-tag>
            <el-tag v-else-if="row.alert_level === 'warning'" type="warning" size="small" effect="dark">预警</el-tag>
            <el-tag v-else type="success" size="small" effect="plain">正常</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="库存状态" width="100" align="center">
          <template #default="{ row }"><el-tag :type="statusTagType(row.status)" size="small" effect="dark">{{ row.status_label }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
