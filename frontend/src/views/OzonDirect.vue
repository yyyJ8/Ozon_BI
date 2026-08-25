<template>
  <el-container style="min-height: 100vh; background: #f5f7fa;">
    <el-header style="height: auto; padding: 16px 24px; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,0.08);">
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 12px;">
          <h2 style="margin: 0; font-size: 20px;">OZON 直发信息</h2>
        </div>
        <div style="display: flex; gap: 8px;">
          <el-button type="primary" @click="exportZip">
            <el-icon><Download /></el-icon> 导出 ZIP
          </el-button>
        </div>
      </div>
    </el-header>

    <el-main style="padding: 20px 24px;">
      <el-card shadow="hover">
        <el-tabs v-model="activeTab" @tab-change="onTabChange">
          <!-- SKU 基础数据 -->
          <el-tab-pane label="SKU基础数据" name="sku">
            <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center;">
              <el-input
                v-model="sku.search"
                placeholder="搜索 SKU / 产品名 / 供应商"
                clearable
                style="width: 320px;"
                @clear="sku.onSearch()"
                @keyup.enter="sku.onSearch()"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-select v-model="skuGroupBy" style="width: 120px;" @change="onSkuGroupByChange">
                <el-option label="按店铺分组" value="store_name" />
              </el-select>
              <el-button type="primary" @click="sku.onSearch()">搜索</el-button>
              <el-button type="success" @click="openSkuDialog()">新增 SKU</el-button>
              <el-button v-if="skuSelected.length > 0" type="danger" @click="batchDeleteSku">删除选中 ({{ skuSelected.length }})</el-button>
            </div>

            <div v-loading="sku.loading">
              <div style="width:100%;height:calc(100vh - 320px);">
                <el-auto-resizer>
                  <template #default="{ height, width }">
                    <el-table-v2
                      class="sku-table-v2"
                      :columns="skuColumns"
                      :data="flatSkuList"
                      :width="width"
                      :height="height"
                      :row-height="36"
                    />
                  </template>
                </el-auto-resizer>
              </div>
            </div>

            <div style="margin-top: 8px; color: #909399; font-size: 12px;">共 {{ sku.total }} 条</div>
          </el-tab-pane>

          <!-- 直发跟进表 -->
          <el-tab-pane label="直发跟进表" name="shipment">
            <div style="display: flex; gap: 12px; margin-bottom: 16px; align-items: center; flex-wrap: wrap;">
              <el-select v-model="shipDatePreset" style="width: 110px;" @change="applyShipDatePreset">
                <el-option label="近1月" value="1month" />
                <el-option label="近3月" value="3months" />
                <el-option label="近6月" value="6months" />
                <el-option label="近1年" value="1year" />
                <el-option label="全部" value="all" />
                <el-option label="自定义" value="custom" />
              </el-select>
              <el-date-picker
                v-if="shipDatePreset === 'custom'"
                v-model="shipment.dateRange"
                type="daterange"
                range-separator="-"
                start-placeholder="开始"
                end-placeholder="结束"
                value-format="YYYY-MM-DD"
                style="width: 240px;"
                @change="shipment.fetchAll()"
              />
              <el-input
                v-model="shipment.search"
                placeholder="搜索申购单号 / SKU / 产品名 / 供应商 / 头程单号"
                clearable
                style="width: 240px;"
                @clear="shipment.onSearch()"
                @keyup.enter="shipment.onSearch()"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-button :type="shipConds.length ? 'primary' : 'default'" @click="openShipFilter">筛选{{ shipConds.length ? `(${shipConds.length})` : '' }}</el-button>
              <el-button :type="shipGroupFields.length > 1 ? 'primary' : 'default'" @click="openShipGroup">分组{{ shipGroupFields.length > 1 ? `(${shipGroupFields.length})` : '' }}</el-button>
              <el-button type="primary" @click="shipment.onSearch()">搜索</el-button>
              <el-button type="success" @click="openShipmentDialog()">新增记录</el-button>
              <el-button v-if="shipSelected.length > 0" type="danger" @click="batchDeleteShipment">删除选中 ({{ shipSelected.length }})</el-button>
              <span style="color: #909399; font-size: 12px; margin-left: auto;">共 {{ shipment.total }} 条</span>
            </div>

            <div v-loading="shipment.loading">
              <div style="width:100%;height:calc(100vh - 300px);">
                <el-auto-resizer>
                  <template #default="{ height, width }">
                    <el-table-v2
                      class="ship-table-v2"
                      :columns="shipColumns"
                      :data="flatShipmentList"
                      :width="width"
                      :height="height"
                      :row-height="36"
                      fixed
                    />
                  </template>
                </el-auto-resizer>
              </div>
            </div>

          </el-tab-pane>

        <!-- ══════════════════════════════════════════ -->
        <!-- 直发 高级筛选 面板 -->
        <!-- ══════════════════════════════════════════ -->
        <el-dialog v-model="shipFilterDialogVisible" title="筛选（多字段组合）" width="780px">
          <div style="margin-bottom:12px;color:#909399;font-size:12px;">筛选与分组可同时生效，先筛选后分组。</div>
          <div v-for="(c, idx) in shipFilterDraft" :key="c.id" style="display:flex;gap:8px;align-items:center;margin-bottom:8px;flex-wrap:wrap;">
            <el-select :model-value="idx === 0 ? 'and' : c.logic" style="width:64px;" :disabled="idx === 0" @update:model-value="(v: string) => { c.logic = v as any }">
              <el-option label="当" value="and" />
              <el-option label="且" value="and" />
              <el-option label="或" value="or" />
            </el-select>
            <el-select v-model="c.field" filterable style="width:170px;" @change="c.value = ''">
              <el-option v-for="f in shipFieldOptions" :key="f.value" :label="f.label" :value="f.value" />
            </el-select>
            <el-select v-model="c.op" style="width:110px;">
              <el-option v-for="o in condOps(shipFieldType(c.field))" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <el-select v-if="shipFieldType(c.field) === 'enum'" v-model="c.value" filterable clearable placeholder="请选择" style="width:180px;">
              <el-option v-for="o in shipCondOptions(c.field)" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
            <el-date-picker v-else-if="shipFieldType(c.field) === 'date'" v-model="c.value" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:150px;" />
            <el-input v-else v-model="c.value" placeholder="请输入" clearable style="width:180px;" />
            <el-button type="danger" link @click="removeShipCond(c.id)">删除</el-button>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;align-items:center;">
            <el-button type="primary" @click="addShipCond">+ 添加条件</el-button>
            <el-button @click="clearShipConds">清空</el-button>
            <span style="margin-left:auto;color:#909399;font-size:12px;">当前 {{ shipFilterDraft.length }} 个条件</span>
          </div>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;">
            <el-button @click="shipFilterDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="applyShipFilterDraft">应用</el-button>
          </div>
        </el-dialog>

        <!-- ══════════════════════════════════════════ -->
        <!-- 直发 多级分组 面板 -->
        <!-- ══════════════════════════════════════════ -->
        <el-dialog v-model="shipGroupDialogVisible" title="分组（最多 3 级）" width="620px">
          <div v-for="(g, i) in shipGroupDraft" :key="i" style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
            <span style="color:#909399;font-size:12px;width:32px;">{{ i + 1 }}级</span>
            <el-select v-model="g.field" filterable style="width:210px;">
              <el-option v-for="f in shipFieldOptions" :key="f.value" :label="f.label" :value="f.value" />
            </el-select>
            <el-select v-model="g.dir" style="width:100px;">
              <el-option label="A→Z" value="asc" />
              <el-option label="Z→A" value="desc" />
            </el-select>
            <el-button type="danger" link @click="removeShipGroupField(i)" :disabled="shipGroupFields.length <= 1">删除</el-button>
          </div>
          <div style="display:flex;gap:8px;margin-top:12px;align-items:center;">
            <el-button type="primary" @click="addShipGroupField" :disabled="shipGroupFields.length >= 3">+ 添加分组</el-button>
            <el-button @click="expandAllShipGroups">展开所有</el-button>
            <el-button @click="collapseAllShipGroups">折叠所有</el-button>
            <span style="margin-left:auto;color:#909399;font-size:12px;">已选 {{ shipGroupDraft.length }} 级分组</span>
          </div>
          <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;">
            <el-button @click="shipGroupDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="applyShipGroupDraft">应用</el-button>
          </div>
        </el-dialog>
        </el-tabs>
      </el-card>
    </el-main>

    <!-- 底部固定横向滚动条 -->
    <div ref="hScrollBar" class="fixed-h-bar" @scroll="onFixedBarScroll">
      <div ref="hScrollInner" :style="{ width: hScrollWidth + 'px', height: '1px' }"></div>
    </div>

    <!-- ══════════════════════════════════════════ -->
    <!-- SKU 编辑弹窗 -->
    <!-- ══════════════════════════════════════════ -->
    <el-dialog
      v-model="skuDialogVisible"
      :title="editingSku?.id ? '编辑 SKU' : '新增 SKU'"
      width="500px"
      @closed="resetSkuForm"
    >
      <el-form :model="skuForm" label-width="80px">
        <el-form-item label="SKU" required>
          <el-input v-model="skuForm.sku" placeholder="SKU 编码" :disabled="!!editingSku" />
        </el-form-item>
        <el-form-item label="产品名称" required>
          <el-input v-model="skuForm.product_name" placeholder="产品名称" />
        </el-form-item>
        <el-form-item label="供应商" required>
          <el-input v-model="skuForm.supplier" placeholder="供应商" />
        </el-form-item>
        <el-form-item label="店铺" required>
          <el-input v-model="skuForm.store_name" placeholder="店铺" />
        </el-form-item>
        <el-form-item label="销售负责人">
          <el-input v-model="skuForm.sales_manager" placeholder="销售负责人" />
        </el-form-item>
        <el-form-item label="标签文件">
          <el-input v-model="skuForm.label_file" placeholder="标签文件名（选填）" />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            :on-change="handleSkuFileChange"
            :show-file-list="false"
            multiple
            :auto-upload="false"
            accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.zip"
          >
            <el-button size="small" type="primary">
              <el-icon><Upload /></el-icon> 上传文件
            </el-button>
            <template #tip>
              <div style="font-size: 12px; color: #909399;">支持 PDF、Excel、图片（单个 ≤ 20MB）</div>
            </template>
          </el-upload>
          <div v-if="skuFiles.files.length > 0" style="margin-top: 8px;">
            <div v-for="f in skuFiles.files" :key="f.id" style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
              <el-button size="small" link type="primary" @click="downloadFile(f.id)">{{ f.file_name }}</el-button>
              <el-button size="small" type="danger" link @click="removeFile(f.id)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="skuDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveSku" :loading="skuSaving">保存</el-button>
      </template>
    </el-dialog>

    <!-- ══════════════════════════════════════════ -->
    <!-- 发货记录编辑弹窗 -->
    <!-- ══════════════════════════════════════════ -->
    <el-dialog
      v-model="shipmentDialogVisible"
      :title="editingShipment?.id ? '编辑发货记录' : '新增发货记录'"
      width="900px"
      @closed="resetShipmentForm"
    >
      <el-form :model="shipmentForm" label-width="110px" size="small">
        <el-divider content-position="left">基础信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="申购时间" required><el-date-picker v-model="shipmentForm.pr_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="申购单号" required><el-input v-model="shipmentForm.pr_no" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="SKU" required><el-input v-model="shipmentForm.sku" @blur="onShipmentSkuBlur" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="申购人员"><el-input v-model="shipmentForm.pr_person" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="产品中文名"><el-input v-model="shipmentForm.product_cn_name" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="上期售后情况"><el-input v-model="shipmentForm.previous_aftersales" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="供应商"><el-input v-model="shipmentForm.supplier" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="物流商" required>
              <el-select v-model="shipmentForm.logistics_provider" placeholder="请选择物流商" style="width:100%">
                <el-option label="超光速" value="超光速" />
                <el-option label="SDK" value="SDK" />
                <el-option label="昆仑" value="昆仑" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="头程单号" required><el-input v-model="shipmentForm.first_leg_tracking" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">发货信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="总数" required><el-input-number v-model="shipmentForm.total_qty" :min="0" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="总箱数" required><el-input-number v-model="shipmentForm.total_boxes" :min="0" style="width:100%" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="收货地址" required><el-input v-model="shipmentForm.receiving_address" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="贴标发货说明" required><el-input v-model="shipmentForm.labeling_notes" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">标签内容</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="产品标签">
              <div style="display:flex;gap:8px;">
                <el-input v-model="shipmentForm.product_label" placeholder="文件名或描述" style="flex:1;" />
                <el-upload :on-change="(f: any) => handleFieldFileUpload(f, 'product_label')" :show-file-list="false" :auto-upload="false" accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.zip">
                  <el-button size="small"><el-icon><Upload /></el-icon></el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="外箱箱唛">
              <div style="display:flex;gap:8px;">
                <el-input v-model="shipmentForm.carton_mark" placeholder="文件名或描述" style="flex:1;" />
                <el-upload :on-change="(f: any) => handleFieldFileUpload(f, 'carton_mark')" :show-file-list="false" :auto-upload="false" accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.zip">
                  <el-button size="small"><el-icon><Upload /></el-icon></el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="入库清单">
              <div style="display:flex;gap:8px;">
                <el-input v-model="shipmentForm.warehouse_receipt" placeholder="文件名或描述" style="flex:1;" />
                <el-upload :on-change="(f: any) => handleFieldFileUpload(f, 'warehouse_receipt')" :show-file-list="false" :auto-upload="false" accept=".pdf,.xlsx,.xls,.png,.jpg,.jpeg,.gif,.webp,.zip">
                  <el-button size="small"><el-icon><Upload /></el-icon></el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">采购信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="采购单号"><el-input v-model="shipmentForm.po_no" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="网采单号"><el-input v-model="shipmentForm.online_po_no" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="是否收货上架">
              <el-select v-model="shipmentForm.is_received" style="width:100%">
                <el-option label="是" value="是" /><el-option label="否" value="否" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="发货时间"><el-date-picker v-model="shipmentForm.ship_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="备注"><el-input v-model="shipmentForm.special_notes" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">货件情况</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="货件单号"><el-input v-model="shipmentForm.shipment_no" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="收货状态">
              <el-select v-model="shipmentForm.receiving_status" style="width:100%;">
                <el-option label="已收到" value="已收到" />
                <el-option label="异常" value="异常" />
                <el-option label="已取消" value="已取消" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="收货时间"><el-date-picker v-model="shipmentForm.receiving_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item>
          </el-col>
        </el-row>

      </el-form>
      <template #footer>
        <el-button @click="shipmentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveShipment" :loading="shipmentSaving">保存</el-button>
      </template>
    </el-dialog>

  </el-container>
