<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, toRef, nextTick } from 'vue'
import * as echarts from 'echarts'
import { TrendCharts, DataAnalysis } from '@element-plus/icons-vue'
import { useAdvertising } from '@/composables/useAdvertising'
import type { Product } from '@/types'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
}>()

const dr = toRef(props, 'dateRange')

// ── 产品查找表 ──────────────────────────────────
const productMap = computed(() => {
  const map = new Map<number, Product>()
  for (const p of props.products) map.set(p.sku_id, p)
  return map
})

const {
  loading,
  summaryCards, campaignTable, skuTable, chartData,
  loadingDaily, campaignDaily,
  fetchCampaignDaily,
} = useAdvertising(dr)

// ── 表切换 ──────────────────────────────────────
const tableMode = ref<'campaign' | 'sku'>('sku')

// ── 折线图: CTR / 加购率 / CVR ─────────────────
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null
let resizeObserver: ResizeObserver | null = null

function tryInitChart() {
  if (chart || !chartRef.value) return
  if (chartRef.value.clientWidth > 0) {
    chart = echarts.init(chartRef.value)
    window.addEventListener('resize', () => chart?.resize())
    resizeObserver?.disconnect()
    resizeObserver = null
    renderChart()
  }
}

function renderChart() {
  if (!chart || !chartData.value.length) return
  chart.resize()

  const dates = chartData.value.map(d => d.date)
  const ctrData = chartData.value.map(d => d.ctr)
  const cartData = chartData.value.map(d => d.cart_rate)
  const cvrData = chartData.value.map(d => d.cvr)

  chart.setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => v?.toFixed(2) + '%' },
    legend: { data: ['CTR', '加购率', 'CVR'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: (v: number) => v.toFixed(1) + '%' },
    },
    series: [
      { name: 'CTR', type: 'line', data: ctrData, smooth: true, color: '#409eff' },
      { name: '加购率', type: 'line', data: cartData, smooth: true, color: '#e6a23c' },
      { name: 'CVR', type: 'line', data: cvrData, smooth: true, color: '#67c23a' },
    ],
  }, true)
}

watch(chartData, () => renderChart(), { deep: true })

onMounted(async () => {
  await nextTick()
  tryInitChart()
  if (!chart && chartRef.value) {
    resizeObserver = new ResizeObserver(() => tryInitChart())
    resizeObserver.observe(chartRef.value)
  }
})
onUnmounted(() => {
  chart?.dispose(); chart = null
  resizeObserver?.disconnect()
})

// ── 活动展开行 ──────────────────────────────────
const expandedCampaign = ref<string | null>(null)

function onExpand(campaignId: string) {
  if (expandedCampaign.value === campaignId) {
    expandedCampaign.value = null
  } else {
    expandedCampaign.value = campaignId
    fetchCampaignDaily(campaignId)
  }
}

const expandedDaily = computed(() => {
  const cid = expandedCampaign.value
  if (!cid) return []
  return campaignDaily.value[cid] || []
})

