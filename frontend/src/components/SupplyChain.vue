<script setup lang="ts">
import { ref, watch, computed, reactive } from 'vue'
import type { PlanTableRow } from '@/types'
import { getPlanPipelineList, updateCargoStatus } from '@/api'
import { useLocalDateRange } from '@/composables/useLocalDateRange'

const props = defineProps<{
  dateRange: [string, string] | null
  activeTab: string
}>()

const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

const loading = ref(false)
const list = ref<PlanTableRow[]>([])
const search = ref('')
const pageSize = 9999

async function fetchList() {
  if (!localDateRange.value) return
  loading.value = true
  try {
    const [d1, d2] = localDateRange.value
    const res = await getPlanPipelineList(d1, d2, search.value || undefined, 1, pageSize)
    list.value = res.items
  } catch { /* ignore */ }
  finally { loading.value = false }
}

watch(() => [localDateRange.value, search.value], () => { fetchList() }, { immediate: true })
watch(() => props.activeTab, (t) => { if (t === 'supply-chain') fetchList() })

// ── 货物状态 ──
const CARGO_STATUSES = ['国内仓备货', '跨境在途', '已约仓', '已上架']

async function onChangeCargoStatus(row: PlanTableRow, val: string) {
  try {
    const manual = (val === '已约仓' || val === '已上架') ? val : ''
    await updateCargoStatus(row.po_plan_no, manual)
    row.manual_status = manual
  } catch { /* ignore */ }
}

// ── 分组展示（按货物状态）──
const expandedGroups = reactive(new Set<string>())
const GROUP_ORDER = ['国内仓备货', '跨境在途', '已约仓', '已上架']

const cargoGroups = computed(() => {
  const groups: Record<string, PlanTableRow[]> = {}
  for (const r of list.value) {
    const key = r.cargo_status || '未分组'
    if (!groups[key]) groups[key] = []
    groups[key].push(r)
  }
  const result: { key: string; items: PlanTableRow[] }[] = []
  for (const key of GROUP_ORDER) {
    if (groups[key]) result.push({ key, items: groups[key] })
  }
  for (const [key, items] of Object.entries(groups)) {
    if (!GROUP_ORDER.includes(key)) result.push({ key, items })
  }
  return result
})

// 新数据到达时自动展开所有分组
watch(cargoGroups, (groups) => {
  for (const g of groups) expandedGroups.add(g.key)
})

function toggleGroup(key: string) {
  if (expandedGroups.has(key)) expandedGroups.delete(key)
  else expandedGroups.add(key)
}

// 扁平列表：分组行 + 展开的数据行
const flatList = computed(() => {
  const result: any[] = []
  for (const group of cargoGroups.value) {
    result.push({ _type: 'group', _groupKey: group.key, _count: group.items.length })
    if (expandedGroups.has(group.key)) {
      for (const item of group.items) result.push(item)
    }
  }
  return result
})

function rowClassName({ row }: any) {
  return row._type === 'group' ? 'cargo-group-row' : ''
}

function spanMethod({ row, columnIndex }: any) {
  if (row._type !== 'group') return [1, 1]
  if (columnIndex === 0) return [1, 100]  // 分组标题跨越所有列
  return [0, 0]
}

