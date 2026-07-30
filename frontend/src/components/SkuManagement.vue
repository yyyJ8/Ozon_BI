<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Check, Close,
} from '@element-plus/icons-vue'
import type { SkuManagementRow, SkuManagementUpdate } from '@/types'
import { getSkuManagement, batchUpdateSkuManagement } from '@/api'
import { useStore } from '@/composables/useStore'

const { selectedStoreId } = useStore()

// ── 列定义 ──────────────────────────────────────────────

interface ColDef {
  key: string
  label: string
  width?: number
  minWidth?: number
  fixed?: 'left' | 'right'
  editable?: boolean
  type?: 'text' | 'number' | 'int' | 'pct' | 'price'
  sortable?: boolean
  group?: string
}

const COLUMNS: ColDef[] = [
  // -- 固定左侧：只读 --
  { key: 'primary_image', label: '图片', width: 55, fixed: 'left', type: 'image' },
  { key: 'sku_id', label: 'SKU', width: 100, fixed: 'left', sortable: true },
  { key: 'offer_id', label: '货号', width: 160, fixed: 'left' },
  { key: 'name', label: '商品名称', minWidth: 180, fixed: 'left' },
  { key: 'price', label: '售价 ₽', width: 90, fixed: 'left', type: 'price', sortable: true },
  { key: 'stock_present', label: '库存', width: 65, fixed: 'left', sortable: true },

  // -- 基本信息 --
  { key: 'main_sku', label: '主SKU', width: 75, group: '基本信息', editable: true, type: 'text' },
  { key: 'specification', label: '规格', width: 170, group: '基本信息', editable: true, type: 'text' },
  { key: 'sales_manager', label: '负责人', width: 70, group: '基本信息', editable: true, type: 'text' },
  { key: 'listed_stores', label: '店铺', width: 55, group: '基本信息', editable: true, type: 'text' },
  { key: 'product_status', label: '状态', width: 70, group: '基本信息', editable: true, type: 'text' },
  { key: 'key_notes', label: '备注', width: 160, group: '基本信息', editable: true, type: 'text' },
  { key: 'source_url_1688', label: '1688链接', width: 200, group: '基本信息', editable: true, type: 'text' },

  // -- 尺寸重量 --
  { key: 'length_cm', label: '长', width: 55, group: '尺寸', editable: true, type: 'number' },
  { key: 'width_cm', label: '宽', width: 55, group: '尺寸', editable: true, type: 'number' },
  { key: 'height_cm', label: '高', width: 55, group: '尺寸', editable: true, type: 'number' },
  { key: 'actual_weight_kg', label: '实重 kg', width: 75, group: '尺寸', editable: true, type: 'number' },
  { key: 'volume_cbm', label: '体积 m³', width: 75, group: '尺寸', editable: true, type: 'number' },
  { key: 'density', label: '密度', width: 65, group: '尺寸', editable: true, type: 'number' },

  // -- 包装 --
  { key: 'first_leg_unit_price', label: '头程单价', width: 80, group: '包装', editable: true, type: 'number' },
  { key: 'units_per_carton', label: '装箱数', width: 65, group: '包装', editable: true, type: 'int' },
  { key: 'carton_length_cm', label: '外箱长', width: 70, group: '包装', editable: true, type: 'number' },
  { key: 'carton_width_cm', label: '外箱宽', width: 70, group: '包装', editable: true, type: 'number' },
  { key: 'carton_height_cm', label: '外箱高', width: 70, group: '包装', editable: true, type: 'number' },
  { key: 'gross_weight_kg', label: '毛重', width: 65, group: '包装', editable: true, type: 'number' },
  { key: 'volume_liters', label: '升', width: 55, group: '包装', editable: true, type: 'number' },

  // -- 成本RMB --
  { key: 'purchase_cost_rmb', label: '采购成本 ¥', width: 95, group: '成本', editable: true, type: 'number' },
  { key: 'purchase_cost_pct', label: '采购占比%', width: 85, group: '成本', editable: true, type: 'pct' },
  { key: 'warehousing_fee_rmb', label: '入库费 ¥', width: 80, group: '成本', editable: true, type: 'number' },
  { key: 'fbo_delivery_fee_rmb', label: '送仓费 ¥', width: 80, group: '成本', editable: true, type: 'number' },
  { key: 'first_leg_cost_rmb', label: '头程费 ¥', width: 85, group: '成本', editable: true, type: 'number' },
  { key: 'first_leg_pct', label: '头程占比%', width: 85, group: '成本', editable: true, type: 'pct' },
  { key: 'product_cost_rmb', label: '产品成本 ¥', width: 95, group: '成本', editable: true, type: 'number' },

  // -- 平台费用 --
  { key: 'acquiring_fee_pct', label: '收单%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'fbo_commission_pct', label: '佣金%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'logistics_rub', label: '物流 ₽', width: 80, group: '费用', editable: true, type: 'number' },
  { key: 'delivery_pickup_rub', label: '配送 ₽', width: 80, group: '费用', editable: true, type: 'number' },
  { key: 'last_mile_pct', label: '尾程%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'advertising_rate_pct', label: '广告%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'return_rate_pct', label: '退货%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'tax_and_fee_pct', label: '税费%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'risk_reserve_rub', label: '风险金 ₽', width: 85, group: '费用', editable: true, type: 'number' },

  // -- 财务 --
  { key: 'exchange_rate', label: '汇率', width: 65, group: '财务', editable: true, type: 'number' },
  { key: 'green_price_rub', label: '绿标价 ₽', width: 90, group: '财务', editable: true, type: 'number' },
  { key: 'discount_pct', label: '折扣%', width: 65, group: '财务', editable: true, type: 'pct' },
  { key: 'platform_payout_rub', label: '平台打款 ₽', width: 100, group: '财务', editable: true, type: 'number' },
  { key: 'actual_payout_rub', label: '实际回款 ₽', width: 100, group: '财务', editable: true, type: 'number' },
  { key: 'profit_rmb', label: '利润 ¥', width: 85, group: '财务', editable: true, type: 'number' },
  { key: 'profit_rub', label: '利润 ₽', width: 85, group: '财务', editable: true, type: 'number' },
  { key: 'profit_margin_pct', label: '利润率%', width: 75, group: '财务', editable: true, type: 'pct' },

  // -- 竞品 --
  { key: 'competitor_1', label: '对标1', width: 120, group: '竞品', editable: true, type: 'text' },
  { key: 'competitor_2', label: '对标2', width: 120, group: '竞品', editable: true, type: 'text' },
  { key: 'competitor_sales', label: '竞品销量', width: 80, group: '竞品', editable: true, type: 'int' },
]