// ── 格式化 ──────────────────────────────────────
function fmtRub(v: unknown) {
  const n = typeof v === 'number' ? v : Number(v ?? 0)
  return n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
function fmtNum(v: unknown) {
  const n = typeof v === 'number' ? v : Number(v ?? 0)
  return n.toLocaleString('ru-RU')
}
function fmtPct(v: unknown) {
  if (v == null) return '-'
  const n = typeof v === 'number' ? v : Number(v)
  return n.toFixed(2) + '%'
}
</script>

<template>
  <div v-loading="loading">

    <!-- ── 汇总卡 ────────────────────────────── -->
    <el-row :gutter="12" style="margin-bottom: 16px">
      <el-col v-for="card in summaryCards" :key="card.label" :span="4">
        <el-card shadow="hover" :body-style="{ padding: '12px 16px', textAlign: 'center' }">
          <div style="font-size: 12px; color: #909399">{{ card.label }}</div>
          <div :style="{ fontSize: '18px', fontWeight: 700, color: card.color }">
            {{ card.prefix }}{{
              (card as any).decimals != null
                ? card.value.toFixed((card as any).decimals)
                : card.value >= 1000 && card.prefix === ''
                  ? fmtNum(card.value)
                  : typeof card.value === 'number' && card.prefix === '₽'
                    ? fmtRub(card.value)
                    : card.value
            }}{{ (card as any).suffix || '' }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- ── 折线图: CTR / 加购率 / CVR ────────── -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <span><el-icon><TrendCharts /></el-icon> 转化率趋势</span>
      </template>
      <div ref="chartRef" style="width: 100%; height: 300px" />
    </el-card>

    <!-- ── 表切换 ────────────────────────────── -->
    <el-card>
      <template #header>
        <div style="display: flex; align-items: center; gap: 16px">
          <span><el-icon><DataAnalysis /></el-icon> 广告明细</span>
          <el-radio-group v-model="tableMode" size="small">
            <el-radio-button value="sku">商品维度 ({{ skuTable.length }})</el-radio-button>
            <el-radio-button value="campaign">活动维度 ({{ campaignTable.length }})</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- 活动表 -->
      <el-table
        v-if="tableMode === 'campaign'"
        :data="campaignTable"
        stripe size="small"
        @row-click="(row: any) => onExpand(row.campaign_id)"
        style="cursor: pointer"
        max-height="450"
      >
        <el-table-column type="index" width="50" label="#" />
        <el-table-column prop="title" label="活动名称" min-width="220" show-overflow-tooltip />
        <el-table-column label="SKU" width="130">
          <template #default="{ row }">{{ row.sku_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="货号" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.offer_id || '-' }}</template>
        </el-table-column>
        <el-table-column prop="spend" label="花费 ₽" width="100" sortable>
          <template #default="{ row }">{{ fmtRub(row.spend) }}</template>
        </el-table-column>
        <el-table-column prop="impressions" label="展示" width="90" sortable>
          <template #default="{ row }">{{ fmtNum(row.impressions) }}</template>
        </el-table-column>
        <el-table-column prop="clicks" label="点击" width="90" sortable />
        <el-table-column prop="orders" label="订单" width="90" sortable />
        <el-table-column prop="orders_sum" label="广告收入 ₽" width="150" sortable>
          <template #default="{ row }">{{ fmtRub(row.orders_sum) }}</template>
        </el-table-column>

        <template #expanded>
          <div style="padding: 8px 0 8px 40px">
            <el-table
              v-if="expandedDaily.length > 0"
              :data="expandedDaily"
              size="small"
              max-height="250"
            >
              <el-table-column prop="stat_date" label="日期" width="110" />
              <el-table-column prop="impressions" label="展示" width="90" />
              <el-table-column prop="clicks" label="点击" width="80" />
              <el-table-column prop="spend" label="花费 ₽" width="110">
                <template #default="{ row }">{{ fmtRub(row.spend) }}</template>
              </el-table-column>
              <el-table-column prop="orders_count" label="订单" width="70" />
              <el-table-column prop="orders_sum" label="收入 ₽" width="120">
                <template #default="{ row }">{{ fmtRub(row.orders_sum) }}</template>
              </el-table-column>
            </el-table>
            <div v-else style="color: #909399; padding: 12px">
              {{ loadingDaily[expandedCampaign || ''] ? '加载中...' : '点击行加载每日明细' }}
            </div>
          </div>
        </template>
      </el-table>

      <!-- SKU 表 -->
      <el-table
        v-else
        :data="skuTable"
        stripe size="small"
        max-height="450"
        row-key="sku_id"
      >
        <el-table-column type="index" width="50" label="#" />
        <el-table-column label="" width="44">
          <template #default="{ row }">
            <el-avatar
              v-if="productMap.get(row.sku_id)?.primary_image"
              :src="productMap.get(row.sku_id)?.primary_image!"
              :size="32"
              shape="square"
            />
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="110">
          <template #default="{ row }">{{ row.sku_id }}</template>
        </el-table-column>
        <el-table-column label="货号" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ productMap.get(row.sku_id)?.offer_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="商品名" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size: 12px">{{ productMap.get(row.sku_id)?.name || row.sku_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="impressions" label="展示" width="90" sortable>
          <template #default="{ row }">{{ fmtNum(row.impressions) }}</template>
        </el-table-column>
        <el-table-column prop="clicks" label="点击" width="80" sortable />
        <el-table-column label="CTR" width="80">
          <template #default="{ row }">{{ fmtPct(row.ctr) }}</template>
        </el-table-column>
        <el-table-column prop="add_to_cart" label="加购" width="70" sortable />
        <el-table-column label="CPC" width="90">
          <template #default="{ row }">{{ row.avg_cpc ? '₽' + Number(row.avg_cpc).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="spend" label="花费 ₽" width="110" sortable>
          <template #default="{ row }">{{ fmtRub(row.spend) }}</template>
        </el-table-column>
        <el-table-column prop="sold_units" label="售出" width="70" sortable />
        <el-table-column label="销售额" width="110">
          <template #default="{ row }">{{ row.sales_promotion ? fmtRub(row.sales_promotion) : '-' }}</template>
        </el-table-column>
        <el-table-column label="DRR" width="80">
          <template #default="{ row }">{{ fmtPct(row.drr_total) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

  </div>
</template>
