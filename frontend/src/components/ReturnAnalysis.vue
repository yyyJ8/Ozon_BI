<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ProductSummary, SummaryRow } from '@/types'

const props = defineProps<{
  products: ProductSummary[]
  summaryRows: SummaryRow[]
  activeTab: string
}>()

const selectedSkuId = ref<number | null>(null)
const selectedSkuLabel = computed(() => {
  if (selectedSkuId.value === null) return '全部商品'
  const p = props.products.find(x => x.sku_id === selectedSkuId.value)
  return `SKU ${selectedSkuId.value} / ${p?.offer_id || '—'}`
})
function selectSku(skuId: number) {
  selectedSkuId.value = selectedSkuId.value === skuId ? null : skuId
}

// ─── 三条线 ──────────────────────────────────────────
const dailyOrders = computed(() => {
  const rows = selectedSkuId.value === null ? props.summaryRows : props.summaryRows.filter(r => r.sku_id === selectedSkuId.value)
  const map = new Map<string, number>()
  for (const row of rows) map.set(row.date, (map.get(row.date) || 0) + row.ordered_units)
  return Array.from(map.entries()).map(([date, units]) => ({ date, units })).sort((a, b) => a.date.localeCompare(b.date))
})

const dailyDelivered = computed(() => {
  const rows = selectedSkuId.value === null ? props.summaryRows : props.summaryRows.filter(r => r.sku_id === selectedSkuId.value)
  const map = new Map<string, number>()
  for (const row of rows) map.set(row.date, (map.get(row.date) || 0) + row.delivered_units)
  return Array.from(map.entries()).map(([date, units]) => ({ date, units })).sort((a, b) => a.date.localeCompare(b.date))
})

const dailyReturns = computed(() => {
  const rows = selectedSkuId.value === null ? props.summaryRows : props.summaryRows.filter(r => r.sku_id === selectedSkuId.value)
  const map = new Map<string, number>()
  for (const row of rows) map.set(row.date, (map.get(row.date) || 0) + row.returns_units)
  return Array.from(map.entries()).map(([date, units]) => ({ date, units })).sort((a, b) => a.date.localeCompare(b.date))
})

// ─── 表格 ─────────────────────────────────────────────
interface ReturnItem {
  sku_id: number; offer_id: string; name: string; primary_image: string | null
  ordered_units: number; delivered_units: number; returns_units: number
  revenue: number; returns_amount: number
  return_rate: number; severity: 'danger' | 'warning' | 'success'
}

const items = computed<ReturnItem[]>(() => {
  return props.products
    .filter(p => p.delivered_units > 0 || p.returns_units > 0)
    .map(p => {
      const return_rate = p.delivered_units > 0 ? (p.returns_units / p.delivered_units) * 100 : 0
      let severity: 'danger' | 'warning' | 'success'
      if (return_rate > 20) severity = 'danger'
      else if (return_rate > 10) severity = 'warning'
      else severity = 'success'
      return { sku_id: p.sku_id, offer_id: p.offer_id, name: p.name, primary_image: p.primary_image,
        ordered_units: p.ordered_units, delivered_units: p.delivered_units, returns_units: p.returns_units,
        revenue: p.revenue, returns_amount: p.returns_amount, return_rate, severity }
    })
    .sort((a, b) => b.return_rate - a.return_rate)
})

const minUnits = ref(3)
const severityFilter = ref('')
const filteredItems = computed(() => {
  return items.value.filter(i => {
    if (i.delivered_units < minUnits.value) return false
    if (severityFilter.value && i.severity !== severityFilter.value) return false
    return true
  })
})

const overview = computed(() => {
  const total_returns_units = items.value.reduce((s, i) => s + i.returns_units, 0)
  const total_delivered_units = items.value.reduce((s, i) => s + i.delivered_units, 0)
  const overall_return_rate = total_delivered_units > 0 ? (total_returns_units / total_delivered_units) * 100 : 0
  return { total_returns_units, overall_return_rate, danger_count: items.value.filter(i => i.severity === 'danger').length, warning_count: items.value.filter(i => i.severity === 'warning').length }
})

// ─── 折线图 ──────────────────────────────────────────
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

// ─── 点击图表日期 → 筛选下方表格 ───────────────────────
const selectedDate = ref<string | null>(null)
const selectedDateLabel = computed(() => selectedDate.value || null)

