<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useDashboard } from '@/composables/useDashboard'
import type { ProductSummary } from '@/types'
import type { SummaryRow, FinanceTransaction } from '@/types'
import { getFinanceTransactions, getTransactionsByPostings } from '@/api'
import SummaryCards from '@/components/SummaryCards.vue'
import TrendChart from '@/components/TrendChart.vue'
import TopProducts from '@/components/TopProducts.vue'
import InventoryHealth from '@/components/InventoryHealth.vue'
import ReturnAnalysis from '@/components/ReturnAnalysis.vue'
import AdvertisingAnalysis from '@/components/AdvertisingAnalysis.vue'
import CostAnalysis from '@/components/CostAnalysis.vue'

const {
  dateRange,
  selectedSkuId,
  products,
  summaryRows,
  stats,
  loading,
  dailyAggregation,
  productSummary,
  disabledDate,
  availableRange,
  fetchProducts,
} = useDashboard()

// 商品详情弹窗
const detailVisible = ref(false)
const detailProduct = ref<ProductSummary | null>(null)

const productDailyDetail = computed(() => {
  if (!detailProduct.value) return []
  return summaryRows.value
    .filter(r => r.sku_id === detailProduct.value!.sku_id)
    .sort((a, b) => b.date.localeCompare(a.date))
})

function openProductDetail(product: ProductSummary) {
  detailProduct.value = product
  detailVisible.value = true
}

// 展开行：加载当日订单流水
const transactionsMap = ref<Record<string, FinanceTransaction[]>>({})
const loadingTx = ref<Record<string, boolean>>({})
const activeTab = ref('all')

// ─── 日期预设 ──────────────────────────────────────────────
const periodPreset = ref('30days')
const showCustomDate = ref(false)

function daysAgoStr(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().split('T')[0]
}

function applyPreset(preset: string) {
  showCustomDate.value = preset === 'custom'
  switch (preset) {
    case 'yesterday': {
      const y = daysAgoStr(1)
      dateRange.value = [y, y]
      break
    }
    case '7days':
      dateRange.value = [daysAgoStr(7), daysAgoStr(1)]
      break
    case '30days':
      dateRange.value = [daysAgoStr(30), daysAgoStr(1)]
      break
    case 'all':
    default:
      if (availableRange.value) {
        // 排除今天（T+0 数据不完整）
        const maxDate = availableRange.value.max_date
        const yesterday = daysAgoStr(1)
        dateRange.value = [availableRange.value.min_date, maxDate < yesterday ? maxDate : yesterday]
      }
      break
  }
}

// 首次拿到日期范围后，按默认预设（近30天）设置
watch(availableRange, (range) => {
  if (range) applyPreset('30days')
})

function rowKey(row: SummaryRow) {
  return `${row.date}_${row.sku_id}`
}

function normalizeTx(tx: FinanceTransaction): FinanceTransaction {
  return {
    ...tx,
    amount: Number(tx.amount) || 0,
    accruals_for_sale: Number(tx.accruals_for_sale) || 0,
    sale_commission: Number(tx.sale_commission) || 0,
    delivery_charge: Number(tx.delivery_charge) || 0,
    return_delivery_charge: Number(tx.return_delivery_charge) || 0,
  }
}

async function handleExpandChange(row: SummaryRow, expandedRows: SummaryRow[]) {
  const key = rowKey(row)
  const expanded = expandedRows.some(r => rowKey(r) === key)
  if (!expanded) return // 收起时不处理

  if (transactionsMap.value[key]) return // 已缓存

  loadingTx.value[key] = true
  try {
    // 1. 获取当天流水
    const raw = await getFinanceTransactions(row.sku_id, row.date)
    const txs = raw.map(normalizeTx)

    // 2. 跨日期查询这些 posting 的完整流水（销售、退货、费用）
    const postingNumbers = [...new Set(
      txs.map(tx => tx.posting_number).filter(Boolean) as string[]
    )]
    if (postingNumbers.length > 0) {
      try {
        const allTxs = await getTransactionsByPostings(postingNumbers)
        // 合并（去重：同一 operation_id 已存在则跳过）
        const existingIds = new Set(txs.map(tx => tx.operation_id))
        for (const ftx of allTxs.map(normalizeTx)) {
          if (!existingIds.has(ftx.operation_id)) {
            txs.push(ftx)
          }
        }
      } catch {
        // 溯源失败不阻塞主流程
      }
    }

    transactionsMap.value[key] = txs
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '未知错误'
    ElMessage.error('加载订单流水失败: ' + msg)
  } finally {
    loadingTx.value[key] = false
  }
}

