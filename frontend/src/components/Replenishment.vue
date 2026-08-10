<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import type { ReplenishmentRow } from '@/types'
import { getReplenishment } from '@/api'
import { useStore } from '@/composables/useStore'

const { selectedStoreId } = useStore()

// ── 数据状态 ──
const rows = ref<ReplenishmentRow[]>([])
const loading = ref(false)
const selectedRow = ref<ReplenishmentRow | null>(null)
const onlyNeedReplenishment = ref(false)

// ── 筛选后的行 ──
const HIDDEN_STATUSES = ['已清零', '淘汰']

const filteredRows = computed(() => {
  let list = rows.value.filter(r => !HIDDEN_STATUSES.includes(r.product_status || ''))
  if (onlyNeedReplenishment.value) {
    list = list.filter(r => r.suggested_replenishment !== '♥☺♥')
  }
  return list
})

// ── 加载 ──
async function fetchData() {
  loading.value = true
  try {
    rows.value = await getReplenishment(selectedStoreId.value)
    if (selectedRow.value) {
      const found = rows.value.find(r => r.sku_id === selectedRow.value!.sku_id)
      selectedRow.value = found || null
    }
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.message || '未知'))
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
watch(selectedStoreId, fetchData)

// ── 统计 ──
const stats = computed(() => {
  const all = filteredRows.value
  const need = all.filter(r => r.suggested_replenishment !== '♥☺♥')
  const totalQty = need.reduce((sum, r) => sum + (r.suggested_replenishment === '♥☺♥' ? 0 : parseInt(r.suggested_replenishment) || 0), 0)
  return { total: all.length, need: need.length, totalQty }
})

// ── 行点击 ──
function onRowClick(row: ReplenishmentRow) {
  selectedRow.value = row
}

// ── 计算每个变量的展示值 ──
function calcStep(row: ReplenishmentRow) {
  const s3 = row.sales_3d
  const s7 = row.sales_7d
  const s14 = row.sales_14d
  const s30 = row.sales_30d
  const w3 = s3 ? s3 / 3 * 0.2 : 0
  const w7 = s7 ? s7 / 7 * 0.3 : 0
  const w14 = s14 ? s14 / 14 * 0.3 : 0
  const w30 = s30 ? s30 / 30 * 0.2 : 0

  return {
    // ① 加权日销量
    w3, w7, w14, w30,
    weighted: row.weighted_daily_sales,
    // ② 跨境在途
    cb_parts: [
      { label: 'SDK', val: row.cross_border_sdk },
      { label: '运盟', val: row.cross_border_yunmeng },
      { label: '昆仑', val: row.cross_border_kunlun },
      { label: '超光速', val: row.cross_border_cgs },
    ],
    cb_total: row.cross_border_total,
    // ③ 补货数量
    safety: row.safety_days,
    logistics: row.logistics_days,
    stock: row.stock_present,
    domestic: row.domestic_in_transit,
    qty_raw: row.replenishment_qty_raw,
    suggested: row.suggested_replenishment,
  }
}

// ── 用于公式面板宽度计算 ──
function formatNum(n: number, decimals?: number): string {
  if (decimals === undefined) {
    decimals = Number.isInteger(n) ? 0 : 2
  }
  return n.toFixed(decimals)
}
</script>