</template>

<style>
.fixed-h-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 14px;
  overflow-x: auto;
  overflow-y: hidden;
  background: #f0f2f5;
  border-top: 1px solid #dcdfe6;
  z-index: 100;
}
.fixed-h-bar::-webkit-scrollbar { height: 12px; }
.fixed-h-bar::-webkit-scrollbar-thumb { background: #c0c4cc; border-radius: 6px; }

/* 表头：主题蓝色醒目 */
.sku-table .el-table__header th,
.ship-table .el-table__header th {
  background: var(--el-color-primary) !important;
  color: #fff !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  border-bottom: 2px solid var(--el-color-primary-light-3) !important;
}

/* 分组行样式 — 覆盖所有子表（fixed 列会拆成多张表） */
tr.ship-group-row > td,
tr.sku-group-row > td {
  background: #f0f2f5 !important;
  font-weight: 600;
  border-bottom: 2px solid #dcdfe6;
}

/* ElTableV2 表头 — 主题蓝色醒目 */
.ship-table-v2 .el-table-v2__header-cell,
.sku-table-v2 .el-table-v2__header-cell {
  background: var(--el-color-primary) !important;
  color: #fff !important;
  font-weight: 700 !important;
  font-size: 13px !important;
  border-bottom: 2px solid var(--el-color-primary-light-3) !important;
}
</style>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch, h } from 'vue'
import { ElMessage, ElMessageBox, ElCheckbox, ElButton, ElTag } from 'element-plus'
import { Search, Upload, Download, Delete } from '@element-plus/icons-vue'
import { useDirectSku, useDirectShipment, useDirectFiles } from '@/composables/useOzonDirect'
import { getDirectFileUrl, getDirectFiles, getExportUrl } from '@/api'
import type { DirectSkuItem, DirectShipmentItem } from '@/types'