// -- 分组信息（用于表头合并提示）--
const groups = computed(() => {
  const seen = new Map<string, { label: string; start: number; end: number }>()
  COLUMNS.forEach((col, i) => {
    if (col.group) {
      if (seen.has(col.group)) {
        seen.get(col.group)!.end = i
      } else {
        seen.set(col.group, { label: col.group, start: i, end: i })
      }
    }
  })
  return Array.from(seen.values())
})

// ── 数据状态 ──────────────────────────────────────────────

const rows = ref<SkuManagementRow[]>([])
const loading = ref(false)
const searchText = ref('')

// 编辑状态
const editingCell = ref<string | null>(null) // `${sku_id}_${key}`
const editValue = ref<string>('')
const dirtyMap = ref<Record<number, Record<string, any>>>({}) // sku_id → partial fields

const dirtyCount = computed(() => Object.keys(dirtyMap.value).length)

// 筛选后的行
const filteredRows = computed(() => {
  if (!searchText.value) return rows.value
  const s = searchText.value.toLowerCase()
  return rows.value.filter(r =>
    String(r.sku_id).includes(s) ||
    (r.offer_id || '').toLowerCase().includes(s) ||
    (r.name || '').toLowerCase().includes(s) ||
    (r.main_sku || '').toLowerCase().includes(s)
  )
})

// ── 数据加载 ──────────────────────────────────────────────

async function fetchData() {
  loading.value = true
  try {
    rows.value = await getSkuManagement(selectedStoreId.value)
    dirtyMap.value = {}
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.message || '未知'))
  } finally {
    loading.value = false
  }
}

// ── 单元格编辑 ────────────────────────────────────────────

function cellKey(row: SkuManagementRow, key: string) {
  return `${row.sku_id}_${key}`
}

function isEditing(row: SkuManagementRow, key: string) {
  return editingCell.value === cellKey(row, key)
}

function isDirty(row: SkuManagementRow, key: string) {
  return dirtyMap.value[row.sku_id] && key in dirtyMap.value[row.sku_id]
}

function getDisplayValue(row: SkuManagementRow, col: ColDef): string {
  const v = (row as any)[col.key]
  if (v === null || v === undefined) return ''
  if (col.type === 'price') return '₽ ' + Number(v).toLocaleString('ru-RU')
  if (col.type === 'pct') return Number(v).toFixed(1) + '%'
  if (col.type === 'number') return Number(v).toLocaleString('ru-RU', { maximumFractionDigits: 2 })
  if (col.type === 'int') return Number(v).toLocaleString('ru-RU')
  return String(v)
}

