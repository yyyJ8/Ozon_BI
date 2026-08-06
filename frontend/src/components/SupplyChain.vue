<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import type { Product, SkuTableRow, SkuPipelineDetail } from '@/types'
import { getSkuPipelineList, getSkuPipelineDetail } from '@/api'
import { useLocalDateRange } from '@/composables/useLocalDateRange'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

const loading = ref(false)
const list = ref<SkuTableRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(30)
const search = ref('')

// Product name lookup
const productMap = computed(() => {
  const m = new Map<string, Product>()
  for (const p of props.products) {
    if (p.offer_id) m.set(p.offer_id, p)
  }
  return m
})

function productName(itemId: string) {
  return productMap.value.get(itemId)?.name || null
}

// 阶段状态颜色
function planTagType(row: SkuTableRow) {
  if (!row.plan_status) return 'info'
  if (row.plan_status === '4') return 'success'
  if (row.plan_status === '5') return 'danger'
  return 'warning'
}
function orderTagType(row: SkuTableRow) {
  if (!row.order_status) return 'info'
  if (row.order_status === '7') return 'success'
  if (row.order_status === '6') return 'danger'
  return 'warning'
}
function shippingTagType(row: SkuTableRow) {
  if (!row.shipping_status) return 'info'
  if (row.shipping_status === '11' || row.shipping_status === '12' || row.shipping_status === '13') return 'success'
  if (row.shipping_status === '9') return 'danger'
  return 'warning'
}

async function fetchList() {
  if (!localDateRange.value) return
  loading.value = true
  try {
    const [d1, d2] = localDateRange.value
    const res = await getSkuPipelineList(d1, d2, search.value || undefined, page.value, pageSize.value)
    list.value = res.items
    total.value = res.total
  } catch { /* ignore */ }
  finally { loading.value = false }
}

watch([localDateRange, page, pageSize, search], () => { fetchList() }, { immediate: true })
watch(() => props.activeTab, (t) => { if (t === 'supply-chain') fetchList() })

// ── 展开行 ──
const expandedSet = ref<Set<string>>(new Set())
const detailMap = ref<Record<string, SkuPipelineDetail>>({})
const loadingDetail = ref<Record<string, boolean>>({})

async function onExpandChange(row: SkuTableRow, expanded: boolean) {
  if (!expanded) { expandedSet.value.delete(row.item_id); return }
  expandedSet.value.add(row.item_id)
  if (detailMap.value[row.item_id]) return
  loadingDetail.value[row.item_id] = true
  try { detailMap.value[row.item_id] = await getSkuPipelineDetail(row.item_id) }
  catch { /* ignore */ }
  finally { loadingDetail.value[row.item_id] = false }
}

