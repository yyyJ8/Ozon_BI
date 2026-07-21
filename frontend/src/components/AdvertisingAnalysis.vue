<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed, toRef, nextTick } from 'vue'
import * as echarts from 'echarts'
import { TrendCharts, DataAnalysis } from '@element-plus/icons-vue'
import { useAdvertising } from '@/composables/useAdvertising'
import type { Product } from '@/types'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const dr = toRef(props, 'dateRange')

const productMap = computed(() => {
  const map = new Map<number, Product>()
  for (const p of props.products) map.set(p.sku_id, p)
  return map
})

const {
  loading, adSummary,
  summaryCards, campaignTable, skuTable, convTrend,
  loadingDaily, campaignDaily,
  fetchCampaignDaily,
} = useAdvertising(dr)

// ── 表切换 ──────────────────────────────────────
const tableMode = ref<'campaign' | 'sku'>('sku')

// ── 活动类型标签 ────────────────────────────────
const TYPE_LABELS: Record<string, string> = {
  SKU: 'SKU广告', SEARCH_PROMO: '搜索推广', ALL_SKU_PROMO: '全店推广',
  REF_VK: 'VK引荐', REF_BLOGGER: '博主引荐',
}
const TYPE_COLORS: Record<string, string> = {
  SKU: '#409eff', SEARCH_PROMO: '#e6a23c', ALL_SKU_PROMO: '#67c23a',
}
function typeLabel(t: string) { return TYPE_LABELS[t] || t }
function typeColor(t: string) { return TYPE_COLORS[t] || '#909399' }

const typeEntries = computed(() => {
  if (!adSummary.value?.by_type) return []
  return Object.entries(adSummary.value.by_type)
    .map(([t, v]) => ({ type: t, spend: v.spend, count: v.count, orders_sum: v.orders_sum }))
    .sort((a, b) => b.spend - a.spend)
})

const mappedPct = computed(() => {
  const total = adSummary.value ? adSummary.value.total_spend : 0
  const mapped = adSummary.value ? adSummary.value.mapped_spend : 0
  return total > 0 ? (mapped / total * 100) : 0
})

// ── 图表管理 ────────────────────────────────────
const convChartRef = ref<HTMLDivElement>()
let convChart: echarts.ECharts | null = null

function ensureConvChart() {
  if (convChart) return true
  if (!convChartRef.value || convChartRef.value.clientWidth === 0) return false
  convChart = echarts.init(convChartRef.value)
  return true
}

