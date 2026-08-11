<script setup lang="ts">
import { ref, computed, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Search, Refresh, Edit,
} from '@element-plus/icons-vue'
import type { SkuManagementRow, SkuManagementUpdate } from '@/types'
import { getSkuManagement, batchUpdateSkuManagement } from '@/api'
import { useStore } from '@/composables/useStore'

const { selectedStoreId } = useStore()

// ── 字段分类（与后端 sku_formulas.py 保持一致）─────────────

const INPUT_FIELDS = [
  'main_sku', 'source_url_1688', 'specification', 'sales_manager',
  'listed_stores', 'product_status', 'key_notes',
  'length_cm', 'width_cm', 'height_cm', 'actual_weight_kg',
  'first_leg_unit_price', 'units_per_carton',
  'carton_length_cm', 'carton_width_cm', 'carton_height_cm', 'gross_weight_kg',
  'purchase_cost_rmb', 'purchase_cost_pct',
  'acquiring_fee_pct', 'fbo_commission_pct',
  'delivery_pickup_rub', 'advertising_rate_pct', 'return_rate_pct',
  'product_cost_rmb', 'exchange_rate', 'green_price_rub',
  'competitor_1', 'competitor_2', 'competitor_sales',
]

const COMPUTED_FIELDS = [
  'volume_cbm', 'density', 'volume_liters',
  'warehousing_fee_rmb', 'fbo_delivery_fee_rmb', 'first_leg_cost_rmb',
  'logistics_rub', 'first_leg_pct', 'last_mile_pct', 'discount_pct',
  'platform_payout_rub', 'actual_payout_rub', 'tax_and_fee_pct',
  'risk_reserve_rub', 'profit_rmb', 'profit_rub', 'profit_margin_pct',
  'target_price_3pct', 'target_price_5pct', 'target_price_10pct',
]

