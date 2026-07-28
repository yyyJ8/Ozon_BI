<script setup lang="ts">
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import type { ProfitSkuItem, ProfitDailyItem, ProfitOverview } from '@/types'
import { getProfitOverview, getProfitSkuRanking, getProfitSkuDaily } from '@/api'
import { useStore } from '@/composables/useStore'

const props = defineProps<{
  dateRange: [string, string] | null
  activeTab: string
}>()

const { selectedStoreId } = useStore()

const overview = ref<ProfitOverview | null>(null)
const skuItems = ref<ProfitSkuItem[]>([])
const loading = ref(false)

// SKU 下钻
const detailVisible = ref(false)
const detailSku = ref<ProfitSkuItem | null>(null)
const dailyDetail = ref<ProfitDailyItem[]>([])
const detailLoading = ref(false)

async function openSkuDetail(sku: ProfitSkuItem) {
  detailSku.value = sku
  detailVisible.value = true
  detailLoading.value = true
  try {
    if (props.dateRange) {
      dailyDetail.value = await getProfitSkuDaily(
        sku.sku_id,
        props.dateRange[0],
        props.dateRange[1],
        selectedStoreId.value,
      )
    }
  } catch {
    dailyDetail.value = []
  } finally {
    detailLoading.value = false
  }
}

