<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { Document, Van, Box, CircleCheck, CircleClose, TrendCharts } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import type { Product, OrderListItem } from '@/types'
import { useOrders } from '@/composables/useOrders'
import { useLocalDateRange } from '@/composables/useLocalDateRange'
import { getSkuNote, saveSkuNote, getSkuNoteDates } from '@/api'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()
const selectedSkuId = ref<number>()

// ── 状态映射 ────────────────────────────────────────────
const STATUS_MAP: Record<string, { label: string; type: string }> = {
  awaiting_packaging: { label: '等待打包', type: 'info' },
  awaiting_deliver: { label: '待发货', type: 'warning' },
  delivering: { label: '配送中', type: 'primary' },
  delivered: { label: '已签收', type: 'success' },
  cancelled: { label: '已取消', type: 'danger' },
}
function statusLabel(st: string | null) {
  if (!st) return '—'
  return STATUS_MAP[st]?.label || st
}
function statusTagType(st: string | null) {
  if (!st) return 'info'
  return STATUS_MAP[st]?.type || 'info'
}

// ── composable ──────────────────────────────────────────
const {
  loading, overview, trend,
  orderList, listTotal, currentPage, pageSize,
  statusFilter, schemaFilter, searchFilter,
  viewMode, skuStats,
  selectedOrder, fetchDetail, clearDetail,
} = useOrders(localDateRange, selectedSkuId)

// ── 订单详情抽屉 ────────────────────────────────────────
const drawerVisible = ref(false)

async function onRowClick(row: OrderListItem) {
  drawerVisible.value = true
  await fetchDetail(row.posting_number)
}

function onDrawerClosed() {
  clearDetail()
}

// ── SKU 点击筛选 ────────────────────────────────────────
function skuRowClassName({ row }: { row: any }): string {
  return row.sku_id === selectedSkuId.value ? 'selected-sku-row' : ''
}
function onSkuRowClick(row: any) {
  if (selectedSkuId.value === row.sku_id) {
    selectedSkuId.value = undefined
  } else {
    selectedSkuId.value = row.sku_id
  }
}
function clearSkuFilter() {
  selectedSkuId.value = undefined
  viewMode.value = 'sku'
}

// ── SKU 搜索 ────────────────────────────────────────────
const skuSearch = ref('')
const onlyOptimize = ref(false)
const filteredSkuStats = computed(() => {
  const q = skuSearch.value.trim().toLowerCase()
  let list = skuStats.value
  if (onlyOptimize.value) {
    list = list.filter(s => s.recent_deals === 0 && s.stock > 0)
  }
  if (!q) return list
  return list.filter(s =>
    String(s.sku_id).includes(q) || (s.offer_id || '').toLowerCase().includes(q)
  )
})

const selectedSkuName = computed(() => {
  if (!selectedSkuId.value) return ''
  const s = skuStats.value.find(s => s.sku_id === selectedSkuId.value)
  return s ? (s.offer_id || `SKU ${s.sku_id}`) : ''
})
// ── 趋势图 ──────────────────────────────────────────────
const trendChartRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null

