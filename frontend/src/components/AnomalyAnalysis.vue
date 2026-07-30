<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { WarningFilled } from '@element-plus/icons-vue'
import type { AnomalyItem, AnomalyResponse } from '@/types'
import { getAnomalies } from '@/api'
import { useStore } from '@/composables/useStore'
import { useLocalDateRange } from '@/composables/useLocalDateRange'

const props = defineProps<{
  dateRange: [string, string] | null
  activeTab: string
}>()

const { selectedStoreId } = useStore()
const { localDateRange, periodPreset, showCustomDate, applyPreset, disabledDate } = useLocalDateRange()

const data = ref<AnomalyResponse | null>(null)
const loading = ref(false)

// 筛选
const filterType = ref<string>('')
const filterSeverity = ref<string>('')

const anomalyTypes = computed(() => {
  if (!data.value) return []
  return Object.keys(data.value.summary.by_type)
})

const filteredItems = computed(() => {
  if (!data.value) return []
  return data.value.items.filter(item => {
    if (filterType.value && item.anomaly_type !== filterType.value) return false
    if (filterSeverity.value && item.severity !== filterSeverity.value) return false
    return true
  })
})

// 严重程度颜色
const severityColors: Record<string, string> = {
  critical: 'danger',
  warning: 'warning',
  info: 'info',
}

const severityLabels: Record<string, string> = {
  critical: '严重',
  warning: '预警',
  info: '提示',
}

// 异常类型图标/颜色
const typeColors: Record<string, string> = {
  'SKU退货异常': '#f56c6c',
  'SKU利润率预警': '#e6a23c',
  '广告DRR过高': '#f56c6c',
  '高点击低转化': '#909399',
  'SKU断货风险': '#e6a23c',
  'SKU滞销积压': '#909399',
}