// ── 工具 ──
function fmtFloat(v: number) { return v ? v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : '0' }
function fmtMoney(v: number) { return v ? v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00' }
function fmtDate(v: string | null) { if (!v) return ''; return v.length > 10 ? v.slice(0, 10) : v }
function fmtDatetime(v: string | null) { if (!v) return ''; return v.length > 16 ? v.slice(0, 16) : v }
function planTagType(s: string | null) { if (!s) return 'info'; if (s === '已创建采购订单') return 'success'; if (s === '已作废') return 'danger'; return 'warning' }
function orderTagType(s: string | null) { if (!s) return 'info'; if (s === '完结') return 'success'; if (s === '已作废') return 'danger'; return 'warning' }
function shippingTagType(s: string | null) { if (!s) return 'info'; if (s.startsWith('已')) return 'success'; if (s === '已作废') return 'danger'; return 'warning' }
</script>

<template>
  <div v-loading="loading" style="min-height:300px;">

    <!-- 工具栏 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
      <el-select v-model="periodPreset" style="width:100px" size="small" @change="applyPreset">
        <el-option label="近30天" value="30days" /><el-option label="本月" value="thisMonth" /><el-option label="近7天" value="7days" />
        <el-option label="全部" value="all" /><el-option label="自定义" value="custom" />
      </el-select>
      <el-date-picker v-if="showCustomDate" v-model="localDateRange" type="daterange" size="small" range-separator="至"
        start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width:220px" :disabled-date="disabledDate" />
      <el-input v-model="search" placeholder="搜索申购单号/货号" clearable size="small" style="width:200px;margin-left:auto;"
        @clear="fetchList()" @keyup.enter="fetchList()" />
      <el-tag type="info" size="small">{{ list.length }} 个申购单</el-tag>
    </div>

    <!-- 主表 -->
    <el-card shadow="hover">
      <el-table :data="flatList" stripe size="small" max-height="calc(100vh - 260px)"
        :row-class-name="rowClassName" :span-method="spanMethod" :row-key="(r: any) => r.po_plan_no || r._groupKey">

        <el-table-column label="申购单号" width="150">
          <template #default="{ row }">
            <div v-if="row._type === 'group'" style="display:flex;align-items:center;gap:8px;padding:2px 0;">
              <span @click.stop="toggleGroup(row._groupKey)" style="font-size:12px;cursor:pointer;">{{ expandedGroups.has(row._groupKey) ? '▼' : '▶' }}</span>
              <span style="font-weight:700;color:#409eff;cursor:pointer;" @click.stop="toggleGroup(row._groupKey)">{{ row._groupKey }}</span>
              <el-tag size="small" type="info">{{ row._count }}</el-tag>
            </div>
            <span v-else style="font-family:monospace;font-size:12px;">{{ row.po_plan_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="头程单号" width="140" show-overflow-tooltip>
          <template #default="{ row }"><span v-if="row._type !== 'group' && row.direct_first_leg_tracking" style="font-family:monospace;font-size:11px;">{{ row.direct_first_leg_tracking }}</span></template>
        </el-table-column>
        <el-table-column label="SKU" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row._type !== 'group' && row.sku_id" style="font-family:monospace;font-size:12px;">{{ row.sku_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="货号" min-width="170" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row._type !== 'group'" style="font-family:monospace;font-size:12px;">{{ row.item_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="申购状态" width="115" align="center">
          <template #default="{ row }">
            <el-tag v-if="row._type !== 'group' && row.plan_status_label" size="small" effect="plain" :type="planTagType(row.plan_status)">{{ row.plan_status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="计划数" width="70" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group'" :style="{fontWeight: row.plan_qty > 0 ? 600 : 400}">{{ fmtFloat(row.plan_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已下单" width="70" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group'" :style="{color: row.already_qty > 0 ? '#409eff' : '#c0c4cc'}">{{ fmtFloat(row.already_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="货物状态" width="120" align="center">
          <template #default="{ row }">
            <el-select v-if="row._type !== 'group'" v-model="row.cargo_status" size="small" style="width:105px"
              @change="(val: string) => onChangeCargoStatus(row, val)">
              <el-option v-for="s in CARGO_STATUSES" :key="s" :label="s" :value="s" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="采购单号" width="145" show-overflow-tooltip>
          <template #default="{ row }"><span v-if="row._type !== 'group' && row.order_no" style="font-family:monospace;font-size:11px;">{{ row.order_no }}</span></template>
        </el-table-column>
        <el-table-column label="采购状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row._type !== 'group' && row.order_status_label" size="small" effect="plain" :type="orderTagType(row.order_status)">{{ row.order_status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="采购数" width="70" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group'" :style="{fontWeight: row.order_qty > 0 ? 600 : 400}">{{ fmtFloat(row.order_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已收货" width="70" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group'" :style="{color: row.receipt_qty > 0 ? '#67c23a' : '#c0c4cc'}">{{ fmtFloat(row.receipt_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="单价" width="75" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group' && row.order_price" style="font-size:11px;">¥{{ fmtMoney(row.order_price) }}</span></template>
        </el-table-column>
        <el-table-column label="金额" width="85" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group' && row.order_amount" style="font-weight:600;font-size:11px;">¥{{ fmtMoney(row.order_amount) }}</span></template>
        </el-table-column>
        <el-table-column label="发货单号" width="150" show-overflow-tooltip>
          <template #default="{ row }"><span v-if="row._type !== 'group' && row.shipping_no" style="font-family:monospace;font-size:11px;">{{ row.shipping_no }}</span></template>
        </el-table-column>
        <el-table-column label="发货状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row._type !== 'group' && row.shipping_status_label" size="small" effect="plain" :type="shippingTagType(row.shipping_status)">{{ row.shipping_status_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发货数" width="70" align="right">
          <template #default="{ row }"><span v-if="row._type !== 'group'" :style="{fontWeight: row.final_shipping_qty > 0 ? 600 : 400}">{{ fmtFloat(row.final_shipping_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="物流" width="80" align="center">
          <template #default="{ row }"><span v-if="row._type !== 'group'" style="font-size:11px;">{{ row.channel_code || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="发货时间" width="95" align="center">
          <template #default="{ row }"><span v-if="row._type !== 'group'" style="font-size:11px;">{{ fmtDate(row.shipping_time) || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="到仓时间" width="95" align="center">
          <template #default="{ row }"><span v-if="row._type !== 'group'" style="font-size:11px;">{{ fmtDate(row.arrived_time) || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="期望交期" width="95" align="center">
          <template #default="{ row }"><span v-if="row._type !== 'group'" style="font-size:11px;">{{ fmtDate(row.expect_date) || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="最近更新" width="130" align="center">
          <template #default="{ row }"><span v-if="row._type !== 'group'" style="font-size:11px;">{{ fmtDatetime(row.latest_update) || '—' }}</span></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<style scoped>
:deep(.cargo-group-row > td) {
  background-color: #f0f7ff !important;
}
/* 表头 + 数据单元格统一居中 */
:deep(.el-table th.el-table__cell .cell),
:deep(.el-table td.el-table__cell .cell) {
  text-align: center !important;
}
</style>