function renderTrendChart() {
  if (!trendChart || !trend.value.length) return
  const dates = trend.value.map(d => d.date.slice(5))
  const fullDates = trend.value.map(d => d.date)
  trendChart.off('click')
  trendChart.getZr().off('click')
  trendChart.getZr().on('click', (e: any) => {
    if (!selectedSkuId.value) return
    // legend 区域不触发
    if (e.offsetY > trendChart!.getHeight() - 40) return
    const pointInGrid = trendChart!.convertFromPixel({ seriesIndex: 0 }, [e.offsetX, e.offsetY])
    const dataIdx = Math.round(pointInGrid[0])
    if (dataIdx >= 0 && dataIdx < fullDates.length) {
      noteDate.value = fullDates[dataIdx]
      noteVisible.value = true
      loadNote()
    }
  })
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const items = Array.isArray(params) ? params : [params]
        let h = `<div style="font-size:13px;line-height:1.8"><strong>${items[0].axisValue}</strong>`
        const units: Record<string, string> = { '实际售出': '单', '实际成交': '单', '售价': '₽', '折扣': '%', '绿标价': '₽' }
        for (const p of items) {
          const u = units[p.seriesName] || ''
          let v: string
          if (u === '₽') v = Number(p.value).toLocaleString('ru-RU') + ' ₽'
          else if (u === '%') v = (p.value != null ? Number(p.value).toFixed(1) : '—') + '%'
          else v = Number(p.value).toLocaleString() + ' 单'
          h += `<br/><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px"></span>${p.seriesName}: <strong>${v}</strong>` }
        return h + '</div>'
      },
    },
    legend: { data: ['实际售出', '实际成交', '售价', '折扣', '绿标价'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'category', data: dates,
      axisLabel: {
        fontSize: 11,
        rotate: dates.length > 30 ? 45 : 0,
        formatter: (val: string) => noteShortSet.value.has(val) ? `${val}\n{note|●}` : val,
        rich: {
          note: { color: '#f56c6c', fontSize: 9, align: 'center', lineHeight: 12 },
        },
      },
    },
    yAxis: [
      { type: 'value', min: 0, minInterval: 1, name: '单' },
      { type: 'value', min: 0, name: '₽', axisLabel: { formatter: (v: number) => v >= 1000 ? (v/1000).toFixed(0)+'k' : String(v) } },
    ],
    series: [
      {
        name: '实际售出', type: 'line', data: trend.value.map(d => d.ordered - d.cancelled),
        lineStyle: { width: 3, type: 'dashed' }, itemStyle: { color: '#409eff' },
        symbol: 'circle', symbolSize: 4,
      },
      {
        name: '实际成交', type: 'line', data: trend.value.map(d => d.ordered - d.cancelled - d.client_return),
        lineStyle: { width: 3 }, itemStyle: { color: '#67c23a' },
        symbol: 'diamond', symbolSize: 6, areaStyle: { color: 'rgba(103,194,58,0.1)' },
      },
      {
        name: '售价', type: 'line', yAxisIndex: 1, data: trend.value.map(d => d.price),
        lineStyle: { width: 2, type: 'dotted' }, itemStyle: { color: '#e6a23c' },
        symbol: 'triangle', symbolSize: 6,
      },
      {
        name: '折扣', type: 'line', yAxisIndex: 1, data: trend.value.map(d => d.discount),
        lineStyle: { width: 1.5, type: 'dashed' }, itemStyle: { color: '#909399' },
        symbol: 'diamond', symbolSize: 4,
      },
      {
        name: '绿标价', type: 'line', yAxisIndex: 1, data: trend.value.map(d => d.green_price),
        lineStyle: { width: 2, type: 'dotted' }, itemStyle: { color: '#67c23a' },
        symbol: 'circle', symbolSize: 5,
      },
    ],
  }, true)
}

let chartReady = false
function initChart() {
  if (chartReady) return
  if (trendChartRef.value) trendChart = echarts.init(trendChartRef.value)
  chartReady = true
  renderTrendChart()
}
onMounted(() => { if (props.activeTab === 'orders') nextTick(() => initChart()) })
watch(() => props.activeTab, (tab) => { if (tab === 'orders') nextTick(() => { initChart(); trendChart?.resize() }) })
watch(trend, () => { if (chartReady) renderTrendChart() })
onUnmounted(() => { trendChart?.dispose() })

