<script setup lang="ts">
import { computed, watch } from 'vue'
import { Document, List, Checked, Close, Clock, Coin } from '@element-plus/icons-vue'
import type { Product } from '@/types'
import { usePurOrder } from '@/composables/useProcurement'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const {
  loading, overview, list, total, page, pageSize,
  detailLoading, detail, fetchDetail, clearDetail, fetchAll,
} = usePurOrder(computed(() => props.dateRange))

watch(() => props.activeTab, (t) => { if (t === 'purchase') fetchAll() })

const STATUS_MAP: Record<string, { label: string; type: string }> = {
  '0': { label: '待提交', type: 'info' },
  '1': { label: '已提交', type: 'primary' },
  '2': { label: '待审批', type: 'warning' },
  '3': { label: '待入库', type: 'warning' },
  '4': { label: '部分入库', type: 'primary' },
  '5': { label: '异常', type: 'danger' },
  '6': { label: '已作废', type: 'danger' },
  '7': { label: '完结', type: 'success' },
}
function statusLabel(s: string | null) { return s ? STATUS_MAP[s]?.label || s : '—' }
function statusType(s: string | null) { return s ? STATUS_MAP[s]?.type || 'info' : 'info' }

const drawerVisible = computed({
  get: () => detail.value !== null,
  set: (v) => { if (!v) clearDetail() },
})

function fmtInt(v: number) { return v.toLocaleString('ru-RU') }
function fmtFloat(v: number) { return v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }
function fmtMoney(v: number) { return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
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
              <div style="font-size:12px;color:#909399;">采购单总数</div>
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
              <div style="font-size:12px;color:#909399;">待审批</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_2_pending_approval) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><List /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">待入库</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_3_pending_receipt) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><Checked /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">完结</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_7_completed) }}</div>
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
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_6_cancelled) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><Coin /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">采购总金额</div>
              <div style="font-size:16px;font-weight:700;">{{ overview.total_amount ? '¥ ' + fmtMoney(overview.total_amount) : '—' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#f56c6c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#f56c6c;"><el-icon><Close /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">部分入库/异常</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_4_partial_receipt + overview.status_5_exception) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="hover" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-weight:600;">采购单列表</span>
          <el-tag type="info" size="small">{{ total }} 条</el-tag>
        </div>
      </template>

      <el-table :data="list" stripe size="small" max-height="500" @row-click="(row: any) => fetchDetail(row.po_no)">
        <el-table-column prop="po_no" label="采购单号" min-width="160" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-family:monospace;font-size:13px;">{{ row.po_no }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vendor_id" label="供应商ID" min-width="150" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-family:monospace;font-size:12px;color:#909399;">{{ row.vendor_id || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="SKU数" width="70" align="right">
          <template #default="{ row }"><span style="font-weight:600;">{{ row.item_count }}</span></template>
        </el-table-column>
        <el-table-column label="总数量" width="80" align="right">
          <template #default="{ row }"><span style="font-weight:600;">{{ fmtFloat(row.total_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="金额" width="110" align="right" sortable>
          <template #default="{ row }">
            <span style="font-weight:600;">{{ row.amount > 0 ? '¥ ' + fmtMoney(row.amount) : '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="币别" width="55" align="center">
          <template #default="{ row }"><span style="font-size:12px;">{{ row.currency_code || '—' }}</span></template>
        </el-table-column>
        <el-table-column label="创建时间" width="140" sortable>
          <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.create_time) }}</span></template>
        </el-table-column>
        <el-table-column label="物流" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size:11px;color:#909399;">{{ row.logistics_name || '' }} {{ row.logistics_num || '' }}</span>
          </template>
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
    <el-drawer v-model="drawerVisible" title="采购单详情" direction="rtl" size="700px" @closed="clearDetail">
      <template v-if="detail" v-loading="detailLoading">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px;">
          <el-descriptions-item label="采购单号" :span="2">
            <span style="font-family:monospace;font-size:13px;">{{ detail.po_no }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusType(detail.status)" effect="plain">{{ detail.status_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="币别">{{ detail.currency_code || '—' }}</el-descriptions-item>
          <el-descriptions-item label="供应商ID">{{ detail.vendor_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="仓库ID">{{ detail.location_id || '—' }}</el-descriptions-item>
          <el-descriptions-item label="总金额（含税）"><span style="font-weight:700;color:#e6a23c;">¥ {{ fmtMoney(detail.amount) }}</span></el-descriptions-item>
          <el-descriptions-item label="未税金额">¥ {{ fmtMoney(detail.untaxed_amount) }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(detail.create_time) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(detail.update_time) }}</el-descriptions-item>
          <el-descriptions-item label="期望交期">{{ formatDate(detail.receipt_date) }}</el-descriptions-item>
          <el-descriptions-item label="物流">{{ detail.logistics_name || '—' }} {{ detail.logistics_num || '' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.memo || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-card shadow="never">
          <template #header><span style="font-weight:600;">📦 采购明细（{{ detail.items.length }} 行）</span></template>
          <el-table :data="detail.items" size="small" stripe max-height="400">
            <el-table-column prop="row_id" label="行号" width="55" align="center" />
            <el-table-column prop="item_id" label="SKU编码" min-width="170" show-overflow-tooltip>
              <template #default="{ row }"><span style="font-family:monospace;font-size:12px;">{{ row.item_id || '—' }}</span></template>
            </el-table-column>
            <el-table-column label="数量" width="70" align="right">
              <template #default="{ row }"><span style="font-weight:600;">{{ fmtFloat(row.qty) }}</span></template>
            </el-table-column>
            <el-table-column label="未税单价" width="90" align="right">
              <template #default="{ row }"><span>¥ {{ fmtMoney(row.price) }}</span></template>
            </el-table-column>
            <el-table-column label="未税金额" width="100" align="right">
              <template #default="{ row }"><span style="font-weight:600;">¥ {{ fmtMoney(row.untaxed_amount) }}</span></template>
            </el-table-column>
            <el-table-column label="已收货" width="70" align="right">
              <template #default="{ row }"><span style="color:#67c23a;">{{ fmtFloat(row.receipt_qty) }}</span></template>
            </el-table-column>
            <el-table-column label="期望交期" width="100">
              <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.expect_receipt_date) }}</span></template>
            </el-table-column>
            <el-table-column label="关联申购单" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                <span style="font-family:monospace;font-size:11px;color:#409eff;">{{ row.po_plan_no || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="箱规" width="60" align="right">
              <template #default="{ row }"><span>{{ fmtFloat(row.package_qty) }}</span></template>
            </el-table-column>
            <el-table-column prop="sale_platform" label="平台" width="65" align="center" />
          </el-table>
        </el-card>
      </template>
    </el-drawer>
  </div>
</template>