function onChartClick(params: any) {
  // 点击 series 或 xAxis 都能触发
  const idx = params.dataIndex
  if (idx == null) return
  const date = dailyOrders.value[idx]?.date
  if (date) {
    selectedDate.value = selectedDate.value === date ? null : date
  }
}

// 按选中日期过滤退货明细（日期筛选时忽略 minUnits/severity）
const dateFilteredItems = computed(() => {
  if (!selectedDate.value) return filteredItems.value
  const skusWithReturns = new Set<number>()
  for (const row of props.summaryRows) {
    if (row.date === selectedDate.value && row.returns_units > 0) {
      skusWithReturns.add(row.sku_id)
    }
  }
  return items.value.filter(i => skusWithReturns.has(i.sku_id))
})

const COLOR: Record<string, string> = { '下单': '#e6a23c', '送达': '#409eff', '退货': '#f56c6c' }

function renderChart() {
  if (!chart) return
  const dates = dailyOrders.value.map(d => d.date.slice(5))
  if (!dates.length) {
    chart.setOption({ title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { fontSize: 14, color: '#c0c4cc' } } }, true)
    return
  }
  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => {
        const items = Array.isArray(params) ? params : [params]
        let h = `<div style="font-size:13px;line-height:1.8"><strong>${items[0].axisValue}</strong>`
        for (const p of items) {
          const c = COLOR[p.seriesName] || '#909399'
          h += `<br/><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${c};margin-right:4px"></span>${p.seriesName}: <strong>${Number(p.value).toLocaleString()} 件</strong>`
        }
        return h + '</div>'
      },
    },
    grid: { left: 55, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { fontSize: 11 }, minInterval: 1 },
    legend: { data: ['下单', '送达', '退货'], bottom: 0 },
    series: [
      { name: '下单', type: 'line', data: dailyOrders.value.map(d => d.units), smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { width: 1.5, color: '#e6a23c', type: 'dashed' }, itemStyle: { color: '#e6a23c' } },
      { name: '送达', type: 'line', data: dailyDelivered.value.map(d => d.units), smooth: true, symbol: 'circle', symbolSize: 6, lineStyle: { width: 2, color: '#409eff' }, itemStyle: { color: '#409eff' }, areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(64,158,255,0.2)' }, { offset: 1, color: 'rgba(64,158,255,0.02)' }]) } },
      { name: '退货', type: 'line', data: dailyReturns.value.map(d => d.units), smooth: true, symbol: 'diamond', symbolSize: 8, lineStyle: { width: 2.5, color: '#f56c6c' }, itemStyle: { color: '#f56c6c' }, emphasis: { scale: 2 } },
    ],
  }, true)
  chart.off('click')
  chart.on('click', onChartClick)
}

let initialized = false
function initIfNeeded() { if (initialized) return; chart = echarts.init(chartRef.value!); initialized = true; renderChart() }
onMounted(() => { if (props.activeTab === 'returns') initIfNeeded() })
watch(() => props.activeTab, (tab) => { if (tab === 'returns') { nextTick(() => { initIfNeeded(); chart?.resize() }) } })
watch(() => [dailyOrders.value, dailyDelivered.value, dailyReturns.value], () => { if (initialized) renderChart() })
onUnmounted(() => { chart?.dispose() })