// ── 通用工具函数 ────────────────────────────────────────
function formatMoney(v: number) {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtInt(v: number) { return v.toLocaleString('ru-RU') }
function formatDate(v: string | null) {
  if (!v) return '—'
  const s = v.replace('T', ' ').slice(0, 16)
  // finance 补的日期是 00:00，只显示日期
  if (s.endsWith('00:00')) return s.slice(0, 10)
  return s
}

// ── 分页 ──────────────────────────────────────────────────
function onPageChange(page: number) { currentPage.value = page }
function onPageSizeChange(size: number) { pageSize.value = size; currentPage.value = 1 }

// ── SKU 每日备注 ────────────────────────────────────────
const noteVisible = ref(false)
const noteDate = ref('')
const noteContent = ref('')
const noteLoading = ref(false)
const noteDates = ref<string[]>([])
const noteShortSet = computed(() => new Set(noteDates.value.map(d => d.slice(5))))

async function refreshNoteDates() {
  // 当前不支持批量查，用趋势数据匹配
  noteDates.value = []
}
watch(selectedSkuId, async (sid) => {
  if (!sid) { noteDates.value = []; return }
  try {
    noteDates.value = await getSkuNoteDates(sid)
    if (chartReady) renderTrendChart()
  } catch { noteDates.value = [] }
})

async function loadNote() {
  if (!selectedSkuId.value || !noteDate.value) return
  noteLoading.value = true
  try {
    const r = await getSkuNote(selectedSkuId.value, noteDate.value)
    noteContent.value = r.content || ''
  } catch { noteContent.value = '' }
  finally { noteLoading.value = false }
}

async function handleSaveNote() {
  if (!selectedSkuId.value || !noteDate.value) return
  noteLoading.value = true
  try {
    await saveSkuNote(selectedSkuId.value, noteDate.value, noteContent.value)
    if (noteContent.value && !noteDates.value.includes(noteDate.value)) {
      noteDates.value.push(noteDate.value)
      if (chartReady) renderTrendChart()
    } else if (!noteContent.value) {
      noteDates.value = noteDates.value.filter(d => d !== noteDate.value)
      if (chartReady) renderTrendChart()
    }
    ElMessage.success('已保存')
  } catch { ElMessage.error('保存失败') }
  finally { noteLoading.value = false }
}

// ── 详情：该订单财务汇总 ──────────────────────────────────
const financeSummary = computed(() => {
  if (!selectedOrder.value || !selectedOrder.value.finance_transactions.length) return null
  const txs = selectedOrder.value.finance_transactions
  const totalIncome = txs.filter(t => t.amount > 0).reduce((s, t) => s + t.amount, 0)
  const totalCost = txs.filter(t => t.amount < 0).reduce((s, t) => s + t.amount, 0)
  return { totalIncome, totalCost, net: totalIncome + totalCost }
})
</script>

<template>
  <div v-loading="loading" style="min-height: 300px;">
    <!-- 独立日期筛选 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
      <span style="font-size:12px;color:#909399;">📅 时间筛选</span>
      <el-select v-model="periodPreset" style="width:100px" size="small" @change="applyPreset">
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
        style="width:240px"
        :disabled-date="disabledDate"
      />
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16" v-if="overview" style="flex-wrap:wrap;">
      <el-col v-for="col in 4" :key="col" :style="{ flex: '1 1 0', minWidth: '140px' }">
        <template v-if="col === 1">
          <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Document /></el-icon></div>
              <div>
                <div style="font-size:12px;color:#909399;">实际成交数</div>
                <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.total_orders - overview.cancelled_count - overview.client_return_count) }} 单</div>
              </div>
            </div>
          </el-card>
        </template>
        <template v-if="col === 2">
          <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><CircleCheck /></el-icon></div>
              <div>
                <div style="font-size:12px;color:#909399;">已签收</div>
                <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.delivered_count) }}</div>
              </div>
            </div>
          </el-card>
        </template>
        <template v-if="col === 3">
          <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width:40px;height:40px;border-radius:8px;background:#f56c6c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#f56c6c;"><el-icon><CircleClose /></el-icon></div>
              <div>
                <div style="font-size:12px;color:#909399;">已取消</div>
                <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.cancelled_count) }}</div>
              </div>
            </div>
          </el-card>
        </template>
        <template v-if="col === 4">
          <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
            <div style="display: flex; align-items: center; gap: 10px;">
              <div style="width:40px;height:40px;border-radius:8px;background:#90939918;display:flex;align-items:center;justify-content:center;font-size:18px;color:#909399;"><el-icon><Document /></el-icon></div>
              <div>
                <div style="font-size:12px;color:#909399;">总件数</div>
                <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.total_ordered_units) }}</div>
              </div>
            </div>
          </el-card>
        </template>
      </el-col>
    </el-row>
    <!-- SKU 选中时额外卡片 -->
    <el-row :gutter="16" v-if="selectedSkuId" style="margin-top:12px;flex-wrap:wrap;">
      <el-col :span="3" :style="{ flex: '1 1 0', minWidth: '140px' }">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><TrendCharts /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">售价</div>
              <div style="font-size:20px;font-weight:700;color:#c0c4cc;">—</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3" :style="{ flex: '1 1 0', minWidth: '140px' }">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><TrendCharts /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">预估毛利率</div>
              <div style="font-size:20px;font-weight:700;color:#c0c4cc;">—</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3" :style="{ flex: '1 1 0', minWidth: '140px' }">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><TrendCharts /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">广告占比</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ overview.ad_ratio != null ? overview.ad_ratio.toFixed(1) + '%' : '—' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 进行中订单状态标签 -->
    <div v-if="overview && overview.in_progress_count > 0" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
      <span style="font-size:12px;color:#909399;margin-right:4px;">其他:</span>
      <el-tag type="warning" size="small" effect="plain">进行中 {{ overview.in_progress_count }} 单</el-tag>
    </div>

    <!-- 订单趋势图 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-weight:600;">实际售出 &amp; 实际成交（按下单日期）</span>
          <el-tag type="info" size="small">{{ trend.length }} 天</el-tag>
        </div>
      </template>
      <div v-if="trend.length" ref="trendChartRef" style="width:100%;height:320px;" />
      <div v-else style="text-align:center;color:#c0c4cc;padding:40px;">暂无订单数据</div>
    </el-card>

    <!-- 订单列表 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:12px;">
            <span style="font-weight:600;">{{ viewMode === 'posting' ? '订单明细' : 'SKU 统计' }}</span>
            <el-button v-if="viewMode === 'posting'" size="small" @click="clearSkuFilter">← 返回 SKU 统计</el-button>
            <el-tag v-if="selectedSkuId" type="warning" closable size="small" @close="clearSkuFilter">
              {{ selectedSkuName }}
            </el-tag>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <el-input v-if="viewMode === 'sku'" v-model="skuSearch" placeholder="搜索 SKU / 货号" clearable size="small" style="width:180px;" />
            <el-checkbox v-if="viewMode === 'sku'" v-model="onlyOptimize" size="small">只看需优化</el-checkbox>
            <el-tag type="info" size="small">{{ viewMode === 'posting' ? listTotal + ' 单' : filteredSkuStats.length + ' / ' + skuStats.length }}</el-tag>
          </div>
        </div>
      </template>

      <!-- 订单视图 -->
      <el-table v-if="viewMode === 'posting'" :data="orderList" stripe size="small" style="width:100%" max-height="500"
        @row-click="onRowClick">
        <el-table-column prop="posting_number" label="订单号" min-width="175" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:13px;">{{ row.posting_number }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="order_number" label="原始订单" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px;color:#909399;">{{ row.order_number || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sku" label="SKU" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px;color:#909399;">{{ row.sku || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="offer_id" label="货号" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px;color:#909399;">{{ row.offer_id || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="140" sortable>
          <template #default="{ row }">
            <span style="font-size:12px;">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="签收时间" width="140">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ formatDate(row.delivered_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_price" label="售价" width="110" align="right" sortable>
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.total_price > 0 ? '₽ ' + formatMoney(row.total_price) : '—' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <!-- SKU 视图 -->
      <el-table v-else :data="filteredSkuStats" stripe size="small" style="width:100%" max-height="500"
        :row-class-name="skuRowClassName"
        @row-click="onSkuRowClick">
        <el-table-column label="图片" width="50">
          <template #default="{ row }">
            <el-image v-if="row.primary_image" :src="row.primary_image" style="width:28px;height:28px;border-radius:4px;" fit="cover" lazy>
              <template #error><div style="width:28px;height:28px;background:#f5f7fa;border-radius:4px;" /></template>
            </el-image>
            <div v-else style="width:28px;height:28px;background:#f5f7fa;border-radius:4px;" />
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="95">
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px;">{{ row.sku_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="offer_id" label="货号" min-width="120">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.offer_id || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="实际成交数" width="85" align="right" sortable :sort-method="(a:any,b:any) => (a.order_count - a.cancelled_count - a.return_count) - (b.order_count - b.cancelled_count - b.return_count)">
          <template #default="{ row }">
            <span style="font-weight:600;">{{ fmtInt(row.order_count - row.cancelled_count - row.return_count) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="current_price" label="售价" width="100" align="right" sortable>
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.current_price > 0 ? '₽ ' + formatMoney(row.current_price) : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="佣金" width="75" align="right">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.commission_pct != null ? row.commission_pct.toFixed(1) + '%' : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="折扣" width="75" align="right" sortable :sort-method="(a:any,b:any) => (a.discount_pct||0) - (b.discount_pct||0)">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.discount_pct != null ? row.discount_pct.toFixed(1) + '%' : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_rmb" label="利润 ¥" width="90" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.profit_rmb != null && row.profit_rmb >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
              {{ row.profit_rmb != null ? '¥ ' + row.profit_rmb.toFixed(2) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="profit_margin_pct" label="利润率" width="75" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.profit_margin_pct != null && row.profit_margin_pct >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
              {{ row.profit_margin_pct != null ? row.profit_margin_pct.toFixed(1) + '%' : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="green_price" label="绿标价" width="100" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.green_price != null ? '#67c23a' : '#c0c4cc', fontWeight: row.green_price != null ? 600 : 400 }">
              {{ row.green_price != null ? '₽ ' + formatMoney(row.green_price) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="退货" width="70" align="center">
          <template #default="{ row }">
            <span :style="{ color: row.return_count > 0 ? '#e6a23c' : '#303133', fontWeight: row.return_count > 0 ? 600 : 400 }">
              {{ row.return_count }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="70" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.stock > 0 ? '#303133' : '#f56c6c', fontWeight: 600 }">
              {{ fmtInt(row.stock) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="标记" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.recent_deals === 0 && row.stock > 0" type="warning" size="small" effect="plain">需优化</el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="viewMode === 'posting' && listTotal > 0" style="margin-top:12px;display:flex;justify-content:flex-end;">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="listTotal"
          layout="total, sizes, prev, pager, next, jumper"
          small
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- 订单详情抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="订单详情"
      direction="rtl"
      size="620px"
      @closed="onDrawerClosed"
    >
      <template v-if="selectedOrder" v-loading="detailLoading">
        <!-- 基本信息 -->
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px;">
          <el-descriptions-item label="发货单号" :span="2">
            <span style="font-family:monospace;font-size:13px;">{{ selectedOrder.posting_number }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="原始订单" :span="2">
            <span style="font-family:monospace;font-size:12px;">{{ selectedOrder.order_number || '—' }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="配送方式">
            <el-tag size="small" effect="plain" :type="selectedOrder.delivery_schema === 'FBO' ? 'primary' : 'warning'">
              {{ selectedOrder.delivery_schema || '—' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusTagType(selectedOrder.status)" effect="plain">
              {{ statusLabel(selectedOrder.status) }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 时间线 -->
        <el-card shadow="never" style="margin-bottom:16px;">
          <template #header><span style="font-weight:600;font-size:14px;">📅 时间线</span></template>
          <el-timeline>
            <el-timeline-item
              v-if="selectedOrder.created_at"
              :timestamp="formatDate(selectedOrder.created_at)"
              placement="top"
              type="primary"
            >
              下单
            </el-timeline-item>
            <el-timeline-item
              v-if="selectedOrder.in_process_at"
              :timestamp="formatDate(selectedOrder.in_process_at)"
              placement="top"
              type="warning"
            >
              开始处理
            </el-timeline-item>
            <el-timeline-item
              v-if="selectedOrder.delivered_at"
              :timestamp="formatDate(selectedOrder.delivered_at)"
              placement="top"
              type="success"
            >
              签收
            </el-timeline-item>
            <el-timeline-item
              v-if="selectedOrder.status === 'cancelled' && !selectedOrder.delivered_at"
              placement="top"
              type="danger"
            >
              已取消（原因ID: {{ selectedOrder.cancel_reason_id || '未知' }}）
            </el-timeline-item>
          </el-timeline>
        </el-card>

        <!-- 商品清单 -->
        <el-card shadow="never" style="margin-bottom:16px;">
          <template #header><span style="font-weight:600;font-size:14px;">📦 商品清单</span></template>
          <el-table :data="selectedOrder.products" size="small" stripe style="width:100%">
            <el-table-column label="图片" width="60">
              <template #default="{ row }">
                <el-image
                  v-if="row.image"
                  :src="row.image"
                  style="width:40px;height:40px;"
                  fit="contain"
                  :preview-src-list="[row.image]"
                />
                <span v-else style="font-size:11px;color:#c0c4cc;">—</span>
              </template>
            </el-table-column>
            <el-table-column label="SKU" width="85">
              <template #default="{ row }">
                <span style="font-family:monospace;font-size:12px;">{{ row.sku || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="offer_id" label="货号" min-width="140" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-size:11px;">{{ row.offer_id || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="数量" width="55" align="right">
              <template #default="{ row }">
                <span style="font-weight:600;">{{ row.quantity }}</span>
              </template>
            </el-table-column>
            <el-table-column label="单价" width="100" align="right">
              <template #default="{ row }">
                <span>{{ row.price > 0 ? '₽ ' + formatMoney(row.price) : '—' }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 关联退货（如果有） -->
        <el-card v-if="selectedOrder.returns.length" shadow="never" style="margin-bottom:16px;">
          <template #header><span style="font-weight:600;font-size:14px;">↩️ 关联退货</span></template>
          <el-table :data="selectedOrder.returns" size="small" stripe style="width:100%">
            <el-table-column label="类型" width="90">
              <template #default="{ row }">
                <el-tag size="small" :type="row.type === 'Cancellation' ? 'warning' : 'danger'" effect="plain">
                  {{ row.type === 'Cancellation' ? '取消退回' : '签收后退' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="return_reason_name" label="原因" min-width="110" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-size:12px;">{{ row.return_reason_name || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="quantity" label="件数" width="50" align="right" />
            <el-table-column label="状态" width="100">
              <template #default="{ row }">
                <el-tag size="small" effect="plain" type="info">{{ row.visual_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="发起时间" width="140">
              <template #default="{ row }">
                <span style="font-size:12px;">{{ formatDate(row.returned_at) }}</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- 财务流水（如果有） -->
        <el-card v-if="selectedOrder.finance_transactions.length" shadow="never" style="margin-bottom:16px;">
          <template #header>
            <div style="display:flex;align-items:center;justify-content:space-between;">
              <span style="font-weight:600;font-size:14px;">💰 财务流水</span>
              <div v-if="financeSummary" style="font-size:13px;">
                <span style="color:#67c23a;">收入 ₽{{ formatMoney(financeSummary.totalIncome) }}</span>
                <span style="color:#c0c4cc;margin:0 6px;">+</span>
                <span style="color:#f56c6c;">支出 ₽{{ formatMoney(financeSummary.totalCost) }}</span>
                <span style="color:#c0c4cc;margin:0 6px;">=</span>
                <span :style="{ color: financeSummary.net >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 700 }">
                  ₽{{ formatMoney(financeSummary.net) }}
                </span>
              </div>
            </div>
          </template>
          <el-table :data="selectedOrder.finance_transactions" size="small" stripe style="width:100%" max-height="300">
            <el-table-column prop="operation_type_name" label="操作" min-width="160" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-size:12px;">{{ row.operation_type_name || row.type || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="operation_date" label="日期" width="95">
              <template #default="{ row }">
                <span style="font-size:12px;">{{ row.operation_date }}</span>
              </template>
            </el-table-column>
            <el-table-column label="金额" width="110" align="right">
              <template #default="{ row }">
                <span :style="{ color: row.amount >= 0 ? '#67c23a' : '#f56c6c', fontFamily: 'monospace', fontWeight: 600 }">
                  {{ row.amount >= 0 ? '+' : '' }}₽{{ formatMoney(row.amount) }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>
      <div v-else style="text-align:center;color:#c0c4cc;padding:40px;">加载中...</div>
    </el-drawer>

    <!-- SKU 每日备注弹窗 -->
    <el-dialog v-model="noteVisible" :title="`操作记录 — ${noteDate}`" width="450px" destroy-on-close>
      <el-input v-model="noteContent" type="textarea" :rows="5" maxlength="100" show-word-limit
        placeholder="记录当天的操作（不超过100字）" :disabled="noteLoading" />
      <template #footer>
        <el-button @click="noteVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveNote" :loading="noteLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
:deep(.el-table .selected-sku-row > td) {
  background-color: #ecf5ff !important;
}
</style>