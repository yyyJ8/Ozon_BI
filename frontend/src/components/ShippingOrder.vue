<script setup lang="ts">
import { computed, watch } from 'vue'
import { Document, Van, Checked, Close, Clock, Box } from '@element-plus/icons-vue'
import type { Product } from '@/types'
import { useShipping } from '@/composables/useProcurement'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const {
  loading, overview, list, total, page, pageSize,
  detailLoading, detail, fetchDetail, clearDetail, fetchAll,
} = useShipping(computed(() => props.dateRange))

watch(() => props.activeTab, (t) => { if (t === 'shipping') fetchAll() })

const STATUS_MAP: Record<string, { label: string; type: string }> = {
  '1': { label: '待推送', type: 'info' },
  '2': { label: '待拣货', type: 'warning' },
  '3': { label: '拣货完成', type: 'primary' },
  '4': { label: '装箱完成', type: 'primary' },
  '5': { label: '待质检', type: 'warning' },
  '6': { label: '待上传箱唛', type: 'warning' },
  '7': { label: '待物流发货', type: 'warning' },
  '8': { label: '待复核', type: 'warning' },
  '9': { label: '已作废', type: 'danger' },
  '10': { label: '复核完成', type: 'primary' },
  '11': { label: '已发货', type: 'success' },
  '12': { label: '已到仓', type: 'success' },
  '13': { label: '部分到仓', type: 'success' },
}
function statusLabel(s: string | null) { return s ? STATUS_MAP[s]?.label || s : '—' }
function statusType(s: string | null) { return s ? STATUS_MAP[s]?.type || 'info' : 'info' }

const drawerVisible = computed({
  get: () => detail.value !== null,
  set: (v) => { if (!v) clearDetail() },
})

function fmtInt(v: number) { return v.toLocaleString('ru-RU') }
function fmtFloat(v: number) { return v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }
function formatDate(v: string | null) {
  if (!v) return '—'
  return v.length > 10 ? v.slice(0, 16) : v
}
function onPageChange(p: number) { page.value = p }
function onPageSizeChange(s: number) { pageSize.value = s; page.value = 1 }
</script>

