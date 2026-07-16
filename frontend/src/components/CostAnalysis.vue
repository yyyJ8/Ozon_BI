<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ProductSummary, SummaryStats } from '@/types'

const props = defineProps<{
  stats: SummaryStats | null
  productSummary: ProductSummary[]
  dateRange: [string, string] | null
  loading: boolean
  activeTab: string
}>()

// ─── SKU 选择状态 ──────────────────────────────────────
const selectedSku = ref<ProductSummary | null>(null)

function selectSku(sku: ProductSummary) {
  if (selectedSku.value?.sku_id === sku.sku_id) {
    selectedSku.value = null // 再次点击取消选择
  } else {
    selectedSku.value = sku
  }
}

function clearSelection() {
  selectedSku.value = null
}

// ─── 辅助函数 ──────────────────────────────────────────
function abs(v: number): number {
  return Math.abs(v)
}

function formatMoney(v: number): string {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function skuTotalCost(sku: ProductSummary): number {
  return abs(sku.commissions) + abs(sku.logistics_costs) + abs(sku.storage_fees)
       + abs(sku.advertising) + abs(sku.returns_amount) + abs(sku.other_costs)
}

// ─── 饼图数据 ──────────────────────────────────────────
const COST_CATEGORIES = [
  { name: '佣金', color: '#409eff' },
  { name: '物流', color: '#e6a23c' },
  { name: '仓储', color: '#67c23a' },
  { name: '广告', color: '#f56c6c' },
  { name: '退货', color: '#909399' },
  { name: '其他', color: '#b37feb' },
]

const pieItems = computed(() => {
  if (selectedSku.value) {
    const sku = selectedSku.value
    const raw = [
      { name: '佣金', value: abs(sku.commissions) },
      { name: '物流', value: abs(sku.logistics_costs) },
      { name: '仓储', value: abs(sku.storage_fees) },
      { name: '广告', value: abs(sku.advertising) },
      { name: '退货', value: abs(sku.returns_amount) },
      { name: '其他', value: abs(sku.other_costs) },
    ]
    return raw.filter(item => item.value > 0)
  }

  if (!props.stats) return []
  const raw = [
    { name: '佣金', value: abs(props.stats.total_commissions) },
    { name: '物流', value: abs(props.stats.total_logistics) },
    { name: '仓储', value: abs(props.stats.total_storage) },
    { name: '广告', value: abs(props.stats.total_advertising) },
    { name: '退货', value: abs(props.stats.total_returns) },
    { name: '其他', value: abs(props.stats.total_other_costs) },
  ]
  return raw.filter(item => item.value > 0)
})

const pieTotal = computed(() => pieItems.value.reduce((s, i) => s + i.value, 0))

const pieTitle = computed(() => {
  if (selectedSku.value) {
    const oid = selectedSku.value.offer_id || '—'
    return `SKU ${selectedSku.value.sku_id} / ${oid} 成本结构`
  }
  return '整体成本结构'
})

// ─── SKU 表格数据 ──────────────────────────────────────
interface SkuCostItem extends ProductSummary {
  totalCost: number
  costRate: number
}

const skuItems = computed<SkuCostItem[]>(() => {
  return props.productSummary
    .map(p => ({
      ...p,
      totalCost: skuTotalCost(p),
      costRate: p.revenue > 0 ? (skuTotalCost(p) / p.revenue) * 100 : 0,
    }))
    .sort((a, b) => b.totalCost - a.totalCost)
})

// ─── ECharts 饼图 ──────────────────────────────────────
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chart || !pieItems.value.length) return

  const colorMap: Record<string, string> = {}
  for (const c of COST_CATEGORIES) {
    colorMap[c.name] = c.color
  }

  chart.setOption(
    {
      tooltip: {
        trigger: 'item',
        formatter: (params: { name: string; value: number; percent: number }) => {
          const v = `₽ ${params.value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
          return `<div style="font-size:13px;line-height:1.8">
            <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${colorMap[params.name] || '#909399'};margin-right:6px"></span>
            ${params.name}: <strong>${v}</strong> (${params.percent.toFixed(1)}%)
          </div>`
        },
      },
      legend: {
        orient: 'vertical',
        right: 10,
        top: 'center',
        itemGap: 12,
        textStyle: { fontSize: 13 },
      },
      series: [
        {
          type: 'pie',
          radius: ['42%', '68%'],
          center: ['38%', '50%'],
          avoidLabelOverlap: false,
          itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 },
          label: {
            show: true,
            position: 'outside',
            formatter: '{b}\n{d}%',
            fontSize: 12,
          },
          emphasis: {
            label: { show: true, fontSize: 16, fontWeight: 'bold' },
            scaleSize: 8,
          },
          data: pieItems.value.map(item => ({
            ...item,
            itemStyle: { color: colorMap[item.name] },
          })),
        },
      ],
      graphic: pieTotal.value > 0
        ? [
            {
              type: 'text',
              left: '30%',
              top: '47%',
              style: {
                text: `₽ ${pieTotal.value.toLocaleString('ru-RU', { maximumFractionDigits: 0 })}`,
                textAlign: 'center',
                fontSize: 16,
                fontWeight: 700,
                color: '#303133',
              },
            },
            {
              type: 'text',
              left: '30%',
              top: '53%',
              style: {
                text: '总费用',
                textAlign: 'center',
                fontSize: 12,
                color: '#909399',
              },
            },
          ]
        : [],
    },
    true,
  )
}

let initialized = false

function initIfNeeded() {
  if (initialized) return
  chart = echarts.init(chartRef.value!)
  initialized = true
  renderChart()
}

onMounted(() => {
  if (props.activeTab === 'costs') initIfNeeded()
})

watch(
  () => props.activeTab,
  (tab) => {
    if (tab === 'costs') {
      nextTick(() => {
        initIfNeeded()
        chart?.resize()
      })
    }
  },
)

watch(
  () => [pieItems.value, pieTitle.value],
  () => {
    if (initialized) renderChart()
  },
  { deep: true },
)

onUnmounted(() => {
  chart?.dispose()
})
</script>

<template>
  <div>
    <!-- 上半部分：饼图 -->
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-weight: 600;">
                🥧 {{ pieTitle }}
              </span>
              <div style="display: flex; align-items: center; gap: 8px;">
                <el-button
                  v-if="selectedSku"
                  size="small"
                  @click="clearSelection"
                >
                  显示全部
                </el-button>
                <el-tag v-if="selectedSku" type="warning" size="small" effect="plain">
                  SKU {{ selectedSku.sku_id }}
                </el-tag>
                <el-tag type="info" size="small">
                  {{ pieItems.length }} 项
                </el-tag>
              </div>
            </div>
          </template>
          <div
            v-if="pieItems.length === 0 && !loading"
            style="text-align: center; color: #c0c4cc; padding: 80px 0; font-size: 14px;"
          >
            暂无成本数据
          </div>
          <div
            v-else
            ref="chartRef"
            style="width: 100%; height: 380px;"
          />
        </el-card>
      </el-col>

      <!-- 右侧：当前总览 -->
      <el-col :span="10">
        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600;">📋 {{ selectedSku ? 'SKU 成本概览' : '成本概览' }}</span>
          </template>
          <div v-if="pieItems.length === 0 && !loading" style="text-align: center; color: #c0c4cc; padding: 40px 0;">
            暂无数据
          </div>
          <div v-else style="display: flex; flex-direction: column; gap: 10px;">
            <div
              v-for="item in pieItems"
              :key="item.name"
              style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: #fafafa; border-radius: 6px;"
            >
              <div style="display: flex; align-items: center; gap: 8px;">
                <span
                  style="display: inline-block; width: 10px; height: 10px; border-radius: 3px;"
                  :style="{ background: COST_CATEGORIES.find(c => c.name === item.name)?.color || '#909399' }"
                />
                <span style="font-size: 14px;">{{ item.name }}</span>
              </div>
              <div style="text-align: right;">
                <div style="font-family: monospace; font-weight: 600; font-size: 14px; color: #f56c6c;">
                  ₽ {{ formatMoney(item.value) }}
                </div>
                <div style="font-size: 11px; color: #909399;">
                  {{ pieTotal > 0 ? ((item.value / pieTotal) * 100).toFixed(1) : 0 }}%
                </div>
              </div>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; background: #f5f7fa; border-radius: 6px; border: 1px solid #e4e7ed; margin-top: 4px;">
              <span style="font-weight: 600; font-size: 14px;">合计</span>
              <span style="font-family: monospace; font-weight: 700; font-size: 16px; color: #f56c6c;">
                ₽ {{ formatMoney(pieTotal) }}
              </span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 下半部分：SKU 成本明细表 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-weight: 600;">
            📊 SKU 成本明细
          </span>
          <el-tag type="info" size="small">{{ skuItems.length }} 个商品</el-tag>
        </div>
      </template>
      <el-table
        :data="skuItems"
        stripe
        size="small"
        style="width: 100%"
        max-height="500"
        highlight-current-row
        @row-click="selectSku"
      >
        <el-table-column type="index" width="50" label="#" />
        <el-table-column label="" width="44">
          <template #default="{ row }">
            <el-avatar
              v-if="row.primary_image"
              :src="row.primary_image"
              :size="32"
              shape="square"
            />
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="110">
          <template #default="{ row }">{{ row.sku_id }}</template>
        </el-table-column>
        <el-table-column label="货号" width="150" show-overflow-tooltip>
          <template #default="{ row }">{{ row.offer_id || '-' }}</template>
        </el-table-column>
        <el-table-column label="商品名" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size: 12px">{{ row.name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收入" width="110" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => a.revenue - b.revenue">
          <template #default="{ row }">
            <span :style="{ color: row.revenue > 0 ? '#303133' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.revenue > 0 ? '₽ ' + formatMoney(row.revenue) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="佣金" width="95" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => abs(a.commissions) - abs(b.commissions)">
          <template #default="{ row }">
            <span :style="{ color: row.commissions !== 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.commissions !== 0 ? '₽ ' + formatMoney(abs(row.commissions)) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="物流" width="95" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => abs(a.logistics_costs) - abs(b.logistics_costs)">
          <template #default="{ row }">
            <span :style="{ color: row.logistics_costs !== 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.logistics_costs !== 0 ? '₽ ' + formatMoney(abs(row.logistics_costs)) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="仓储" width="95" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => abs(a.storage_fees) - abs(b.storage_fees)">
          <template #default="{ row }">
            <span :style="{ color: row.storage_fees !== 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.storage_fees !== 0 ? '₽ ' + formatMoney(abs(row.storage_fees)) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="广告" width="95" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => abs(a.advertising) - abs(b.advertising)">
          <template #default="{ row }">
            <span :style="{ color: row.advertising !== 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.advertising !== 0 ? '₽ ' + formatMoney(abs(row.advertising)) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="退货" width="95" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => abs(a.returns_amount) - abs(b.returns_amount)">
          <template #default="{ row }">
            <span :style="{ color: row.returns_amount !== 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.returns_amount !== 0 ? '₽ ' + formatMoney(abs(row.returns_amount)) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="其他" width="95" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => abs(a.other_costs) - abs(b.other_costs)">
          <template #default="{ row }">
            <span :style="{ color: row.other_costs !== 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.other_costs !== 0 ? '₽ ' + formatMoney(abs(row.other_costs)) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="成本率" width="85" align="right" sortable :sort-method="(a: SkuCostItem, b: SkuCostItem) => a.costRate - b.costRate">
          <template #default="{ row }">
            <el-tag
              v-if="row.revenue > 0"
              :type="row.costRate > 50 ? 'danger' : row.costRate > 25 ? 'warning' : 'success'"
              size="small"
            >
              {{ row.costRate.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc;">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