// ── Tab ──
const activeTab = ref('sku')

// ── SKU ──
const sku = reactive(useDirectSku())
const skuDialogVisible = ref(false)
const skuSaving = ref(false)
// 独立选中状态（不受折叠/展开影响）
const selectedSkuIds = ref(new Set<number>())
const skuSelected = computed(() => sku.list.filter(it => selectedSkuIds.value.has(it.id)))
const editingSku = ref<DirectSkuItem | null>(null)
const expandedSkuGroups = reactive(new Set<string>())

const skuGroupBy = ref('store_name')
const isSkuAllSelected = computed(() => sku.list.length > 0 && selectedSkuIds.value.size >= sku.list.length)
function onSkuRowCheck(row: any, checked: boolean) {
  if (checked) selectedSkuIds.value.add(row.id)
  else selectedSkuIds.value.delete(row.id)
  selectedSkuIds.value = new Set(selectedSkuIds.value)
}

function onSkuHeaderCheck(checked: boolean) {
  if (checked) {
    for (const group of skuGroups.value) {
      expandedSkuGroups.add(group.key)
      for (const item of group.items) selectedSkuIds.value.add(item.id)
    }
  } else {
    selectedSkuIds.value = new Set()
  }
  selectedSkuIds.value = new Set(selectedSkuIds.value)
}


function toggleSkuGroup(key: string) {
  if (expandedSkuGroups.has(key)) expandedSkuGroups.delete(key)
  else expandedSkuGroups.add(key)
}

function onSkuGroupByChange() { expandedSkuGroups.clear(); sku.fetchAll() }

const skuGroups = computed(() => {
  const groups: Record<string, DirectSkuItem[]> = {}
  for (const item of sku.list) {
    const key = (item as any)[skuGroupBy.value] || '未分组'
    if (!groups[key]) groups[key] = []
    groups[key].push(item)
  }
  return Object.entries(groups).map(([key, items]) => ({ key, items }))
})
// 新数据到达时自动展开所有分组
watch(skuGroups, (groups) => {
  for (const g of groups) expandedSkuGroups.add(g.key)
})

// 单表数据：分组行 + 展开的数据行
const flatSkuList = computed(() => {
  const result: any[] = []
  for (const group of skuGroups.value) {
    result.push({
      _type: 'group',
      id: `__group__${group.key}`,
      _groupKey: group.key,
      _count: group.items.length,
    })
    if (expandedSkuGroups.has(group.key)) {
      for (const item of group.items) {
        result.push({ _type: 'data', _groupKey: group.key, ...item })
      }
    }
  }
  return result
})

