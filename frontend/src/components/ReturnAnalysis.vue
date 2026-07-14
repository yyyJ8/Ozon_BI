<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ProductSummary } from '@/types'

const props = defineProps<{
  products: ProductSummary[]
  activeTab: string
}>()

const emit = defineEmits<{
  (e: 'row-click', product: ProductSummary): void
}>()

// ─── 衍生数据 ────────────────────────────────────────────
interface ReturnItem {
  sku_id: number
  offer_id: string
  name: string
  primary_image: string | null
  ordered_units: number
  revenue: number
  returns_amount: number
  return_rate: number // 退货金额 / 收入 * 100
  severity: 'danger' | 'warning' | 'success'
}

const items = computed<ReturnItem[]>(() => {
  return props.products
    .filter(p => p.revenue > 0)
    .map(p => {
      const return_rate = p.revenue > 0 ? (p.returns_amount / p.revenue) * 100 : 0
      let severity: 'danger' | 'warning' | 'success'
      if (return_rate > 20) severity = 'danger'
      else if (return_rate > 10) severity = 'warning'
      else severity = 'success'

      return {
        sku_id: p.sku_id,
        offer_id: p.offer_id,
        name: p.name,
        primary_image: p.primary_image,
        ordered_units: p.ordered_units,
        revenue: p.revenue,
        returns_amount: p.returns_amount,
        return_rate,
        severity,
      }
    })
    .sort((a, b) => b.return_rate - a.return_rate)
})

// 统计概览
const overview = computed(() => {
  const total = items.value.length
  const total_returns = items.value.reduce((s, i) => s + i.returns_amount, 0)
  const total_revenue = items.value.reduce((s, i) => s + i.revenue, 0)
  const avg_return_rate = total_revenue > 0 ? (total_returns / total_revenue) * 100 : 0
  const danger_count = items.value.filter(i => i.severity === 'danger').length
  const warning_count = items.value.filter(i => i.severity === 'warning').length
  const top_returner = items.value.length > 0 ? items.value[0] : null
  return { total, total_returns, total_revenue, avg_return_rate, danger_count, warning_count, top_returner }
})

// 图表数据 — 取退货率前 20
const chartData = computed(() => {
  return items.value.slice(0, 20).reverse() // reverse for horizontal bar (top-to-bottom)
})

// ─── 退货率排行图 ─────────────────────────────────────────
const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chart || !chartData.value.length) return

  // 用 dataIndex 映射，避免按名称匹配的坑
  const itemMap: Record<number, ReturnItem> = {}
  chartData.value.forEach((d, i) => { itemMap[i] = d })

  const maxRate = Math.max(...chartData.value.map(d => d.return_rate), 0) * 1.2

  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        formatter: (params: { dataIndex: number; value: number }[]) => {
          const item = itemMap[params[0].dataIndex]
          if (!item) return ''
          return `<div style="font-size:13px;line-height:1.8">
            <strong>${item.name}</strong><br/>
            退货率: <strong style="color:${item.return_rate > 20 ? '#f56c6c' : item.return_rate > 10 ? '#e6a23c' : '#67c23a'}">${item.return_rate.toFixed(1)}%</strong><br/>
            退货金额: ₽ ${item.returns_amount.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}<br/>
            收入: ₽ ${item.revenue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}<br/>
            销量: ${item.ordered_units} 件
          </div>`
        },
      },
      grid: { left: 10, right: 70, top: 10, bottom: 20 },
      xAxis: {
        type: 'value',
        max: Math.max(maxRate, 5),
        axisLabel: { formatter: '{value}%', fontSize: 11 },
      },
      yAxis: {
        type: 'category',
        data: chartData.value.map(d => d.name),
        axisLabel: {
          fontSize: 11,
          width: 100,
          overflow: 'truncate',
        },
      },
      series: [
        {
          type: 'bar',
          data: chartData.value.map(d => ({
            value: d.return_rate,
            itemStyle: {
              color:
                d.severity === 'danger'
                  ? '#f56c6c'
                  : d.severity === 'warning'
                    ? '#e6a23c'
                    : '#67c23a',
              borderRadius: [0, 4, 4, 0],
            },
          })),
          barMaxWidth: 24,
          label: {
            show: true,
            position: 'right',
            formatter: (p: { value: number }) => `${p.value.toFixed(1)}%`,
            fontSize: 11,
          },
        },
      ],
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
  if (props.activeTab === 'returns') initIfNeeded()
})

watch(() => props.activeTab, (tab) => {
  if (tab === 'returns') {
    nextTick(() => {
      initIfNeeded()
      chart?.resize()
    })
  }
})

watch(() => props.products, () => {
  if (initialized) renderChart()
}, { deep: true })

onUnmounted(() => {
  chart?.dispose()
})

