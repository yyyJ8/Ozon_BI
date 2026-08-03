<script setup lang="ts">
import { computed, watch } from 'vue'
import { Document, List, Checked, Close, Clock, Box } from '@element-plus/icons-vue'
import type { Product } from '@/types'
import { usePlan } from '@/composables/useProcurement'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const {
  loading, overview, list, total, page, pageSize,
  detailLoading, detail, fetchDetail, clearDetail, fetchAll,
} = usePlan(computed(() => props.dateRange))

// 强制刷新（tab 切换时）
watch(() => props.activeTab, (t) => { if (t === 'plan') fetchAll() })

// ── 状态映射 ──
const STATUS_MAP: Record<string, { label: string; type: string }> = {
  '0': { label: '待提交', type: 'info' },
  '1': { label: '待审批', type: 'warning' },
  '2': { label: '待创建采购单', type: 'warning' },
  '3': { label: '部分创建', type: 'primary' },
  '4': { label: '已创建采购订单', type: 'success' },
  '5': { label: '已作废', type: 'danger' },
  '6': { label: '审批中', type: 'warning' },
}
function statusLabel(s: string | null) { return s ? STATUS_MAP[s]?.label || s : '—' }
function statusType(s: string | null) { return s ? STATUS_MAP[s]?.type || 'info' : 'info' }

const PLAN_TYPE_MAP: Record<string, string> = {
  '0': '平台仓备货', '1': '海外仓备货', '2': '计划备货', '3': '组合备货',
}

// ── 抽屉 ──
const drawerVisible = computed({
  get: () => detail.value !== null,
  set: (v) => { if (!v) clearDetail() },
})

// ── 工具函数 ──
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

    <!-- 概览卡片 -->
    <el-row :gutter="16" v-if="overview">
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><Document /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">申购单总数</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.total) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#e6a23c18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#e6a23c;"><el-icon><Clock /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">待审批/审批中</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_1_pending_approval + overview.status_6_approving) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#409eff18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#409eff;"><el-icon><List /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">待创建采购单</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_2_pending_create_po) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><Checked /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">已创建采购订单</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_4_created) }}</div>
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
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_5_cancelled) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#90939918;display:flex;align-items:center;justify-content:center;font-size:18px;color:#909399;"><el-icon><Box /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">计划总数量</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtFloat(overview.total_plan_qty) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="4">
        <el-card shadow="hover" :body-style="{ padding: '14px 18px' }">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:40px;height:40px;border-radius:8px;background:#67c23a18;display:flex;align-items:center;justify-content:center;font-size:18px;color:#67c23a;"><el-icon><Checked /></el-icon></div>
            <div>
              <div style="font-size:12px;color:#909399;">部分创建</div>
              <div style="font-size:20px;font-weight:700;">{{ fmtInt(overview.status_3_partial_create) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 申购单列表 -->
    <el-card shadow="hover" style="margin-top:16px;">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between;">
          <span style="font-weight:600;">申购单列表</span>
          <el-tag type="info" size="small">{{ total }} 条</el-tag>
        </div>
      </template>

      <el-table :data="list" stripe size="small" max-height="500" @row-click="(row: any) => fetchDetail(row.po_plan_no)">
        <el-table-column prop="po_plan_no" label="申购单号" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:13px;">{{ row.po_plan_no }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)" effect="plain">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="申购类型" width="100">
          <template #default="{ row }">
            <span style="font-size:12px;">{{ row.plan_type_label || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="logistics_method" label="物流方式" width="90" />
        <el-table-column label="SKU数" width="70" align="right">
          <template #default="{ row }"><span style="font-weight:600;">{{ row.item_count }}</span></template>
        </el-table-column>
        <el-table-column label="计划总数量" width="100" align="right">
          <template #default="{ row }"><span style="font-weight:600;">{{ fmtFloat(row.total_plan_qty) }}</span></template>
        </el-table-column>
        <el-table-column label="创建时间" width="140" sortable>
          <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.create_time) }}</span></template>
        </el-table-column>
        <el-table-column prop="memo" label="备注" min-width="150" show-overflow-tooltip>
          <template #default="{ row }"><span style="font-size:12px;color:#909399;">{{ row.memo || '—' }}</span></template>
        </el-table-column>
      </el-table>

      <div v-if="total > 0" style="margin-top:12px;display:flex;justify-content:flex-end;">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          small
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </el-card>

    <!-- 详情抽屉 -->
    <el-drawer v-model="drawerVisible" title="申购单详情" direction="rtl" size="700px" @closed="clearDetail">
      <template v-if="detail" v-loading="detailLoading">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px;">
          <el-descriptions-item label="申购单号" :span="2">
            <span style="font-family:monospace;font-size:13px;">{{ detail.po_plan_no }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag size="small" :type="statusType(detail.status)" effect="plain">{{ detail.status_label }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="申购类型">{{ detail.plan_type_label || '—' }}</el-descriptions-item>
          <el-descriptions-item label="物流方式">{{ detail.logistics_method || '—' }}</el-descriptions-item>
          <el-descriptions-item label="单据来源">{{ detail.plan_source === '1' ? '采购申购单' : detail.plan_source === '2' ? '计划备货单' : detail.plan_source || '—' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(detail.create_time) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(detail.update_time) }}</el-descriptions-item>
          <el-descriptions-item label="是否紧急">{{ detail.is_urgent === '1' ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="是否新品">{{ detail.is_new_product === 'Y' ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="是否年底备货">{{ detail.is_year_stock === '1' ? '是' : '否' }}</el-descriptions-item>
          <el-descriptions-item label="退回原因" :span="2">{{ detail.return_reason || '—' }}</el-descriptions-item>
          <el-descriptions-item label="备注" :span="2">{{ detail.memo || '—' }}</el-descriptions-item>
        </el-descriptions>

        <!-- 明细行 -->
        <el-card shadow="never">
          <template #header><span style="font-weight:600;">📦 申购明细（{{ detail.items.length }} 行）</span></template>
          <el-table :data="detail.items" size="small" stripe max-height="400">
            <el-table-column prop="row_id" label="行号" width="55" align="center" />
            <el-table-column prop="item_id" label="SKU编码" min-width="170" show-overflow-tooltip>
              <template #default="{ row }"><span style="font-family:monospace;font-size:12px;">{{ row.item_id || '—' }}</span></template>
            </el-table-column>
            <el-table-column label="计划数量" width="90" align="right">
              <template #default="{ row }"><span style="font-weight:600;">{{ fmtFloat(row.plan_qty) }}</span></template>
            </el-table-column>
            <el-table-column label="已下单" width="80" align="right">
              <template #default="{ row }"><span style="color:#409eff;">{{ fmtFloat(row.already_qty) }}</span></template>
            </el-table-column>
            <el-table-column label="WMS收货" width="80" align="right">
              <template #default="{ row }"><span style="color:#67c23a;">{{ fmtFloat(row.wms_rec_qty) }}</span></template>
            </el-table-column>
            <el-table-column label="期望交期" width="100">
              <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.expect_date) }}</span></template>
            </el-table-column>
            <el-table-column prop="marketplace" label="站点" width="55" align="center" />
            <el-table-column label="店铺" min-width="120" show-overflow-tooltip>
              <template #default="{ row }"><span style="font-size:11px;color:#909399;">{{ row.store_id || '—' }}</span></template>
            </el-table-column>
            <el-table-column label="箱规" width="60" align="right">
              <template #default="{ row }"><span>{{ fmtFloat(row.package_qty) }}</span></template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>
    </el-drawer>
  </div>
</template>