const INPUT_FIELDS_SET = new Set(INPUT_FIELDS)

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
  { key: 'length_cm', label: '长 cm', width: 65, group: '尺寸', editable: true, type: 'number' },
  { key: 'width_cm', label: '宽 cm', width: 65, group: '尺寸', editable: true, type: 'number' },
  { key: 'height_cm', label: '高 cm', width: 65, group: '尺寸', editable: true, type: 'number' },
  { key: 'actual_weight_kg', label: '实重 kg', width: 75, group: '尺寸', editable: true, type: 'number' },
  { key: 'volume_cbm', label: '体积 m³', width: 80, group: '尺寸', type: 'number' },
  { key: 'density', label: '密度', width: 70, group: '尺寸', type: 'number' },

  // -- 包装 --
  { key: 'first_leg_unit_price', label: '头程单价', width: 80, group: '包装', editable: true, type: 'number' },
  { key: 'units_per_carton', label: '装箱数', width: 65, group: '包装', editable: true, type: 'int' },
  { key: 'carton_length_cm', label: '外箱长 cm', width: 80, group: '包装', editable: true, type: 'number' },
  { key: 'carton_width_cm', label: '外箱宽 cm', width: 80, group: '包装', editable: true, type: 'number' },
  { key: 'carton_height_cm', label: '外箱高 cm', width: 80, group: '包装', editable: true, type: 'number' },
  { key: 'gross_weight_kg', label: '毛重 kg', width: 75, group: '包装', editable: true, type: 'number' },
  { key: 'volume_liters', label: '升', width: 60, group: '包装', type: 'number' },

  // -- 成本RMB --
  { key: 'purchase_cost_rmb', label: '采购成本 ¥', width: 95, group: '成本', editable: true, type: 'number' },
  { key: 'purchase_cost_pct', label: '采购占比%', width: 85, group: '成本', editable: true, type: 'pct' },
  { key: 'warehousing_fee_rmb', label: '入库费 ¥', width: 85, group: '成本', type: 'number' },
  { key: 'fbo_delivery_fee_rmb', label: '送仓费 ¥', width: 85, group: '成本', type: 'number' },
  { key: 'first_leg_cost_rmb', label: '头程费 ¥', width: 90, group: '成本', type: 'number' },
  { key: 'first_leg_pct', label: '头程占比%', width: 90, group: '成本', type: 'pct' },
  { key: 'product_cost_rmb', label: '产品成本 ¥', width: 100, group: '成本', editable: true, type: 'number' },

  // -- 平台费用 --
  { key: 'acquiring_fee_pct', label: '收单%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'fbo_commission_pct', label: '佣金%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'logistics_rub', label: '物流 ₽', width: 80, group: '费用', type: 'number' },
  { key: 'delivery_pickup_rub', label: '配送 ₽', width: 80, group: '费用', editable: true, type: 'number' },
  { key: 'last_mile_pct', label: '尾程%', width: 70, group: '费用', type: 'pct' },
  { key: 'advertising_rate_pct', label: '广告%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'return_rate_pct', label: '退货%', width: 65, group: '费用', editable: true, type: 'pct' },
  { key: 'tax_and_fee_pct', label: '税费%', width: 70, group: '费用', type: 'pct' },
  { key: 'risk_reserve_rub', label: '风险金 ₽', width: 90, group: '费用', type: 'number' },

  // -- 财务 --
  { key: 'exchange_rate', label: '汇率', width: 65, group: '财务', editable: true, type: 'number' },
  { key: 'green_price_rub', label: '绿标价 ₽', width: 95, group: '财务', editable: true, type: 'number', fixed: 'left' },
  { key: 'discount_pct', label: '折扣%', width: 70, group: '财务', type: 'pct' },
  { key: 'platform_payout_rub', label: '平台打款 ₽', width: 105, group: '财务', type: 'number' },
  { key: 'actual_payout_rub', label: '实际回款 ₽', width: 105, group: '财务', type: 'number' },
  { key: 'profit_rmb', label: '利润 ¥', width: 90, group: '财务', type: 'number' },
  { key: 'profit_rub', label: '利润 ₽', width: 90, group: '财务', type: 'number' },
  { key: 'profit_margin_pct', label: '利润率%', width: 80, group: '财务', type: 'pct' },

  // -- 目标售价 --
  { key: 'target_price_3pct', label: '目标售价 3% ₽', width: 120, group: '目标售价', type: 'number' },
  { key: 'target_price_5pct', label: '目标售价 5% ₽', width: 120, group: '目标售价', type: 'number' },
  { key: 'target_price_10pct', label: '目标售价 10% ₽', width: 120, group: '目标售价', type: 'number' },

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

// ── 编辑弹窗 ──────────────────────────────────────────────

interface EditFieldDef {
  key: string
  label: string
  type?: 'text' | 'number' | 'int' | 'pct'
  span?: number
  _group?: true
  _formulas?: string[]
  _result?: true
}

const DIALOG_FIELDS: EditFieldDef[] = [
  // ── 基本信息（无公式）───────────────────────────────────
  { key: '_g1', label: '基本信息', _group: true },
  { key: 'main_sku', label: '主SKU', type: 'text', span: 1 },
  { key: 'source_url_1688', label: '1688链接', type: 'text', span: 2 },
  { key: 'specification', label: '规格', type: 'text', span: 2 },
  { key: 'sales_manager', label: '负责人', type: 'text', span: 1 },
  { key: 'listed_stores', label: '店铺', type: 'text', span: 1 },
  { key: 'product_status', label: '状态', type: 'text', span: 1 },
  { key: 'key_notes', label: '备注', type: 'text', span: 2 },

  // ── 尺寸重量 ─────────────────────────────────────────────
  { key: '_g2', label: '尺寸重量', _group: true, _formulas: [
    '外箱体积 (m³) = 长 × 宽 × 高 ÷ 1,000,000',
    '密度 = 实重 ÷ 体积',
  ]},
  { key: 'length_cm', label: '外箱长 cm', type: 'number', span: 1 },
  { key: 'width_cm', label: '外箱宽 cm', type: 'number', span: 1 },
  { key: 'height_cm', label: '外箱高 cm', type: 'number', span: 1 },
  { key: 'actual_weight_kg', label: '外箱实重 kg', type: 'number', span: 1 },
  { key: 'volume_cbm', label: '外箱体积 m³', _result: true },
  { key: 'density', label: '密度', _result: true },

  // ── 包装 ─────────────────────────────────────────────────
  { key: '_g3', label: '包装', _group: true, _formulas: [
    '升 = 内盒长 × 内盒宽 × 内盒高 ÷ 1,000',
  ]},
  { key: 'first_leg_unit_price', label: '头程单价', type: 'number', span: 1 },
  { key: 'units_per_carton', label: '装箱数', type: 'int', span: 1 },
  { key: 'carton_length_cm', label: '内盒长 cm', type: 'number', span: 1 },
  { key: 'carton_width_cm', label: '内盒宽 cm', type: 'number', span: 1 },
  { key: 'carton_height_cm', label: '内盒高 cm', type: 'number', span: 1 },
  { key: 'gross_weight_kg', label: '内盒毛重 kg', type: 'number', span: 1 },
  { key: 'volume_liters', label: '升', _result: true },

  // ── 成本 ─────────────────────────────────────────────────
  { key: '_g4', label: '成本', _group: true, _formulas: [
    '入库费 = 实重 × 3 ÷ 装箱数',
    '送仓费 = 阶梯{ <10→5 | ≤20→10 | <40→15 | ≥40→20 }',
    '头程费 = 实重 × 头程单价 × 7 ÷ 装箱数 + 入库费 + 送仓费',
  ]},
  { key: 'purchase_cost_rmb', label: '采购成本 ¥', type: 'number', span: 1 },
  { key: 'purchase_cost_pct', label: '采购占比 %', type: 'pct', span: 1 },
  { key: 'product_cost_rmb', label: '产品成本 ¥', type: 'number', span: 1 },
  { key: 'warehousing_fee_rmb', label: '入库费 ¥', _result: true },
  { key: 'fbo_delivery_fee_rmb', label: '送仓费 ¥', _result: true },
  { key: 'first_leg_cost_rmb', label: '头程费 ¥', _result: true },

  // ── 平台费率 ─────────────────────────────────────────────
  { key: '_g5', label: '平台费率', _group: true, _formulas: [
    '物流 ₽ = 阶梯{ <1→46 | 1~2→56 | 2~3→66 | ≥3→CEILING(升-3)×15+66 }',
  ]},
  { key: 'acquiring_fee_pct', label: '收单 %', type: 'pct', span: 1 },
  { key: 'fbo_commission_pct', label: '佣金 %', type: 'pct', span: 1 },
  { key: 'delivery_pickup_rub', label: '配送至取货点 ₽', type: 'number', span: 1 },
  { key: 'advertising_rate_pct', label: '广告费率 %', type: 'pct', span: 1 },
  { key: 'return_rate_pct', label: '退货率 %', type: 'pct', span: 1 },
  { key: 'logistics_rub', label: '物流 ₽', _result: true },

  // ── 财务（公式链，依赖售价）──────────────────────────────
  { key: '_g6', label: '财务', _group: true, _formulas: [
    '头程占比 = 头程费 × 汇率 ÷ 售价',
    '尾程占比 = (物流 + 配送) ÷ 售价 + 收单',
    '折扣 = 1 - 绿标价 ÷ 售价',
    '平台打款 = 售价 × (1 - 尾程占比 - 广告费率 - 退货率 - 佣金)',
    '实际回款 = 平台打款 - (售价 × 2% + 平台打款 × 8%)',
    '税点+手续费 = (平台打款 - 实际回款) ÷ 售价',
    '风险金 = 售价 × 1%',
    '利润 RMB = (实际回款 - 风险金) ÷ 汇率 - 产品成本',
    '利润 ₽ = 利润 RMB × 汇率',
    '利润率 = 利润 ₽ ÷ 售价',
  ]},
  { key: 'exchange_rate', label: '汇率', type: 'number', span: 1 },
  { key: 'green_price_rub', label: '绿标价格 ₽', type: 'number', span: 1 },
  { key: 'first_leg_pct', label: '头程占比 %', _result: true },
  { key: 'last_mile_pct', label: '尾程占比 %', _result: true },
  { key: 'discount_pct', label: '折扣 %', _result: true },
  { key: 'platform_payout_rub', label: '平台打款 ₽', _result: true },
  { key: 'actual_payout_rub', label: '实际回款 ₽', _result: true },
  { key: 'tax_and_fee_pct', label: '税点+手续费 %', _result: true },
  { key: 'risk_reserve_rub', label: '风险金 ₽', _result: true },
  { key: 'profit_rmb', label: '利润 ¥', _result: true },
  { key: 'profit_rub', label: '利润 ₽', _result: true },
  { key: 'profit_margin_pct', label: '利润率 %', _result: true },

  // ── 竞品（无公式）────────────────────────────────────────
  { key: '_g7', label: '竞品', _group: true },
  { key: 'competitor_1', label: '对标1', type: 'text', span: 1 },
  { key: 'competitor_2', label: '对标2', type: 'text', span: 1 },
  { key: 'competitor_sales', label: '竞品销量', type: 'int', span: 1 },

  // ── 目标售价 ─────────────────────────────────────────────
  { key: '_g8', label: '目标售价', _group: true, _formulas: [
    '利润率 = C₁ - D ÷ 售价  →  目标售价 = D ÷ (C₁ - 目标利润率)',
    'C₁ = 0.92 × (1 - 收单% - 广告% - 退货% - 佣金%) - 0.03',
    'D = 0.92 × (物流₽ + 配送₽) + 产品成本RMB × 汇率',
  ]},
  { key: 'target_price_3pct', label: '3% 利润率售价 ₽', _result: true },
  { key: 'target_price_5pct', label: '5% 利润率售价 ₽', _result: true },
  { key: 'target_price_10pct', label: '10% 利润率售价 ₽', _result: true },
]

const dialogVisible = ref(false)
const editingRow = ref<SkuManagementRow | null>(null)
const formData = reactive<Record<string, any>>({})

function formatResult(val: any, label: string): string {
  if (val === null || val === undefined) return '—'
  const n = Number(val)
  if (isNaN(n)) return String(val)
  if (label.includes('%')) return n.toFixed(2) + '%'
  if (label.includes('₽') || label.includes('¥')) return n.toFixed(2)
  if (label.includes('m³')) return n.toFixed(4)
  return n.toFixed(2)
}

function openEditDialog(row: SkuManagementRow) {
  editingRow.value = row
  // 初始化表单数据（跳过 _group / _result 占位）
  for (const f of DIALOG_FIELDS) {
    if (f._group || f._result) continue
    const v = (row as any)[f.key]
    formData[f.key] = v !== null && v !== undefined ? v : null
  }
  dialogVisible.value = true
}

async function onDialogSave() {
  if (!editingRow.value) return
  const row = editingRow.value
  const dirty: Record<string, any> = {}

  for (const f of DIALOG_FIELDS) {
    if (f._group || f._result) continue
    const newVal = formData[f.key]
    const oldVal = (row as any)[f.key]
    const newStr = newVal !== null && newVal !== undefined ? String(newVal) : ''
    const oldStr = oldVal !== null && oldVal !== undefined ? String(oldVal) : ''
    if (newStr !== oldStr) {
      dirty[f.key] = newVal
    }
  }

  if (Object.keys(dirty).length === 0) {
    dialogVisible.value = false
    return
  }

  dialogVisible.value = false
  saving.value = true
  try {
    const items: SkuManagementUpdate[] = [{
      sku_id: row.sku_id,
      ...dirty,
    }]
    const updated = await batchUpdateSkuManagement(items, selectedStoreId.value)
    // 用服务端返回的整行数据更新本地行（含重算后的计算字段）
    const updatedRow = updated.find(r => r.sku_id === row.sku_id)
    if (updatedRow) {
      const idx = rows.value.findIndex(r => r.sku_id === row.sku_id)
      if (idx >= 0) rows.value[idx] = updatedRow
    } else {
      // fallback：乐观更新输入字段
      for (const [k, v] of Object.entries(dirty)) {
        ;(row as any)[k] = v
      }
    }
    ElMessage.success(`SKU ${row.sku_id} 保存成功`)
  } catch (e: any) {
    ElMessage.error('保存失败: ' + (e.message || '未知'))
  } finally {
    saving.value = false
  }
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
        prop="price"
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

      <!-- 绿标价 -->
      <el-table-column
        key="green_price_rub"
        prop="green_price_rub"
        label="绿标价 ₽"
        width="95"
        fixed="left"
      >
        <template #default="{ row }">
          <span style="font-weight: 600; font-size: 13px;">
            {{ row.green_price_rub ? '₽ ' + row.green_price_rub.toLocaleString('ru-RU') : '—' }}
          </span>
        </template>
      </el-table-column>

      <!-- 库存 -->
      <el-table-column
        key="stock_present"
        prop="stock_present"
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

      <!-- 动态列（固定列之外的所有数据列）-->
      <template v-for="col in COLUMNS.filter(c => !c.fixed)" :key="col.key">
        <el-table-column
          :label="col.label"
          :width="col.width"
          :min-width="col.minWidth"
          :sortable="col.sortable"
          :align="col.type === 'text' ? 'left' : 'right'"
          show-overflow-tooltip
        >
          <template #default="{ row }">
            <!-- 可编辑：支持点击编辑 -->
            <template v-if="col.editable">
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
            <!-- 只读（计算字段）：纯展示 -->
            <template v-else>
              <span v-if="(row as any)[col.key] !== null && (row as any)[col.key] !== undefined"
                    class="cell-value"
                    :style="{ color: COMPUTED_FIELDS.includes(col.key) ? '#909399' : '' }">
                {{ getDisplayValue(row, col) }}
              </span>
              <span v-else class="cell-null">—</span>
            </template>
          </template>
        </el-table-column>
      </template>

      <!-- 操作列 -->
      <el-table-column label="操作" width="70" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" :icon="Edit" @click="openEditDialog(row)">
            编辑
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      width="800px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <div v-if="editingRow" style="display: flex; align-items: center; gap: 12px;">
          <el-image
            v-if="editingRow.primary_image"
            :src="editingRow.primary_image"
            style="width: 40px; height: 40px; border-radius: 6px; flex-shrink: 0;"
            fit="cover"
          >
            <template #error>
              <div style="width: 40px; height: 40px; background: #f5f7fa; border-radius: 6px;" />
            </template>
          </el-image>
          <div style="min-width: 0;">
            <span style="font-weight: 600;">SKU {{ editingRow.sku_id }}</span>
            <span v-if="editingRow.offer_id" style="color: #909399; font-family: monospace; font-size: 13px; margin-left: 8px;">
              {{ editingRow.offer_id }}
            </span>
          </div>
        </div>
      </template>
      <el-form label-width="130px" label-position="right">
        <el-row :gutter="20">
          <template v-for="f in DIALOG_FIELDS" :key="f.key">
            <!-- 分组标题 + 公式 -->
            <el-col v-if="f._group" :span="24">
              <el-divider content-position="left"><b>{{ f.label }}</b></el-divider>
              <template v-if="f._formulas">
                <div v-if="f._formulas.length <= 3" style="font-size: 12px; color: #909399; margin: -8px 0 8px 12px; line-height: 1.8;">
                  <div v-for="(formula, fi) in f._formulas" :key="fi">{{ formula }}</div>
                </div>
                <el-collapse v-else style="margin: -4px 0 8px 12px;">
                  <el-collapse-item :title="`展开公式 (${f._formulas.length} 条)`">
                    <div style="font-size: 12px; color: #909399; line-height: 1.8; padding-left: 8px;">
                      <div v-for="(formula, fi) in f._formulas" :key="fi">{{ formula }}</div>
                    </div>
                  </el-collapse-item>
                </el-collapse>
              </template>
            </el-col>
            <!-- 计算结果（只读） -->
            <el-col v-else-if="f._result" :span="12">
              <el-form-item :label="f.label">
                <el-input
                  :model-value="editingRow ? formatResult((editingRow as any)[f.key], f.label) : '—'"
                  readonly
                  disabled
                  size="small"
                />
              </el-form-item>
            </el-col>
            <!-- 表单字段 -->
            <el-col v-else :span="(f.span || 1) === 2 ? 24 : 12">
              <el-form-item :label="f.label">
                <el-input
                  v-if="f.type === 'text'"
                  v-model="formData[f.key]"
                  :placeholder="f.label"
                />
                <el-input
                  v-else
                  v-model="formData[f.key]"
                  :placeholder="f.label"
                  @input="(v: string) => { if (f.type === 'int') formData[f.key] = v === '' ? null : parseInt(v,10) || null }"
                />
              </el-form-item>
            </el-col>
          </template>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onDialogSave">确定</el-button>
      </template>
    </el-dialog>
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