function formatMoney(v: number): string {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatMoneyShort(v: number): string {
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

async function loadData() {
  if (!props.dateRange) return
  loading.value = true
  try {
    const [d1, d2] = props.dateRange
    const [ov, sku] = await Promise.all([
      getProfitOverview(d1, d2, selectedStoreId.value),
      getProfitSkuRanking(d1, d2, selectedStoreId.value),
    ])
    overview.value = ov
    skuItems.value = sku
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '未知错误'
    ElMessage.error('加载利润数据失败: ' + msg)
  } finally {
    loading.value = false
  }
}

watch(() => props.dateRange, () => {
  if (props.dateRange) loadData()
})

watch(() => selectedStoreId.value, () => {
  if (props.dateRange) loadData()
})
</script>

<template>
  <div v-loading="loading">
    <!-- KPI 卡片 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">总收入</div>
            <div style="font-size: 22px; font-weight: 700; color: #409eff; font-family: monospace;">
              ₽ {{ overview ? formatMoneyShort(overview.revenue) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">净利润</div>
            <div
              :style="{
                fontSize: '22px', fontWeight: 700, fontFamily: 'monospace',
                color: overview && overview.net_profit >= 0 ? '#67c23a' : '#f56c6c',
              }"
            >
              ₽ {{ overview ? formatMoneyShort(overview.net_profit) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">利润率</div>
            <el-tag
              v-if="overview"
              :type="overview.profit_margin >= 20 ? 'success' : overview.profit_margin >= 0 ? 'warning' : 'danger'"
              size="large"
              effect="dark"
              style="font-size: 18px; font-weight: 700;"
            >
              {{ overview.profit_margin.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc;">—</span>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">总费用</div>
            <div style="font-size: 22px; font-weight: 700; color: #f56c6c; font-family: monospace;">
              ₽ {{ overview ? formatMoneyShort(overview.total_costs) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 费用明细行 -->
    <el-row v-if="overview" :gutter="12" style="margin-top: 12px;">
      <el-col :span="24">
        <div style="display: flex; gap: 10px; flex-wrap: wrap; align-items: center; padding: 0 4px;">
          <span style="font-size: 12px; color: #909399;">费用构成:</span>
          <el-tag size="small" type="info">佣金 ₽{{ formatMoneyShort(overview.total_commissions) }}</el-tag>
          <el-tag size="small" type="info">物流 ₽{{ formatMoneyShort(overview.total_logistics) }}</el-tag>
          <el-tag size="small" type="info">仓储 ₽{{ formatMoneyShort(overview.total_storage) }}</el-tag>
          <el-tag size="small" type="info">广告 ₽{{ formatMoneyShort(overview.total_advertising) }}</el-tag>
          <el-tag size="small" type="info">推广 ₽{{ formatMoneyShort(overview.total_promotion) }}</el-tag>
          <el-tag size="small" type="info">退货 ₽{{ formatMoneyShort(overview.total_returns) }}</el-tag>
          <el-tag size="small" type="info">其他 ₽{{ formatMoneyShort(overview.total_other) }}</el-tag>
        </div>
      </el-col>
    </el-row>

    <!-- SKU 利润排行表 -->
    <el-card shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-weight: 600;">🏆 SKU 利润排行</span>
          <el-tag type="info" size="small">{{ skuItems.length }} 个商品</el-tag>
        </div>
      </template>
      <el-table
        :data="skuItems"
        stripe
        size="small"
        style="width: 100%"
        max-height="500"
        highlight-current-row
        @row-click="openSkuDetail"
      >
        <el-table-column type="index" width="50" label="#" />
        <el-table-column label="" width="44">
          <template #default="{ row }">
            <el-avatar
              v-if="row.primary_image"
              :src="row.primary_image"
              :size="32"
              shape="square"
            />
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="110">
          <template #default="{ row }">{{ row.sku_id }}</template>
        </el-table-column>
        <el-table-column label="货号" width="140" show-overflow-tooltip>
          <template #default="{ row }">{{ row.offer_id || '—' }}</template>
        </el-table-column>
        <el-table-column label="商品名" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size: 12px">{{ row.name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="销量" width="65" align="right">
          <template #default="{ row }">{{ row.ordered_units }}</template>
        </el-table-column>
        <el-table-column label="库存" width="65" align="right">
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
        <el-table-column label="收入" width="110" align="right" sortable
          :sort-method="(a: ProfitSkuItem, b: ProfitSkuItem) => a.revenue - b.revenue">
          <template #default="{ row }">
            <span :style="{ color: row.revenue > 0 ? '#303133' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.revenue > 0 ? '₽ ' + formatMoney(row.revenue) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="费用" width="100" align="right" sortable
          :sort-method="(a: ProfitSkuItem, b: ProfitSkuItem) => a.costs - b.costs">
          <template #default="{ row }">
            <span :style="{ color: row.costs > 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
              {{ row.costs > 0 ? '₽ ' + formatMoney(row.costs) : '—' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="净利" width="110" align="right" sortable
          :sort-method="(a: ProfitSkuItem, b: ProfitSkuItem) => a.net_profit - b.net_profit">
          <template #default="{ row }">
            <span
              :style="{
                color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c',
                fontWeight: 700, fontFamily: 'monospace',
              }"
            >
              ₽ {{ formatMoney(row.net_profit) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column label="利润率" width="85" align="right" sortable
          :sort-method="(a: ProfitSkuItem, b: ProfitSkuItem) => a.profit_margin - b.profit_margin">
          <template #default="{ row }">
            <el-tag
              v-if="row.revenue > 0"
              :type="row.profit_margin >= 20 ? 'success' : row.profit_margin >= 0 ? 'warning' : 'danger'"
              size="small"
            >
              {{ row.profit_margin.toFixed(1) }}%
            </el-tag>
            <span v-else style="color: #c0c4cc;">—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- SKU 每日明细弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="detailSku ? `SKU ${detailSku.sku_id} / ${detailSku.offer_id || '—'} 每日利润` : 'SKU 明细'"
      width="1000px"
      top="5vh"
      destroy-on-close
    >
      <template v-if="detailSku">
        <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 16px; padding: 12px 16px; background: #f5f7fa; border-radius: 8px;">
          <el-image
            v-if="detailSku.primary_image"
            :src="detailSku.primary_image"
            style="width: 56px; height: 56px; border-radius: 6px; flex-shrink: 0;"
            fit="cover"
          >
            <template #error>
              <div style="width: 56px; height: 56px; background: #e4e7ed; border-radius: 6px;" />
            </template>
          </el-image>
          <div style="flex: 1; display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 6px 16px; font-size: 13px;">
            <div><span style="color: #909399;">SKU</span> {{ detailSku.sku_id }}</div>
            <div><span style="color: #909399;">收入</span> <strong>₽ {{ formatMoney(detailSku.revenue) }}</strong></div>
            <div><span style="color: #909399;">净利润</span>
              <strong :style="{ color: detailSku.net_profit >= 0 ? '#67c23a' : '#f56c6c' }">
                ₽ {{ formatMoney(detailSku.net_profit) }}
              </strong>
            </div>
            <div><span style="color: #909399;">利润率</span>
              <el-tag :type="detailSku.profit_margin >= 20 ? 'success' : detailSku.profit_margin >= 0 ? 'warning' : 'danger'" size="small">
                {{ detailSku.profit_margin.toFixed(1) }}%
              </el-tag>
            </div>
          </div>
        </div>

        <el-table
          :data="dailyDetail"
          stripe size="small"
          style="width: 100%"
          max-height="400"
          v-loading="detailLoading"
          :default-sort="{ prop: 'date', order: 'descending' }"
        >
          <el-table-column prop="date" label="日期" width="100" sortable />
          <el-table-column prop="revenue" label="收入" width="110" align="right" sortable>
            <template #default="{ row }">
              <span style="font-family: monospace;">₽ {{ formatMoney(row.revenue) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="costs" label="费用" width="110" align="right" sortable>
            <template #default="{ row }">
              <span :style="{ color: row.costs > 0 ? '#f56c6c' : '#c0c4cc', fontFamily: 'monospace' }">
                {{ row.costs > 0 ? '₽ ' + formatMoney(row.costs) : '—' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="net_profit" label="净利" width="110" align="right" sortable>
            <template #default="{ row }">
              <span
                :style="{
                  color: row.net_profit >= 0 ? '#67c23a' : '#f56c6c',
                  fontWeight: 600, fontFamily: 'monospace',
                }"
              >
                ₽ {{ formatMoney(row.net_profit) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="profit_margin" label="利润率" width="80" align="right" sortable>
            <template #default="{ row }">
              <el-tag
                v-if="row.revenue > 0"
                :type="row.profit_margin >= 20 ? 'success' : row.profit_margin >= 0 ? 'warning' : 'danger'"
                size="small"
              >
                {{ row.profit_margin.toFixed(1) }}%
              </el-tag>
              <span v-else style="color: #c0c4cc;">—</span>
            </template>
          </el-table-column>
          <el-table-column label="费用明细" min-width="200">
            <template #default="{ row }">
              <div style="display: flex; gap: 4px; flex-wrap: wrap;">
                <el-tag v-if="row.commissions > 0" size="small" type="info">佣金 {{ formatMoneyShort(row.commissions) }}</el-tag>
                <el-tag v-if="row.logistics_costs > 0" size="small" type="info">物流 {{ formatMoneyShort(row.logistics_costs) }}</el-tag>
                <el-tag v-if="row.storage_fees > 0" size="small" type="info">仓储 {{ formatMoneyShort(row.storage_fees) }}</el-tag>
                <el-tag v-if="row.advertising > 0" size="small" type="info">广告 {{ formatMoneyShort(row.advertising) }}</el-tag>
                <el-tag v-if="row.promotion_costs > 0" size="small" type="info">推广 {{ formatMoneyShort(row.promotion_costs) }}</el-tag>
                <el-tag v-if="row.returns_amount > 0" size="small" type="info">退货 {{ formatMoneyShort(row.returns_amount) }}</el-tag>
                <el-tag v-if="row.other_costs > 0" size="small" type="info">其他 {{ formatMoneyShort(row.other_costs) }}</el-tag>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-dialog>
  </div>
</template>
