<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick, toRef } from 'vue'
import * as echarts from 'echarts'
import { Failed, Remove, CircleCloseFilled, TrendCharts, Timer, InfoFilled } from '@element-plus/icons-vue'
import type { Product } from '@/types'
import { useReturns } from '@/composables/useReturns'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const dr = toRef(props, 'dateRange')
const selectedSkuId = ref<number>()
const { loading, overview, trend, skuStats, reasons, fetchAll } = useReturns(dr, selectedSkuId)

function onSkuRowClick(row: any) {
  if (selectedSkuId.value === row.sku_id) {
    selectedSkuId.value = undefined  // 取消选中
  } else {
    selectedSkuId.value = row.sku_id
  }
}
function clearSkuFilter() {
  selectedSkuId.value = undefined
}

// 选中 SKU 的名称
const selectedSkuName = computed(() => {
  if (!selectedSkuId.value) return ''
  const s = skuStats.value.find(s => s.sku_id === selectedSkuId.value)
  return s ? (s.offer_id || `SKU ${s.sku_id}`) : ''
})

// ── 状态标签中文 ──────────────────────────────────────
const STATUS_LABELS: Record<string, string> = {
  ReturnedToOzon: '已退回Ozon',
  Utilized: '已销毁/利用',
  ArrivedAtReturnPlace: '已到退货点',
  MovingToOzon: '退回Ozon途中',
  ReceivedBySeller: '卖家已收货',
  MovingToSeller: '退回卖家途中',
  WaitingShipment: '等待发货',
  Utilizing: '销毁中',
  WriteOff: '已核销',
}
function statusLabel(st: string) { return STATUS_LABELS[st] || st }

// ── 趋势图：堆叠柱状（按 returned_at 日期）─────────────
const trendChartRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null

function renderTrendChart() {
  if (!trendChart || !trend.value.length) return
  const dates = trend.value.map(d => d.date.slice(5))
  trendChart.setOption({
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const items = Array.isArray(params) ? params : [params]
        let h = `<div style="font-size:13px;line-height:1.8"><strong>${items[0].axisValue}</strong>`
        let sum = 0
        for (const p of items) { sum += Number(p.value)
          h += `<br/><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${p.color};margin-right:4px"></span>${p.seriesName}: <strong>${Number(p.value).toLocaleString()} 件</strong>` }
        return h + `<br/>合计: <strong>${sum.toLocaleString()} 件</strong></div>`
      },
    },
    legend: { data: ['取消退回', '签收后退货'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 35 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11, rotate: dates.length > 30 ? 45 : 0 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '取消退回', type: 'bar', stack: 'total', data: trend.value.map(d => d.cancellation),
        itemStyle: { color: '#e6a23c' }, emphasis: { focus: 'series' }, barMaxWidth: 24 },
      { name: '签收后退货', type: 'bar', stack: 'total', data: trend.value.map(d => d.client_return),
        itemStyle: { color: '#f56c6c' }, emphasis: { focus: 'series' }, barMaxWidth: 24 },
    ],
  }, true)
}

// ── 生命周期（图表懒初始化）────────────────────────────
let chartReady = false
function initChart() {
  if (chartReady) return
  if (trendChartRef.value) trendChart = echarts.init(trendChartRef.value)
  chartReady = true
  renderTrendChart()
}
onMounted(() => { if (props.activeTab === 'returns') nextTick(() => initChart()) })
watch(() => props.activeTab, (tab) => { if (tab === 'returns') nextTick(() => { initChart(); trendChart?.resize() }) })
watch(trend, () => { if (chartReady) renderTrendChart() })
onUnmounted(() => { trendChart?.dispose() })

// ── SKU 表筛选 ────────────────────────────────────────
const minOrdered = ref(3)
const minReturns = ref(1)
const severityFilter = ref('')

