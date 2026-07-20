<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick, toRef } from 'vue'
import * as echarts from 'echarts'
import { Document, Van, Box, CircleCheck, CircleClose, TrendCharts } from '@element-plus/icons-vue'
import type { Product, OrderListItem } from '@/types'
import { useOrders } from '@/composables/useOrders'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const dr = toRef(props, 'dateRange')

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
  statusFilter, schemaFilter,
  selectedOrder, fetchDetail, clearDetail,
} = useOrders(dr)

// ── 订单详情抽屉 ────────────────────────────────────────
const drawerVisible = ref(false)

async function onRowClick(row: OrderListItem) {
  drawerVisible.value = true
  await fetchDetail(row.posting_number)
}

function onDrawerClosed() {
  clearDetail()
}

// ── 趋势图 ──────────────────────────────────────────────
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
          h += `<br/><span style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${p.color};margin-right:4px"></span>${p.seriesName}: <strong>${Number(p.value).toLocaleString()} 单</strong>` }
        return h + `<br/>合计: <strong>${sum.toLocaleString()} 单</strong></div>`
      },
    },
    legend: { data: ['已签收', '已取消'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 35 },
    xAxis: { type: 'category', data: dates, axisLabel: { fontSize: 11, rotate: dates.length > 30 ? 45 : 0 } },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '已签收', type: 'bar', stack: 'total', data: trend.value.map(d => d.delivered),
        itemStyle: { color: '#67c23a' }, emphasis: { focus: 'series' }, barMaxWidth: 24 },
      { name: '已取消', type: 'bar', stack: 'total', data: trend.value.map(d => d.cancelled),
        itemStyle: { color: '#f56c6c' }, emphasis: { focus: 'series' }, barMaxWidth: 24 },
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
  return v.replace('T', ' ').slice(0, 16)
}

// ── 分页 ──────────────────────────────────────────────────
function onPageChange(page: number) { currentPage.value = page }
function onPageSizeChange(size: number) { pageSize.value = size; currentPage.value = 1 }

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
    <!-- 概览卡片 6 张 -->
    <el-row :gutter="16" v-if="overview">
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Document /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">订单总数</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.total_orders) }} 单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Van /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">FBO（官方仓）</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.fbo_count) }} 单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><Box /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">FBS（自发货）</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.fbs_count) }} 单</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><CircleCheck /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">已签收</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.delivered_count) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f56c6c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#f56c6c;"><el-icon><CircleClose /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">已取消</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.cancelled_count) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><TrendCharts /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">取消率</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ overview.cancellation_rate.toFixed(1) }}%</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display: flex; align-items: center; gap: 10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#90939918;display:flex;align-items:center;justify-content:center;font-size:18px;color:#909399;"><el-icon><Document /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">总件数</div>
              <div style="font-size:20px;font-weight:700;color:#303133;">{{ fmtInt(overview.total_ordered_units) }}</div>
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
          <span style="font-weight:600;">订单趋势（按下单日期）</span>
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
          <span style="font-weight:600;">订单列表</span>
          <div style="display:flex;align-items:center;gap:8px;">
            <el-select v-model="statusFilter" placeholder="全部状态" clearable size="small" style="width:110px;">
              <el-option label="待发货" value="awaiting_deliver" />
              <el-option label="配送中" value="delivering" />
              <el-option label="已签收" value="delivered" />
              <el-option label="已取消" value="cancelled" />
            </el-select>
            <el-select v-model="schemaFilter" placeholder="全部配送" clearable size="small" style="width:100px;">
              <el-option label="FBO" value="FBO" />
              <el-option label="FBS" value="FBS" />
            </el-select>
            <el-tag type="info" size="small">{{ listTotal }} 单</el-tag>
          </div>
        </div>
      </template>
      <el-table :data="orderList" stripe size="small" style="width:100%" max-height="500"
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
        <el-table-column label="配送" width="70" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain" :type="row.delivery_schema === 'FBO' ? 'primary' : 'warning'">
              {{ row.delivery_schema || '—' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusTagType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下单时间" width="140" sortable :sort-method="(a:OrderListItem,b:OrderListItem) => (a.created_at||'').localeCompare(b.created_at||'')">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ formatDate(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="签收时间" width="140">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ formatDate(row.delivered_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="product_count" label="商品数" width="70" align="center" sortable />
        <el-table-column prop="total_quantity" label="总件数" width="70" align="right" sortable>
          <template #default="{ row }">
            <span style="font-weight:600;">{{ fmtInt(row.total_quantity) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_price" label="金额" width="110" align="right" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.total_price > 0 ? '#303133' : '#c0c4cc' }">
              {{ row.total_price > 0 ? '₽ ' + formatMoney(row.total_price) : '—' }}
            </span>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="listTotal > 0" style="margin-top:12px;display:flex;justify-content:flex-end;">
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
            <el-table-column label="SKU" width="85">
              <template #default="{ row }">
                <span style="font-family:monospace;font-size:12px;">{{ row.sku || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="offer_id" label="货号" width="90">
              <template #default="{ row }">
                <span style="font-size:12px;">{{ row.offer_id || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="140" show-overflow-tooltip />
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
  </div>
</template>

<style scoped>
</style>