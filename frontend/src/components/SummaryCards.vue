<script setup lang="ts">
import {
  Money,
  Coin,
  TrendCharts,
  ShoppingCart,
  Failed,
  DataAnalysis,
} from '@element-plus/icons-vue'
import type { SummaryStats } from '@/types'

const props = defineProps<{
  stats: SummaryStats
}>()

const totalCosts =
  props.stats.total_commissions +
  props.stats.total_logistics +
  props.stats.total_storage +
  props.stats.total_advertising +
  props.stats.total_other_costs

const cards = [
  {
    label: '总收入',
    value: props.stats.total_revenue,
    prefix: '₽',
    color: '#409eff',
    icon: Money,
    display: props.stats.total_revenue.toLocaleString('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }),
  },
  {
    label: '净利润',
    value: props.stats.total_net_profit,
    prefix: '₽',
    color: props.stats.total_net_profit >= 0 ? '#67c23a' : '#f56c6c',
    icon: Coin,
    display: props.stats.total_net_profit.toLocaleString('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }),
  },
  {
    label: '利润率',
    value: props.stats.avg_profit_margin,
    suffix: '%',
    color: '#e6a23c',
    icon: TrendCharts,
    display: props.stats.avg_profit_margin.toFixed(2) + '%',
  },
  {
    label: '总订单量',
    value: props.stats.total_ordered_units,
    suffix: '件',
    color: '#909399',
    icon: ShoppingCart,
    display: props.stats.total_ordered_units.toLocaleString('ru-RU') + ' 件',
  },
  {
    label: '总费用',
    value: totalCosts,
    prefix: '₽',
    color: '#f56c6c',
    icon: Failed,
    display: '₽ ' + Math.abs(totalCosts).toLocaleString('ru-RU', {
      minimumFractionDigits: 2, maximumFractionDigits: 2,
    }),
  },
  {
    label: '覆盖',
    value: `${props.stats.day_count} 天 / ${props.stats.sku_count} SKU`,
    color: '#409eff',
    icon: DataAnalysis,
    display: `${props.stats.day_count} 天 / ${props.stats.sku_count} SKU`,
  },
]
</script>

<template>
  <div
    style="
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      gap: 16px;
    "
  >
    <el-card
      v-for="card in cards"
      :key="card.label"
      shadow="hover"
      :body-style="{ padding: '16px 20px' }"
    >
      <div style="display: flex; align-items: center; gap: 12px;">
        <div
          :style="{
            width: '44px',
            height: '44px',
            borderRadius: '10px',
            background: card.color + '18',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '20px',
            color: card.color,
          }"
        >
          <el-icon>
            <component :is="card.icon" />
          </el-icon>
        </div>
        <div>
          <div
            style="font-size: 13px; color: #909399; margin-bottom: 2px;"
          >
            {{ card.label }}
          </div>
          <div
            style="font-size: 18px; font-weight: 700; color: #303133;"
          >
            {{ card.display }}
          </div>
        </div>
      </div>
    </el-card>
  </div>
</template>