function startEdit(row: SkuManagementRow, col: ColDef, event: MouseEvent) {
  event.stopPropagation()
  const ck = cellKey(row, col.key)
  editingCell.value = ck
  const v = (row as any)[col.key]
  editValue.value = v !== null && v !== undefined ? String(v) : ''
  // 下一帧聚焦输入框
  requestAnimationFrame(() => {
    const input = document.querySelector(`[data-cell="${ck}"] input`) as HTMLInputElement
    input?.focus()
    input?.select()
  })
}

function commitEdit(row: SkuManagementRow, col: ColDef) {
  if (editingCell.value === null) return
  const raw = editValue.value.trim()
  const original = (row as any)[col.key]

  let newValue: any = raw === '' ? null : raw

  if (raw !== '') {
    if (col.type === 'number' || col.type === 'pct' || col.type === 'price') {
      const n = parseFloat(raw.replace(',', '.'))
      if (isNaN(n)) { cancelEdit(); return }
      newValue = n
    } else if (col.type === 'int') {
      const n = parseInt(raw, 10)
      if (isNaN(n)) { cancelEdit(); return }
      newValue = n
    }
  }

  // 值没变就不标记
  const origStr = original !== null && original !== undefined ? String(original) : ''
  if (String(newValue ?? '') === origStr) {
    cancelEdit()
    return
  }

  // 标记 dirty
  if (!dirtyMap.value[row.sku_id]) {
    dirtyMap.value[row.sku_id] = {}
  }
  dirtyMap.value[row.sku_id][col.key] = newValue

  // 乐观更新本地数据
  ;(row as any)[col.key] = newValue

  editingCell.value = null
}

function cancelEdit() {
  editingCell.value = null
}

function onEditKeydown(e: KeyboardEvent, row: SkuManagementRow, col: ColDef) {
  if (e.key === 'Enter') {
    e.preventDefault()
    commitEdit(row, col)
  } else if (e.key === 'Escape') {
    cancelEdit()
  } else if (e.key === 'Tab') {
    e.preventDefault()
    commitEdit(row, col)
    // 聚焦下一个可编辑单元格
    const currentIdx = COLUMNS.findIndex(c => c.key === col.key)
    for (let i = currentIdx + 1; i < COLUMNS.length; i++) {
      if (COLUMNS[i].editable) {
        const nextCol = COLUMNS[i]
        const nextCk = cellKey(row, nextCol.key)
        editingCell.value = nextCk
        editValue.value = (row as any)[nextCol.key] !== null ? String((row as any)[nextCol.key]) : ''
        requestAnimationFrame(() => {
          const input = document.querySelector(`[data-cell="${nextCk}"] input`) as HTMLInputElement
          input?.focus()
          input?.select()
        })
        break
      }
    }
  }
}

// ── 保存 ──────────────────────────────────────────────────

const saving = ref(false)

async function saveAll() {
  if (dirtyCount.value === 0) {
    ElMessage.info('没有需要保存的修改')
    return
  }

  saving.value = true
  try {
    const items: SkuManagementUpdate[] = Object.entries(dirtyMap.value).map(([skuId, fields]) => ({
      sku_id: Number(skuId),
      ...fields,
    }))

    rows.value = await batchUpdateSkuManagement(items, selectedStoreId.value)
    dirtyMap.value = {}
    ElMessage.success(`已保存 ${items.length} 个 SKU 的修改`)
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || '未知'))
  } finally {
    saving.value = false
  }
}