// SKU 分组勾选：全选 ☑ / 全空 □
function isSkuGroupAllSelected(groupKey: string): boolean {
  const group = skuGroups.value.find(g => g.key === groupKey)
  if (!group || group.items.length === 0) return false
  return group.items.every(it => selectedSkuIds.value.has(it.id))
}
function toggleSkuGroupAll(groupKey: string, select: boolean) {
  const group = skuGroups.value.find(g => g.key === groupKey)
  if (!group) return
  if (select) group.items.forEach(it => selectedSkuIds.value.add(it.id))
  else group.items.forEach(it => selectedSkuIds.value.delete(it.id))
  selectedSkuIds.value = new Set(selectedSkuIds.value)
  // 折叠状态自动展开
  if (!expandedSkuGroups.has(groupKey)) expandedSkuGroups.add(groupKey)
}

// 点击 SKU 分组标签 → 全选该组
function selectSkuGroup(groupKey: string) { toggleSkuGroupAll(groupKey, true) }

// 直发表 SKU → 申购人员（供 SKU 表销售负责人兜底）
const skuPrPersonMap = computed(() => {
  const map = new Map<string, string>()
  for (const it of shipment.list) {
    if (it.sku && it.pr_person && !map.has(it.sku)) {
      map.set(it.sku, it.pr_person)
    }
  }
  return map
})

// SKU 编码 → SKU 详情映射（供直发跟进表自动填充用）
const skuMap = computed(() => {
  const map = new Map<string, DirectSkuItem>()
  for (const item of sku.list) {
    map.set(item.sku, item)
  }
  return map
})

// ── SKU 表格 ElTableV2 虚拟滚动：列定义 + 单元格渲染 ──
const skuColumns = computed(() => {
  const cell: any = (render: (p: any) => any) => (p: any) =>
    p.rowData._type === 'group' ? _shipGroupCell() : render(p)
  return [
    { key: '__sel', width: 40, title: '', headerCellRenderer: () => h(ElCheckbox, {
        modelValue: isSkuAllSelected.value,
        onChange: (v: boolean) => onSkuHeaderCheck(v),
      }),
      cellRenderer: (p: any) => p.rowData._type === 'group'
        ? _shipGroupCell()
        : h(ElCheckbox, { modelValue: selectedSkuIds.value.has(p.rowData.id), onChange: (v: boolean) => onSkuRowCheck(p.rowData, v) }),
    },
    // SKU：分组标题所在列
    { key: 'sku', dataKey: 'sku', title: 'SKU', width: 160, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') {
          return h('div', { style: `display:flex;align-items:center;gap:8px;background:${_shipGroupBg};padding-left:16px;height:35px;` }, [
            h('span', { onClick: () => toggleSkuGroup(row._groupKey), style: 'font-size:12px;cursor:pointer;' }, expandedSkuGroups.has(row._groupKey) ? '▼' : '▶'),
            h('span', { onClick: () => toggleSkuGroup(row._groupKey), style: 'font-weight:600;cursor:pointer;font-size:13px;max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', title: row._groupKey }, row._groupKey),
            h(ElTag, { size: 'small', type: 'info' }, () => String(row._count)),
          ])
        }
        return _txt(p.cellData)
      },
    },
    { key: 'product_name', dataKey: 'product_name', title: '产品名称', width: 180, flexGrow: 1, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'supplier', dataKey: 'supplier', title: '供应商', width: 160, flexGrow: 1, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'sales_manager', title: '销售负责人', width: 110, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return _txt(row.sales_manager || skuPrPersonMap.value.get(row.sku) || '—')
      },
    },
    { key: 'label_file', title: '标签文件', width: 220, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return row.label_file ? _fileBtn(row, 'sku', row.label_file) : h('span', { style: 'color:#c0c4cc;' }, '—')
      },
    },
    { key: '__op', title: '操作', width: 80, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return h(ElButton, { size: 'small', onClick: () => openSkuDialog(row) }, () => '编辑')
      },
    },
  ]
})

const skuForm = reactive({
  sku: '', product_name: '', supplier: '', store_name: '', sales_manager: '', label_file: '',
})
const skuFiles = reactive(useDirectFiles())

function openSkuDialog(row?: DirectSkuItem) {
  if (row) {
    editingSku.value = row
    skuForm.sku = row.sku
    skuForm.product_name = row.product_name || ''
    skuForm.supplier = row.supplier || ''
    skuForm.store_name = row.store_name || ''
    skuForm.sales_manager = row.sales_manager || ''
    skuForm.label_file = row.label_file || ''
    skuFiles.fetchFiles('sku', row.sku)
  } else {
    editingSku.value = null
    resetSkuForm()
  }
  skuDialogVisible.value = true
}

function resetSkuForm() {
  editingSku.value = null
  skuForm.sku = ''
  skuForm.product_name = ''
  skuForm.supplier = ''
  skuForm.store_name = ''
  skuForm.sales_manager = ''
  skuForm.label_file = ''
  skuFiles.files = [] as any
}

