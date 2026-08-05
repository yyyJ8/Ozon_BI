<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { Document, Box, Van, Checked, Clock, WarningFilled } from '@element-plus/icons-vue'
import type { Product, SkuPipelineItem, SkuPipelineDetail } from '@/types'
import { getSkuPipelineList, getSkuPipelineDetail } from '@/api'
import { useLocalDateRange } from '@/composables/useLocalDateRange'

const props = defineProps<{
  dateRange: [string, string] | null
  products: Product[]
  activeTab: string
}>()

const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

// ── 数据状态 ──
const loading = ref(false)
const list = ref<SkuPipelineItem[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

async function fetchList() {
  if (!localDateRange.value) return
  loading.value = true
  try {
    const [d1, d2] = localDateRange.value
    const res = await getSkuPipelineList(d1, d2, page.value, pageSize.value)
    list.value = res.items
    total.value = res.total
  } catch { /* error handled by composable */ }
  finally { loading.value = false }
}

watch([localDateRange, page, pageSize], () => { fetchList() }, { immediate: true })
watch(() => props.activeTab, (t) => { if (t === 'supply-chain') fetchList() })

// ── 概览 ──
const overview = computed(() => {
  const items = list.value
  return {
    total: items.length,
    hasPlan: items.filter(i => i.plan_count > 0).length,
    hasOrder: items.filter(i => i.order_count > 0).length,
    hasShipping: items.filter(i => i.shipping_count > 0).length,
    hasInbound: items.filter(i => i.total_inbound_qty > 0).length,
    totalPlanQty: items.reduce((s, i) => s + i.total_plan_qty, 0),
    totalOrderQty: items.reduce((s, i) => s + i.total_order_qty, 0),
    totalShippedQty: items.reduce((s, i) => s + i.total_shipped_qty, 0),
  }
})

// ── 展开行详情 ──
const expandedRows = ref<Set<string>>(new Set())
const detailMap = ref<Record<string, SkuPipelineDetail>>({})
const loadingDetail = ref<Record<string, boolean>>({})

async function onExpandChange(row: SkuPipelineItem, expanded: boolean) {
  if (!expanded) {
    expandedRows.value.delete(row.item_id)
    return
  }
  expandedRows.value.add(row.item_id)
  if (detailMap.value[row.item_id]) return
  loadingDetail.value[row.item_id] = true
  try {
    detailMap.value[row.item_id] = await getSkuPipelineDetail(row.item_id)
  } catch { /* ignore */ }
  finally { loadingDetail.value[row.item_id] = false }
}

function isExpanded(row: SkuPipelineItem) {
  return expandedRows.value.has(row.item_id)
}

// ── 工具函数 ──
function fmtInt(v: number) { return v.toLocaleString('ru-RU') }
function fmtFloat(v: number) { return v.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }
function formatDate(v: string | null) {
  if (!v) return '—'
  return v.length > 10 ? v.slice(0, 10) : v
}
function onPageChange(p: number) { page.value = p }
function onPageSizeChange(s: number) { pageSize.value = s; page.value = 1 }
</script>

<template>
  <div v-loading="loading" style="min-height:300px;">

    <!-- 独立日期筛选 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
      <span style="font-size:12px;color:#909399;">📅 时间筛选</span>
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
        start-placeholder="开始日期" end-placeholder="结束日期"
        value-format="YYYY-MM-DD" style="width:240px"
        :disabled-date="disabledDate"
      />
      <el-tag type="info" size="small" style="margin-left:auto;">{{ total }} 个 SKU</el-tag>
    </div>

    <!-- 概览卡片 -->
    <el-row :gutter="16">
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#409eff;"><el-icon><Document /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">SKU总数</div>
              <div style="font-size:18px;font-weight:700;">{{ fmtInt(overview.total) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#e6a23c;"><el-icon><Clock /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">申购中</div>
              <div style="font-size:18px;font-weight:700;">{{ fmtInt(overview.hasPlan) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#409eff;"><el-icon><Box /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">采购中</div>
              <div style="font-size:18px;font-weight:700;">{{ fmtInt(overview.hasOrder) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#67c23a;"><el-icon><Van /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">发货中</div>
              <div style="font-size:18px;font-weight:700;">{{ fmtInt(overview.hasShipping) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#67c23a;"><el-icon><Checked /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">已到仓</div>
              <div style="font-size:18px;font-weight:700;">{{ fmtInt(overview.hasInbound) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#f56c6c;"><el-icon><WarningFilled /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">计划-发货差</div>
              <div style="font-size:16px;font-weight:700;">{{ fmtFloat(Math.max(0, overview.totalPlanQty - overview.totalShippedQty)) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#909399;"><el-icon><Document /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">计划总数</div>
              <div style="font-size:16px;font-weight:700;">{{ fmtFloat(overview.totalPlanQty) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="3">
        <el-card shadow="hover" :body-style="{ padding: '10px 14px' }">
          <div style="display:flex;align-items:center;gap:8px;">
            <div style="font-size:20px;color:#67c23a;"><el-icon><Checked /></el-icon></div>
            <div>
              <div style="font-size:11px;color:#909399;">已发货总数</div>
              <div style="font-size:16px;font-weight:700;">{{ fmtFloat(overview.totalShippedQty) }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- SKU 供应链表格 -->
    <el-card shadow="hover" style="margin-top:16px;">
      <template #header>
        <span style="font-weight:600;">SKU 供应链追踪</span>
      </template>

      <el-table
        :data="list"
        stripe
        size="small"
        max-height="600"
        @expand-change="onExpandChange"
        :row-key="(r: SkuPipelineItem) => r.item_id"
      >
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-loading="loadingDetail[row.item_id]" style="padding:12px 24px;">
              <template v-if="detailMap[row.item_id]">
                <el-row :gutter="16">
                  <!-- 申购阶段 -->
                  <el-col :span="8">
                    <div style="border:1px solid #e4e7ed;border-radius:6px;padding:10px 14px;min-height:120px;">
                      <div style="font-weight:600;font-size:13px;color:#e6a23c;margin-bottom:8px;">📋 申购计划</div>
                      <div v-if="detailMap[row.item_id].plans.length === 0" style="color:#c0c4cc;font-size:12px;">暂无</div>
                      <div v-for="p in detailMap[row.item_id].plans" :key="p.po_plan_no"
                        style="font-size:12px;line-height:1.8;padding:4px 0;border-bottom:1px dashed #f0f0f0;">
                        <div><span style="font-family:monospace;color:#409eff;">{{ p.po_plan_no }}</span>
                          <el-tag size="small" effect="plain" style="margin-left:4px;">{{ p.status_label }}</el-tag></div>
                        <div>计划 {{ fmtFloat(p.plan_qty) }} 个 | 已下单 {{ fmtFloat(p.already_qty) }}
                          <span v-if="p.wms_rec_qty > 0" style="color:#67c23a;"> | 收货 {{ fmtFloat(p.wms_rec_qty) }}</span>
                        </div>
                        <div style="font-size:11px;color:#909399;">期望交期: {{ formatDate(p.expect_date) }}</div>
                      </div>
                    </div>
                  </el-col>
                  <!-- 采购阶段 -->
                  <el-col :span="8">
                    <div style="border:1px solid #e4e7ed;border-radius:6px;padding:10px 14px;min-height:120px;">
                      <div style="font-weight:600;font-size:13px;color:#409eff;margin-bottom:8px;">📦 采购订单</div>
                      <div v-if="detailMap[row.item_id].orders.length === 0" style="color:#c0c4cc;font-size:12px;">暂无</div>
                      <div v-for="o in detailMap[row.item_id].orders" :key="o.po_no"
                        style="font-size:12px;line-height:1.8;padding:4px 0;border-bottom:1px dashed #f0f0f0;">
                        <div><span style="font-family:monospace;color:#409eff;">{{ o.po_no }}</span>
                          <el-tag size="small" effect="plain" :type="o.status === '7' ? 'success' : 'warning'">{{ o.status_label }}</el-tag></div>
                        <div>下单 {{ fmtFloat(o.qty) }} 个
                          <span v-if="o.receipt_qty > 0" style="color:#67c23a;"> | 已收货 {{ fmtFloat(o.receipt_qty) }}</span>
                        </div>
                        <div v-if="o.price > 0" style="font-size:11px;color:#909399;">
                          单价 ¥{{ o.price.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                          | 金额 ¥{{ fmtFloat(o.untaxed_amount) }}
                        </div>
                      </div>
                    </div>
                  </el-col>
                  <!-- 发货阶段 -->
                  <el-col :span="8">
                    <div style="border:1px solid #e4e7ed;border-radius:6px;padding:10px 14px;min-height:120px;">
                      <div style="font-weight:600;font-size:13px;color:#67c23a;margin-bottom:8px;">🚚 头程发货</div>
                      <div v-if="detailMap[row.item_id].shippings.length === 0" style="color:#c0c4cc;font-size:12px;">暂无</div>
                      <div v-for="s in detailMap[row.item_id].shippings" :key="s.order_code"
                        style="font-size:12px;line-height:1.8;padding:4px 0;border-bottom:1px dashed #f0f0f0;">
                        <div><span style="font-family:monospace;color:#409eff;">{{ s.order_code }}</span>
                          <el-tag size="small" effect="plain"
                            :type="s.order_status === '11' || s.order_status === '12' ? 'success' : 'warning'">
                            {{ s.status_label }}</el-tag></div>
                        <div>发货 {{ fmtFloat(s.final_shipping_num) }} 件 | 物流 {{ s.channel_code || '—' }}</div>
                        <div style="font-size:11px;color:#909399;">
                          发货时间: {{ formatDate(s.shipping_time) }}
                          <span v-if="s.arrived_time"> | 到仓: {{ formatDate(s.arrived_time) }}</span>
                        </div>
                      </div>
                    </div>
                  </el-col>
                </el-row>
              </template>
              <div v-else style="text-align:center;color:#c0c4cc;padding:16px;">加载中...</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="item_id" label="SKU" min-width="160" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-family:monospace;font-size:13px;">{{ row.item_id }}</span>
          </template>
        </el-table-column>
        <el-table-column label="申购" width="130" align="center">
          <template #default="{ row }">
            <div style="font-size:12px;">
              <div><span style="font-weight:600;color:#e6a23c;">{{ row.plan_count }}</span> 单</div>
              <div style="color:#909399;">计划 {{ fmtFloat(row.total_plan_qty) }}</div>
              <div v-if="row.total_ordered_qty > 0" style="color:#409eff;">已下单 {{ fmtFloat(row.total_ordered_qty) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="采购" width="130" align="center">
          <template #default="{ row }">
            <div style="font-size:12px;">
              <div><span style="font-weight:600;color:#409eff;">{{ row.order_count }}</span> 单</div>
              <div style="color:#909399;">下单 {{ fmtFloat(row.total_order_qty) }}</div>
              <div v-if="row.total_receipt_qty > 0" style="color:#67c23a;">已收货 {{ fmtFloat(row.total_receipt_qty) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="发货" width="130" align="center">
          <template #default="{ row }">
            <div style="font-size:12px;">
              <div><span style="font-weight:600;color:#67c23a;">{{ row.shipping_count }}</span> 单</div>
              <div style="color:#909399;">发货 {{ fmtFloat(row.total_shipped_qty) }}</div>
              <div v-if="row.total_inbound_qty > 0" style="color:#67c23a;">上架 {{ fmtFloat(row.total_inbound_qty) }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="阶段状态" min-width="180" align="center">
          <template #default="{ row }">
            <div style="display:flex;align-items:center;gap:2px;justify-content:center;">
              <el-tag :type="row.plan_count > 0 ? 'success' : 'info'" size="small" effect="plain" round>申购</el-tag>
              <span style="color:#c0c4cc;font-size:10px;">→</span>
              <el-tag :type="row.order_count > 0 ? (row.total_receipt_qty >= row.total_order_qty ? 'success' : 'warning') : 'info'" size="small" effect="plain" round>采购</el-tag>
              <span style="color:#c0c4cc;font-size:10px;">→</span>
              <el-tag :type="row.shipping_count > 0 ? (row.total_inbound_qty > 0 ? 'success' : 'warning') : 'info'" size="small" effect="plain" round>发货</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="marketplace" label="站点" width="55" align="center" />
        <el-table-column label="期望交期" width="100">
          <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.expect_date) }}</span></template>
        </el-table-column>
        <el-table-column label="最新更新" width="140" sortable>
          <template #default="{ row }"><span style="font-size:12px;">{{ formatDate(row.latest_update) }}</span></template>
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
  </div>
</template>