function severityTagType(rate: number) {
  return rate > 20 ? 'danger' : rate > 10 ? 'warning' : 'success'
}
function severityLabel(rate: number) {
  return rate > 20 ? '高' : rate > 10 ? '中' : '低'
}
function formatMoney(v: number) {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtInt(v: number) { return v.toLocaleString('ru-RU') }

const filteredSkuStats = computed(() => {
  return skuStats.value.filter(s => {
    if ((s.ordered_units ?? 0) < minOrdered.value) return false
    if (s.total_returns < minReturns.value) return false
    if (severityFilter.value && severityTagType(s.return_rate) !== severityFilter.value) return false
    return true
  })
})

const unitOptions = [0, 3, 5, 10]
const minReturnOptions = [1, 2, 3, 5]
</script>

<template>
  <div v-loading="loading" style="min-height: 300px;">
    <!-- 概览卡片 5 张 -->
    <el-row :gutter="16" v-if="overview">
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f56c6c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#f56c6c;"><el-icon><Failed /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">退货总数</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.total_returns) }} 件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><Remove /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">取消退回（未签收）</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.cancellation_count) }} 件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f56c6c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#f56c6c;"><el-icon><CircleCloseFilled /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">签收后退货</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.client_return_count) }} 件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><TrendCharts /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">退货率</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ overview.return_rate.toFixed(2) }}%</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="5">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Timer /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">平均处理天数</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">
                {{ overview.avg_processing_days != null ? overview.avg_processing_days.toFixed(1) + ' 天' : '—' }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 状态分布标签 -->
    <div v-if="overview && Object.keys(overview.by_status).length" style="margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;">
      <span style="font-size:12px;color:#909399;margin-right:4px;">状态分布:</span>
      <el-tag v-for="(count, st) in overview.by_status" :key="st" size="small" effect="plain"
        :type="count > 50 ? 'danger' : count > 10 ? 'warning' : 'info'">
        {{ statusLabel(st) }}: {{ count }}
      </el-tag>
    </div>

    <!-- 退货趋势图 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-weight:600;">退货趋势（按下单日期）</span>
          <el-tag type="info" size="small">{{ trend.length }} 天</el-tag>
        </div>
      </template>
      <div v-if="trend.length" ref="trendChartRef" style="width:100%;height:320px;" />
      <div v-else style="text-align:center;color:#c0c4cc;padding:40px;">暂无退货数据</div>
    </el-card>

    <!-- SKU 退货明细表（全宽） -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-weight:600;">SKU 退货明细</span>
            <el-tag v-if="selectedSkuId" type="warning" closable size="small" @close="clearSkuFilter">
              {{ selectedSkuName }}
            </el-tag>
          </div>
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:12px;color:#909399;">最小订单</span>
            <el-select v-model="minOrdered" size="small" style="width:80px;">
              <el-option v-for="n in unitOptions" :key="n" :label="n===0?'全部':`≥ ${n}`" :value="n" />
            </el-select>
            <span style="font-size:12px;color:#909399;">最小退货</span>
            <el-select v-model="minReturns" size="small" style="width:80px;">
              <el-option v-for="n in minReturnOptions" :key="n" :label="`≥ ${n}`" :value="n" />
            </el-select>
            <el-select v-model="severityFilter" placeholder="退货率" clearable size="small" style="width:90px;">
              <el-option label="全部" value="" /><el-option label="高" value="danger" /><el-option label="中" value="warning" /><el-option label="低" value="success" />
            </el-select>
            <el-tag type="info" size="small">{{ filteredSkuStats.length }} / {{ skuStats.length }}</el-tag>
          </div>
        </div>
      </template>
      <el-table :data="filteredSkuStats" stripe size="small" style="width:100%" max-height="500"
        :row-class-name="({ row }: { row: any }) => row.sku_id === selectedSkuId ? 'selected-sku-row' : ''"
        @row-click="onSkuRowClick">
        <el-table-column type="index" label="#" width="40" />
        <el-table-column label="图片" width="50">
          <template #default="{ row }">
            <el-image v-if="row.primary_image" :src="row.primary_image" style="width:28px;height:28px;border-radius:4px;" fit="cover" lazy>
              <template #error><div style="width:28px;height:28px;background:#f5f7fa;border-radius:4px;" /></template>
            </el-image>
            <div v-else style="width:28px;height:28px;background:#f5f7fa;border-radius:4px;" />
          </template>
        </el-table-column>
        <el-table-column prop="sku_id" label="SKU" width="95" sortable>
          <template #default="{ row }"><span style="font-family:monospace;font-size:12px;">{{ row.sku_id }}</span></template>
        </el-table-column>
        <el-table-column prop="offer_id" label="货号" min-width="110">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.offer_id || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="退货类型" width="120" align="center">
          <template #default="{ row }">
            <div style="display:flex;align-items:center;gap:4px;">
              <el-tag size="small" type="warning" effect="plain">取消 {{ row.cancellation_count }}</el-tag>
              <el-tag size="small" type="danger" effect="plain">签收 {{ row.client_return_count }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="total_returns" label="合计" width="55" align="right" sortable>
          <template #default="{ row }"><span style="font-weight:600;">{{ row.total_returns }}</span></template>
        </el-table-column>
        <el-table-column label="配送" width="75" align="center">
          <template #default="{ row }">
            <span style="font-size:12px;" v-if="row.fbo_count || row.fbs_count">
              <span v-if="row.fbo_count" style="color:#409eff;">FBO {{ row.fbo_count }}</span>
              <span v-if="row.fbo_count && row.fbs_count" style="color:#c0c4cc;"> / </span>
              <span v-if="row.fbs_count" style="color:#e6a23c;">FBS {{ row.fbs_count }}</span>
            </span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="完结状态" min-width="115" align="center">
          <template #default="{ row }">
            <div style="display:flex;align-items:center;gap:4px;justify-content:center;">
              <el-tag size="small" type="success" effect="plain">已完结 {{ row.completed_count }}</el-tag>
              <el-tag v-if="row.pending_count" size="small" type="info" effect="plain">处理中 {{ row.pending_count }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="total_return_price" label="退货估值" width="100" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.total_return_price > 0 ? '#f56c6c' : '#c0c4cc' }">
              {{ row.total_return_price > 0 ? '₽ ' + formatMoney(row.total_return_price) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="退货率" width="130" sortable :sort-method="(a:any,b:any) => a.return_rate - b.return_rate">
          <template #default="{ row }">
            <div style="display:flex;align-items:center;gap:4px;">
              <el-progress :percentage="Math.min(row.return_rate, 100)"
                :color="severityTagType(row.return_rate)==='danger'?'#f56c6c':severityTagType(row.return_rate)==='warning'?'#e6a23c':'#67c23a'"
                :stroke-width="5" :show-text="false" style="flex:1;min-width:40px;" />
              <span style="font-size:12px;font-weight:600;min-width:42px;text-align:right;">{{ row.return_rate.toFixed(1) }}%</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="main_reason" label="主要原因" min-width="110" show-overflow-tooltip>
          <template #default="{ row }">
            <span :style="{ color: row.main_reason ? '#303133' : '#c0c4cc' }">{{ row.main_reason || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="avg_processing_days" label="处理天数" width="80" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.avg_processing_days != null ? '#303133' : '#c0c4cc' }">
              {{ row.avg_processing_days != null ? row.avg_processing_days.toFixed(0)+'天' : '—' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
:deep(.el-table .selected-sku-row > td) {
  background-color: #ecf5ff !important;
}
</style>
