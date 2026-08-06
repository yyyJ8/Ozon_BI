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
              <el-table
                :data="flatSkuList"
                stripe
                size="small"
                class="sku-table"
                row-key="id"
                :span-method="skuSpanMethod"
                :row-class-name="skuRowClassName"
                max-height="calc(100vh - 250px)"
                style="width:100%;"
              >
                <el-table-column width="40">
                  <template #header>
                    <el-checkbox :model-value="isSkuAllSelected" @change="(v: boolean) => onSkuHeaderCheck(v)" />
                  </template>
                  <template #default="{ row }">
                    <el-checkbox
                      v-if="row._type !== 'group'"
                      :model-value="selectedSkuIds.has(row.id)"
                      @change="(v: boolean) => onSkuRowCheck(row, v)"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="sku" label="SKU" min-width="160">
                  <template #default="{ row }">
                    <div v-if="row._type === 'group'" style="display:flex;align-items:center;gap:8px;padding:2px 0;">
                      <el-checkbox :model-value="isSkuGroupAllSelected(row._groupKey)" @change="(v: boolean) => toggleSkuGroupAll(row._groupKey, v)" />
                      <span @click.stop="toggleSkuGroup(row._groupKey)" style="font-size:12px;cursor:pointer;">{{ expandedSkuGroups.has(row._groupKey) ? '▼' : '▶' }}</span>
                      <span @click.stop="selectSkuGroup(row._groupKey)" style="font-weight:600;cursor:pointer;">{{ row._groupKey }}</span>
                      <el-tag size="small" type="info">{{ row._count }}</el-tag>
                    </div>
                    <span v-else>{{ row.sku }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="product_name" label="产品名称" min-width="180" show-overflow-tooltip />
                <el-table-column prop="supplier" label="供应商" min-width="160" show-overflow-tooltip />
                <el-table-column label="销售负责人" width="110">
                  <template #default="{ row }">
                    <span v-if="row._type !== 'group'">{{ row.sales_manager || skuPrPersonMap.get(row.sku) || '—' }}</span>
                  </template>
                </el-table-column>
                <el-table-column label="标签文件" min-width="200" show-overflow-tooltip>
                  <template #default="{ row }">
                    <template v-if="row._type !== 'group'">
                      <el-button v-if="row.label_file" size="small" type="primary" link @click="openRecordFile('sku', row.sku, row.label_file)">{{ row.label_file }}</el-button>
                      <span v-else style="color:#c0c4cc;">—</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="80">
                  <template #default="{ row }">
                    <el-button v-if="row._type !== 'group'" size="small" @click="openSkuDialog(row)">编辑</el-button>
                  </template>
                </el-table-column>
              </el-table>
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
                placeholder="搜索申购单号 / SKU / 产品名 / 供应商"
                clearable
                style="width: 240px;"
                @clear="shipment.onSearch()"
                @keyup.enter="shipment.onSearch()"
              >
                <template #prefix><el-icon><Search /></el-icon></template>
              </el-input>
              <el-select v-model="shipGroupBy" style="width: 160px;" @change="onShipGroupByChange">
                <el-option label="按收货情况分组" value="receiving_status" />
                <el-option label="按收货上架分组" value="is_received" />
                <el-option label="按物流商分组" value="logistics_provider" />
              </el-select>
              <el-button type="primary" @click="shipment.onSearch()">搜索</el-button>
              <el-button type="success" @click="openShipmentDialog()">新增记录</el-button>
              <el-button v-if="shipSelected.length > 0" type="danger" @click="batchDeleteShipment">删除选中 ({{ shipSelected.length }})</el-button>
              <span style="color: #909399; font-size: 12px; margin-left: auto;">共 {{ shipment.total }} 条</span>
            </div>

            <div v-loading="shipment.loading">
              <el-table
                :data="flatShipmentList"
                stripe
                size="small"
                class="ship-table"
                row-key="id"
                :span-method="shipSpanMethod"
                :row-class-name="shipRowClassName"
                style="width:100%;"
              >
                <el-table-column width="40" fixed="left">
                  <template #header>
                    <el-checkbox :model-value="isShipAllSelected" @change="(v: boolean) => onShipHeaderCheck(v)" />
                  </template>
                  <template #default="{ row }">
                    <el-checkbox
                      v-if="row._type !== 'group'"
                      :model-value="selectedShipIds.has(row.id)"
                      @change="(v: boolean) => onShipRowCheck(row, v)"
                    />
                  </template>
                </el-table-column>
                <el-table-column prop="pr_date" label="申购时间" width="105" fixed="left">
                  <template #default="{ row }">
                    <div v-if="row._type === 'group'" style="display:flex;align-items:center;gap:6px;white-space:nowrap;">
                      <span @click.stop="toggleShipGroup(row._groupKey)" style="font-size:12px;cursor:pointer;">{{ expandedShipGroups.has(row._groupKey) ? '▼' : '▶' }}</span>
                      <span @click.stop="selectShipGroup(row._groupKey)" style="font-weight:600;cursor:pointer;font-size:13px;">{{ row._groupKey }}</span>
                      <span style="color:#909399;font-size:12px;">({{ row._count }})</span>
                    </div>
                    <span v-else>{{ row.pr_date }}</span>
                  </template>
                </el-table-column>
                <el-table-column prop="pr_no" label="申购单号" width="140" show-overflow-tooltip fixed="left" />
                <el-table-column prop="sku" label="SKU" width="160" show-overflow-tooltip fixed="left" />
                <el-table-column prop="pr_person" label="申购人员" width="80" />
                <el-table-column prop="product_cn_name" label="产品中文名" width="130" show-overflow-tooltip />
                <el-table-column prop="previous_aftersales" label="上期售后" width="120" show-overflow-tooltip />
                <el-table-column prop="supplier" label="供应商" width="160" show-overflow-tooltip />
                <el-table-column prop="logistics_provider" label="物流商" width="90" />
                <el-table-column prop="first_leg_tracking" label="头程单号" width="140" show-overflow-tooltip />
                <el-table-column prop="total_qty" label="总数" width="65" align="center" />
                <el-table-column prop="total_boxes" label="总箱数" width="75" align="center" />
                <el-table-column prop="receiving_address" label="收货地址" width="180" show-overflow-tooltip />
                <el-table-column prop="labeling_notes" label="贴标说明" width="150" show-overflow-tooltip />
                <el-table-column label="产品标签" width="110" show-overflow-tooltip>
                  <template #default="{ row }">
                    <template v-if="row._type !== 'group'">
                      <el-button v-if="shipmentProductLabel(row)" size="small" type="primary" link @click="openRecordFile('sku', row.sku, shipmentProductLabel(row)!)">{{ shipmentProductLabel(row) }}</el-button>
                      <span v-else style="color:#c0c4cc;">—</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column label="外箱箱唛" width="110" show-overflow-tooltip>
                  <template #default="{ row }">
                    <template v-if="row._type !== 'group'">
                      <el-button v-if="row.carton_mark" size="small" type="primary" link @click="openRecordFile('shipment', row.sku, row.carton_mark, row.pr_no)">{{ row.carton_mark }}</el-button>
                      <span v-else style="color:#c0c4cc;">—</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column label="入库清单" width="180" show-overflow-tooltip>
                  <template #default="{ row }">
                    <template v-if="row._type !== 'group'">
                      <el-button v-if="row.warehouse_receipt" size="small" type="primary" link @click="openRecordFile('shipment', row.sku, row.warehouse_receipt, row.pr_no)">{{ row.warehouse_receipt }}</el-button>
                      <span v-else style="color:#c0c4cc;">—</span>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column prop="po_no" label="采购单号" width="140" show-overflow-tooltip />
                <el-table-column prop="online_po_no" label="网采单号" width="180" show-overflow-tooltip />
                <el-table-column prop="is_received" label="收货上架" width="90" align="center">
                  <template #default="{ row }">
                    <template v-if="row._type !== 'group'">
                      <el-tag :type="row.is_received === '是' ? 'success' : 'info'" size="small">{{ row.is_received || '—' }}</el-tag>
                    </template>
                  </template>
                </el-table-column>
                <el-table-column prop="ship_date" label="发货时间" width="105" />
                <el-table-column prop="special_notes" label="备注" width="150" show-overflow-tooltip />
                <el-table-column prop="tracking_no" label="物流单号" width="180" show-overflow-tooltip />
                <el-table-column prop="receiving_status" label="收货状态" width="110" show-overflow-tooltip />
                <el-table-column prop="receiving_date" label="收货时间" width="105" />
                <el-table-column label="操作" width="80" fixed="right">
                  <template #default="{ row }">
                    <el-button v-if="row._type !== 'group'" size="small" type="primary" @click="openShipmentDialog(row)">编辑</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

          </el-tab-pane>
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
          <el-input v-model="skuForm.sku" placeholder="SKU 编码" />
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
            <el-form-item label="物流商" required><el-input v-model="shipmentForm.logistics_provider" /></el-form-item>
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
                <el-upload :before-upload="(f: File) => handleFieldFileUpload(f, 'product_label')" :show-file-list="false" :auto-upload="false">
                  <el-button size="small"><el-icon><Upload /></el-icon></el-button>
                </el-upload>
              </div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="外箱箱唛">
              <div style="display:flex;gap:8px;">
                <el-input v-model="shipmentForm.carton_mark" placeholder="文件名或描述" style="flex:1;" />
                <el-upload :before-upload="(f: File) => handleFieldFileUpload(f, 'carton_mark')" :show-file-list="false" :auto-upload="false">
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
                <el-upload :before-upload="(f: File) => handleFieldFileUpload(f, 'warehouse_receipt')" :show-file-list="false" :auto-upload="false">
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
          <el-col :span="8">
            <el-form-item label="物流单号"><el-input v-model="shipmentForm.tracking_no" /></el-form-item>
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
</style>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
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

function skuSpanMethod({ row, columnIndex }: { row: any; rowIndex: number; columnIndex: number }) {
  if (row._type !== 'group') return [1, 1]
  if (columnIndex === 0) return [1, 1]   // selection 列不合并
  if (columnIndex === 1) return [1, 6]   // 分组标题跨越所有数据列
  return [0, 0]
}

function skuRowClassName({ row }: { row: any }) {
  return row._type === 'group' ? 'sku-group-row' : ''
}

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

const uploadFileList = ref<any[]>([])

async function handleSkuFileUpload(file: File) {
  if (!skuForm.sku.trim()) {
    ElMessage.warning('请先填写 SKU')
    return false
  }
  await skuFiles.upload(file, 'sku', skuForm.sku.trim())
  return false
}

async function openRecordFile(sourceTable: string, sku: string, fileName: string, prNo?: string) {
  const fileList = await getDirectFiles(sourceTable, sku, prNo)
  const match = fileList.find(f => f.file_name === fileName)
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
const shipSelected = computed(() => shipment.list.filter(it => selectedShipIds.value.has(it.id)))
const expandedShipGroups = reactive(new Set<string>())

const shipGroupBy = ref('receiving_status')
const isShipAllSelected = computed(() => shipment.list.length > 0 && selectedShipIds.value.size >= shipment.list.length)
function onShipRowCheck(row: any, checked: boolean) {
  if (checked) selectedShipIds.value.add(row.id)
  else selectedShipIds.value.delete(row.id)
  selectedShipIds.value = new Set(selectedShipIds.value)
}

function onShipHeaderCheck(checked: boolean) {
  if (checked) {
    for (const group of shipmentGroups.value) {
      expandedShipGroups.add(group.key)
      for (const item of group.items) selectedShipIds.value.add(item.id)
    }
  } else {
    selectedShipIds.value = new Set()
  }
  selectedShipIds.value = new Set(selectedShipIds.value)
}

const shipmentGroups = computed(() => {
  const groups: Record<string, DirectShipmentItem[]> = {}
  for (const item of shipment.list) {
    const key = ((item as any)[shipGroupBy.value] || '').trim() || '未分组'
    if (!groups[key]) groups[key] = []
    groups[key].push(item)
  }
  return Object.entries(groups).map(([key, items]) => ({ key, items }))
})
// 新数据到达时自动展开所有分组
watch(shipmentGroups, (groups) => {
  for (const g of groups) expandedShipGroups.add(g.key)
})

// 单表数据：分组行 + 展开的数据行
const flatShipmentList = computed(() => {
  const result: any[] = []
  for (const group of shipmentGroups.value) {
    result.push({
      _type: 'group',
      id: `__group__${group.key}`,
      _groupKey: group.key,
      _count: group.items.length,
    })
    if (expandedShipGroups.has(group.key)) {
      for (const item of group.items) {
        result.push({ _type: 'data', _groupKey: group.key, ...item })
      }
    }
  }
  return result
})

// 直发分组勾选：全选 ☑ / 全空 □
function isShipGroupAllSelected(groupKey: string): boolean {
  const group = shipmentGroups.value.find(g => g.key === groupKey)
  if (!group || group.items.length === 0) return false
  return group.items.every(it => selectedShipIds.value.has(it.id))
}
function toggleShipGroupAll(groupKey: string, select: boolean) {
  const group = shipmentGroups.value.find(g => g.key === groupKey)
  if (!group) return
  if (select) group.items.forEach(it => selectedShipIds.value.add(it.id))
  else group.items.forEach(it => selectedShipIds.value.delete(it.id))
  selectedShipIds.value = new Set(selectedShipIds.value)
  // 折叠状态自动展开
  if (!expandedShipGroups.has(groupKey)) expandedShipGroups.add(groupKey)
}

// 点击直发分组标签 → 全选该组
function selectShipGroup(groupKey: string) { toggleShipGroupAll(groupKey, true) }

function shipSpanMethod({ row, columnIndex }: { row: any; rowIndex: number; columnIndex: number }) {
  if (row._type !== 'group') return [1, 1]
  if (columnIndex === 0) return [1, 1]   // selection 列
  if (columnIndex === 1) return [1, 1]   // pr_date 列：只占自己的格子，不跨列
  return [1, 1]                           // 其余列：正常渲染（空但有背景色，形成连续灰条）
}

function shipRowClassName({ row }: { row: any }) {
  return row._type === 'group' ? 'ship-group-row' : ''
}

function toggleShipGroup(key: string) {
  if (expandedShipGroups.has(key)) expandedShipGroups.delete(key)
  else expandedShipGroups.add(key)
}

function onShipGroupByChange() { expandedShipGroups.clear(); shipment.fetchAll() }

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
  ship_date: null, special_notes: '', tracking_no: '',
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

async function handleFieldFileUpload(file: File, fieldName: string) {
  if (!file) return
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