// 按订单号聚合
interface OrderGroup {
  posting_number: string
  delivery_schema: string | null
  operations: FinanceTransaction[]
  total_income: number
  total_cost: number
  net_amount: number
  operation_count: number
}

function groupByPostingNumber(transactions: FinanceTransaction[]): OrderGroup[] {
  const map = new Map<string, FinanceTransaction[]>()
  for (const tx of transactions) {
    const key = tx.posting_number || '(无订单号)'
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(tx)
  }
  return Array.from(map.entries())
    .map(([posting_number, ops]) => {
      const total_income = ops
        .filter(tx => tx.amount > 0)
        .reduce((s, tx) => s + tx.amount, 0)
      const total_cost = ops
        .filter(tx => tx.amount < 0)
        .reduce((s, tx) => s + tx.amount, 0)
      const firstDeliveryTx = ops.find(tx => tx.delivery_schema)
      return {
        posting_number,
        delivery_schema: firstDeliveryTx?.delivery_schema || null,
        operations: ops,
        total_income,
        total_cost,
        net_amount: total_income + total_cost,
        operation_count: ops.length,
      }
    })
    .sort((a, b) => b.net_amount - a.net_amount) // 净额高的排前面
}

// 拆解单笔操作的算式
interface FormulaPart {
  label: string
  value: number
}

function getFormulaParts(op: FinanceTransaction): FormulaPart[] {
  const parts: FormulaPart[] = []
  const accruals = Number(op.accruals_for_sale) || 0
  const commission = Number(op.sale_commission) || 0
  const delivery = Number(op.delivery_charge) || 0
  const returnDelivery = Number(op.return_delivery_charge) || 0
  if (accruals !== 0) parts.push({ label: '销售', value: accruals })
  if (commission !== 0) parts.push({ label: '佣金', value: commission })
  if (delivery !== 0) parts.push({ label: '物流', value: delivery })
  if (returnDelivery !== 0) parts.push({ label: '退货运费', value: returnDelivery })
  return parts
}