function formatMoney(v: number) { return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function severityTagType(s: string) { return s === 'danger' ? 'danger' : s === 'warning' ? 'warning' : 'success' }
function severityColor(s: string) { return s === 'danger' ? '#f56c6c' : s === 'warning' ? '#e6a23c' : '#67c23a' }
function severityLabel(s: string) { return s === 'danger' ? '高' : s === 'warning' ? '中' : '低' }
const unitOptions = [0, 3, 5, 10]
</script>

<template>
  <div>
    <el-row :gutter="16">
      <el-col :span="16">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-weight: 600">
                📈 {{ selectedSkuId === null ? '销量 & 退货趋势' : selectedSkuLabel + ' 退货趋势' }}
              </span>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 11px; color: #c0c4cc;">退货已归因到原销售日期 · 点击数据点筛选</span>
                <el-button v-if="selectedSkuId !== null" size="small" @click="selectSku(selectedSkuId!)">显示全部</el-button>
                <el-tag type="info" size="small">{{ dailyOrders.length }} 天</el-tag>
              </div>
            </div>
          </template>
          <div ref="chartRef" style="width: 100%; height: 360px" />
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover">
          <template #header><span style="font-weight: 600">📋 退货概况</span></template>
          <div style="display: flex; flex-direction: column; gap: 12px;">
            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0;">
              <span style="color: #909399;">退货件数总计</span><span style="font-weight: 600; color: #f56c6c;">{{ overview.total_returns_units.toLocaleString() }} 件</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0;">
              <span style="color: #909399;">整体退货率</span><span style="font-weight: 600;">{{ overview.overall_return_rate.toFixed(2) }}%</span>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #f0f0f0;">
              <span style="color: #909399;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #f56c6c; margin-right: 4px;" />高退货率</span>
              <el-tag size="small" :type="overview.danger_count > 0 ? 'danger' : 'info'">{{ overview.danger_count }}</el-tag>
            </div>
            <div style="display: flex; justify-content: space-between; padding: 6px 0;">
              <span style="color: #909399;"><span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: #e6a23c; margin-right: 4px;" />中退货率</span>
              <el-tag size="small" :type="overview.warning_count > 0 ? 'warning' : 'info'">{{ overview.warning_count }}</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;">
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-weight: 600; white-space: nowrap;">退货明细</span>
            <el-tag v-if="selectedDate" type="warning" size="small" closable @close="selectedDate = null">
              {{ selectedDate }}
            </el-tag>
          </div>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 13px; color: #909399; white-space: nowrap;">最小送达</span>
            <el-select v-model="minUnits" size="small" style="width: 80px;">
              <el-option v-for="n in unitOptions" :key="n" :label="n === 0 ? '全部' : `≥ ${n}`" :value="n" />
            </el-select>
            <el-select v-model="severityFilter" placeholder="风险等级" clearable size="small" style="width: 100px;">
              <el-option label="全部" value="" /><el-option label="高" value="danger" /><el-option label="中" value="warning" /><el-option label="低" value="success" />
            </el-select>
            <el-tag type="info" size="small">{{ dateFilteredItems.length }} / {{ items.length }}</el-tag>
          </div>
        </div>
      </template>
      <el-table :data="dateFilteredItems" stripe size="small" style="width: 100%" max-height="480" highlight-current-row @row-click="(row: ReturnItem) => selectSku(row.sku_id)">
        <el-table-column type="index" label="#" width="45" />
        <el-table-column prop="sku_id" label="SKU" width="85" sortable>
          <template #default="{ row }"><span style="font-family: monospace; font-size: 12px;">{{ row.sku_id }}</span></template>
        </el-table-column>
        <el-table-column prop="offer_id" label="货号" width="80" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-family: monospace; font-size: 11px; color: #909399;">{{ row.offer_id }}</span></template>
        </el-table-column>
        <el-table-column label="商品" min-width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-image v-if="row.primary_image" :src="row.primary_image" style="width: 28px; height: 28px; border-radius: 4px; flex-shrink: 0;" fit="cover" lazy>
                <template #error><div style="width: 28px; height: 28px; background: #f5f7fa; border-radius: 4px;" /></template>
              </el-image>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="ordered_units" label="下单" width="55" align="right" sortable />
        <el-table-column prop="delivered_units" label="送达" width="55" align="right" sortable>
          <template #default="{ row }"><span :style="{ color: row.delivered_units > 0 ? '#409eff' : '#c0c4cc' }">{{ row.delivered_units }}</span></template>
        </el-table-column>
        <el-table-column prop="returns_units" label="退货" width="55" align="right" sortable>
          <template #default="{ row }"><span :style="{ color: row.returns_units > 0 ? '#f56c6c' : '#c0c4cc' }">{{ row.returns_units }}</span></template>
        </el-table-column>
        <el-table-column prop="returns_amount" label="退货金额" width="100" align="right" sortable>
          <template #default="{ row }"><span style="color: #f56c6c;">₽ {{ formatMoney(row.returns_amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="return_rate" label="退货率" width="200" sortable>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <el-progress :percentage="Math.min(row.return_rate, 100)" :color="severityColor(row.severity)" :stroke-width="6" :show-text="false" style="flex: 1;" />
              <span style="font-size: 13px; font-weight: 600; min-width: 48px; text-align: right;">{{ row.return_rate.toFixed(1) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="程度" width="70" align="center">
          <template #default="{ row }"><el-tag :type="severityTagType(row.severity)" size="small" effect="dark">{{ severityLabel(row.severity) }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
