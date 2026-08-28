<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import type { RealProfitSkuItem, RealProfitDailyItem, RealProfitOverview, ProfitTrendItem } from '@/types'
import { getRealProfitOverview, getRealProfitSkuRanking, getRealProfitSkuDaily, getProfitTrend } from '@/api'
import { useStore } from '@/composables/useStore'
import { useLocalDateRange } from '@/composables/useLocalDateRange'

const props = defineProps<{
  dateRange: [string, string] | null
  activeTab: string
}>()

const { selectedStoreId } = useStore()
const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

// ── 数据 ──
const overview = ref<RealProfitOverview | null>(null)
const skuItems = ref<RealProfitSkuItem[]>([])
const trendItems = ref<ProfitTrendItem[]>([])
const loading = ref(false)

// SKU 搜索
const skuSearch = ref('')

const filteredSkuItems = computed(() => {
  if (!skuSearch.value) return skuItems.value
  const q = skuSearch.value.toLowerCase()
  return skuItems.value.filter(s =>
    String(s.sku_id).includes(q) ||
    (s.offer_id || '').toLowerCase().includes(q) ||
    (s.name || '').toLowerCase().includes(q),
  )
})

// ── SKU 下钻弹窗 ──
const detailVisible = ref(false)
const detailSku = ref<RealProfitSkuItem | null>(null)
const dailyDetail = ref<RealProfitDailyItem[]>([])
const detailLoading = ref(false)

async function openSkuDetail(sku: RealProfitSkuItem) {
  detailSku.value = sku
  detailVisible.value = true
  detailLoading.value = true
  try {
    dailyDetail.value = await getRealProfitSkuDaily(
      sku.sku_id,
      localDateRange.value[0],
      localDateRange.value[1],
      selectedStoreId.value,
    )
  } catch {
    dailyDetail.value = []
  } finally {
    detailLoading.value = false
  }
}