function formatMoney(v: number): string {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 按类别分组操作（分离订单相关 vs 杂费）
interface OpGroup {
  category: string
  icon: string
  color: string
  operations: FinanceTransaction[]
  subtotal: number
}

function categorizeOperation(op: FinanceTransaction): string {
  const name = (op.operation_type_name || '').toLowerCase()
  if (op.type === 'cancellation') return '取消退款'
  if (name.includes('退货') || op.type === 'returns') return '退货'
  if (op.accruals_for_sale > 0 || (op.amount > 0 && name.includes('配送完成'))) return '销售'
  // 内部会计操作（Redistribution = 支付手续费冲销，净额=0，无实际财务影响）
  if ((op.operation_type || '').includes('Redistribution')) return '冲销'
  return '费用'
}

function groupOperations(ops: FinanceTransaction[]): { orderOps: OpGroup[]; otherFees: FinanceTransaction[] } {
  const orderOps: FinanceTransaction[] = []
  const otherFees: FinanceTransaction[] = []
  for (const op of ops) {
    // Redistribution 类型是内部会计调整（如手续费冲销），不是真实订单
    const isInternalAdjustment = (op.operation_type || '').includes('Redistribution')
    if (op.posting_number && op.posting_number !== '(无订单号)' && !isInternalAdjustment) {
      orderOps.push(op)
    } else {
      otherFees.push(op)
    }
  }
  const map = new Map<string, FinanceTransaction[]>()
  for (const op of orderOps) {
    const cat = categorizeOperation(op)
    if (!map.has(cat)) map.set(cat, [])
    map.get(cat)!.push(op)
  }
  const meta: Record<string, { icon: string; color: string }> = {
    '销售': { icon: '💰', color: '#67c23a' },
    '退货': { icon: '↩️', color: '#f56c6c' },
    '取消退款': { icon: '❌', color: '#909399' },
    '费用': { icon: '📄', color: '#e6a23c' },
    '冲销': { icon: '🔄', color: '#c0c4cc' },
  }
  const order = ['销售', '退货', '取消退款', '费用', '冲销']
  return {
    orderOps: order
      .filter(c => map.has(c))
      .map(c => ({
        category: c,
        ...meta[c],
        operations: map.get(c)!,
        subtotal: map.get(c)!.reduce((s, op) => s + op.amount, 0),
      })),
    otherFees,
  }
}

onMounted(() => {
  fetchProducts()
})
</script>

<template>
  <el-container>
    <!-- 顶部工具栏 -->
    <el-header
      style="
        height: auto;
        padding: 12px 24px;
        background: #fff;
        border-bottom: 1px solid #e4e7ed;
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
      "
    >
      <h2 style="margin: 0; font-size: 20px; color: #303133; white-space: nowrap;">
        Ozon BI Dashboard
      </h2>

      <div style="flex: 1; min-width: 20px" />

      <el-select
        v-model="periodPreset"
        style="width: 120px"
        @change="applyPreset"
      >
        <el-option label="昨天" value="yesterday" />
        <el-option label="近7天" value="7days" />
        <el-option label="近30天" value="30days" />
        <el-option label="全部" value="all" />
        <el-option label="自定义" value="custom" />
      </el-select>

      <el-date-picker
        v-if="showCustomDate"
        v-model="dateRange"
        type="daterange"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width: 260px"
        :disabled-date="disabledDate"
      />

      <el-select
        v-model="selectedSkuId"
        placeholder="全部商品"
        clearable
        filterable
        style="width: 220px"
      >
        <el-option
          v-for="p in products"
          :key="p.sku_id"
          :label="p.name"
          :value="p.sku_id"
        />
      </el-select>

      <el-tag type="info" effect="plain" size="small" style="margin-left: 8px;">
        每日 5:00 / 16:00 自动同步
      </el-tag>
    </el-header>

    <!-- 主体内容 -->
    <el-main style="padding: 20px 24px;">
      <div v-loading="loading" style="min-height: 400px;">
        <!-- 汇总卡片 -->
        <SummaryCards v-if="stats" :stats="stats" />

        <!-- 趋势图 -->
        <el-card shadow="hover" style="margin-top: 20px;">
          <template #header>
            <span style="font-weight: 600">收入 &amp; 利润趋势</span>
          </template>
          <TrendChart :data="dailyAggregation" />
        </el-card>

        <!-- 商品排行榜（预留） -->

        <!-- 商品分析 Tab 面板 -->
        <el-card shadow="hover" style="margin-top: 20px;">
          <el-tabs v-model="activeTab" style="padding: 0 4px;">
            <el-tab-pane label="全部数据" name="all">
              <template #label>
                <span><el-icon><DataBoard /></el-icon> 全部数据</span>
              </template>
              <div style="display: flex; align-items: center; justify-content: flex-end; margin-bottom: 12px;">
                <el-tag type="info" size="small">{{ productSummary.length }} 个商品</el-tag>
              </div>
              <TopProducts
                :products="productSummary"
                @row-click="openProductDetail"
              />
            </el-tab-pane>
            <el-tab-pane label="库存健康" name="inventory">
              <template #label>
                <span><el-icon><Box /></el-icon> 库存健康</span>
              </template>
              <InventoryHealth
                :products="productSummary"
                :summary-rows="summaryRows"
                :active-tab="activeTab"
                @row-click="openProductDetail"
              />
            </el-tab-pane>
            <el-tab-pane label="退货分析" name="returns">
              <template #label>
                <span><el-icon><Failed /></el-icon> 退货分析</span>
              </template>
              <ReturnAnalysis
                :date-range="dateRange"
                :products="products"
                :active-tab="activeTab"
              />
            </el-tab-pane>
            <el-tab-pane label="广告分析" name="advertising">
              <template #label>
                <span><el-icon><TrendCharts /></el-icon> 广告分析</span>
              </template>
              <AdvertisingAnalysis :date-range="dateRange" :products="products" />
            </el-tab-pane>
            <el-tab-pane label="成本分析" name="costs">
              <template #label>
                <span><el-icon><Coin /></el-icon> 成本分析</span>
              </template>
              <CostAnalysis
                :stats="stats"
                :product-summary="productSummary"
                :date-range="dateRange"
                :loading="loading"
                :active-tab="activeTab"
              />
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </div>
    </el-main>

    <!-- 商品详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="detailProduct?.name || '商品详情'"
      width="1200px"
      top="5vh"
      destroy-on-close
    >
      <template v-if="detailProduct">
        <!-- 商品概要信息 -->
        <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px;">
          <el-image
            v-if="detailProduct.primary_image"
            :src="detailProduct.primary_image"
            style="width: 64px; height: 64px; border-radius: 8px; flex-shrink: 0;"
            fit="cover"
          >
            <template #error>
              <div style="width: 64px; height: 64px; background: #e4e7ed; border-radius: 8px;" />
            </template>
          </el-image>

          <div style="flex: 1; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px 24px; font-size: 14px;">
            <div>
              <span style="color: #909399; margin-right: 4px;">SKU</span>
              <span style="font-family: monospace;">{{ detailProduct.sku_id }}</span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">货号</span>
              <span style="font-family: monospace; color: #606266;">{{ detailProduct.offer_id }}</span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">现有库存</span>
              <el-tag
                :type="detailProduct.stock_present > 10 ? 'success' : detailProduct.stock_present > 0 ? 'warning' : 'danger'"
                size="small"
                effect="plain"
              >
                {{ detailProduct.stock_present }}
              </el-tag>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">预留库存</span>
              <span :style="{ color: detailProduct.stock_reserved > 0 ? '#e6a23c' : '#909399' }">
                {{ detailProduct.stock_reserved }}
              </span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">下单件数</span>
              <span style="font-weight: 600;">{{ detailProduct.ordered_units }}</span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">送达件数</span>
              <span style="font-weight: 600; color: #409eff;">{{ detailProduct.delivered_units }}</span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">退货件数</span>
              <span :style="{ color: detailProduct.returns_units > 0 ? '#f56c6c' : '#909399', fontWeight: 600 }">
                {{ detailProduct.returns_units }}
              </span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">佣金率</span>
              <span>{{ detailProduct.commission_rate != null ? detailProduct.commission_rate.toFixed(1) + '%' : '—' }}</span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">总收入</span>
              <span>₽ {{ detailProduct.revenue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">净利润</span>
              <span :style="{ color: detailProduct.net_profit >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
                ₽ {{ detailProduct.net_profit.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
              </span>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">净利润率</span>
              <el-tag
                :type="detailProduct.profit_margin >= 20 ? 'success' : detailProduct.profit_margin >= 0 ? 'warning' : 'danger'"
                size="small"
              >
                {{ detailProduct.profit_margin.toFixed(1) }}%
              </el-tag>
            </div>
            <div>
              <span style="color: #909399; margin-right: 4px;">总费用</span>
              <span style="color: #f56c6c; font-weight: 600;">
                ₽ {{ formatMoney(Math.abs(detailProduct.net_profit - detailProduct.revenue)) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 日明细表格 -->
        <h4 style="margin: 0 0 12px; font-size: 15px; color: #303133;">
          每日明细
          <el-tag type="info" size="small" style="margin-left: 8px;">
            {{ productDailyDetail.length }} 条
          </el-tag>
        </h4>
        <el-table
          :data="productDailyDetail"
          stripe
          size="small"
          style="width: 100%"
          max-height="400"
          :default-sort="{ prop: 'date', order: 'descending' }"
          @expand-change="handleExpandChange"
          :row-key="rowKey"
        >
          <el-table-column type="expand">
            <template #default="{ row }">
              <div v-loading="loadingTx[rowKey(row)]" style="padding: 12px 24px;">
                <template v-if="transactionsMap[rowKey(row)]?.length">
                  <!-- 按订单号聚合 -->
                  <el-table
                    :data="groupByPostingNumber(transactionsMap[rowKey(row)])"
                    size="small"
                    stripe
                    style="width: 100%"
                    border
                    :show-header="true"
                    :row-key="(r: OrderGroup) => r.posting_number"
                  >
                    <!-- 订单内操作明细：按销售/退货/费用分组 -->
                    <el-table-column type="expand">
                      <template #default="{ row: order }">
                        <div style="padding: 8px 24px 8px 48px;">
                          <template v-if="groupOperations(order.operations).orderOps.length">
                            <div
                              v-for="grp in groupOperations(order.operations).orderOps"
                              :key="grp.category"
                              style="margin-bottom: 8px; border: 1px solid #ebeef5; border-radius: 6px; overflow: hidden; max-width: 680px;"
                            >
                              <!-- 组标题 -->
                              <div :style="{
                                padding: '6px 14px',
                                background: grp.color + '0c',
                                borderBottom: '1px solid #ebeef5',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                fontSize: '13px',
                                fontWeight: 600,
                                color: grp.color,
                              }">
                                <span>
                                  {{ grp.icon }} {{ grp.category }}
                                  <template v-if="grp.category === '退货' && grp.operations.length">
                                    <span style="font-size:11px;color:#909399;margin-left:4px">
                                      ({{ [...new Set(grp.operations.map((o: any) => o.operation_date))].sort().join(', ') }})
                                    </span>
                                  </template>
                                </span>
                                <span :style="{ fontFamily: 'monospace' }">
                                  合计 ₽ {{ formatMoney(grp.subtotal) }}
                                </span>
                              </div>
                              <!-- 组内操作 -->
                              <div style="padding: 4px 14px;">
                                <div
                                  v-for="(op, oi) in grp.operations"
                                  :key="oi"
                                  style="display: flex; align-items: center; gap: 12px; padding: 4px 0; border-bottom: 1px dashed #f0f0f0; min-height: 28px;"
                                >
                                  <!-- 算式 -->
                                  <div style="flex: 1; font-family: monospace; font-size: 13px; line-height: 1.8;">
                                    <template v-if="getFormulaParts(op).length">
                                      <span v-for="(part, pi) in getFormulaParts(op)" :key="pi">
                                        <span v-if="pi > 0" style="color: #c0c0c0; margin: 0 2px;">+</span>
                                        <span :style="{ color: part.value >= 0 ? '#67c23a' : '#f56c6c' }">
                                          ₽ {{ formatMoney(part.value) }}
                                        </span>
                                        <span style="color: #c0c0c0; font-size: 11px; margin-left: 2px;">{{ part.label }}</span>
                                      </span>
                                      <span style="color: #c0c0c0; margin: 0 4px;">=</span>
                                      <span :style="{ color: op.amount >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 700 }">
                                        ₽ {{ formatMoney(op.amount) }}
                                      </span>
                                    </template>
                                    <span v-else :style="{ color: op.amount >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
                                      ₽ {{ formatMoney(op.amount) }}
                                    </span>
                                  </div>
                                  <!-- 发货单号后8位 -->
                                  <span v-if="op.posting_number" style="color: #c0c4cc; font-size: 11px; font-family: monospace; white-space: nowrap;">
                                    {{ op.posting_number.slice(-8) }}
                                  </span>
                                </div>
                              </div>
                            </div>

                            <!-- 订单合计 -->
                            <div style="max-width: 680px; padding: 6px 14px; background: #f5f7fa; border-radius: 6px; display: flex; align-items: center; justify-content: space-between; font-size: 14px;">
                              <span style="font-weight: 600; color: #303133;">📦 订单合计</span>
                              <span :style="{
                                color: order.net_amount >= 0 ? '#67c23a' : '#f56c6c',
                                fontFamily: 'monospace',
                                fontWeight: 700,
                                fontSize: '15px',
                              }">
                                ₽ {{ formatMoney(order.net_amount) }}
                                <el-tag
                                  :type="order.net_amount >= 0 ? 'success' : 'danger'"
                                  size="small"
                                  effect="dark"
                                  style="margin-left: 6px;"
                                >
                                  {{ order.net_amount >= 0 ? '盈利' : '亏损' }}
                                </el-tag>
                              </span>
                            </div>
                          </template>

                          <!-- 无订单号的杂费 -->
                          <template v-if="groupOperations(order.operations).otherFees.length">
                            <div style="max-width: 680px; margin-top: 8px; border: 1px dashed #e0e0e0; border-radius: 6px; padding: 8px 14px;">
                              <div style="font-size: 12px; color: #909399; margin-bottom: 4px;">📋 其他扣费（无订单号）</div>
                              <div
                                v-for="(op, oi) in groupOperations(order.operations).otherFees"
                                :key="oi"
                                style="font-family: monospace; font-size: 13px; line-height: 1.8;"
                              >
                                <span style="color: #909399; margin-right: 8px;">{{ op.operation_type_name }}</span>
                                <span :style="{ color: op.amount >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
                                  ₽ {{ formatMoney(op.amount) }}
                                </span>
                              </div>
                            </div>
                          </template>
                        </div>
                      </template>
                    </el-table-column>

                    <el-table-column label="订单号" min-width="200">
                      <template #default="{ row: order }">
                        <div style="display:flex;align-items:center;gap:6px">
                          <span style="font-family: monospace; font-size: 13px; font-weight: 600; color: #303133;">
                            {{ order.posting_number }}
                          </span>
                          <el-tag
                            v-if="order.operations.some(op => categorizeOperation(op) === '退货')"
                            type="danger"
                            size="small"
                            effect="plain"
                          >有退货</el-tag>
                          <el-tag
                            v-if="order.operations.some(op => categorizeOperation(op) === '取消退款') && !order.operations.some(op => categorizeOperation(op) === '退货')"
                            type="info"
                            size="small"
                            effect="plain"
                          >已取消</el-tag>
                        </div>
                      </template>
                    </el-table-column>
                    <el-table-column label="配送" width="65" align="center">
                      <template #default="{ row: order }">
                        <el-tag size="small" effect="plain" :type="order.delivery_schema === 'FBO' ? 'primary' : 'warning'">
                          {{ order.delivery_schema || '—' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="收入" width="130" align="right" sortable :sort-method="(a: OrderGroup, b: OrderGroup) => a.total_income - b.total_income">
                      <template #default="{ row: order }">
                        <span style="color: #67c23a; font-family: monospace;">
                          ₽ {{ order.total_income.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column label="费用" width="130" align="right" sortable :sort-method="(a: OrderGroup, b: OrderGroup) => Math.abs(a.total_cost) - Math.abs(b.total_cost)">
                      <template #default="{ row: order }">
                        <span style="color: #f56c6c; font-family: monospace;">
                          ₽ {{ order.total_cost.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column label="净额" width="130" align="right" sortable :sort-method="(a: OrderGroup, b: OrderGroup) => a.net_amount - b.net_amount">
                      <template #default="{ row: order }">
                        <span :style="{
                          color: order.net_amount >= 0 ? '#67c23a' : '#f56c6c',
                          fontFamily: 'monospace',
                          fontWeight: 700,
                        }">
                          ₽ {{ order.net_amount.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                        </span>
                        <el-tag
                          :type="order.net_amount >= 0 ? 'success' : 'danger'"
                          size="small"
                          effect="dark"
                          style="margin-left: 6px;"
                        >
                          {{ order.net_amount >= 0 ? '盈利' : '亏损' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="操作" width="50" align="center">
                      <template #default="{ row: order }">
                        <span style="color: #c0c4cc; font-size: 12px;">×{{ order.operation_count }}</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </template>
                <div v-else style="text-align: center; color: #c0c4cc; padding: 16px; font-size: 13px;">
                  暂无订单流水数据
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column prop="date" label="日期" width="90" sortable />
          <el-table-column label="质量" width="70" align="center">
            <template #default="{ row }">
              <el-tag
                :type="row.data_quality === 'complete' ? 'success' : 'warning'"
                size="small"
                effect="plain"
              >
                {{ row.data_quality === 'complete' ? '完整' : '部分' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="ordered_units" label="下单" width="50" align="right" sortable />
          <el-table-column prop="delivered_units" label="送达" width="50" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.delivered_units > 0 ? '#409eff' : '#c0c4cc', fontWeight: row.delivered_units > 0 ? 600 : 400 }">
                {{ row.delivered_units }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="returns_units" label="退货" width="50" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.returns_units > 0 ? '#f56c6c' : '#c0c4cc' }">
                {{ row.returns_units }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="returns_amount" label="退货金额" width="100" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.returns_amount !== 0 ? '#f56c6c' : '#c0c4cc' }">
                {{ row.returns_amount !== 0 ? '₽ ' + formatMoney(row.returns_amount) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="revenue" label="收入" width="100" align="right" sortable>
            <template #default="{ row }">
              ₽ {{ formatMoney(row.revenue) }}
            </template>
          </el-table-column>
          <el-table-column prop="commissions" label="佣金" width="90" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.commissions !== 0 ? '#f56c6c' : '#c0c4cc' }">
                {{ row.commissions !== 0 ? '₽ ' + formatMoney(row.commissions) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="logistics_costs" label="物流" width="90" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.logistics_costs !== 0 ? '#f56c6c' : '#c0c4cc' }">
                {{ row.logistics_costs !== 0 ? '₽ ' + formatMoney(row.logistics_costs) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="费用" width="100" align="right" sortable>
            <template #default="{ row }">
              <el-popover
                v-if="(row.storage_fees + row.advertising + row.other_costs) !== 0"
                placement="top"
                :width="180"
                trigger="hover"
              >
                <template #reference>
                  <span style="color: #f56c6c; cursor: pointer; border-bottom: 1px dashed #c0c4cc;">
                    ₽ {{ formatMoney(row.storage_fees + row.advertising + row.other_costs) }}
                  </span>
                </template>
                <div style="font-family:monospace;font-size:12px;line-height:2">
                  <div>仓储: <span style="color:#f56c6c">₽ {{ formatMoney(row.storage_fees) }}</span></div>
                  <div>广告: <span style="color:#f56c6c">₽ {{ formatMoney(row.advertising) }}</span></div>
                  <div>其他: <span style="color:#f56c6c">₽ {{ formatMoney(row.other_costs) }}</span></div>
                </div>
              </el-popover>
              <span v-else style="color: #c0c4cc;">—</span>
            </template>
          </el-table-column>
          <el-table-column prop="net_profit" label="净利" width="100" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
                ₽ {{ formatMoney(row.net_profit) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="profit_margin" label="利润率" width="75" align="right" sortable>
            <template #default="{ row }">
              <el-tag
                :type="row.profit_margin >= 20 ? 'success' : row.profit_margin >= 0 ? 'warning' : 'danger'"
                size="small"
              >
                {{ row.profit_margin.toFixed(1) }}%
              </el-tag>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>
  </el-container>
</template>