function discardAll() {
  if (dirtyCount.value === 0) return
  ElMessageBox.confirm(`丢弃 ${dirtyCount.value} 个 SKU 的未保存修改？`, '确认', {
    confirmButtonText: '丢弃',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(() => {
    fetchData()
  }).catch(() => {})
}

// ── 生命周期 ──────────────────────────────────────────────

onMounted(fetchData)
watch(selectedStoreId, fetchData)
</script>

<template>
  <div v-loading="loading || saving" style="min-height: 400px;">
    <!-- 顶部工具栏 -->
    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; gap: 12px;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-input
          v-model="searchText"
          placeholder="搜索 SKU / 货号 / 名称..."
          clearable
          size="small"
          style="width: 220px;"
          :prefix-icon="Search"
        />
        <el-tag type="info" size="small">{{ filteredRows.length }} 个 SKU</el-tag>
      </div>
      <div style="display: flex; align-items: center; gap: 8px;">
        <el-button
          v-if="dirtyCount > 0"
          size="small"
          @click="discardAll"
        >
          <el-icon><Close /></el-icon>
          丢弃 ({{ dirtyCount }})
        </el-button>
        <el-button
          type="primary"
          size="small"
          :disabled="dirtyCount === 0"
          @click="saveAll"
        >
          <el-icon><Check /></el-icon>
          保存修改
          <el-tag v-if="dirtyCount > 0" size="small" effect="dark" type="danger" style="margin-left: 6px;">
            {{ dirtyCount }}
          </el-tag>
        </el-button>
        <el-button size="small" @click="fetchData" :icon="Refresh">刷新</el-button>
      </div>
    </div>

    <!-- 分组标签提示 -->
    <div style="margin-bottom: 8px; display: flex; gap: 4px; flex-wrap: wrap;">
      <el-tag v-for="g in groups" :key="g.label" size="small" effect="plain" type="info">
        {{ g.label }}
      </el-tag>
    </div>

    <!-- 数据表格 -->
    <el-table
      :data="filteredRows"
      stripe
      size="small"
      style="width: 100%"
      max-height="calc(100vh - 280px)"
      border
      :default-sort="{ prop: 'sku_id', order: 'ascending' }"
      @cell-click="() => {}"
    >
      <!-- 图片列 -->
      <el-table-column
        key="primary_image"
        label="图片"
        width="55"
        fixed="left"
      >
        <template #default="{ row }">
          <el-image
            v-if="row.primary_image"
            :src="row.primary_image"
            style="width: 32px; height: 32px; border-radius: 4px;"
            fit="cover"
            lazy
          >
            <template #error>
              <div style="width: 32px; height: 32px; background: #f5f7fa; border-radius: 4px;" />
            </template>
          </el-image>
          <div v-else style="width: 32px; height: 32px; background: #f5f7fa; border-radius: 4px;" />
        </template>
      </el-table-column>

      <!-- SKU -->
      <el-table-column
        key="sku_id"
        prop="sku_id"
        label="SKU"
        width="100"
        fixed="left"
        sortable
      >
        <template #default="{ row }">
          <span style="font-family: monospace; font-size: 12px;">{{ row.sku_id }}</span>
        </template>
      </el-table-column>

      <!-- 货号 -->
      <el-table-column
        key="offer_id"
        prop="offer_id"
        label="货号"
        width="160"
        fixed="left"
        show-overflow-tooltip
      >
        <template #default="{ row }">
          <span style="font-family: monospace; font-size: 12px; color: #909399;">{{ row.offer_id }}</span>
        </template>
      </el-table-column>

      <!-- 商品名称 -->
      <el-table-column
        key="name"
        prop="name"
        label="商品名称"
        min-width="180"
        fixed="left"
        show-overflow-tooltip
      />

      <!-- 售价 -->
      <el-table-column
        key="price"
        label="售价 ₽"
        width="90"
        fixed="left"
        sortable
        align="right"
      >
        <template #default="{ row }">
          <span style="font-weight: 600; font-size: 13px;">
            {{ row.price ? '₽ ' + row.price.toLocaleString('ru-RU') : '—' }}
          </span>
        </template>
      </el-table-column>

      <!-- 库存 -->
      <el-table-column
        key="stock_present"
        label="库存"
        width="65"
        fixed="left"
        sortable
        align="center"
      >
        <template #default="{ row }">
          <el-tag
            :type="row.stock_present > 10 ? 'success' : row.stock_present > 0 ? 'warning' : 'danger'"
            size="small"
            effect="plain"
          >
            {{ row.stock_present ?? '—' }}
          </el-tag>
        </template>
      </el-table-column>

      <!-- 可编辑列（动态渲染）-->
      <template v-for="col in COLUMNS.filter(c => c.editable)" :key="col.key">
        <el-table-column
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          :sortable="col.sortable"
          :align="col.type === 'text' ? 'left' : 'right'"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <div
              v-if="isEditing(row, col.key)"
              :data-cell="cellKey(row, col.key)"
              style="width: 100%;"
            >
              <el-input
                v-model="editValue"
                size="small"
                style="width: 100%;"
                @blur="commitEdit(row, col)"
                @keydown="onEditKeydown($event, row, col)"
              />
            </div>
            <div
              v-else
              :class="['editable-cell', { 'cell-dirty': isDirty(row, col.key) }]"
              @click="(e: MouseEvent) => startEdit(row, col, e)"
            >
              <span v-if="(row as any)[col.key] !== null && (row as any)[col.key] !== undefined" class="cell-value">
                {{ getDisplayValue(row, col) }}
              </span>
              <span v-else class="cell-null">—</span>
            </div>
          </template>
        </el-table-column>
      </template>
    </el-table>
  </div>
</template>

<style scoped>
.editable-cell {
  min-height: 28px;
  padding: 2px 6px;
  margin: -2px -6px;
  border-radius: 3px;
  cursor: text;
  transition: background 0.15s;
}
.editable-cell:hover {
  background: #ecf5ff;
}
.cell-value {
  font-size: 12px;
}
.cell-null {
  color: #c0c4cc;
  font-size: 12px;
}
.cell-dirty {
  background: #fef0f0 !important;
  border-radius: 3px;
}
.cell-dirty:hover {
  background: #fde2e2 !important;
}
</style>
