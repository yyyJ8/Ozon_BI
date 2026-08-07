<script setup lang="ts">
import { ref, watch } from 'vue'
import type { SkuTableRow, SkuPipelineDetail } from '@/types'
import { getSkuPipelineList, getSkuPipelineDetail } from '@/api'
import { useLocalDateRange } from '@/composables/useLocalDateRange'

const props = defineProps<{
  dateRange: [string, string] | null
  activeTab: string
}>()

const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

const loading = ref(false)
const list = ref<SkuTableRow[]>([])
const search = ref('')
const pageSize = 9999

async function fetchList() {
  if (!localDateRange.value) return
  loading.value = true
  try {
    const [d1, d2] = localDateRange.value
    const res = await getSkuPipelineList(d1, d2, search.value || undefined, 1, pageSize)
    list.value = res.items
  } catch { /* ignore */ }
  finally { loading.value = false }
}

watch([localDateRange, search], () => { fetchList() }, { immediate: true })
watch(() => props.activeTab, (t) => { if (t === 'supply-chain') fetchList() })

// ── 展开行明细 ──
interface DetailRow {
  type: 'plan' | 'order' | 'shipping'
  // 申购
  plan_no: string; plan_time: string; plan_status: string; plan_qty: number; already_qty: number; expect_date: string
  // 采购
  order_no: string; order_time: string; order_status: string; order_qty: number; receipt_qty: number; price: number; amount: number
  // 发货
  shipping_no: string; shipping_time: string; shipping_status: string; shipped_qty: number; channel: string; arrived_time: string
  // 货件汇总 (cargo_shipments)
  cs_product_name: string; cs_store: string; cs_requisitioner: string
  cs_replenishment_qty: number; cs_carton_qty: number; cs_carton_volume: number; cs_carton_gross_weight: number
  cs_weight: number; cs_cbm: number; cs_density: number; cs_box_count: number
  cs_transit_warehouse: string; cs_logistics_inbound_no: string; cs_cargo_status: string
  cs_fbo_warehouse_name: string; cs_booking_code: string; cs_fbo_listing_time: string
  cs_warehouse_rent_start: string; cs_actual_listing_qty: number
  cs_info_remarks: string; cs_batch_quotation: string; cs_product_status: string
  cs_stocking_opinion: string; cs_parent_record: string
}

const expandedSet = ref<Set<string>>(new Set())
const detailRows = ref<Record<string, DetailRow[]>>({})
const loadingDetail = ref<Record<string, boolean>>({})

function flattenDetail(d: SkuPipelineDetail): DetailRow[] {
  const rows: DetailRow[] = []
  // 以申购单为基准，关联采购和发货
  for (const p of d.plans) {
    const linkedOrders = d.orders.filter(o => o.po_plan_no === p.po_plan_no)
    const linkedShippings = d.shippings.filter(s => s.source_order_code === p.po_plan_no)
    const max = Math.max(linkedOrders.length, linkedShippings.length, 1)
    for (let i = 0; i < max; i++) {
      const o = linkedOrders[i] || null
      const s = linkedShippings[i] || null
      rows.push({
        type: 'plan',
        plan_no: i === 0 ? p.po_plan_no : '', plan_time: i === 0 ? (p.create_time || '') : '', plan_status: i === 0 ? p.status_label : '',
        plan_qty: i === 0 ? p.plan_qty : 0, already_qty: i === 0 ? p.already_qty : 0, expect_date: i === 0 ? (p.expect_date || '') : '',
        order_no: o ? o.po_no : '', order_time: o ? (o.create_time || '') : '', order_status: o ? o.status_label : '',
        order_qty: o ? o.qty : 0, receipt_qty: o ? o.receipt_qty : 0, price: o ? o.price : 0, amount: o ? o.untaxed_amount : 0,
        shipping_no: s ? s.order_code : '', shipping_time: s ? (s.shipping_time || '') : '', shipping_status: s ? s.status_label : '',
        shipped_qty: s ? s.final_shipping_num : 0, channel: s ? (s.channel_code || '') : '', arrived_time: s ? (s.arrived_time || '') : '',
        cs_product_name: i === 0 ? (p.cs_product_name || '') : '', cs_store: i === 0 ? (p.cs_store || '') : '', cs_requisitioner: i === 0 ? (p.cs_requisitioner || '') : '',
        cs_replenishment_qty: i === 0 ? p.cs_replenishment_qty : 0, cs_carton_qty: i === 0 ? p.cs_carton_qty : 0, cs_carton_volume: i === 0 ? p.cs_carton_volume : 0, cs_carton_gross_weight: i === 0 ? p.cs_carton_gross_weight : 0,
        cs_weight: i === 0 ? p.cs_weight : 0, cs_cbm: i === 0 ? p.cs_cbm : 0, cs_density: i === 0 ? p.cs_density : 0, cs_box_count: i === 0 ? p.cs_box_count : 0,
        cs_transit_warehouse: i === 0 ? (p.cs_transit_warehouse || '') : '', cs_logistics_inbound_no: i === 0 ? (p.cs_logistics_inbound_no || '') : '', cs_cargo_status: i === 0 ? (p.cs_cargo_status || '') : '',
        cs_fbo_warehouse_name: i === 0 ? (p.cs_fbo_warehouse_name || '') : '', cs_booking_code: i === 0 ? (p.cs_booking_code || '') : '', cs_fbo_listing_time: i === 0 ? (p.cs_fbo_listing_time || '') : '',
        cs_warehouse_rent_start: i === 0 ? (p.cs_warehouse_rent_start || '') : '', cs_actual_listing_qty: i === 0 ? p.cs_actual_listing_qty : 0,
        cs_info_remarks: i === 0 ? (p.cs_info_remarks || '') : '', cs_batch_quotation: i === 0 ? (p.cs_batch_quotation || '') : '', cs_product_status: i === 0 ? (p.cs_product_status || '') : '',
        cs_stocking_opinion: i === 0 ? (p.cs_stocking_opinion || '') : '', cs_parent_record: i === 0 ? (p.cs_parent_record || '') : '',
      })
    }
  }
  return rows
}

