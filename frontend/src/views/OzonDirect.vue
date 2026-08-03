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
              <el-button type="primary" @click="sku.onSearch()">搜索</el-button>
              <el-button type="success" @click="openSkuDialog()">新增 SKU</el-button>
            </div>

            <el-table :data="sku.list" stripe size="small" max-height="calc(100vh - 260px)" v-loading="sku.loading">
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="sku" label="SKU" min-width="160" />
              <el-table-column prop="product_name" label="产品名称" min-width="180" show-overflow-tooltip />
              <el-table-column prop="supplier" label="供应商" min-width="160" show-overflow-tooltip />
              <el-table-column prop="store_name" label="店铺" width="80" />
              <el-table-column label="标签文件" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-button
                    v-if="row.label_file"
                    size="small"
                    type="primary"
                    link
                    @click="openRecordFile('sku', row.id, row.label_file)"
                  >{{ row.label_file }}</el-button>
                  <span v-else style="color: #c0c4cc;">—</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" @click="openSkuDialog(row)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>

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
                placeholder="搜索申购单号 / SKU / 产品名 / 供应商"
                clearable
                style="width: 240px;"
                @clear="shipment.onSearch()"
                @keyup.enter="shipment.onSearch()"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-select v-model="shipment.receivingStatus" placeholder="收货情况" clearable style="width: 120px;" @change="shipment.fetchAll()">
                <el-option label="已收到" value="已收到" />
                <el-option label="异常" value="异常" />
                <el-option label="已取消" value="已取消" />
              </el-select>
              <el-button type="primary" @click="shipment.onSearch()">搜索</el-button>
              <el-button type="success" @click="openShipmentDialog()">新增记录</el-button>
              <span style="color: #909399; font-size: 12px; margin-left: auto;">共 {{ shipment.total }} 条</span>
            </div>

            <el-table :data="shipment.list" stripe size="small" max-height="calc(100vh - 260px)" v-loading="shipment.loading" style="width: 100%;">
              <el-table-column prop="id" label="ID" width="55" fixed="left" />
              <el-table-column prop="pr_no" label="申购单号" min-width="135" fixed="left" />
              <el-table-column prop="sku" label="SKU" min-width="155" fixed="left" show-overflow-tooltip />
              <el-table-column prop="product_cn_name" label="产品中文名" min-width="120" show-overflow-tooltip />
              <el-table-column prop="pr_date" label="申购时间" width="105" />
              <el-table-column prop="pr_person" label="申购人员" width="80" />
              <el-table-column prop="supplier" label="供应商" min-width="150" show-overflow-tooltip />
              <el-table-column prop="po_no" label="采购单号" min-width="130" />
              <el-table-column prop="online_po_no" label="网采单号" min-width="180" show-overflow-tooltip />
              <el-table-column prop="is_received" label="收货上架" width="90" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.is_received === '是' ? 'success' : 'info'" size="small">
                    {{ row.is_received || '—' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="total_qty" label="总数" width="65" align="center" />
              <el-table-column prop="total_boxes" label="总箱数" width="75" align="center" />
              <el-table-column prop="product_label" label="产品标签" min-width="100" show-overflow-tooltip />
              <el-table-column prop="carton_mark" label="外箱箱唛" min-width="100" show-overflow-tooltip />
              <el-table-column label="入库清单" min-width="180" show-overflow-tooltip>
                <template #default="{ row }">
                  <el-button
                    v-if="row.warehouse_receipt"
                    size="small"
                    type="primary"
                    link
                    @click="openRecordFile('shipment', row.id, row.warehouse_receipt)"
                  >{{ row.warehouse_receipt }}</el-button>
                  <span v-else style="color: #c0c4cc;">—</span>
                </template>
              </el-table-column>
              <el-table-column prop="receiving_address" label="收货地址" min-width="180" show-overflow-tooltip />
              <el-table-column prop="labeling_notes" label="贴标发货说明" min-width="150" show-overflow-tooltip />
              <el-table-column prop="logistics_provider" label="物流商" width="85" />
              <el-table-column prop="first_leg_tracking" label="头程单号" min-width="135" show-overflow-tooltip />
              <el-table-column prop="total_boxes_2" label="总箱数." width="75" align="center" />
              <el-table-column prop="length_cm" label="长(cm)" width="75" align="center" />
              <el-table-column prop="width_cm" label="宽(cm)" width="75" align="center" />
              <el-table-column prop="height_cm" label="高(cm)" width="75" align="center" />
              <el-table-column prop="gross_weight" label="毛重(kg)" width="85" align="center" />
              <el-table-column prop="total_cbm" label="总方数" width="80" align="center" />
              <el-table-column prop="density" label="密度" width="70" align="center" />
              <el-table-column prop="plan_no" label="计划单号" min-width="130" />
              <el-table-column prop="ship_date" label="发货时间" width="105" />
              <el-table-column prop="tracking_no" label="物流单号" min-width="180" show-overflow-tooltip />
              <el-table-column prop="logistics_company" label="物流公司" min-width="120" show-overflow-tooltip />
              <el-table-column prop="special_notes" label="特殊情况备注" min-width="140" show-overflow-tooltip />
              <el-table-column prop="previous_aftersales" label="上期售后情况" min-width="120" show-overflow-tooltip />
              <el-table-column prop="qty_total_2" label="总数." width="65" align="center" />
              <el-table-column prop="receiving_status" label="货物收货情况" min-width="120" show-overflow-tooltip />
              <el-table-column prop="shipment_no" label="货件单号" min-width="135" />
              <el-table-column label="操作" width="80" fixed="right">
                <template #default="{ row }">
                  <el-button size="small" type="primary" @click="openShipmentDialog(row)">编辑</el-button>
                </template>
              </el-table-column>
            </el-table>

          </el-tab-pane>
        </el-tabs>
      </el-card>
    </el-main>

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
          <el-input v-model="skuForm.sku" placeholder="SKU 编码" />
        </el-form-item>
        <el-form-item label="产品名称">
          <el-input v-model="skuForm.product_name" placeholder="产品名称" />
        </el-form-item>
        <el-form-item label="供应商">
          <el-input v-model="skuForm.supplier" placeholder="供应商" />
        </el-form-item>
        <el-form-item label="店铺">
          <el-input v-model="skuForm.store_name" placeholder="店铺" />
        </el-form-item>
        <el-form-item label="标签文件">
          <el-input v-model="skuForm.label_file" placeholder="标签文件名" />
        </el-form-item>
        <el-form-item label="附件">
          <el-upload
            :file-list="uploadFileList"
            :before-upload="handleSkuFileUpload"
            :show-file-list="true"
            multiple
            :auto-upload="false"
          >
            <el-button size="small" type="primary">
              <el-icon><Upload /></el-icon> 上传文件
            </el-button>
            <template #tip>
              <div style="font-size: 12px; color: #909399;">支持 PDF、Excel、图片</div>
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
        <el-divider content-position="left">申购信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="申购单号"><el-input v-model="shipmentForm.pr_no" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="SKU"><el-input v-model="shipmentForm.sku" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="产品中文名"><el-input v-model="shipmentForm.product_cn_name" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="申购时间"><el-date-picker v-model="shipmentForm.pr_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="申购人员"><el-input v-model="shipmentForm.pr_person" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="供应商"><el-input v-model="shipmentForm.supplier" /></el-form-item>
          </el-col>
        </el-row>
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

        <el-divider content-position="left">数量/包装</el-divider>
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="总数"><el-input-number v-model="shipmentForm.total_qty" :min="0" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="总箱数"><el-input-number v-model="shipmentForm.total_boxes" :min="0" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="总箱数."><el-input-number v-model="shipmentForm.total_boxes_2" :min="0" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="总数."><el-input-number v-model="shipmentForm.qty_total_2" :min="0" style="width:100%" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="产品标签">
              <div style="display:flex;gap:8px;">
                <el-input v-model="shipmentForm.product_label" placeholder="文件名或描述" style="flex:1;" />
                <el-upload :before-upload="(f) => handleFieldFileUpload(f, 'product_label')" :show-file-list="false" :auto-upload="false">
                  <el-button size="small"><el-icon><Upload /></el-icon></el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="外箱箱唛">
              <div style="display:flex;gap:8px;">
                <el-input v-model="shipmentForm.carton_mark" placeholder="文件名或描述" style="flex:1;" />
                <el-upload :before-upload="(f) => handleFieldFileUpload(f, 'carton_mark')" :show-file-list="false" :auto-upload="false">
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
                <el-upload :before-upload="(f) => handleFieldFileUpload(f, 'warehouse_receipt')" :show-file-list="false" :auto-upload="false">
                  <el-button size="small"><el-icon><Upload /></el-icon></el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">收货/发货说明</el-divider>
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="收货地址"><el-input v-model="shipmentForm.receiving_address" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="24">
            <el-form-item label="贴标发货说明"><el-input v-model="shipmentForm.labeling_notes" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">箱规</el-divider>
        <el-row :gutter="12">
          <el-col :span="6">
            <el-form-item label="长(cm)"><el-input-number v-model="shipmentForm.length_cm" :min="0" :precision="1" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="宽(cm)"><el-input-number v-model="shipmentForm.width_cm" :min="0" :precision="1" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="高(cm)"><el-input-number v-model="shipmentForm.height_cm" :min="0" :precision="1" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="毛重(kg)"><el-input-number v-model="shipmentForm.gross_weight" :min="0" :precision="2" style="width:100%" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="总方数"><el-input-number v-model="shipmentForm.total_cbm" :min="0" :precision="4" style="width:100%" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="密度"><el-input-number v-model="shipmentForm.density" :min="0" :precision="2" style="width:100%" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">物流跟踪</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="物流商"><el-input v-model="shipmentForm.logistics_provider" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="头程单号"><el-input v-model="shipmentForm.first_leg_tracking" /></el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="物流公司"><el-input v-model="shipmentForm.logistics_company" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="物流单号"><el-input v-model="shipmentForm.tracking_no" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="计划单号"><el-input v-model="shipmentForm.plan_no" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="货件单号"><el-input v-model="shipmentForm.shipment_no" /></el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="发货时间"><el-date-picker v-model="shipmentForm.ship_date" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item>
          </el-col>
          <el-col :span="16">
            <el-form-item label="货物收货情况">
              <el-select v-model="shipmentForm.receiving_status" style="width:100%;">
                <el-option label="已收到" value="已收到" />
                <el-option label="异常" value="异常" />
                <el-option label="已取消" value="已取消" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">备注/售后</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="特殊情况备注"><el-input v-model="shipmentForm.special_notes" type="textarea" :rows="2" /></el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="上期售后情况"><el-input v-model="shipmentForm.previous_aftersales" type="textarea" :rows="2" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">附件</el-divider>
        <el-upload :before-upload="handleShipmentFileUpload" :show-file-list="true" multiple :auto-upload="false">
          <el-button size="small" type="primary"><el-icon><Upload /></el-icon> 上传文件</el-button>
        </el-upload>
        <div v-if="shipmentFiles.files.length > 0" style="margin-top: 8px;">
          <div v-for="f in shipmentFiles.files" :key="f.id" style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <el-button size="small" link type="primary" @click="downloadFile(f.id)">{{ f.file_name }}</el-button>
            <el-button size="small" type="danger" link @click="removeFile(f.id)"><el-icon><Delete /></el-icon></el-button>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="shipmentDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveShipment" :loading="shipmentSaving">保存</el-button>
      </template>
    </el-dialog>

  </el-container>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const editingSku = ref<DirectSkuItem | null>(null)
const skuForm = reactive({
  sku: '', product_name: '', supplier: '', store_name: '', label_file: '',
})
const skuFiles = reactive(useDirectFiles())

function openSkuDialog(row?: DirectSkuItem) {
  if (row) {
    editingSku.value = row
    skuForm.sku = row.sku
    skuForm.product_name = row.product_name || ''
    skuForm.supplier = row.supplier || ''
    skuForm.store_name = row.store_name || ''
    skuForm.label_file = row.label_file || ''
    skuFiles.fetchFiles('sku', row.id)
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
  skuForm.label_file = ''
  skuFiles.files.value = []
}

async function saveSku() {
  if (!skuForm.sku.trim()) {
    ElMessage.warning('SKU 不能为空')
    return
  }
  skuSaving.value = true
  try {
    const body = {
      sku: skuForm.sku.trim(),
      product_name: skuForm.product_name || null,
      supplier: skuForm.supplier || null,
      store_name: skuForm.store_name || null,
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

const uploadFileList = ref<any[]>([])

async function handleSkuFileUpload(file: File) {
  if (!editingSku.value?.id) {
    ElMessage.warning('请先保存记录，再上传文件')
    return false
  }
  await skuFiles.upload(file, 'sku', editingSku.value.id)
  return false
}

async function openRecordFile(sourceTable: string, sourceId: number, fileName: string) {
  // 查询该记录关联的文件，找到文件名匹配的
  const fileList = await getDirectFiles(sourceTable, sourceId)
  const match = fileList.find(f => f.file_name === fileName)
  if (match) {
    window.open(getDirectFileUrl(match.id), '_blank')
  } else {
    // fallback: 文件名不完全匹配时，如果有任何文件就打开第一个
    if (fileList.length > 0) {
      window.open(getDirectFileUrl(fileList[0].id), '_blank')
    } else {
      ElMessage.info('文件未在文件库中找到')
    }
  }
}

// ── Shipment ──
const shipment = reactive(useDirectShipment())
const shipmentDialogVisible = ref(false)
const shipmentSaving = ref(false)
const editingShipment = ref<DirectShipmentItem | null>(null)
const shipmentForm = reactive<Record<string, any>>({
  pr_no: '', sku: '', product_cn_name: '', pr_date: null, pr_person: '',
  supplier: '', po_no: '', online_po_no: '', is_received: null,
  total_qty: null, total_boxes: null, product_label: '', carton_mark: '',
  warehouse_receipt: '', receiving_address: '', labeling_notes: '',
  logistics_provider: '', first_leg_tracking: '', total_boxes_2: null,
  length_cm: null, width_cm: null, height_cm: null,
  gross_weight: null, total_cbm: null, density: null,
  plan_no: '', ship_date: null, tracking_no: '', logistics_company: '',
  special_notes: '', previous_aftersales: '', qty_total_2: null,
  receiving_status: '', shipment_no: '',
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
    shipmentFiles.fetchFiles('shipment', row.id)
  } else {
    editingShipment.value = null
    resetShipmentForm()
  }
  shipmentDialogVisible.value = true
}

function resetShipmentForm() {
  editingShipment.value = null
  Object.keys(shipmentForm).forEach(k => { (shipmentForm as any)[k] = null })
  shipmentFiles.files.value = []
}

async function saveShipment() {
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

async function handleFieldFileUpload(file: File, fieldName: string) {
  if (!file) return
  const srcId = editingShipment.value?.id || 0
  const result = await shipmentFiles.upload(file, 'shipment', srcId)
  if (result) {
    (shipmentForm as any)[fieldName] = result.file_name
  }
  return false
}

async function handleShipmentFileUpload(file: File) {
  if (!editingShipment.value?.id) {
    ElMessage.warning('请先保存记录，再上传文件')
    return false
  }
  await shipmentFiles.upload(file, 'shipment', editingShipment.value.id)
  return false
}

// ── 文件操作 ──
function downloadFile(fileId: number) {
  window.open(getDirectFileUrl(fileId), '_blank')
}

async function removeFile(fileId: number) {
  await ElMessageBox.confirm('确认删除该文件？', '确认', { type: 'warning' })
  const srcTable = activeTab.value === 'sku' ? 'sku' : 'shipment'
  const srcId = activeTab.value === 'sku' ? (editingSku.value?.id || 0) : (editingShipment.value?.id || 0)
  if (srcId > 0) {
    if (activeTab.value === 'sku') {
      await skuFiles.remove(fileId, srcTable, srcId)
    } else {
      await shipmentFiles.remove(fileId, srcTable, srcId)
    }
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

onMounted(() => {
  document.title = 'OZON 直发信息'
  sku.fetchAll()
})
</script>
