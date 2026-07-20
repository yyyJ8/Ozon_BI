import { ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { ReturnsOverview, ReturnsTrendItem, SkuReturnStats, ReasonItem } from '@/types'
import { getReturnsOverview, getReturnsTrend, getSkuReturnStats, getReturnsReasons } from '@/api'

export function useReturns(dateRange: Ref<[string, string] | null>, skuId: Ref<number | undefined> = ref(undefined)) {
  const loading = ref(false)
  const overview = ref<ReturnsOverview | null>(null)
  const trend = ref<ReturnsTrendItem[]>([])
  const skuStats = ref<SkuReturnStats[]>([])
  const reasons = ref<ReasonItem[]>([])

  async function fetchAll() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [d1, d2] = dateRange.value
      const sid = skuId.value
      const [ov, tr, sk, rs] = await Promise.all([
        getReturnsOverview(d1, d2, sid),
        getReturnsTrend(d1, d2, sid),
        getSkuReturnStats(d1, d2),           // 明细表始终全量
        getReturnsReasons(d1, d2, undefined, sid),
      ])
      overview.value = ov
      trend.value = tr
      skuStats.value = sk
      reasons.value = rs
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载退货数据失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  watch([dateRange, skuId], () => { fetchAll() }, { immediate: true })

  return { loading, overview, trend, skuStats, reasons, fetchAll }
}