async function onExpandChange(row: SkuTableRow, expanded: boolean) {
  if (!expanded) { expandedSet.value.delete(row.item_id); return }
  expandedSet.value.add(row.item_id)
  if (detailRows.value[row.item_id]) return
  loadingDetail.value[row.item_id] = true
  try {
    const d = await getSkuPipelineDetail(row.item_id)
    detailRows.value[row.item_id] = flattenDetail(d)
  } catch { /* ignore */ }
  finally { loadingDetail.value[row.item_id] = false }
}

// ── 工具 ──
function fmtInt(v: number) { return v ? v.toLocaleString('ru-RU') : '0' }
function fmtFloat(v: number) { return v ? v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : '0' }
function fmtMoney(v: number) { return v ? v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00' }
function fmtDate(v: string | null) { if (!v) return ''; return v.length > 10 ? v.slice(0, 10) : v }
function fmtDatetime(v: string | null) { if (!v) return ''; return v.length > 16 ? v.slice(0, 16) : v }
function cargoTagType(s: string | null) {
  if (!s) return 'info'; if (s === '已上架') return 'success'; if (s === '跨境在途') return 'warning'; return 'info'
}
function planTagType(s: string | null) { if (!s) return 'info'; if (s === '已创建采购订单') return 'success'; if (s === '已作废') return 'danger'; return 'warning' }
function orderTagType(s: string | null) { if (!s) return 'info'; if (s === '完结') return 'success'; if (s === '已作废') return 'danger'; return 'warning' }
function shippingTagType(s: string | null) { if (!s) return 'info'; if (s.startsWith('已')) return 'success'; if (s === '已作废') return 'danger'; return 'warning' }
</script>

<template>
  <div v-loading="loading" style="min-height:300px;">

    <!-- 工具栏 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap;">
      <el-select v-model="periodPreset" style="width:100px" size="small" @change="applyPreset">
        <el-option label="近30天" value="30days" /><el-option label="近7天" value="7days" />
        <el-option label="全部" value="all" /><el-option label="自定义" value="custom" />
      </el-select>
      <el-date-picker v-if="showCustomDate" v-model="localDateRange" type="daterange" size="small" range-separator="至"
        start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width:220px" :disabled-date="disabledDate" />
      <el-input v-model="search" placeholder="搜索货号" clearable size="small" style="width:180px;margin-left:auto;"
        @clear="fetchList()" @keyup.enter="fetchList()" />
      <el-tag type="info" size="small">{{ list.length }} 个货号</el-tag>
    </div>

    <!-- 主表 -->
    <el-card shadow="hover">
      <el-table :data="list" stripe size="small" max-height="calc(100vh - 260px)"
        @expand-change="onExpandChange" :row-key="(r: SkuTableRow) => r.item_id">
        <el-table-column type="expand" width="30">
          <template #default="{ row }">
            <div v-loading="loadingDetail[row.item_id]" style="padding:4px 8px 8px;">
              <el-table v-if="detailRows[row.item_id]?.length"
                :data="detailRows[row.item_id]" size="small" border style="width:100%">
                <el-table-column label="申购单号" width="145">
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-family:monospace;font-size:12px;">{{ d.plan_no }}</span></template>
                </el-table-column>
                <el-table-column label="申购时间" width="135">
                  <template #default="{ row: d }"><span style="font-size:11px;">{{ fmtDatetime(d.plan_time) || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="申购状态" width="110">
                  <template #default="{ row: d }">
                    <el-tag v-if="d.plan_status" size="small" effect="plain" :type="planTagType(d.plan_status)">{{ d.plan_status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="计划数" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_qty" style="font-weight:600;">{{ fmtFloat(d.plan_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="已下单" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no" :style="{color: d.already_qty > 0 ? '#409eff' : '#c0c4cc'}">{{ fmtFloat(d.already_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="采购单号" width="145">
                  <template #default="{ row: d }"><span v-if="d.order_no" style="font-family:monospace;font-size:12px;">{{ d.order_no }}</span></template>
                </el-table-column>
                <el-table-column label="采购时间" width="135">
                  <template #default="{ row: d }"><span style="font-size:11px;">{{ fmtDatetime(d.order_time) || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="采购状态" width="90">
                  <template #default="{ row: d }">
                    <el-tag v-if="d.order_status" size="small" effect="plain" :type="orderTagType(d.order_status)">{{ d.order_status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="采购数" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.order_qty" style="font-weight:600;">{{ fmtFloat(d.order_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="已收货" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.order_no" :style="{color: d.receipt_qty > 0 ? '#67c23a' : '#c0c4cc'}">{{ fmtFloat(d.receipt_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="单价" width="75" align="right">
                  <template #default="{ row: d }"><span v-if="d.price">¥{{ fmtMoney(d.price) }}</span></template>
                </el-table-column>
                <el-table-column label="金额" width="85" align="right">
                  <template #default="{ row: d }"><span v-if="d.amount" style="font-weight:600;">¥{{ fmtMoney(d.amount) }}</span></template>
                </el-table-column>
                <el-table-column label="发货单号" width="145">
                  <template #default="{ row: d }"><span v-if="d.shipping_no" style="font-family:monospace;font-size:12px;">{{ d.shipping_no }}</span></template>
                </el-table-column>
                <el-table-column label="发货时间" width="135">
                  <template #default="{ row: d }"><span style="font-size:11px;">{{ fmtDatetime(d.shipping_time) || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="发货状态" width="100">
                  <template #default="{ row: d }">
                    <el-tag v-if="d.shipping_status" size="small" effect="plain" :type="shippingTagType(d.shipping_status)">{{ d.shipping_status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="发货数" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.shipped_qty" style="font-weight:600;">{{ fmtFloat(d.shipped_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="物流" width="70" align="center">
                  <template #default="{ row: d }"><span style="font-size:11px;">{{ d.channel || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="到仓时间" width="95">
                  <template #default="{ row: d }"><span style="font-size:11px;">{{ fmtDate(d.arrived_time) || '—' }}</span></template>
                </el-table-column>
                <!-- 货件汇总 -->
                <el-table-column label="产品名称" width="100" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_product_name" style="font-size:11px;">{{ d.cs_product_name }}</span></template>
                </el-table-column>
                <el-table-column label="店铺" width="50" align="center">
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_store || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="申购人" width="65" align="center">
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_requisitioner || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="补货数" width="60" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_replenishment_qty">{{ fmtFloat(d.cs_replenishment_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="装箱数" width="60" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_carton_qty">{{ fmtFloat(d.cs_carton_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="外箱体积" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_carton_volume">{{ d.cs_carton_volume }}</span></template>
                </el-table-column>
                <el-table-column label="外箱毛重" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_carton_gross_weight">{{ d.cs_carton_gross_weight }}</span></template>
                </el-table-column>
                <el-table-column label="重量" width="60" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_weight">{{ d.cs_weight }}</span></template>
                </el-table-column>
                <el-table-column label="方数" width="55" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_cbm">{{ d.cs_cbm }}</span></template>
                </el-table-column>
                <el-table-column label="密度" width="55" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_density">{{ d.cs_density }}</span></template>
                </el-table-column>
                <el-table-column label="箱数" width="50" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_box_count">{{ fmtFloat(d.cs_box_count) }}</span></template>
                </el-table-column>
                <el-table-column label="中转仓" width="80" align="center">
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_transit_warehouse || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="入库单号" width="125" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_logistics_inbound_no" style="font-family:monospace;font-size:11px;">{{ d.cs_logistics_inbound_no }}</span></template>
                </el-table-column>
                <el-table-column label="货物状态" width="80" align="center">
                  <template #default="{ row: d }">
                    <el-tag v-if="d.plan_no && d.cs_cargo_status" size="small" effect="plain"
                      :type="d.cs_cargo_status === '已上架' ? 'success' : d.cs_cargo_status === '跨境在途' ? 'warning' : 'info'">{{ d.cs_cargo_status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="FBO仓" width="80" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_fbo_warehouse_name || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="约仓编码" width="90" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_booking_code || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="FBO上架" width="90" align="center">
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ fmtDate(d.cs_fbo_listing_time) || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="仓租开始" width="90" align="center">
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ fmtDate(d.cs_warehouse_rent_start) || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="实际上架" width="65" align="right">
                  <template #default="{ row: d }"><span v-if="d.plan_no && d.cs_actual_listing_qty">{{ fmtFloat(d.cs_actual_listing_qty) }}</span></template>
                </el-table-column>
                <el-table-column label="信息备注" width="120" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_info_remarks || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="批次报价" width="80" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_batch_quotation || '—' }}</span></template>
                </el-table-column>
                <el-table-column label="产品状态" width="70" align="center">
                  <template #default="{ row: d }">
                    <el-tag v-if="d.plan_no && d.cs_product_status" size="small" effect="plain">{{ d.cs_product_status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="备货意见" width="100" show-overflow-tooltip>
                  <template #default="{ row: d }"><span v-if="d.plan_no" style="font-size:11px;">{{ d.cs_stocking_opinion || '—' }}</span></template>
                </el-table-column>
              </el-table>
              <div v-else-if="!loadingDetail[row.item_id]" style="text-align:center;color:#c0c4cc;padding:12px;">暂无明细</div>
            </div>
          </template>
        </el-table-column>

        <!-- 主表列 -->
        <el-table-column label="SKU" width="90" align="center">
          <template #default="{ row }">
            <span v-if="row.sku_id" style="font-family:monospace;font-size:12px;">{{ row.sku_id }}</span>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="货号" min-width="160" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-family:monospace;font-size:12px;">{{ row.item_id }}</span></template>
        </el-table-column>
        <el-table-column label="申购" width="80" align="center">
          <template #default="{ row }">
            <span :style="{fontWeight:600}">{{ row.plan_count }}</span>
            <span style="font-size:10px;color:#909399;"> 单</span>
          </template>
        </el-table-column>
        <el-table-column label="计划数" width="70" align="right">
          <template #default="{ row }"><span :style="{fontWeight: row.plan_qty > 0 ? 600 : 400}">{{ fmtFloat(row.plan_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已下单" width="70" align="right">
          <template #default="{ row }"><span :style="{color: row.already_qty > 0 ? '#409eff' : '#c0c4cc'}">{{ fmtFloat(row.already_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="采购" width="80" align="center">
          <template #default="{ row }">
            <span :style="{fontWeight:600}">{{ row.order_count }}</span>
            <span style="font-size:10px;color:#909399;"> 单</span>
          </template>
        </el-table-column>
        <el-table-column label="采购数" width="70" align="right">
          <template #default="{ row }"><span :style="{fontWeight: row.order_qty > 0 ? 600 : 400}">{{ fmtFloat(row.order_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已收货" width="70" align="right">
          <template #default="{ row }"><span :style="{color: row.receipt_qty > 0 ? '#67c23a' : '#c0c4cc'}">{{ fmtFloat(row.receipt_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="发货" width="80" align="center">
          <template #default="{ row }">
            <span :style="{fontWeight:600}">{{ row.shipping_count }}</span>
            <span style="font-size:10px;color:#909399;"> 单</span>
          </template>
        </el-table-column>
        <el-table-column label="发货数" width="70" align="right">
          <template #default="{ row }"><span :style="{fontWeight: row.final_shipping_qty > 0 ? 600 : 400}">{{ fmtFloat(row.final_shipping_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="已到仓" width="70" align="right">
          <template #default="{ row }"><span :style="{color: row.inbound_qty > 0 ? '#67c23a' : '#c0c4cc'}">{{ fmtFloat(row.inbound_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="货物状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.cargo_status" size="small" effect="plain" :type="cargoTagType(row.cargo_status)">{{ row.cargo_status }}</el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="直发收货" width="85" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.direct_receiving_status" size="small" effect="plain"
              :type="row.direct_receiving_status === '已收到' ? 'success' : 'warning'">{{ row.direct_receiving_status }}</el-tag>
            <span v-else style="color:#c0c4cc;">—</span>
          </template>
        </el-table-column>
        <el-table-column label="最近更新" width="130" align="center">
          <template #default="{ row }"><span style="font-size:11px;">{{ fmtDatetime(row.latest_update) || '—' }}</span></template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