// ── 工具 ──
function fmtInt(v: number) { return v ? v.toLocaleString('ru-RU') : '0' }
function fmtFloat(v: number) { return v ? v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : '0' }
function fmtMoney(v: number) { return v ? v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00' }
function fmtDate(v: string | null) {
  if (!v) return ''
  return v.length > 10 ? v.slice(0, 10) : v
}
function onPageChange(p: number) { page.value = p }
function onPageSizeChange(s: number) { pageSize.value = s; page.value = 1 }
</script>

<template>
  <div v-loading="loading" style="min-height:300px;">

    <!-- 顶部工具栏：日期 + 搜索 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
      <span style="font-size:12px;color:#909399;white-space:nowrap;">📅</span>
      <el-select v-model="periodPreset" style="width:100px" size="small" @change="applyPreset">
        <el-option label="近30天" value="30days" />
        <el-option label="近7天" value="7days" />
        <el-option label="全部" value="all" />
        <el-option label="自定义" value="custom" />
      </el-select>
      <el-date-picker
        v-if="showCustomDate"
        v-model="localDateRange"
        type="daterange" size="small" range-separator="至"
        start-placeholder="开始" end-placeholder="结束"
        value-format="YYYY-MM-DD" style="width:220px"
        :disabled-date="disabledDate"
      />
      <el-input
        v-model="search"
        placeholder="搜索货号/SKU"
        clearable
        size="small"
        style="width:200px;margin-left:auto;"
        @clear="fetchList()"
        @keyup.enter="fetchList()"
      >
        <template #prefix><span style="font-size:12px;">🔍</span></template>
      </el-input>
      <el-tag type="info" size="small">{{ total }} 个 SKU</el-tag>
    </div>

    <!-- 大表 -->
    <el-card shadow="hover">
      <el-table
        :data="list"
        stripe size="small"
        max-height="calc(100vh - 260px)"
        @expand-change="onExpandChange"
        :row-key="(r: SkuTableRow) => r.item_id"
      >
        <!-- 展开：三阶段明细 -->
        <el-table-column type="expand" width="30">
          <template #default="{ row }">
            <div v-loading="loadingDetail[row.item_id]" style="padding:8px 24px;">
              <template v-if="detailMap[row.item_id]">
                <el-row :gutter="12">
                  <el-col :span="8">
                    <div style="font-size:12px;font-weight:600;color:#e6a23c;margin-bottom:4px;">📋 申购明细</div>
                    <div v-if="!detailMap[row.item_id].plans.length" style="color:#c0c4cc;font-size:11px;">—</div>
                    <div v-for="p in detailMap[row.item_id].plans" :key="p.po_plan_no"
                      style="font-size:11px;line-height:1.7;padding:2px 0;border-bottom:1px dashed #f0f0f0;">
                      <span style="font-family:monospace;color:#409eff;">{{ p.po_plan_no }}</span>
                      <el-tag size="small" effect="plain" style="margin-left:4px;">{{ p.status_label }}</el-tag>
                      | 计划{{ fmtFloat(p.plan_qty) }} 已下单{{ fmtFloat(p.already_qty) }}
                      收货{{ fmtFloat(p.wms_rec_qty) }}
                      <span style="color:#909399;">{{ fmtDate(p.expect_date) }}</span>
                    </div>
                  </el-col>
                  <el-col :span="8">
                    <div style="font-size:12px;font-weight:600;color:#409eff;margin-bottom:4px;">📦 采购明细</div>
                    <div v-if="!detailMap[row.item_id].orders.length" style="color:#c0c4cc;font-size:11px;">—</div>
                    <div v-for="o in detailMap[row.item_id].orders" :key="o.po_no"
                      style="font-size:11px;line-height:1.7;padding:2px 0;border-bottom:1px dashed #f0f0f0;">
                      <span style="font-family:monospace;color:#409eff;">{{ o.po_no }}</span>
                      <el-tag size="small" effect="plain" :type="o.status === '7' ? 'success' : 'warning'">{{ o.status_label }}</el-tag>
                      | {{ fmtFloat(o.qty) }}个 收货{{ fmtFloat(o.receipt_qty) }}
                      <span v-if="o.price">¥{{ fmtMoney(o.price) }}</span>
                      <span style="color:#909399;">{{ fmtDate(o.expect_receipt_date) }}</span>
                    </div>
                  </el-col>
                  <el-col :span="8">
                    <div style="font-size:12px;font-weight:600;color:#67c23a;margin-bottom:4px;">🚚 发货明细</div>
                    <div v-if="!detailMap[row.item_id].shippings.length" style="color:#c0c4cc;font-size:11px;">—</div>
                    <div v-for="s in detailMap[row.item_id].shippings" :key="s.order_code"
                      style="font-size:11px;line-height:1.7;padding:2px 0;border-bottom:1px dashed #f0f0f0;">
                      <span style="font-family:monospace;color:#409eff;">{{ s.order_code }}</span>
                      <el-tag size="small" effect="plain"
                        :type="['11','12','13'].includes(s.order_status||'') ? 'success' : 'warning'">{{ s.status_label }}</el-tag>
                      | {{ fmtFloat(s.final_shipping_num) }}件
                      <span v-if="s.channel_code">{{ s.channel_code }}</span>
                      <span style="color:#909399;">{{ fmtDate(s.shipping_time) }}</span>
                      <span v-if="s.arrived_time" style="color:#67c23a;">到仓{{ fmtDate(s.arrived_time) }}</span>
                    </div>
                  </el-col>
                </el-row>
              </template>
            </div>
          </template>
        </el-table-column>

        <!-- 货号 + 商品名 -->
        <el-table-column label="货号 / 商品" min-width="180" fixed="left" show-overflow-tooltip>
          <template #default="{ row }">
            <div>
              <span style="font-family:monospace;font-size:12px;">{{ row.item_id }}</span>
              <div v-if="productName(row.item_id)" style="font-size:11px;color:#909399;margin-top:2px;">
                {{ productName(row.item_id) }}
              </div>
            </div>
          </template>
        </el-table-column>

        <!-- 申购 -->
        <el-table-column label="申购单号" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.plan_no" style="font-family:monospace;font-size:11px;">{{ row.plan_no }}</span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="申购状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.plan_status" size="small" effect="plain" :type="planTagType(row)">{{ row.plan_status_label }}</el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="计划数" width="70" align="right">
          <template #default="{ row }"><span :style="{fontWeight: row.plan_qty > 0 ? 600 : 400}">{{ fmtFloat(row.plan_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已下单" width="70" align="right">
          <template #default="{ row }"><span :style="{color: row.already_qty > 0 ? '#409eff' : '#c0c4cc'}">{{ fmtFloat(row.already_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="申购类型" width="95" align="center">
          <template #default="{ row }"><span style="font-size:11px;">{{ row.plan_type_label || '—' }}</span></template>
        </el-table-column>

        <!-- 采购 -->
        <el-table-column label="采购单号" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.order_no" style="font-family:monospace;font-size:11px;">{{ row.order_no }}</span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="采购状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.order_status" size="small" effect="plain" :type="orderTagType(row)">{{ row.order_status_label }}</el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="采购数" width="70" align="right">
          <template #default="{ row }"><span :style="{fontWeight: row.order_qty > 0 ? 600 : 400}">{{ fmtFloat(row.order_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已收货" width="70" align="right">
          <template #default="{ row }"><span :style="{color: row.receipt_qty > 0 ? '#67c23a' : '#c0c4cc'}">{{ fmtFloat(row.receipt_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="采购金额" width="100" align="right">
          <template #default="{ row }"><span v-if="row.order_amount" style="font-size:11px;">¥{{ fmtMoney(row.order_amount) }}</span><span v-else style="color:#c0c4cc;">—</span></template>
        </el-table-column>

        <!-- 发货 -->
        <el-table-column label="发货单号" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.shipping_no" style="font-family:monospace;font-size:11px;">{{ row.shipping_no }}</span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="发货状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.shipping_status" size="small" effect="plain" :type="shippingTagType(row)">{{ row.shipping_status_label }}</el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="发货数" width="70" align="right">
          <template #default="{ row }"><span :style="{fontWeight: row.final_shipping_qty > 0 ? 600 : 400}">{{ fmtFloat(row.final_shipping_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已到仓" width="70" align="right">
          <template #default="{ row }"><span :style="{color: row.inbound_qty > 0 ? '#67c23a' : '#c0c4cc'}">{{ fmtFloat(row.inbound_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="物流" width="70" align="center">
          <template #default="{ row }"><span style="font-size:11px;">{{ row.channel_code || '—' }}</span></template>
        </el-table-column>

        <!-- 元数据 -->
        <el-table-column label="站点" width="50" align="center">
          <template #default="{ row }"><span>{{ row.marketplace || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="期望交期" width="95" align="center">
          <template #default="{ row }"><span style="font-size:11px;">{{ fmtDate(row.expect_date) || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="发货时间" width="95" align="center">
          <template #default="{ row }"><span style="font-size:11px;">{{ fmtDate(row.shipping_time) || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="最近更新" width="130" align="center" sortable>
          <template #default="{ row }"><span style="font-size:11px;">{{ row.latest_update ? row.latest_update.slice(0,16) : '—' }}</span></template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" style="margin-top:12px;display:flex;justify-content:flex-end;">
        <el-pagination
          v-model:current-page="page" v-model:page-size="pageSize"
          :page-sizes="[20, 30, 50, 100]" :total="total"
          layout="total, sizes, prev, pager, next, jumper" small
          @current-change="onPageChange" @size-change="onPageSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>