function formatMoney(v: number): string {
  return v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatNumber(v: number): string {
  return v.toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

// 详情弹窗
const detailVisible = ref(false)
const detailItem = ref<AnomalyItem | null>(null)

function openDetail(item: AnomalyItem) {
  detailItem.value = item
  detailVisible.value = true
}

async function loadData() {
  loading.value = true
  try {
    const [d1, d2] = localDateRange.value
    data.value = await getAnomalies(d1, d2, selectedStoreId.value)
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : '未知错误'
    ElMessage.error('加载异常数据失败: ' + msg)
  } finally {
    loading.value = false
  }
}

watch(localDateRange, () => {
  if (props.activeTab === 'anomalies') loadData()
})

watch(() => selectedStoreId.value, () => {
  if (props.activeTab === 'anomalies') loadData()
})

watch(() => props.activeTab, (tab) => {
  if (tab === 'anomalies' && !data.value) loadData()
})
</script>

<template>
  <div v-loading="loading">
    <!-- 独立日期筛选 -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
      <span style="font-size:12px;color:#909399;">📅 时间筛选</span>
      <el-select v-model="periodPreset" style="width:100px" size="small" @change="applyPreset">
        <el-option label="昨天" value="yesterday" />
        <el-option label="近7天" value="7days" />
        <el-option label="近30天" value="30days" />
        <el-option label="全部" value="all" />
        <el-option label="自定义" value="custom" />
      </el-select>
      <el-date-picker
        v-if="showCustomDate"
        v-model="localDateRange"
        type="daterange"
        size="small"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        value-format="YYYY-MM-DD"
        style="width:240px"
        :disabled-date="disabledDate"
      />
    </div>

    <!-- 汇总卡片 -->
    <el-row :gutter="16">
      <!-- 异常总数 -->
      <el-col :span="6">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 13px; margin-bottom: 8px;">异常总数</div>
            <div
              :style="{
                fontSize: '28px', fontWeight: 700,
                color: data && data.summary.total_anomalies > 0 ? '#f56c6c' : '#67c23a',
                fontFamily: 'monospace',
              }"
            >
              {{ data ? data.summary.total_anomalies : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 各异常类型卡片 -->
      <el-col v-for="typeName in anomalyTypes" :key="typeName" :span="6">
        <el-card shadow="hover">
          <div style="text-align: center;">
            <div style="color: #909399; font-size: 12px; margin-bottom: 6px;">
              <el-tag
                :color="typeColors[typeName] || '#909399'"
                size="small"
                effect="dark"
                style="margin-right: 4px;"
              >
                {{ typeName }}
              </el-tag>
            </div>
            <div
              :style="{
                fontSize: '24px', fontWeight: 700,
                color: (data && data.summary.by_type[typeName]) ? typeColors[typeName] || '#f56c6c' : '#c0c4cc',
                fontFamily: 'monospace',
              }"
            >
              {{ data ? (data.summary.by_type[typeName] || 0) : '—' }}
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 无异常时显示空占位 -->
      <el-col v-if="anomalyTypes.length === 0 && data" :span="18">
        <el-card shadow="hover">
          <div style="text-align: center; padding: 20px 0;">
            <el-icon :size="48" style="color: #67c23a;">
              <CircleCheckFilled />
            </el-icon>
            <div style="margin-top: 8px; color: #67c23a; font-size: 16px; font-weight: 600;">
              暂无异常，一切正常 🎉
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 + 表格 -->
    <el-card v-if="data && data.items.length > 0" shadow="hover" style="margin-top: 16px;">
      <template #header>
        <div style="display: flex; align-items: center; justify-content: space-between;">
          <span style="font-weight: 600;">
            <el-icon><WarningFilled /></el-icon> 异常商品列表
          </span>
          <div style="display: flex; gap: 12px; align-items: center;">
            <el-select
              v-model="filterType"
              placeholder="异常类型"
              clearable
              style="width: 160px;"
              size="small"
            >
              <el-option
                v-for="t in anomalyTypes"
                :key="t"
                :label="t"
                :value="t"
              />
            </el-select>
            <el-select
              v-model="filterSeverity"
              placeholder="严重程度"
              clearable
              style="width: 120px;"
              size="small"
            >
              <el-option label="严重" value="critical" />
              <el-option label="预警" value="warning" />
              <el-option label="提示" value="info" />
            </el-select>
            <el-tag type="info" size="small">
              {{ filteredItems.length }} / {{ data.items.length }} 条
            </el-tag>
          </div>
        </div>
      </template>

      <el-table
        :data="filteredItems"
        stripe
        size="small"
        style="width: 100%"
        max-height="500"
        highlight-current-row
        @row-click="openDetail"
      >
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
        <el-table-column label="SKU" width="100">
          <template #default="{ row }">{{ row.sku_id }}</template>
        </el-table-column>
        <el-table-column label="货号" width="130" show-overflow-tooltip>
          <template #default="{ row }">{{ row.offer_id || '—' }}</template>
        </el-table-column>
        <el-table-column label="商品名" min-width="140" show-overflow-tooltip>
          <template #default="{ row }">
            <span style="font-size: 12px;">{{ row.name || '—' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="异常类型" width="130">
          <template #default="{ row }">
            <el-tag
              :color="typeColors[row.anomaly_type] || '#909399'"
              effect="dark"
              size="small"
            >
              {{ row.anomaly_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="严重程度" width="90" align="center">
          <template #default="{ row }">
            <el-tag
              :type="severityColors[row.severity] || 'info'"
              size="small"
              effect="plain"
            >
              {{ severityLabels[row.severity] || row.severity }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发条件" min-width="180">
          <template #default="{ row }">
            <div style="display: flex; gap: 4px; flex-wrap: wrap;">
              <el-tag
                v-for="cond in row.triggered_conditions"
                :key="cond"
                size="small"
                type="info"
                effect="plain"
              >
                {{ cond }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="关键指标" width="160">
          <template #default="{ row }">
            <div style="font-size: 12px; font-family: monospace;">
              <span
                v-for="(val, key) in row.metrics"
                :key="key"
                style="margin-right: 6px;"
              >
                <span style="color: #909399;">{{ key }}:</span>
                <span
                  :style="{
                    color: '#303133',
                    fontWeight: 600,
                  }"
                >
                  {{ Number.isInteger(val) ? formatNumber(val) : val.toFixed(2) }}
                </span>
              </span>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 异常详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      :title="detailItem ? `SKU ${detailItem.sku_id} / ${detailItem.offer_id || '—'} 异常详情` : '异常详情'"
      width="700px"
      top="10vh"
      destroy-on-close
    >
      <template v-if="detailItem">
        <!-- 概览 -->
        <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 20px; padding: 16px; background: #f5f7fa; border-radius: 8px;">
          <el-image
            v-if="detailItem.primary_image"
            :src="detailItem.primary_image"
            style="width: 64px; height: 64px; border-radius: 8px; flex-shrink: 0;"
            fit="cover"
          >
            <template #error>
              <div style="width: 64px; height: 64px; background: #e4e7ed; border-radius: 8px;" />
            </template>
          </el-image>
          <div style="flex: 1; display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; font-size: 13px;">
            <div><span style="color: #909399;">SKU:</span> {{ detailItem.sku_id }}</div>
            <div><span style="color: #909399;">货号:</span> {{ detailItem.offer_id || '—' }}</div>
            <div><span style="color: #909399;">商品:</span> {{ detailItem.name || '—' }}</div>
            <div>
              <span style="color: #909399;">异常类型:</span>
              <el-tag
                :color="typeColors[detailItem.anomaly_type] || '#909399'"
                effect="dark"
                size="small"
                style="margin-left: 4px;"
              >
                {{ detailItem.anomaly_type }}
              </el-tag>
            </div>
            <div>
              <span style="color: #909399;">严重程度:</span>
              <el-tag
                :type="severityColors[detailItem.severity] || 'info'"
                size="small"
                effect="plain"
                style="margin-left: 4px;"
              >
                {{ severityLabels[detailItem.severity] || detailItem.severity }}
              </el-tag>
            </div>
            <div style="grid-column: 1 / -1;">
              <span style="color: #909399;">规则说明:</span>
              <span style="color: #606266;">{{ detailItem.description }}</span>
            </div>
          </div>
        </div>

        <!-- 触发条件 -->
        <h4 style="margin: 0 0 12px; font-size: 14px; color: #303133;">触发条件</h4>
        <el-table
          :data="detailItem.triggered_conditions.map((c, i) => ({
            index: i + 1,
            condition: c,
            value: Object.entries(detailItem.metrics)[i] || [],
          }))"
          size="small"
          style="width: 100%;"
          border
        >
          <el-table-column type="index" width="50" label="#" />
          <el-table-column label="条件表达式" prop="condition" />
          <el-table-column label="实际值" width="200">
            <template #default="{ row }">
              <span v-if="row.value.length" style="font-family: monospace; font-weight: 600;">
                {{ row.value[0] }} = {{ Number.isInteger(row.value[1]) ? formatNumber(row.value[1]) : (row.value[1] as number).toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="判定" width="80" align="center">
            <template #default>
              <el-tag type="danger" size="small" effect="dark">命中</el-tag>
            </template>
          </el-table-column>
        </el-table>

        <!-- 全部指标 -->
        <h4 style="margin: 16px 0 12px; font-size: 14px; color: #303133;">全部指标值</h4>
        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
          <el-tag
            v-for="(val, key) in detailItem.metrics"
            :key="key"
            size="small"
            type="info"
          >
            {{ key }}: {{ Number.isInteger(val) ? formatNumber(val) : val.toFixed(2) }}
          </el-tag>
        </div>
      </template>
    </el-dialog>
  </div>
</template>