<template>
  <div class="replenishment-container">
    <!-- 左侧：表格 -->
    <div class="left-panel">
      <div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;">
        <el-checkbox v-model="onlyNeedReplenishment" size="small">
          只显示需补货
        </el-checkbox>
        <el-button size="small" :icon="Refresh" @click="fetchData" :loading="loading">刷新</el-button>
        <span style="font-size:12px;color:#909399;">
          共 {{ stats.total }} 个 SKU，
          <span style="color:#f56c6c;font-weight:600;">{{ stats.need }} 个需补货</span>
          <template v-if="stats.totalQty > 0">，总补货量 <strong>{{ stats.totalQty }}</strong> 件</template>
        </span>
      </div>

      <el-table
        :data="filteredRows"
        stripe
        size="small"
        max-height="calc(100vh - 280px)"
        v-loading="loading"
        @row-click="onRowClick"
        highlight-current-row
        :row-style="{ cursor: 'pointer' }"
      >
        <el-table-column label="图片" width="50" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.primary_image"
              :src="row.primary_image"
              style="width:36px;height:36px;border-radius:4px;"
              fit="cover"
              lazy
            >
              <template #error><span style="font-size:10px;color:#c0c4cc;">—</span></template>
            </el-image>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>

        <el-table-column prop="offer_id" label="货号" width="160" sortable show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px;">{{ row.offer_id }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="product_name" label="产品名称" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.product_name }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="product_status" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag
              v-if="row.product_status"
              size="small"
              effect="plain"
              :type="row.product_status === '已清零' || row.product_status === '淘汰' ? 'info' : row.product_status === '重点' ? 'warning' : row.product_status === '新品' ? 'success' : ''"
            >
              {{ row.product_status }}
            </el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>

        <el-table-column prop="stock_present" label="库存" width="65" align="right" sortable>
          <template #default="{ row }">
            <el-tag
              size="small"
              effect="plain"
              :type="row.stock_present > 20 ? 'success' : row.stock_present > 0 ? 'warning' : 'danger'"
            >
              {{ row.stock_present }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="sales_manager" label="负责人" width="75" align="center" />

        <el-table-column label="加权日销" width="85" align="right" sortable prop="weighted_daily_sales">
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:12px;">{{ row.weighted_daily_sales.toFixed(3) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="跨境在途" width="80" align="right" sortable prop="cross_border_total">
          <template #default="{ row }">
            <span :style="{ color: row.cross_border_total > 0 ? '#409eff' : '#c0c4cc' }">
              {{ row.cross_border_total }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="国内在途" width="80" align="right" sortable prop="domestic_in_transit">
          <template #default="{ row }">
            <span :style="{ color: row.domestic_in_transit > 0 ? '#409eff' : '#c0c4cc' }">
              {{ row.domestic_in_transit }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="安全+物流" width="85" align="center">
          <template #default="{ row }">
            <span style="font-size:11px;color:#909399;">{{ row.safety_days }}+{{ row.logistics_days }}</span>
          </template>
        </el-table-column>

        <el-table-column label="建议补货" width="100" align="center" fixed="right" sortable prop="replenishment_qty_raw">
          <template #default="{ row }">
            <el-tag
              v-if="row.suggested_replenishment === '♥☺♥'"
              type="success"
              size="small"
              effect="plain"
            >
              ♥☺♥
            </el-tag>
            <el-tag
              v-else
              type="danger"
              size="small"
              effect="dark"
            >
              {{ row.suggested_replenishment }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 右侧：公式详情面板 -->
    <div class="right-panel">
      <template v-if="selectedRow">
        <el-card shadow="hover" style="height:100%;overflow-y:auto;">
          <template #header>
            <div style="display:flex;align-items:center;gap:8px;">
              <span style="font-weight:600;">📐 计算详情</span>
              <span style="font-size:11px;color:#909399;font-weight:400;">
                {{ selectedRow.offer_id }}
              </span>
            </div>
          </template>

          <div class="formula-chain">
            <!-- ① 加权日销量 -->
            <div class="formula-block">
              <div class="formula-title">① 加权日销量 = {{ calcStep(selectedRow).weighted.toFixed(4) }} 件/天</div>
              <div class="formula-expr">= Σ(窗口销量 ÷ 天数 × 权重)</div>
              <div class="formula-steps">
                <div class="step-line">3天: {{ selectedRow.sales_3d }}÷3 × 0.2 = <strong>{{ calcStep(selectedRow).w3.toFixed(3) }}</strong></div>
                <div class="step-line">7天: {{ selectedRow.sales_7d }}÷7 × 0.3 = <strong>{{ calcStep(selectedRow).w7.toFixed(3) }}</strong></div>
                <div class="step-line">14天: {{ selectedRow.sales_14d }}÷14 × 0.3 = <strong>{{ calcStep(selectedRow).w14.toFixed(3) }}</strong></div>
                <div class="step-line">30天: {{ selectedRow.sales_30d }}÷30 × 0.2 = <strong>{{ calcStep(selectedRow).w30.toFixed(3) }}</strong></div>
              </div>
              <div class="formula-data-tags">
                <el-tag size="small" type="info">3天: {{ selectedRow.sales_3d }}</el-tag>
                <el-tag size="small" type="info">7天: {{ selectedRow.sales_7d }}</el-tag>
                <el-tag size="small" type="info">14天: {{ selectedRow.sales_14d }}</el-tag>
                <el-tag size="small" type="info">30天: {{ selectedRow.sales_30d }}</el-tag>
              </div>
            </div>

            <!-- ② 跨境在途 -->
            <div class="formula-block">
              <div class="formula-title">② 跨境在途 = {{ calcStep(selectedRow).cb_total }} 件</div>
              <div class="formula-expr">= SDK + 运盟 + 昆仑 + 超光速</div>
              <div class="formula-data-tags">
                <template v-for="ch in calcStep(selectedRow).cb_parts" :key="ch.label">
                  <el-tag size="small" :type="ch.val > 0 ? '' : 'info'">{{ ch.label }}: {{ ch.val }}</el-tag>
                </template>
              </div>
            </div>

            <!-- ③ 补货数量 -->
            <div class="formula-block">
              <div class="formula-title">③ 补货数量 = {{ calcStep(selectedRow).qty_raw.toFixed(2) }} 件</div>
              <div class="formula-expr">= 日销量 × (安全 + 物流) − 库存 − 跨境在途 − 国内在途</div>
              <div class="formula-steps">
                <div class="step-line">
                  = {{ calcStep(selectedRow).weighted.toFixed(4) }} × ({{ calcStep(selectedRow).safety }} + {{ calcStep(selectedRow).logistics }})
                  − {{ calcStep(selectedRow).stock }} − {{ calcStep(selectedRow).cb_total }} − {{ calcStep(selectedRow).domestic }}
                </div>
              </div>
              <div class="formula-data-tags">
                <el-tag size="small" type="info">安全: {{ calcStep(selectedRow).safety }}天</el-tag>
                <el-tag size="small" type="info">物流: {{ calcStep(selectedRow).logistics }}天</el-tag>
                <el-tag size="small" type="info">库存: {{ calcStep(selectedRow).stock }}</el-tag>
                <el-tag size="small" type="info">跨境: {{ calcStep(selectedRow).cb_total }}</el-tag>
                <el-tag size="small" type="info">国内: {{ calcStep(selectedRow).domestic }}</el-tag>
              </div>
            </div>

            <!-- ④ 结果 -->
            <div class="formula-block result-block">
              <div class="formula-title" style="font-size:16px;">
                📦 建议补货：
                <template v-if="selectedRow.suggested_replenishment === '♥☺♥'">
                  <span style="color:#67c23a;font-size:24px;">♥☺♥</span>
                  <span style="font-size:12px;color:#909399;">（无需补货）</span>
                </template>
                <template v-else>
                  <span style="color:#f56c6c;font-size:24px;">{{ selectedRow.suggested_replenishment }} 件</span>
                </template>
              </div>
              <div class="formula-expr" style="font-size:11px;color:#909399;">
                = IF(补货数量 ≤ 0, "♥☺♥", CEILING(补货数量, 1))
              </div>
            </div>
          </div>
        </el-card>
      </template>
      <template v-else>
        <el-card shadow="hover" style="height:100%;display:flex;align-items:center;justify-content:center;">
          <div style="text-align:center;color:#c0c4cc;">
            <div style="font-size:48px;margin-bottom:12px;">👈</div>
            <div style="font-size:13px;">点击左侧 SKU 行<br/>查看公式与数据详情</div>
          </div>
        </el-card>
      </template>
    </div>
  </div>
</template>

<style scoped>
.replenishment-container {
  display: flex;
  gap: 16px;
  height: calc(100vh - 260px);
}
.left-panel {
  flex: 7;
  min-width: 0;
  overflow: hidden;
}
.right-panel {
  flex: 3;
  min-width: 360px;
  max-width: 480px;
}

.formula-chain {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.formula-block {
  background: #fafbfc;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px 14px;
}

.formula-block.result-block {
  background: #fef0f0;
  border-color: #fde2e2;
}

.formula-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 6px;
}

.formula-expr {
  font-size: 12px;
  font-family: monospace;
  color: #606266;
  margin-bottom: 8px;
  padding: 4px 8px;
  background: #fff;
  border-radius: 4px;
  border-left: 3px solid #409eff;
}

.formula-steps {
  margin-bottom: 8px;
}

.step-line {
  font-size: 12px;
  font-family: monospace;
  color: #606266;
  padding: 2px 0;
  padding-left: 16px;
}

.formula-data-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
</style>
