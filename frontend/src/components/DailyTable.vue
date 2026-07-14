<script setup lang="ts">
import type { SummaryRow } from '@/types'

defineProps<{
  rows: SummaryRow[]
}>()
</script>

<template>
  <el-table
    :data="rows"
    stripe
    style="width: 100%"
    max-height="480"
    size="small"
    :default-sort="{ prop: 'date', order: 'descending' }"
  >
    <el-table-column prop="date" label="日期" width="110" sortable />

    <el-table-column prop="sku_id" label="SKU" width="130" sortable>
      <template #default="{ row }">
        <span style="font-family: monospace; font-size: 12px;">{{ row.sku_id }}</span>
      </template>
    </el-table-column>

    <el-table-column label="图片" width="66" align="center">
      <template #default="{ row }">
        <el-image
          v-if="row.primary_image"
          :src="row.primary_image"
          style="width: 40px; height: 40px; border-radius: 4px;"
          fit="cover"
          lazy
        >
          <template #error>
            <div style="width: 40px; height: 40px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #c0c4cc;">无</div>
          </template>
        </el-image>
        <div v-else style="width: 40px; height: 40px; background: #f5f7fa; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 12px; color: #c0c4cc;">无</div>
      </template>
    </el-table-column>

    <el-table-column prop="offer_id" label="货号" width="140" sortable>
      <template #default="{ row }">
        <span style="font-family: monospace; font-size: 12px; color: #909399;">
          {{ row.offer_id }}
        </span>
      </template>
    </el-table-column>

    <el-table-column
      prop="name"
      label="商品名称"
      min-width="160"
      show-overflow-tooltip
    />

    <el-table-column
      prop="stock_present"
      label="库存"
      width="70"
      align="right"
      sortable
    >
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

    <el-table-column
      prop="ordered_units"
      label="销量"
      width="70"
      align="right"
      sortable
    />
    <el-table-column prop="revenue" label="收入" width="110" align="right" sortable>
      <template #default="{ row }">
        ₽
        {{
          row.revenue.toLocaleString('ru-RU', { maximumFractionDigits: 2 })
        }}
      </template>
    </el-table-column>
    <el-table-column
      prop="commissions"
      label="佣金"
      width="100"
      align="right"
      sortable
    >
      <template #default="{ row }">
        <span v-if="row.commissions !== 0">
          {{ row.commissions.toLocaleString('ru-RU', { maximumFractionDigits: 2 }) }}
        </span>
        <span v-else>—</span>
      </template>
    </el-table-column>
    <el-table-column
      prop="logistics_costs"
      label="物流"
      width="100"
      align="right"
      sortable
    >
      <template #default="{ row }">
        <span v-if="row.logistics_costs !== 0">
          {{ row.logistics_costs.toLocaleString('ru-RU', { maximumFractionDigits: 2 }) }}
        </span>
        <span v-else>—</span>
      </template>
    </el-table-column>
    <el-table-column
      prop="net_profit"
      label="净利润"
      width="120"
      align="right"
      sortable
    >
      <template #default="{ row }">
        <span
          :style="{
            color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c',
            fontWeight: 600,
          }"
        >
          ₽
          {{
            row.net_profit.toLocaleString('ru-RU', {
              maximumFractionDigits: 2,
            })
          }}
        </span>
      </template>
    </el-table-column>
    <el-table-column
      prop="profit_margin"
      label="利润率"
      width="90"
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
    <el-table-column prop="data_quality" label="质量" width="80" align="center">
      <template #default="{ row }">
        <el-tag
          :type="row.data_quality === 'complete' ? 'success' : 'warning'"
          size="small"
        >
          {{ row.data_quality === 'complete' ? '完整' : '部分' }}
        </el-tag>
      </template>
    </el-table-column>
  </el-table>
</template>