// ── 格式化 ──
function formatMoney(v: number): string {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatMoneyShort(v: number): string {
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

function formatRmb(v: number): string {
  return '¥ ' + v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 产品成本：单件 + 全部（¥），以及全部折算 ₽，用于单元格/tooltip
function costCell(row: RealProfitSkuItem): string {
  const unit = row.product_cost_rmb
  const total = unit * row.ordered_units
  return `${formatRmb(unit)} / ${formatRmb(total)}`
}

function costTip(row: RealProfitSkuItem): string {
  const unit = row.product_cost_rmb
  const total = unit * row.ordered_units
  const rub = total * row.exchange_rate
  return `单件成本 ${formatRmb(unit)}；全部成本 ${formatRmb(total)}\n≈ ₽ ${rub.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function pctOfRevenue(cost: number, revenue: number): string {
  if (!revenue || revenue === 0) return '—'
  return (Math.abs(cost) / revenue * 100).toFixed(1) + '%'
}

// ── 成本结构饼图数据（基于 overview 总费用）──
const COST_CATEGORIES = [
  { key: 'commissions', name: '佣金', color: '#409eff' },
  { key: 'logistics', name: '物流', color: '#e6a23c' },
  { key: 'storage', name: '仓储', color: '#67c23a' },
  { key: 'advertising', name: '广告', color: '#f56c6c' },
  { key: 'promotion', name: '推广', color: '#e040fb' },
  { key: 'returns', name: '退货', color: '#909399' },
  { key: 'other', name: '其他', color: '#b37feb' },
]

interface PieItem {
  name: string
  value: number
  color: string
}

const pieItems = computed<PieItem[]>(() => {
  if (!overview.value) return []
  const mapping: Record<string, string> = {
    'commissions': 'total_commissions',
    'logistics': 'total_logistics',
    'storage': 'total_storage',
    'advertising': 'total_advertising',
    'promotion': 'total_promotion',
    'returns': 'total_returns',
    'other': 'total_other',
  }
  const raw: PieItem[] = []
  for (const cat of COST_CATEGORIES) {
    const val = (overview.value as unknown as Record<string, number>)[mapping[cat.key]] || 0
    if (val > 0) raw.push({ name: cat.name, value: val, color: cat.color })
  }
  // 如有产品成本（含采购+送仓+头程），追加
  if (overview.value.total_product_cost_rub > 0) {
    raw.push({ name: '产品成本', value: overview.value.total_product_cost_rub, color: '#ff6b6b' })
  }
  return raw
})

const pieTotal = computed(() => pieItems.value.reduce((s, i) => s + i.value, 0))

// ── ECharts: 趋势图 ──
const trendChartRef = ref<HTMLDivElement>()
let trendChart: echarts.ECharts | null = null

function renderTrendChart() {
  if (!trendChart || !trendItems.value.length) return
  const dates = trendItems.value.map(t => t.date)
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params: any[]) => {
        const ms: string[] = [params[0]?.axisValue || '']
        for (const p of params) {
          if (p.seriesName === '利润率') {
            ms.push(`${p.marker} ${p.seriesName}: ${p.value.toFixed(1)}%`)
          } else {
            ms.push(`${p.marker} ${p.seriesName}: ₽ ${(p.value as number).toLocaleString('ru-RU', { maximumFractionDigits: 0 })}`)
          }
        }
        return ms.join('<br/>')
      },
    },
    legend: { data: ['收入', '平台净利', '利润率'], bottom: 0 },
    grid: { left: 10, right: 60, top: 20, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: [
      { type: 'value', name: '₽', axisLabel: { formatter: (v: number) => (v / 1000).toFixed(0) + 'k' } },
      { type: 'value', name: '%', axisLabel: { formatter: '{value}%' } },
    ],
    series: [
      {
        name: '收入', type: 'bar', data: trendItems.value.map(t => t.revenue),
        itemStyle: { color: '#409eff', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '平台净利', type: 'bar', data: trendItems.value.map(t => t.net_profit),
        itemStyle: { color: '#67c23a', borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '利润率', type: 'line', yAxisIndex: 1, data: trendItems.value.map(t => t.profit_margin),
        lineStyle: { color: '#e6a23c', width: 2 }, itemStyle: { color: '#e6a23c' },
        symbol: 'circle', symbolSize: 4,
      },
    ],
  }, true)
}

// ── ECharts: 成本饼图 ──
const pieChartRef = ref<HTMLDivElement>()
let pieChart: echarts.ECharts | null = null

function renderPieChart() {
  if (!pieChart || !pieItems.value.length) return
  const colorMap: Record<string, string> = {}
  for (const item of pieItems.value) colorMap[item.name] = item.color
  const total = pieTotal.value

  pieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params: { name: string; value: number; percent: number }) => {
        const v = `₽ ${params.value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
        const revPct = overview.value ? pctOfRevenue(-params.value, overview.value.revenue) : '—'
        return `<div style="font-size:13px;line-height:1.8">
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${colorMap[params.name] || '#909399'};margin-right:6px"></span>
          ${params.name}: <strong>${v}</strong><br/>
          <span style="color:#909399;font-size:11px;">占总费用 ${params.percent.toFixed(1)}%  |  占收入 ${revPct}</span>
        </div>`
      },
    },
    legend: {
      orient: 'vertical', right: 10, top: 'center',
      itemGap: 10, textStyle: { fontSize: 12 },
    },
    series: [{
      type: 'pie', radius: ['42%', '68%'], center: ['38%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
      label: { show: true, position: 'outside', formatter: '{b}\n{d}%', fontSize: 11 },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' }, scaleSize: 6 },
      data: pieItems.value.map(item => ({ ...item, itemStyle: { color: item.color } })),
    }],
    graphic: total > 0 ? [
      {
        type: 'text', left: '30%', top: '47%',
        style: { text: `₽ ${total.toLocaleString('ru-RU', { maximumFractionDigits: 0 })}`, textAlign: 'center', fontSize: 15, fontWeight: 700, color: '#303133' },
      },
      {
        type: 'text', left: '30%', top: '53%',
        style: { text: '总费用', textAlign: 'center', fontSize: 11, color: '#909399' },
      },
    ] : [],
  }, true)
}

// ── ECharts 生命周期 ──
let chartsInited = false

function initCharts() {
  if (chartsInited) return
  if (trendChartRef.value) {
    trendChart = echarts.init(trendChartRef.value)
    renderTrendChart()
  }
  if (pieChartRef.value) {
    pieChart = echarts.init(pieChartRef.value)
    renderPieChart()
  }
  chartsInited = true
}

onMounted(() => {
  if (props.activeTab === 'profit') initCharts()
})

watch(() => props.activeTab, (tab) => {
  if (tab === 'profit') {
    nextTick(() => {
      initCharts()
      trendChart?.resize()
      pieChart?.resize()
    })
  }
})

watch([trendItems, pieItems], () => {
  if (chartsInited) {
    renderTrendChart()
    renderPieChart()
  }
})

onUnmounted(() => {
  trendChart?.dispose()
  pieChart?.dispose()
})

// ── 数据加载 ──
async function loadData() {
  loading.value = true
  try {
    const [d1, d2] = localDateRange.value
    const [ov, sku, trend] = await Promise.all([
      getRealProfitOverview(d1, d2, selectedStoreId.value),
      getRealProfitSkuRanking(d1, d2, selectedStoreId.value),
      getProfitTrend(d1, d2, selectedStoreId.value),
    ])
    overview.value = ov
    skuItems.value = sku
    trendItems.value = trend
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '未知错误'
    ElMessage.error('加载利润数据失败: ' + msg)
  } finally {
    loading.value = false
  }
}

watch(localDateRange, () => { loadData() }, { immediate: true })
watch(() => selectedStoreId.value, () => { loadData() })
</script>

<template>
  <div v-loading="loading">
    <!-- 日期筛选 -->
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

    <!-- KPI 卡片 -->
    <el-row :gutter="16">
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">总收入</div>
            <div style="font-size: 22px; font-weight: 700; color: #409eff; font-family: monospace;">
              ₽ {{ overview ? formatMoneyShort(overview.revenue) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">平台毛利</div>
            <div
              :style="{
                fontSize: '22px', fontWeight: 700, fontFamily: 'monospace',
                color: overview && overview.net_profit >= 0 ? '#67c23a' : '#f56c6c',
              }"
            >
              ₽ {{ overview ? formatMoneyShort(overview.net_profit) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">平台利润率</div>
            <el-tag
              v-if="overview"
              :type="overview.profit_margin >= 20 ? 'success' : overview.profit_margin >= 0 ? 'warning' : 'danger'"
              size="large" effect="dark"
              style="font-size: 18px; font-weight: 700;"
            >
              {{ overview.profit_margin.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc;">—</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">
              真实净利
              <el-tooltip content="平台毛利 − 产品成本（¥ 单件 × 销量 × 汇率13）。单件成本含采购+送仓+头程，估算值，与公司财务可能有偏差，仅供经营参考。" placement="top">
                <span style="font-size:11px;color:#c0c4cc;">ⓘ</span>
              </el-tooltip>
            </div>
            <div
              :style="{
                fontSize: '22px', fontWeight: 700, fontFamily: 'monospace',
                color: overview && overview.real_net_profit >= 0 ? '#409eff' : '#f56c6c',
              }"
            >
              ₽ {{ overview ? formatMoneyShort(overview.real_net_profit) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">真实利润率</div>
            <el-tag
              v-if="overview"
              :type="overview.real_profit_margin >= 20 ? '' : overview.real_profit_margin >= 0 ? 'warning' : 'danger'"
              size="large" effect="dark"
              style="font-size: 18px; font-weight: 700;"
            >
              {{ overview.real_profit_margin.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc;">—</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">总费用</div>
            <div style="font-size: 22px; font-weight: 700; color: #f56c6c; font-family: monospace;">
              ₽ {{ overview ? formatMoneyShort(overview.total_costs) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 费用构成 + 产品成本信息 -->
    <div v-if="overview" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; padding: 10px 4px 0;">
      <span style="font-size: 12px; color: #909399;">Ozon费用:</span>
      <el-tag size="small" type="info">佣金 ₽{{ formatMoneyShort(overview.total_commissions) }}</el-tag>
      <el-tag size="small" type="info">物流 ₽{{ formatMoneyShort(overview.total_logistics) }}</el-tag>
      <el-tag size="small" type="info">仓储 ₽{{ formatMoneyShort(overview.total_storage) }}</el-tag>
      <el-tag size="small" type="info">广告 ₽{{ formatMoneyShort(overview.total_advertising) }}</el-tag>
      <el-tag size="small" type="info">推广 ₽{{ formatMoneyShort(overview.total_promotion) }}</el-tag>
      <el-tag size="small" type="info">退货 ₽{{ formatMoneyShort(overview.total_returns) }}</el-tag>
      <el-tag size="small" type="info">其他 ₽{{ formatMoneyShort(overview.total_other) }}</el-tag>
      <span style="color:#dcdfe6;margin:0 4px;">|</span>
      <span style="font-size:12px;color:#ff6b6b;">产品成本:</span>
      <el-tag size="small" type="danger" effect="plain">
        ¥ {{ overview.total_product_cost_rmb.toFixed(2) }}
        ≈ ₽ {{ formatMoneyShort(overview.total_product_cost_rub) }}
      </el-tag>
      <el-tag size="small" type="warning" effect="plain">
        {{ overview.sku_with_product_cost }}/{{ overview.sku_count }} SKU 有成本
      </el-tag>
    </div>

    <!-- 偏差说明 -->
    <el-alert
      v-if="overview"
      style="margin-top: 10px;"
      type="warning"
      :closable="false"
      show-icon
    >
      <template #title>
        <span style="font-size: 12px;">
          注：下方「真实净利 / 真实利润率」为<span style="font-weight:600;">估算值</span>
          （单件产品成本 ¥ 含采购+送仓+头程×1.06，× 销量 × 汇率13）。因产品成本为估算、汇率为固定值、
          销量与财务回款口径略有差异，<span style="font-weight:600;">与公司财务实际结算可能存在偏差</span>，
          仅供经营参考，对账请以公司财务为准。
        </span>
      </template>
    </el-alert>

    <!-- 利润趋势图 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <span style="font-weight: 600;">📈 利润趋势</span>
      </template>
      <div
        v-if="trendItems.length === 0 && !loading"
        style="text-align: center; color: #c0c4cc; padding: 80px 0; font-size: 14px;"
      >
        暂无趋势数据
      </div>
      <div v-else ref="trendChartRef" style="width: 100%; height: 320px;" />
    </el-card>

    <!-- 成本结构饼图 + 概览 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-weight: 600;">🥧 成本结构</span>
              <el-tag type="info" size="small">{{ pieItems.length }} 项</el-tag>
            </div>
          </template>
          <div
            v-if="pieItems.length === 0 && !loading"
            style="text-align: center; color: #c0c4cc; padding: 80px 0; font-size: 14px;"
          >
            暂无成本数据
          </div>
          <div v-else ref="pieChartRef" style="width: 100%; height: 350px;" />
        </el-card>
      </el-col>
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600;">📋 费用明细</span>
          </template>
          <div v-if="pieItems.length === 0 && !loading" style="text-align: center; color: #c0c4cc; padding: 40px 0;">
            暂无数据
          </div>
          <div v-else style="display: flex; flex-direction: column; gap: 8px;">
            <div
              v-for="item in pieItems"
              :key="item.name"
              style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: #fafafa; border-radius: 6px;"
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <span
                  style="display: inline-block; width: 10px; height: 10px; border-radius: 3px;"
                  :style="{ background: item.color }"
                />
                <span style="font-size: 13px;">{{ item.name }}</span>
              </div>
              <div style="text-align: right;">
                <div style="font-family: monospace; font-weight: 600; font-size: 13px; color: #f56c6c;">
                  ₽ {{ formatMoney(item.value) }}
                </div>
                <div style="font-size: 11px;">
                  <span style="color: #409eff; font-weight: 600;">占收入 {{ overview ? pctOfRevenue(-item.value, overview.revenue) : '—' }}</span>
                </div>
              </div>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 10px; background: #f5f7fa; border-radius: 6px; border: 1px solid #e4e7ed; margin-top: 4px;">
              <div>
                <span style="font-weight: 600; font-size: 13px;">合计</span>
                <div style="font-size: 11px; color: #409eff; font-weight: 600;">
                  占收入 {{ overview ? pctOfRevenue(pieTotal, overview.revenue) : '—' }}
                </div>
              </div>
              <span style="font-family: monospace; font-weight: 700; font-size: 15px; color: #f56c6c;">
                ₽ {{ formatMoney(pieTotal) }}
              </span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- SKU 利润排行表 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between; gap: 12px;">
          <span style="font-weight: 600;">🏆 SKU 利润排行</span>
          <div style="display: flex; align-items: center; gap: 8px;">
            <el-input
              v-model="skuSearch"
              placeholder="搜索 SKU / 货号 / 名称"
              size="small"
              clearable
              style="width: 220px;"
            />
            <el-tag type="info" size="small">{{ filteredSkuItems.length }} 个商品</el-tag>
          </div>
        </div>
      </template>
      <el-table
        :data="filteredSkuItems"
        stripe
        size="small"
        style="width: 100%"
        max-height="500"
        highlight-current-row
        @row-click="openSkuDetail"
      >
        <el-table-column type="index" width="45" label="#" />
        <el-table-column label="" width="40">
          <template #default="{ row }">
            <el-avatar v-if="row.primary_image" :src="row.primary_image" :size="28" shape="square" />
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="105">
          <template #default="{ row }">{{ row.sku_id }}</template>
        </el-table-column>
        <el-table-column label="货号" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.offer_id || '—' }}</template>
        </el-table-column>
        <el-table-column label="销量" width="55" align="right">
          <template #default="{ row }">{{ row.ordered_units }}</template>
        </el-table-column>
        <el-table-column label="库存" width="55" align="right">
          <template #default="{ row }">
            <el-tag
              :type="row.stock_present > 10 ? 'success' : row.stock_present > 0 ? 'warning' : 'danger'"
              size="small" effect="plain"
            >
              {{ row.stock_present }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="收入" width="100" align="right" sortable
          :sort-method="(a: RealProfitSkuItem, b: RealProfitSkuItem) => a.revenue - b.revenue">
          <template #default="{ row }">
            <span :style="{ color: row.revenue > 0 ? '#303133' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.revenue > 0 ? '₽ ' + formatMoney(row.revenue) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="平台净利" width="100" align="right" sortable
          :sort-method="(a: RealProfitSkuItem, b: RealProfitSkuItem) => a.net_profit - b.net_profit">
          <template #default="{ row }">
            <span
              :style="{
                color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c',
                fontWeight: 700, fontFamily: 'monospace',
              }"
            >
              ₽ {{ formatMoney(row.net_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="产品成本 ¥(单件/全部)" width="150" align="right" sortable
          :sort-method="(a: RealProfitSkuItem, b: RealProfitSkuItem) => a.product_cost_rmb - b.product_cost_rmb">
          <template #default="{ row }">
            <el-tooltip v-if="row.has_product_cost" :content="costTip(row)" placement="top">
              <span
                style="font-family:monospace;font-size:12px;color:#ff6b6b;white-space:nowrap;"
                :title="costTip(row)"
              >
                {{ costCell(row) }}
              </span>
            </el-tooltip>
            <span v-else style="color:#c0c4cc;font-size:11px;">未填写</span>
          </template>
        </el-table-column>
        <el-table-column label="汇率" width="60" align="right">
          <template #default="{ row }">
            <span v-if="row.has_product_cost" style="font-family:monospace;font-size:12px;color:#909399;">
              {{ row.exchange_rate.toFixed(1) }}
            </span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="真实净利" width="110" align="right" sortable
          :sort-method="(a: RealProfitSkuItem, b: RealProfitSkuItem) => a.real_net_profit - b.real_net_profit">
          <template #default="{ row }">
            <span
              :style="{
                color: row.has_product_cost
                  ? (row.real_net_profit >= 0 ? '#409eff' : '#f56c6c')
                  : '#c0c4cc',
                fontWeight: 700, fontFamily: 'monospace',
              }"
            >
              {{ row.has_product_cost ? '₽ ' + formatMoney(row.real_net_profit) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="真实利润率" width="85" align="right" sortable
          :sort-method="(a: RealProfitSkuItem, b: RealProfitSkuItem) => a.real_profit_margin - b.real_profit_margin">
          <template #default="{ row }">
            <el-tag
              v-if="row.has_product_cost"
              :type="row.real_profit_margin >= 20 ? '' : row.real_profit_margin >= 0 ? 'warning' : 'danger'"
              size="small"
            >
              {{ row.real_profit_margin.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc; font-size: 11px;">缺成本</span>
          </template>
        </el-table-column>
        <el-table-column label="平台利润率" width="80" align="right" sortable
          :sort-method="(a: RealProfitSkuItem, b: RealProfitSkuItem) => a.profit_margin - b.profit_margin">
          <template #default="{ row }">
            <el-tag
              v-if="row.revenue > 0"
              :type="row.profit_margin >= 20 ? 'success' : row.profit_margin >= 0 ? 'warning' : 'danger'"
              size="small"
            >
              {{ row.profit_margin.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc;">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- SKU 每日明细弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="detailSku ? `SKU ${detailSku.sku_id} / ${detailSku.offer_id || '—'} 每日利润` : 'SKU 明细'"
      width="1100px"
      top="5vh"
      destroy-on-close
    >
      <template v-if="detailSku">
        <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 16px; padding: 12px 16px; background: #f5f7fa; border-radius: 8px;">
          <el-image
            v-if="detailSku.primary_image"
            :src="detailSku.primary_image"
            style="width: 56px; height: 56px; border-radius: 6px; flex-shrink: 0;"
            fit="cover"
          >
            <template #error>
              <div style="width: 56px; height: 56px; background: #e4e7ed; border-radius: 6px;" />
            </template>
          </el-image>
          <div style="flex: 1; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 4px 12px; font-size: 12px;">
            <div><span style="color: #909399;">SKU</span> {{ detailSku.sku_id }}</div>
            <div><span style="color: #909399;">收入</span> <strong>₽ {{ formatMoney(detailSku.revenue) }}</strong></div>
            <div><span style="color: #909399;">平台净利</span>
              <strong :style="{ color: detailSku.net_profit >= 0 ? '#67c23a' : '#f56c6c' }">
                ₽ {{ formatMoney(detailSku.net_profit) }}
              </strong>
            </div>
            <div v-if="detailSku.has_product_cost">
              <span style="color: #909399;">产品成本 ¥</span>
              <strong style="color: #ff6b6b;">{{ formatRmb(detailSku.product_cost_rmb) }}</strong>
            </div>
            <div v-if="detailSku.has_product_cost">
              <span style="color: #909399;">真实净利</span>
              <strong :style="{ color: detailSku.real_net_profit >= 0 ? '#409eff' : '#f56c6c' }">
                ₽ {{ formatMoney(detailSku.real_net_profit) }}
              </strong>
            </div>
          </div>
        </div>

        <el-table
          :data="dailyDetail"
          stripe size="small"
          style="width: 100%"
          max-height="400"
          v-loading="detailLoading"
          :default-sort="{ prop: 'date', order: 'descending' }"
        >
          <el-table-column prop="date" label="日期" width="95" sortable />
          <el-table-column prop="revenue" label="收入" width="100" align="right" sortable>
            <template #default="{ row }">
              <span style="font-family: monospace;">₽ {{ formatMoney(row.revenue) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="costs" label="费用" width="100" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.costs > 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
                {{ row.costs > 0 ? '₽ ' + formatMoney(row.costs) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="net_profit" label="平台净利" width="100" align="right" sortable>
            <template #default="{ row }">
              <span
                :style="{
                  color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c',
                  fontWeight: 600, fontFamily: 'monospace',
                }"
              >
                ₽ {{ formatMoney(row.net_profit) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column v-if="detailSku?.has_product_cost" label="成本摊" width="80" align="right">
            <template #default="{ row }">
              <span v-if="row.has_product_cost" style="font-family:monospace;color:#ff6b6b;">
                ₽ {{ formatMoney(row.product_cost_rub) }}
              </span>
              <span v-else style="color:#c0c4cc;">—</span>
            </template>
          </el-table-column>
          <el-table-column v-if="detailSku?.has_product_cost" prop="real_net_profit" label="真实净利" width="100" align="right" sortable>
            <template #default="{ row }">
              <span
                :style="{
                  color: (row.has_product_cost) ? (row.real_net_profit >= 0 ? '#409eff' : '#f56c6c') : '#c0c4cc',
                  fontWeight: 600, fontFamily: 'monospace',
                }"
              >
                {{ (row.has_product_cost) ? '₽ ' + formatMoney(row.real_net_profit) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="profit_margin" label="利润率" width="75" align="right" sortable>
            <template #default="{ row }">
              <el-tag
                v-if="row.revenue > 0"
                :type="row.profit_margin >= 20 ? 'success' : row.profit_margin >= 0 ? 'warning' : 'danger'"
                size="small"
              >
                {{ row.profit_margin.toFixed(1) }}%
              </el-tag>
              <span v-else style="color: #c0c4cc;">—</span>
            </template>
          </el-table-column>
          <el-table-column label="费用明细" min-width="180">
            <template #default="{ row }">
              <div style="display: flex; gap: 3px; flex-wrap: wrap;">
                <el-tag v-if="row.commissions > 0" size="small" type="info">佣金 {{ formatMoneyShort(row.commissions) }}</el-tag>
                <el-tag v-if="row.logistics_costs > 0" size="small" type="info">物流 {{ formatMoneyShort(row.logistics_costs) }}</el-tag>
                <el-tag v-if="row.storage_fees > 0" size="small" type="info">仓储 {{ formatMoneyShort(row.storage_fees) }}</el-tag>
                <el-tag v-if="row.advertising > 0" size="small" type="info">广告 {{ formatMoneyShort(row.advertising) }}</el-tag>
                <el-tag v-if="row.promotion_costs > 0" size="small" type="info">推广 {{ formatMoneyShort(row.promotion_costs) }}</el-tag>
                <el-tag v-if="row.returns_amount > 0" size="small" type="info">退货 {{ formatMoneyShort(row.returns_amount) }}</el-tag>
                <el-tag v-if="row.other_costs > 0" size="small" type="info">其他 {{ formatMoneyShort(row.other_costs) }}</el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>
  </div>
</template>