// ─── 工具函数 ────────────────────────────────────────────
function formatMoney(v: number): string {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function severityTagType(s: string): string {
  return s === 'danger' ? 'danger' : s === 'warning' ? 'warning' : 'success'
}

function severityLabel(s: string): string {
  return s === 'danger' ? '高' : s === 'warning' ? '中' : '低'
}
</script>

<template>
  <div>
    <!-- 概览卡片 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px 20px' }">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 44px; height: 44px; border-radius: 10px; background: #409eff18; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #409eff;">
              <el-icon><Money /></el-icon>
            </div>
            <div>
              <div style="font-size: 13px; color: #909399; margin-bottom: 2px;">退货总额</div>
              <div style="font-size: 18px; font-weight: 700; color: #f56c6c;">
                ₽ {{ formatMoney(overview.total_returns) }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px 20px' }">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 44px; height: 44px; border-radius: 10px; background: #e6a23c18; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #e6a23c;">
              <el-icon><TrendCharts /></el-icon>
            </div>
            <div>
              <div style="font-size: 13px; color: #909399; margin-bottom: 2px;">平均退货率</div>
              <div style="font-size: 18px; font-weight: 700; color: #303133;">
                {{ overview.avg_return_rate.toFixed(2) }}%
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px 20px' }">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 44px; height: 44px; border-radius: 10px; background: #f56c6c18; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #f56c6c;">
              <el-icon><WarningFilled /></el-icon>
            </div>
            <div>
              <div style="font-size: 13px; color: #909399; margin-bottom: 2px;">高退货率商品</div>
              <div style="font-size: 18px; font-weight: 700;">
                <span style="color: #f56c6c;">{{ overview.danger_count }}</span>
                <span v-if="overview.warning_count > 0" style="color: #e6a23c; margin-left: 8px;">+{{ overview.warning_count }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" :body-style="{ padding: '16px 20px' }">
          <div style="display: flex; align-items: center; gap: 12px;">
            <div style="width: 44px; height: 44px; border-radius: 10px; background: #67c23a18; display: flex; align-items: center; justify-content: center; font-size: 20px; color: #67c23a;">
              <el-icon><ShoppingCart /></el-icon>
            </div>
            <div>
              <div style="font-size: 13px; color: #909399; margin-bottom: 2px;">覆盖商品</div>
              <div style="font-size: 18px; font-weight: 700; color: #303133;">
                {{ overview.total }} 个
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表 + 表格 -->
    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <span style="font-weight: 600">退货率 TOP 20</span>
          </template>
          <div ref="chartRef" style="width: 100%; height: 420px" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="font-weight: 600">退货明细排行</span>
              <el-tag type="info" size="small">按退货率降序</el-tag>
            </div>
          </template>
          <el-table
            :data="items"
            stripe
            size="small"
            style="width: 100%"
            max-height="400"
            highlight-current-row
            @row-click="(row: ReturnItem) => emit('row-click', props.products.find(p => p.sku_id === row.sku_id)!)"
          >
            <el-table-column type="index" label="#" width="40" />
            <el-table-column prop="sku_id" label="SKU" width="80" sortable>
              <template #default="{ row }">
                <span style="font-family: monospace; font-size: 12px;">{{ row.sku_id }}</span>
              </template>
            </el-table-column>
            <el-table-column label="商品" min-width="130" show-overflow-tooltip>
              <template #default="{ row }">
                <div style="display: flex; align-items: center; gap: 8px;">
                  <el-image
                    v-if="row.primary_image"
                    :src="row.primary_image"
                    style="width: 28px; height: 28px; border-radius: 4px; flex-shrink: 0;"
                    fit="cover"
                    lazy
                  >
                    <template #error>
                      <div style="width: 28px; height: 28px; background: #f5f7fa; border-radius: 4px;" />
                    </template>
                  </el-image>
                  <span>{{ row.name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="ordered_units" label="销量" width="60" align="right" sortable />
            <el-table-column prop="revenue" label="收入" width="90" align="right" sortable>
              <template #default="{ row }">
                ₽ {{ formatMoney(row.revenue) }}
              </template>
            </el-table-column>
            <el-table-column prop="returns_amount" label="退货金额" width="90" align="right" sortable>
              <template #default="{ row }">
                <span style="color: #f56c6c;">₽ {{ formatMoney(row.returns_amount) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="return_rate" label="退货率" width="80" align="right" sortable>
              <template #default="{ row }">
                <el-tag
                  :type="severityTagType(row.severity)"
                  size="small"
                  effect="dark"
                >
                  {{ row.return_rate.toFixed(1) }}%
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="程度" width="60" align="center">
              <template #default="{ row }">
                <el-tag :type="severityTagType(row.severity)" size="small" effect="plain">
                  {{ severityLabel(row.severity) }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