<template>
  <div v-loading="loading" style="min-height: 300px;">

    <el-row :gutter="16" v-if="overview">
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Document /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">发货单总数</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.total) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><Clock /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">待拣货</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_2_pending_pick) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Box /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">拣货/装箱完成</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_3_4_picked_packed) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><Van /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">待发货</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_7_8_10_pending_ship) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><Checked /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">已发货</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_11_shipped) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><Van /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">已到仓</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_12_13_arrived) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f56c6c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#f56c6c;"><el-icon><Close /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">已作废</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_9_cancelled) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="2">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#90939918;display:flex;align-items:center;justify-content:center;font-size:18px;color:#909399;"><el-icon><Box /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">总件数</div>
              <div style="font-size:16px;font-weight:700;">{{ fmtFloat(overview.total_item_qty) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-weight:600;">发货单列表</span>
          <el-tag type="info" size="small">{{ total }} 条</el-tag>
        </div>
      </template>

      <el-table :data="list" stripe size="small" max-height="500" @row-click="(row: any) => fetchDetail(row.order_code)">
        <el-table-column prop="order_code" label="发货单号" min-width="160" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-family:monospace;font-size:13px;">{{ row.order_code }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.order_status)" effect="plain">{{ statusLabel(row.order_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="channel_code" label="物流方式" width="100" />
        <el-table-column label="发货仓" min-width="140" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-size:11px;color:#909399;">{{ row.shipping_warehouse_id || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="目的仓" min-width="140" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-size:11px;color:#909399;">{{ row.destination_warehouse_id || '—' }}</span></template>
        </el-table-column>
        <el-table-column prop="destination_country_code" label="目的国" width="65" align="center" />
        <el-table-column label="SKU数" width="70" align="right">
          <template #default="{ row }"><span style="font-weight:600;">{{ row.item_count }}</span></template>
        </el-table-column>
        <el-table-column label="发货计划" min-width="150" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-family:monospace;font-size:11px;color:#909399;">{{ row.plan_code || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="创建时间" width="140" sortable>
          <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.create_time) }}</span></template>
        </el-table-column>
        <el-table-column label="发货时间" width="140">
          <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.shipping_time) }}</span></template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" style="margin-top:12px;display:flex;justify-content:flex-end;">
        <el-pagination
          v-model:current-page="page" v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]" :total="total"
          layout="total, sizes, prev, pager, next, jumper" small
          @current-change="onPageChange" @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="发货单详情" direction="rtl" size="700px" @closed="clearDetail">
      <template v-if="detail" v-loading="detailLoading">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px;">
          <el-descriptions-item label="发货单号" :span="2">
            <span style="font-family:monospace;font-size:13px;">{{ detail.order_code }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusType(detail.order_status)" effect="plain">{{ detail.status_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="物流方式">{{ detail.channel_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="发货仓">{{ detail.shipping_warehouse_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="目的仓">{{ detail.destination_warehouse_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="目的国">{{ detail.destination_country_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="收货平台">{{ detail.receiving_platform || '—' }}</el-descriptions-item>
          <el-descriptions-item label="发货计划">{{ detail.plan_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="计划发货时间">{{ formatDate(detail.shipping_plan_time) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(detail.create_time) }}</el-descriptions-item>
          <el-descriptions-item label="发货时间">{{ formatDate(detail.shipping_time) }}</el-descriptions-item>
          <el-descriptions-item label="到仓时间">{{ formatDate(detail.arrived_time) }}</el-descriptions-item>
          <el-descriptions-item label="物流单号">{{ detail.logistics_order || '—' }}</el-descriptions-item>
          <el-descriptions-item label="是否直发">{{ detail.is_direct_ship === '1' ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="是否AGL">{{ detail.is_agl === '1' ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="装箱类型">{{ detail.package_type === '1' ? '混装' : detail.package_type === '0' ? '一箱一种SKU' : detail.package_type || '—' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.remark || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-card shadow="never">
          <template #header><span style="font-weight:600;">📦 发货明细（{{ detail.items.length }} 行）</span></template>
          <el-table :data="detail.items" size="small" stripe max-height="400">
            <el-table-column prop="row_id" label="行号" width="55" align="center" />
            <el-table-column prop="item_id" label="系统SKU" min-width="170" show-overflow-tooltip>
              <template #default="{ row }"><span style="font-family:monospace;font-size:12px;">{{ row.item_id || '—' }}</span></template>
            </el-table-column>
            <el-table-column label="计划发货" width="80" align="right">
              <template #default="{ row }"><span>{{ fmtFloat(row.planed_shipping_num) }}</span></template>
            </el-table-column>
            <el-table-column label="运营发货" width="80" align="right">
              <template #default="{ row }"><span>{{ fmtFloat(row.operation_shipping_num) }}</span></template>
            </el-table-column>
            <el-table-column label="最终发货" width="80" align="right">
              <template #default="{ row }"><span style="font-weight:700;color:#67c23a;">{{ fmtFloat(row.final_shipping_num) }}</span></template>
            </el-table-column>
            <el-table-column label="箱规" width="65" align="right">
              <template #default="{ row }"><span>{{ fmtFloat(row.package_qty) }}</span></template>
            </el-table-column>
            <el-table-column label="来源申购单" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-family:monospace;font-size:11px;color:#409eff;">{{ row.source_order_code || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="采购单号" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-family:monospace;font-size:11px;color:#e6a23c;">{{ row.po_no || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="材质" width="60">
              <template #default="{ row }"><span style="font-size:11px;">{{ row.material || '—' }}</span></template>
            </el-table-column>
            <el-table-column label="质检" width="60" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.qc_status === '1' ? 'success' : 'warning'" effect="plain">
                  {{ row.qc_status === '1' ? '已质检' : '待质检' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>
    </el-drawer>
  </div>
</template>