async function batchDeleteSku() {
  if (selectedSkuIds.value.size === 0) return
  const ids = [...selectedSkuIds.value]
  await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条记录？`, '批量删除', { type: 'warning' })
  for (const id of ids) {
    await sku.remove(id)
  }
  selectedSkuIds.value = new Set()
}

async function saveSku() {
  if (!skuForm.sku.trim()) { ElMessage.warning('SKU 不能为空'); return }
  if (!skuForm.product_name.trim()) { ElMessage.warning('产品名称不能为空'); return }
  if (!skuForm.supplier.trim()) { ElMessage.warning('供应商不能为空'); return }
  if (!skuForm.store_name.trim()) { ElMessage.warning('店铺不能为空'); return }
  skuSaving.value = true
  try {
    const body = {
      sku: skuForm.sku.trim(),
      product_name: skuForm.product_name || null,
      supplier: skuForm.supplier || null,
      store_name: skuForm.store_name || null,
      sales_manager: skuForm.sales_manager || null,
      label_file: skuForm.label_file || null,
    }
    if (editingSku.value?.id) {
      await sku.update(editingSku.value.id, body)
    } else {
      await sku.create(body)
    }
    skuDialogVisible.value = false
  } finally {
    skuSaving.value = false
  }
}

async function handleSkuFileChange(uploadFile: any) {
  const file: File | undefined = uploadFile?.raw
  if (!file || uploadFile.status !== 'ready') return
  if (!editingSku.value?.id) {
    ElMessage.warning('请先保存 SKU，再上传附件')
    return
  }
  if (!skuForm.sku.trim()) {
    ElMessage.warning('请先填写 SKU')
    return
  }
  const result = await skuFiles.upload(file, 'sku', skuForm.sku.trim())
  if (result) {
    // 上传成功后同步 label_file，保证表格「标签文件」列可点击匹配
    skuForm.label_file = result.file_name
    if (editingSku.value?.id) {
      await sku.update(editingSku.value.id, { label_file: result.file_name })
    }
  }
}

async function openRecordFile(sourceTable: string, sku: string, fileName: string, prNo?: string) {
  const fileList = await getDirectFiles(sourceTable, sku, prNo)
  let match = fileList.find(f => f.file_name === fileName)
  // 兜底：label_file 可能没带扩展名（如 'xxx产品标' vs 文件 'xxx产品标.pdf'）
  if (!match) {
    const noExt = fileName.replace(/\.[^.]+$/, '')
    match = fileList.find(f => f.file_name.replace(/\.[^.]+$/, '') === noExt) || null
  }
  if (match?.id) {
    const a = document.createElement('a')
    a.href = getDirectFileUrl(match.id)
    a.target = '_blank'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
  } else {
    ElMessage.info('文件未在文件库中找到')
  }
}

// ── Shipment ──
const shipment = reactive(useDirectShipment())
const shipmentDialogVisible = ref(false)
const shipmentSaving = ref(false)
const editingShipment = ref<DirectShipmentItem | null>(null)
// 独立选中状态（不受折叠/展开影响）
const selectedShipIds = ref(new Set<number>())
const shipSelected = computed(() => filteredShipList.value.filter(it => selectedShipIds.value.has(it.id)))
const expandedShipGroups = reactive(new Set<string>())
const shipFilterDialogVisible = ref(false)
const shipGroupDialogVisible = ref(false)

// ── 可选字段（高级筛选 / 分组共用）──
const shipFieldMeta: { key: string; label: string; type: 'text' | 'enum' | 'number' | 'date' }[] = [
  { key: 'pr_date', label: '申购时间', type: 'date' },
  { key: 'pr_no', label: '申购单号', type: 'text' },
  { key: 'sku', label: 'SKU', type: 'text' },
  { key: 'product_cn_name', label: '产品中文名', type: 'text' },
  { key: 'pr_person', label: '申购人员', type: 'enum' },
  { key: 'supplier', label: '供应商', type: 'text' },
  { key: 'logistics_provider', label: '物流商', type: 'enum' },
  { key: 'total_qty', label: '总数', type: 'number' },
  { key: 'total_boxes', label: '总箱数', type: 'number' },
  { key: 'is_received', label: '是否收货上架', type: 'enum' },
  { key: 'receiving_status', label: '收货状态', type: 'enum' },
  { key: 'shipment_no', label: '货件单号', type: 'text' },
  { key: 'first_leg_tracking', label: '头程单号', type: 'text' },
  { key: 'po_no', label: '采购单号', type: 'text' },
  { key: 'special_notes', label: '备注', type: 'text' },
]
function shipFieldLabel(key: string) { return shipFieldMeta.find(f => f.key === key)?.label || key }
function shipFieldType(key: string) { return shipFieldMeta.find(f => f.key === key)?.type || 'text' }
const shipFieldOptions = computed(() => shipFieldMeta.map(f => ({ label: f.label, value: f.key })))
function shipCondOptions(field: string) {
  const set = new Set<string>()
  for (const it of shipment.list) {
    const v = ((it as any)[field] || '').toString().trim()
    if (v) set.add(v)
  }
  return [...set].map(v => ({ label: v, value: v }))
}

// ── 高级筛选：多行条件（字段 + 操作符 + 值，当/且/或）──
type ShipCond = { id: number; logic: 'and' | 'or'; field: string; op: string; value: string }
let shipCondSeq = 0
const shipConds = reactive<ShipCond[]>([])
// 草稿：面板内编辑，点「应用」才写回 shipConds，避免实时连锁刷新
const shipFilterDraft = reactive<ShipCond[]>([])
function openShipFilter() {
  shipFilterDraft.splice(0, shipFilterDraft.length, ...JSON.parse(JSON.stringify(shipConds)))
  shipFilterDialogVisible.value = true
}
function applyShipFilterDraft() {
  shipConds.splice(0, shipConds.length, ...JSON.parse(JSON.stringify(shipFilterDraft)))
  shipFilterDialogVisible.value = false
}
function addShipCond() { shipFilterDraft.push({ id: ++shipCondSeq, logic: 'and', field: 'sku', op: 'eq', value: '' }) }
function removeShipCond(id: number) { const i = shipFilterDraft.findIndex(c => c.id === id); if (i > -1) shipFilterDraft.splice(i, 1) }
function clearShipConds() { shipFilterDraft.splice(0) }
function condOps(type: string) {
  if (type === 'number') return [
    { label: '等于', value: 'eq' }, { label: '大于', value: 'gt' }, { label: '小于', value: 'lt' }, { label: '不等于', value: 'ne' },
  ]
  if (type === 'date') return [
    { label: '等于', value: 'eq' }, { label: '早于', value: 'lt' }, { label: '晚于', value: 'gt' }, { label: '不为空', value: 'notempty' },
  ]
  return [
    { label: '等于', value: 'eq' }, { label: '不等于', value: 'ne' }, { label: '包含', value: 'contains' },
    { label: '为空', value: 'empty' }, { label: '不为空', value: 'notempty' },
  ]
}
function condMatch(item: any, c: ShipCond) {
  const raw = (item as any)[c.field]
  const v = raw == null ? '' : String(raw).trim()
  const val = (c.value ?? '').toString().trim()
  switch (c.op) {
    case 'eq': return v === val
    case 'ne': return v !== val
    case 'contains': return v.includes(val)
    case 'gt': return Number(v) > Number(val)
    case 'lt': return Number(v) < Number(val)
    case 'empty': return v === ''
    case 'notempty': return v !== ''
    default: return true
  }
}
function applyShipConds(list: DirectShipmentItem[]) {
  const conds = shipConds.filter(c => c.field && (c.op === 'empty' || c.op === 'notempty' || (c.value ?? '').toString().trim() !== ''))
  if (!conds.length) return list
  let res = list.filter(it => condMatch(it, conds[0]))
  for (let i = 1; i < conds.length; i++) {
    const c = conds[i]
    const matched = list.filter(it => condMatch(it, c))
    if (c.logic === 'or') { const s = new Set([...res, ...matched]); res = list.filter(it => s.has(it)) }
    else res = res.filter(it => matched.includes(it))
  }
  return res
}

// ── 多级分组：最多 3 级，缩进展示 ──
const shipGroupFields = reactive<{ field: string; dir: 'asc' | 'desc' }[]>([{ field: 'receiving_status', dir: 'asc' }])
const shipGroupDraft = reactive<{ field: string; dir: 'asc' | 'desc' }[]>([])
function openShipGroup() {
  shipGroupDraft.splice(0, shipGroupDraft.length, ...JSON.parse(JSON.stringify(shipGroupFields)))
  shipGroupDialogVisible.value = true
}
function applyShipGroupDraft() {
  shipGroupFields.splice(0, shipGroupFields.length, ...JSON.parse(JSON.stringify(shipGroupDraft)))
  expandAllShipGroups()   // 应用后展开一次
  shipGroupDialogVisible.value = false
}
function addShipGroupField() { if (shipGroupDraft.length < 3) shipGroupDraft.push({ field: 'sku', dir: 'asc' }) }
function removeShipGroupField(i: number) { shipGroupDraft.splice(i, 1) }

// 多字段组合过滤后的数据（高级筛选，分组/计数/全选都基于它）
const filteredShipList = computed(() => applyShipConds(shipment.list))

const isShipAllSelected = computed(() => {
  const ids = filteredShipList.value.map(it => it.id)
  return ids.length > 0 && ids.every(id => selectedShipIds.value.has(id))
})
function onShipRowCheck(row: any, checked: boolean) {
  if (checked) selectedShipIds.value.add(row.id)
  else selectedShipIds.value.delete(row.id)
  selectedShipIds.value = new Set(selectedShipIds.value)
}

function onShipHeaderCheck(checked: boolean) {
  if (checked) {
    expandAllShipGroups()
    filteredShipList.value.forEach(it => selectedShipIds.value.add(it.id))
  } else {
    selectedShipIds.value = new Set()
  }
  selectedShipIds.value = new Set(selectedShipIds.value)
}

// 递归构建多级分组树
const shipGroupTree = computed(() => {
  const fields = [...shipGroupFields]
  const build = (list: any[], depth: number): any[] => {
    if (depth >= fields.length || list.length === 0) return []
    const { field, dir } = fields[depth]
    const map = new Map<string, any[]>()
    for (const it of list) {
      let key = ((it as any)[field] || '').toString().trim()
      if (!key || key === '无') key = '未分组'
      if (!map.has(key)) map.set(key, [])
      map.get(key)!.push(it)
    }
    const entries = [...map.entries()].sort((a, b) => {
      const cmp = a[0].localeCompare(b[0], 'zh')
      return dir === 'desc' ? -cmp : cmp
    })
    return entries.map(([key, items]) => {
      const node: any = { field, key, items, depth, children: build(items, depth + 1), path: [] }
      return node
    })
  }
  const tree = build(filteredShipList.value, 0)
  const fill = (nodes: any[], prefix: string[]) => {
    for (const n of nodes) {
      n.path = [...prefix, n.key]
      if (n.children.length) fill(n.children, n.path)
    }
  }
  fill(tree, [])
  return tree
})

// 分组展开/折叠
function allShipGroupPaths(): string[] {
  const paths: string[] = []
  const walk = (nodes: any[]) => { for (const n of nodes) { paths.push(n.path.join('|')); if (n.children.length) walk(n.children) } }
  walk(shipGroupTree.value)
  return paths
}
function expandAllShipGroups() { allShipGroupPaths().forEach(p => expandedShipGroups.add(p)) }
function collapseAllShipGroups() { expandedShipGroups.clear() }
function toggleShipGroup(key: string) {
  if (expandedShipGroups.has(key)) expandedShipGroups.delete(key)
  else expandedShipGroups.add(key)
}
// 数据加载完成后展开一次（避免 deep watch 每次重算都连锁展开）
watch(() => shipment.list, (list) => { if (list.length) expandAllShipGroups() })

// 单表数据：多级分组行 + 展开的数据行
const flatShipmentList = computed(() => {
  const result: any[] = []
  const walk = (nodes: any[]) => {
    for (const node of nodes) {
      const gKey = node.path.join('|')
      result.push({
        _type: 'group',
        id: `__g__${gKey}`,
        _groupKey: gKey,
        _path: node.path,
        _depth: node.depth,
        _fieldLabel: shipFieldLabel(node.field),
        _count: node.items.length,
      })
      if (expandedShipGroups.has(gKey)) {
        if (node.children.length) walk(node.children)
        else for (const item of node.items) result.push({ _type: 'data', _groupKey: gKey, ...item })
      }
    }
  }
  walk(shipGroupTree.value)
  return result
})

function shipRowClassName({ row }: { row: any }) {
  return row._type === 'group' ? 'ship-group-row' : ''
}

// ── ElTableV2 虚拟滚动：列定义 + 单元格渲染 ──
const _shipGroupBg = '#f0f2f5'
const _shipGroupCell = () => h('div', { style: `background:${_shipGroupBg};height:35px;` })
// 单行省略：长文本截断显示，避免多行重叠
const _txt = (v: any) => h('span', { style: 'display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:35px;' }, v ?? '')
const _fileBtn = (row: any, sourceTable: string, fileName: string, prNo?: string) =>
  h(ElButton, { size: 'small', type: 'primary', link: true, onClick: () => openRecordFile(sourceTable, row.sku, fileName, prNo) }, () => fileName)

const shipColumns = computed(() => {
  const cell: any = (render: (p: any) => any) => (p: any) =>
    p.rowData._type === 'group' ? _shipGroupCell() : render(p)
  return [
    // 复选框（固定左）
    { key: '__sel', width: 40, fixed: 'left', title: '', headerCellRenderer: () => h(ElCheckbox, {
        modelValue: isShipAllSelected.value,
        onChange: (v: boolean) => onShipHeaderCheck(v),
      }),
      cellRenderer: (p: any) => p.rowData._type === 'group'
        ? _shipGroupCell()
        : h(ElCheckbox, { modelValue: selectedShipIds.value.has(p.rowData.id), onChange: (v: boolean) => onShipRowCheck(p.rowData, v) }),
    },
    // 申购时间：分组标题所在列
    { key: 'pr_date', dataKey: 'pr_date', title: '申购时间', width: 150, fixed: 'left', cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') {
          return h('div', { style: `display:flex;align-items:center;gap:6px;white-space:nowrap;background:${_shipGroupBg};padding-left:${14 + row._depth * 18}px;height:35px;` }, [
            h('span', { onClick: () => toggleShipGroup(row._groupKey), style: 'font-size:12px;cursor:pointer;' }, expandedShipGroups.has(row._groupKey) ? '▼' : '▶'),
            h('span', { onClick: () => toggleShipGroup(row._groupKey), style: 'font-weight:600;cursor:pointer;font-size:13px;max-width:110px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;', title: (row._path || []).join(' / ') }, (row._path || [])[(row._path || []).length - 1]),
            h('span', { style: 'color:#909399;font-size:12px;' }, `(${row._count})`),
          ])
        }
        return _txt(p.cellData)
      },
    },
    { key: 'pr_no', dataKey: 'pr_no', title: '申购单号', width: 140, fixed: 'left', cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'sku', dataKey: 'sku', title: 'SKU', width: 160, fixed: 'left', cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'pr_person', dataKey: 'pr_person', title: '申购人员', width: 110, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'product_cn_name', dataKey: 'product_cn_name', title: '产品中文名', width: 130, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'previous_aftersales', dataKey: 'previous_aftersales', title: '上期售后', width: 120, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'supplier', dataKey: 'supplier', title: '供应商', width: 160, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'logistics_provider', dataKey: 'logistics_provider', title: '物流商', width: 110, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'first_leg_tracking', dataKey: 'first_leg_tracking', title: '头程单号', width: 140, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'total_qty', dataKey: 'total_qty', title: '总数', width: 65, align: 'center', cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'total_boxes', dataKey: 'total_boxes', title: '总箱数', width: 75, align: 'center', cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'receiving_address', dataKey: 'receiving_address', title: '收货地址', width: 180, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'labeling_notes', dataKey: 'labeling_notes', title: '贴标说明', width: 150, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'product_label', title: '产品标签', width: 110, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        const lbl = shipmentProductLabel(row)
        return lbl ? _fileBtn(row, 'sku', lbl) : h('span', { style: 'color:#c0c4cc;' }, '—')
      },
    },
    { key: 'carton_mark', title: '外箱箱唛', width: 110, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return row.carton_mark ? _fileBtn(row, 'shipment', row.carton_mark, row.pr_no) : h('span', { style: 'color:#c0c4cc;' }, '—')
      },
    },
    { key: 'warehouse_receipt', title: '入库清单', width: 180, cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return row.warehouse_receipt ? _fileBtn(row, 'shipment', row.warehouse_receipt, row.pr_no) : h('span', { style: 'color:#c0c4cc;' }, '—')
      },
    },
    { key: 'po_no', dataKey: 'po_no', title: '采购单号', width: 140, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'online_po_no', dataKey: 'online_po_no', title: '网采单号', width: 180, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'is_received', dataKey: 'is_received', title: '收货上架', width: 110, align: 'center', cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return h(ElTag, { size: 'small', type: row.is_received === '是' ? 'success' : 'info' }, () => row.is_received || '—')
      },
    },
    { key: 'ship_date', dataKey: 'ship_date', title: '发货时间', width: 105, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'special_notes', dataKey: 'special_notes', title: '备注', width: 150, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'shipment_no', dataKey: 'shipment_no', title: '货件单号', width: 180, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'receiving_status', dataKey: 'receiving_status', title: '收货状态', width: 120, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    { key: 'receiving_date', dataKey: 'receiving_date', title: '收货时间', width: 105, cellRenderer: cell((p: any) => _txt(p.cellData)) },
    // 操作（固定右）
    { key: '__op', title: '操作', width: 80, fixed: 'right', cellRenderer: (p: any) => {
        const row = p.rowData
        if (row._type === 'group') return _shipGroupCell()
        return h(ElButton, { size: 'small', type: 'primary', onClick: () => openShipmentDialog(row) }, () => '编辑')
      },
    },
  ]
})

// SKU 字段失焦时自动从 SKU 表填充
// 产品标签：优先取 SKU 表的 label_file，其次用直发表自身值
function shipmentProductLabel(row: any): string | null {
  if (!row || row._type === 'group') return null
  return skuMap.value.get(row.sku)?.label_file || row.product_label || null
}

function onShipmentSkuBlur() {
  const code = (shipmentForm as any).sku?.trim()
  if (!code) return
  const item = skuMap.value.get(code)
  if (!item) { ElMessage.warning('未找到该 SKU'); return }
  ;(shipmentForm as any).product_cn_name = item.product_name || ''
  ;(shipmentForm as any).supplier = item.supplier || ''
  ;(shipmentForm as any).pr_person = item.sales_manager || ''
  ;(shipmentForm as any).product_label = item.label_file || ''
}

const shipmentForm = reactive<Record<string, any>>({
  pr_date: null, pr_no: '', sku: '', pr_person: '', product_cn_name: '',
  previous_aftersales: '', supplier: '', logistics_provider: '',
  first_leg_tracking: '', total_qty: null, total_boxes: null,
  receiving_address: '', labeling_notes: '', product_label: '', carton_mark: '',
  warehouse_receipt: '', po_no: '', online_po_no: '', is_received: null,
  ship_date: null, special_notes: '', shipment_no: '',
  receiving_status: '', receiving_date: null,
})
const shipmentFiles = reactive(useDirectFiles())

// ── 发货日期筛选 ──
const shipDatePreset = ref('all')

function daysAgoStr(n: number): string {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d.toISOString().split('T')[0]
}

function applyShipDatePreset(preset: string) {
  const yesterday = daysAgoStr(1)
  switch (preset) {
    case '1month': shipment.dateRange = [daysAgoStr(30), yesterday]; break
    case '3months': shipment.dateRange = [daysAgoStr(90), yesterday]; break
    case '6months': shipment.dateRange = [daysAgoStr(180), yesterday]; break
    case '1year': shipment.dateRange = [daysAgoStr(365), yesterday]; break
    case 'all': shipment.dateRange = null; break
    case 'custom': return
  }
  shipment.fetchAll()
}

function openShipmentDialog(row?: DirectShipmentItem) {
  if (row) {
    editingShipment.value = row
    Object.keys(shipmentForm).forEach(k => {
      (shipmentForm as any)[k] = (row as any)[k] ?? null
    })
    // 从 SKU 表补齐：产品标签 = SKU.label_file，产品中文名 / 供应商 / 申购人员同理
    const skuItem = skuMap.value.get(row.sku || '')
    if (skuItem) {
      if (!shipmentForm.product_label) (shipmentForm as any).product_label = skuItem.label_file || ''
      if (!shipmentForm.product_cn_name) (shipmentForm as any).product_cn_name = skuItem.product_name || ''
      if (!shipmentForm.supplier) (shipmentForm as any).supplier = skuItem.supplier || ''
      if (!shipmentForm.pr_person) (shipmentForm as any).pr_person = skuItem.sales_manager || ''
    }
  } else {
    editingShipment.value = null
    resetShipmentForm()
  }
  shipmentDialogVisible.value = true
}

function resetShipmentForm() {
  editingShipment.value = null
  Object.keys(shipmentForm).forEach(k => { (shipmentForm as any)[k] = null })
}

async function batchDeleteShipment() {
  if (selectedShipIds.value.size === 0) return
  const ids = [...selectedShipIds.value]
  await ElMessageBox.confirm(`确认删除选中的 ${ids.length} 条记录？`, '批量删除', { type: 'warning' })
  for (const id of ids) {
    await shipment.remove(id)
  }
  selectedShipIds.value = new Set()
}

async function saveShipment() {
  // 必填校验
  if (!shipmentForm.pr_date) { ElMessage.warning('申购时间不能为空'); return }
  if (!shipmentForm.pr_no?.trim()) { ElMessage.warning('申购单号不能为空'); return }
  if (!shipmentForm.sku?.trim()) { ElMessage.warning('SKU 不能为空'); return }
  if (!shipmentForm.logistics_provider?.trim()) { ElMessage.warning('物流商不能为空'); return }
  if (!shipmentForm.first_leg_tracking?.trim()) { ElMessage.warning('头程单号不能为空'); return }
  if (shipmentForm.total_qty == null || shipmentForm.total_qty === '') { ElMessage.warning('总数不能为空'); return }
  if (shipmentForm.total_boxes == null || shipmentForm.total_boxes === '') { ElMessage.warning('总箱数不能为空'); return }
  if (!shipmentForm.receiving_address?.trim()) { ElMessage.warning('收货地址不能为空'); return }
  if (!shipmentForm.labeling_notes?.trim()) { ElMessage.warning('贴标说明不能为空'); return }

  shipmentSaving.value = true
  try {
    const body: Record<string, any> = {}
    Object.keys(shipmentForm).forEach(k => {
      const v = (shipmentForm as any)[k]
      if (v !== undefined && v !== '') body[k] = v
    })
    if (editingShipment.value?.id) {
      await shipment.update(editingShipment.value.id, body)
    } else {
      await shipment.create(body)
    }
    shipmentDialogVisible.value = false
  } finally {
    shipmentSaving.value = false
  }
}

async function handleFieldFileUpload(uploadFile: any, fieldName: string) {
  const file: File | undefined = uploadFile?.raw
  if (!file || uploadFile.status !== 'ready') return
  const sku = (shipmentForm as any).sku?.trim() || ''
  const prNo = (shipmentForm as any).pr_no?.trim() || ''
  if (!sku) { ElMessage.warning('请先填写 SKU'); return false }

  // 产品标签 → 存到 SKU 文件表，同时更新 SKU 记录的 label_file
  if (fieldName === 'product_label') {
    const result = await shipmentFiles.upload(file, 'sku', sku)
    if (result) {
      (shipmentForm as any)[fieldName] = result.file_name
      // 同步更新 SKU 表的 label_file
      const skuItem = skuMap.value.get(sku)
      if (skuItem) {
        await sku.update(skuItem.id, { label_file: result.file_name })
      }
    }
  } else {
    // 外箱箱唛 / 入库清单 → 存到 shipment 文件表
    const result = await shipmentFiles.upload(file, 'shipment', sku, prNo)
    if (result) {
      (shipmentForm as any)[fieldName] = result.file_name
    }
  }
  return false
}

// ── 文件操作 ──
function downloadFile(fileId: number) {
  window.open(getDirectFileUrl(fileId), '_blank')
}

async function removeFile(fileId: number) {
  await ElMessageBox.confirm('确认删除该文件？', '确认', { type: 'warning' })
  if (activeTab.value === 'sku') {
    const s = skuForm.sku.trim()
    if (s) await skuFiles.remove(fileId, 'sku', s)
  } else {
    const s = (shipmentForm as any).sku?.trim() || ''
    const p = (shipmentForm as any).pr_no?.trim() || ''
    if (s) await shipmentFiles.remove(fileId, 'shipment', s, p)
  }
}

// ── 导出 ──

function exportZip() {
  const a = document.createElement('a')
  a.href = getExportUrl()
  a.download = 'OZON直发信息.zip'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

// ── Tab 切换 ──
function onTabChange() {
  fetchCurrentTab()
}

function fetchCurrentTab() {
  if (activeTab.value === 'sku') {
    sku.fetchAll()
  } else {
    shipment.fetchAll()
  }
}

// ── 底部固定横向滚动条同步 ──
const hScrollBar = ref<HTMLElement | null>(null)
const hScrollInner = ref<HTMLElement | null>(null)
const hScrollWidth = ref(1)

function activeTableSelector(): string {
  // 根据当前 tab 选择对应的表格 CSS class
  return activeTab.value === 'sku' ? '.sku-table' : '.ship-table'
}

function updateHScrollWidth() {
  const sel = activeTableSelector()
  const body = document.querySelector(`${sel} .el-table__body`) as HTMLElement
  if (body) hScrollWidth.value = body.scrollWidth + 80
}

function onFixedBarScroll() {
  const sel = activeTableSelector()
  const el = document.querySelector(`${sel} .el-table__body-wrapper .el-scrollbar__wrap`) as HTMLElement
  if (el && hScrollBar.value) el.scrollLeft = hScrollBar.value.scrollLeft
}

function syncBarFromTable() {
  if (!hScrollBar.value) return
  const sel = activeTableSelector()
  const el = document.querySelector(`${sel} .el-table__body-wrapper .el-scrollbar__wrap`) as HTMLElement
  if (el) hScrollBar.value.scrollLeft = el.scrollLeft
}

function bindTableScroll() {
  // 两张表都尝试绑定（同时只有一个可见）
  for (const sel of ['.sku-table', '.ship-table']) {
    const el = document.querySelector(`${sel} .el-table__body-wrapper .el-scrollbar__wrap`) as HTMLElement
    if (el) {
      el.removeEventListener('scroll', syncBarFromTable)
      el.addEventListener('scroll', syncBarFromTable)
    }
  }
  updateHScrollWidth()
}

// 分组切换 / tab 切换后重新绑定
watch([expandedSkuGroups, expandedShipGroups, activeTab], () => {
  nextTick(() => {
    bindTableScroll()
    updateHScrollWidth()
  })
}, { deep: true })

onMounted(() => {
  document.title = 'OZON 直发信息'
  sku.fetchAll()
  shipment.fetchAll()  // SKU 表销售负责人需要直发数据
  nextTick(bindTableScroll)
})

onUnmounted(() => {
  for (const sel of ['.sku-table', '.ship-table']) {
    const el = document.querySelector(`${sel} .el-table__body-wrapper .el-scrollbar__wrap`) as HTMLElement
    if (el) el.removeEventListener('scroll', syncBarFromTable)
  }
})
</script>