function renderConvChart() {
  if (!ensureConvChart() || !convTrend.value.length) return
  const dates = convTrend.value.map(d => d.date)
  convChart!.setOption({
    tooltip: { trigger: 'axis', valueFormatter: (v: any) => v?.toFixed(2) + '%' },
    legend: { data: ['CTR', '加购率', 'CVR'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', axisLabel: { formatter: (v: number) => v.toFixed(1) + '%' } },
    series: [
      { name: 'CTR', type: 'line', data: convTrend.value.map(d => d.ctr), smooth: true, color: '#409eff' },
      { name: '加购率', type: 'line', data: convTrend.value.map(d => d.cart_rate), smooth: true, color: '#e6a23c' },
      { name: 'CVR', type: 'line', data: convTrend.value.map(d => d.cvr), smooth: true, color: '#67c23a' },
    ],
  }, true)
}

// 窗口 resize 时更新
function onResize() { convChart?.resize() }

// 数据到达时自动初始化+渲染
watch(convTrend, () => { if (convTrend.value.length) { nextTick(() => { renderConvChart() }) } })

onMounted(() => { if (props.activeTab === 'advertising') nextTick(() => renderConvChart()) })
watch(() => props.activeTab, (tab) => { if (tab === 'advertising') nextTick(() => { ensureConvChart(); renderConvChart(); convChart?.resize() }) })
onUnmounted(() => {
  convChart?.dispose(); convChart = null
  window.removeEventListener('resize', onResize)
})

// ── 活动展开 ────────────────────────────────────
const expandedCampaign = ref<string | null>(null)

function onExpand(campaignId: string) {
  if (expandedCampaign.value === campaignId) { expandedCampaign.value = null }
  else { expandedCampaign.value = campaignId; fetchCampaignDaily(campaignId) }
}

const expandedDaily = computed(() => {
  const cid = expandedCampaign.value
  if (!cid) return []
  return campaignDaily.value[cid] || []
})

// ── 格式化 ──────────────────────────────────────
function fmtRub(v: unknown) { const n = typeof v === 'number' ? v : Number(v ?? 0); return n.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function fmtNum(v: unknown) { const n = typeof v === 'number' ? v : Number(v ?? 0); return n.toLocaleString('ru-RU') }
function fmtPct(v: unknown) { if (v == null) return '-'; const n = typeof v === 'number' ? v : Number(v); return n.toFixed(2) + '%' }
function fmtRoas(v: unknown) { const n = typeof v === 'number' ? v : Number(v ?? 0); return n > 0 ? n.toFixed(2) + 'x' : '-' }

const campaignStateLabel = (s: string) => s === 'CAMPAIGN_STATE_RUNNING' ? '运行中' : s === 'CAMPAIGN_STATE_ARCHIVED' ? '已归档' : '停用'
</script>

<template>
  <div v-loading="loading" style="min-height:300px;">

    <!-- ── KPI 卡片 8 张 ────────────────────────── -->
    <el-row :gutter="12" style="margin-bottom:12px">
      <el-col v-for="card in summaryCards" :key="card.label" :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px', textAlign: 'center' }">
          <div style="font-size:11px;color:#909399;">{{ card.label }}</div>
          <div :style="{ fontSize:'17px',fontWeight:700,color:card.color }">
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

    <!-- ── 活动类型 + 活动概况 ──────────────────── -->
    <div v-if="adSummary" style="display:flex;align-items:center;gap:8px;margin-bottom:16px;flex-wrap:wrap;font-size:12px;color:#909399;">
      <el-tag v-for="t in typeEntries" :key="t.type" size="small"
        :color="typeColor(t.type)" effect="dark" style="border:none;">
        {{ typeLabel(t.type) }} ₽{{ fmtRub(t.spend) }}
      </el-tag>
      <span>
        {{ adSummary.active_campaign_count }}/{{ adSummary.campaign_count }} 活动运行中
        · {{ adSummary.mapped_sku_count }} 个 SKU 可追踪（覆盖 {{ mappedPct.toFixed(0) }}% 花费）
      </span>
    </div>

    <!-- ── 转化率趋势图 ──────────────────────────── -->
    <el-card shadow="hover" style="margin-bottom:16px">
      <template #header>
        <span><el-icon><TrendCharts /></el-icon> 转化率趋势</span>
      </template>
      <div ref="convChartRef" style="width:100%;height:280px;">
        <div v-if="!convTrend.length" style="text-align:center;color:#c0c4cc;padding:110px 0;">加载中...</div>
      </div>
    </el-card>

    <!-- ── 明细表 ────────────────────────────────── -->
    <el-card>
      <template #header>
        <div style="display:flex;align-items:center;gap:16px;">
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
        :data="campaignTable" stripe size="small"
        @row-click="(row:any) => onExpand(row.campaign_id)"
        style="cursor:pointer" max-height="450"
      >
        <el-table-column type="index" width="45" label="#" />
        <el-table-column prop="title" label="活动名称" min-width="180" show-overflow-tooltip />
        <el-table-column label="类型" width="85">
          <template #default="{ row }">
            <el-tag size="small" :color="typeColor(row.campaign_type)" effect="dark" style="border:none;">
              {{ typeLabel(row.campaign_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="75">
          <template #default="{ row }">
            <el-tag size="small" :type="row.state==='CAMPAIGN_STATE_RUNNING'?'success':'info'" effect="plain">
              {{ campaignStateLabel(row.state) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="预算" width="105" sortable>
          <template #default="{ row }">₽ {{ fmtRub(row.budget) }}</template>
        </el-table-column>
        <el-table-column prop="spend" label="花费 ₽" width="105" sortable>
          <template #default="{ row }">{{ fmtRub(row.spend) }}</template>
        </el-table-column>
        <el-table-column prop="impressions" label="展示" width="85" sortable>
          <template #default="{ row }">{{ fmtNum(row.impressions) }}</template>
        </el-table-column>
        <el-table-column prop="clicks" label="点击" width="70" sortable />
        <el-table-column label="CTR" width="65">
          <template #default="{ row }">{{ row.impressions > 0 ? (row.clicks/row.impressions*100).toFixed(2)+'%' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="orders" label="订单" width="65" sortable />
        <el-table-column label="收入 ₽" width="110" sortable>
          <template #default="{ row }">{{ fmtRub(row.orders_sum) }}</template>
        </el-table-column>
        <el-table-column label="ROAS" width="65" sortable>
          <template #default="{ row }">
            <span :style="{color:row.roas>=1?'#67c23a':'#f56c6c',fontWeight:600}">{{ fmtRoas(row.roas) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="关联SKU" width="95">
          <template #default="{ row }">{{ row.sku_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="货号" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.offer_id || '-' }}</template>
        </el-table-column>

        <template #expanded>
          <div style="padding:8px 0 8px 40px">
            <el-table v-if="expandedDaily.length" :data="expandedDaily" size="small" max-height="250">
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
            <div v-else style="color:#909399;padding:12px;">
              {{ loadingDaily[expandedCampaign||''] ? '加载中...' : '点击行加载每日明细' }}
            </div>
          </div>
        </template>
      </el-table>

      <!-- SKU 表 -->
      <el-table
        v-else
        :data="skuTable" stripe size="small"
        max-height="450" row-key="sku_id"
      >
        <el-table-column type="index" width="45" label="#" />
        <el-table-column label="" width="40">
          <template #default="{ row }">
            <el-avatar
              v-if="productMap.get(row.sku_id)?.primary_image"
              :src="productMap.get(row.sku_id)?.primary_image!"
              :size="28" shape="square"
            />
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="100">
          <template #default="{ row }">{{ row.sku_id }}</template>
        </el-table-column>
        <el-table-column label="货号" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ productMap.get(row.sku_id)?.offer_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="商品名" min-width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size:12px;">{{ productMap.get(row.sku_id)?.name || row.sku_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="impressions" label="展示" width="80" sortable>
          <template #default="{ row }">{{ fmtNum(row.impressions) }}</template>
        </el-table-column>
        <el-table-column prop="clicks" label="点击" width="65" sortable />
        <el-table-column label="CTR" width="65">
          <template #default="{ row }">{{ fmtPct(row.ctr) }}</template>
        </el-table-column>
        <el-table-column prop="add_to_cart" label="加购" width="60" sortable />
        <el-table-column label="CPC" width="80">
          <template #default="{ row }">{{ row.avg_cpc ? '₽' + Number(row.avg_cpc).toFixed(2) : '-' }}</template>
        </el-table-column>
        <el-table-column prop="spend" label="花费 ₽" width="100" sortable>
          <template #default="{ row }">{{ fmtRub(row.spend) }}</template>
        </el-table-column>
        <el-table-column prop="sold_units" label="售出" width="60" sortable />
        <el-table-column label="销售额" width="100">
          <template #default="{ row }">{{ row.sales_promotion ? fmtRub(row.sales_promotion) : '-' }}</template>
        </el-table-column>
        <el-table-column label="DRR" width="65">
          <template #default="{ row }">{{ fmtPct(row.drr_total) }}</template>
        </el-table-column>
        <el-table-column label="ROAS" width="60" sortable>
          <template #default="{ row }">
            <span :style="{color:row.roas>=1?'#67c23a':'#f56c6c',fontWeight:600}">{{ fmtRoas(row.roas) }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

  </div>
</template>

<style scoped>
:deep(.el-table .cell) {
  white-space: nowrap;
}
</style>
