<script setup lang="ts">
import type { ProductSummary } from '@/types'

defineProps<{
  products: ProductSummary[]
}>()

const emit = defineEmits<{
  (e: 'row-click', product: ProductSummary): void
}>()

function handleRowClick(row: ProductSummary) {
  emit('row-click', row)
}
</script>

<template>
  <el-table
    :data="products"
    stripe
    style="width: 100%"
    max-height="480"
    size="small"
    :default-sort="{ prop: 'revenue', order: 'descending' }"
    @row-click="handleRowClick"
    highlight-current-row
  >
    <el-table-column type="index" label="#" width="44" />

    <el-table-column prop="sku_id" label="SKU" width="100" sortable>
      <template #default="{ row }">
        <span style="font-family: monospace; font-size: 12px;">{{ row.sku_id }}</span>
      </template>
    </el-table-column>

    <el-table-column prop="offer_id" label="货号" width="200" sortable>
      <template #default="{ row }">
        <span style="font-family: monospace; font-size: 12px; color: #909399; white-space: nowrap;">
          {{ row.offer_id }}
        </span>
      </template>
    </el-table-column>

    <el-table-column label="图片" width="56" align="center">
      <template #default="{ row }">
        <el-image
          v-if="row.primary_image"
          :src="row.primary_image"
          style="width: 36px; height: 36px; border-radius: 4px;"
          fit="cover"
          lazy
        >
          <template #error>
            <div style="width: 36px; height: 36px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #c0c4cc;">无</div>
          </template>
        </el-image>
        <div v-else style="width: 36px; height: 36px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #c0c4cc;">无</div>
      </template>
    </el-table-column>

    <el-table-column
      prop="name"
      label="商品名称"
      min-width="100"
      show-overflow-tooltip
    />

    <el-table-column prop="stock_present" label="现有库存" width="80" align="right" sortable>
      <template #default="{ row }">
        <el-tag
          :type="row.stock_present > 10 ? 'success' : row.stock_present > 0 ? 'warning' : 'danger'"
          size="small"
          effect="plain"
        >
          {{ row.stock_present }}
        </el-tag>
      </template>
    </el-table-column>

    <el-table-column prop="stock_reserved" label="预留" width="70" align="right" sortable>
      <template #default="{ row }">
        <span v-if="row.stock_reserved > 0" style="color: #e6a23c;">{{ row.stock_reserved }}</span>
        <span v-else style="color: #c0c4cc;">0</span>
      </template>
    </el-table-column>

    <el-table-column
      prop="stock_present - stock_reserved"
      label="可用"
      width="70"
      align="right"
      sortable
    >
      <template #default="{ row }">
        <span :style="{ color: row.stock_present - row.stock_reserved > 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
          {{ Math.max(0, row.stock_present - row.stock_reserved) }}
        </span>
      </template>
    </el-table-column>

    <el-table-column
      prop="ordered_units"
      label="销量"
      width="60"
      align="right"
      sortable
    />

    <el-table-column prop="commission_rate" label="佣金率" width="80" align="right" sortable>
      <template #default="{ row }">
        <span v-if="row.commission_rate != null">
          {{ row.commission_rate.toFixed(1) }}%
        </span>
        <span v-else style="color: #c0c4cc;">—</span>
      </template>
    </el-table-column>

    <el-table-column prop="revenue" label="收入" width="110" align="right" sortable>
      <template #default="{ row }">
        ₽
        {{
          row.revenue.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
        }}
      </template>
    </el-table-column>

    <el-table-column
      prop="net_profit"
      label="净利润"
      width="110"
      align="right"
      sortable
    >
      <template #default="{ row }">
        <span :style="{ color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
          ₽
          {{
            row.net_profit.toLocaleString('ru-RU', {
              minimumFractionDigits: 2, maximumFractionDigits: 2,
            })
          }}
        </span>
      </template>
    </el-table-column>

    <el-table-column
      prop="profit_margin"
      label="利润率"
      width="80"
      align="right"
      sortable
    >
      <template #default="{ row }">
        <el-tag
          :type="
            row.profit_margin >= 20
              ? 'success'
              : row.profit_margin >= 0
                ? 'warning'
                : 'danger'
          "
          size="small"
        >
          {{ row.profit_margin.toFixed(1) }}%
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>
