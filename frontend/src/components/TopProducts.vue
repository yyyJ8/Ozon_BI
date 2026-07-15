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

    <el-table-column prop="offer_id" label="货号" width="160" sortable>
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

    <el-table-column prop="stock_present" label="库存" width="65" align="right" sortable>
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

    <el-table-column prop="ordered_units" label="下单" width="55" align="right" sortable>
      <template #default="{ row }">
        <span :style="{ color: row.ordered_units > 0 ? '#303133' : '#c0c4cc' }">
          {{ row.ordered_units }}
        </span>
      </template>
    </el-table-column>

    <el-table-column prop="delivered_units" label="送达" width="55" align="right" sortable>
      <template #default="{ row }">
        <span :style="{
          color: row.delivered_units > 0 ? '#409eff' : '#c0c4cc',
          fontWeight: row.delivered_units > 0 ? 600 : 400,
        }">
          {{ row.delivered_units }}
        </span>
      </template>
    </el-table-column>

    <el-table-column prop="returns_units" label="退货" width="55" align="right" sortable>
      <template #default="{ row }">
        <span :style="{ color: row.returns_units > 0 ? '#f56c6c' : '#c0c4cc' }">
          {{ row.returns_units }}
        </span>
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
      label="净利"
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
      width="70"
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
