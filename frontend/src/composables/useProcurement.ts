import { ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type {
  PlanOverview, PlanListItem, PlanDetail,
  PurOrderOverview, PurOrderListItem, PurOrderDetail,
  ShippingOverview, ShippingListItem, ShippingDetail,
} from '@/types'
import {
  getPlanOverview, getPlanList, getPlanDetail,
  getPurOrderOverview, getPurOrderList, getPurOrderDetail,
  getShippingOverview, getShippingList, getShippingDetail,
} from '@/api'

// ═══════════════════════════════════════════════════════════
// 申购计划
// ═══════════════════════════════════════════════════════════

export function usePlan(dateRange: Ref<[string, string] | null>) {
  const loading = ref(false)
  const overview = ref<PlanOverview | null>(null)
  const list = ref<PlanListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  async function fetchAll() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [d1, d2] = dateRange.value
      const [ov, li] = await Promise.all([
        getPlanOverview(d1, d2),
        getPlanList(d1, d2, page.value, pageSize.value),
      ])
      overview.value = ov
      list.value = li.items
      total.value = li.total
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载申购数据失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  watch([dateRange, page, pageSize], () => { fetchAll() }, { immediate: true })

  const detailLoading = ref(false)
  const detail = ref<PlanDetail | null>(null)
  async function fetchDetail(poPlanNo: string) {
    detailLoading.value = true
    try { detail.value = await getPlanDetail(poPlanNo) }
    catch (e: unknown) { ElMessage.error('加载申购详情失败: ' + (e instanceof Error ? e.message : '未知错误')) }
    finally { detailLoading.value = false }
  }
  function clearDetail() { detail.value = null }

  return { loading, overview, list, total, page, pageSize, detailLoading, detail, fetchDetail, clearDetail, fetchAll }
}

// ═══════════════════════════════════════════════════════════
// 采购订单
// ═══════════════════════════════════════════════════════════

export function usePurOrder(dateRange: Ref<[string, string] | null>) {
  const loading = ref(false)
  const overview = ref<PurOrderOverview | null>(null)
  const list = ref<PurOrderListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  async function fetchAll() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [d1, d2] = dateRange.value
      const [ov, li] = await Promise.all([
        getPurOrderOverview(d1, d2),
        getPurOrderList(d1, d2, page.value, pageSize.value),
      ])
      overview.value = ov
      list.value = li.items
      total.value = li.total
    } catch (e: unknown) {
      ElMessage.error('加载采购数据失败: ' + (e instanceof Error ? e.message : '未知错误'))
    } finally {
      loading.value = false
    }
  }

  watch([dateRange, page, pageSize], () => { fetchAll() }, { immediate: true })

  const detailLoading = ref(false)
  const detail = ref<PurOrderDetail | null>(null)
  async function fetchDetail(poNo: string) {
    detailLoading.value = true
    try { detail.value = await getPurOrderDetail(poNo) }
    catch (e: unknown) { ElMessage.error('加载采购详情失败: ' + (e instanceof Error ? e.message : '未知错误')) }
    finally { detailLoading.value = false }
  }
  function clearDetail() { detail.value = null }

  return { loading, overview, list, total, page, pageSize, detailLoading, detail, fetchDetail, clearDetail, fetchAll }
}

// ═══════════════════════════════════════════════════════════
// 头程发货
// ═══════════════════════════════════════════════════════════

export function useShipping(dateRange: Ref<[string, string] | null>) {
  const loading = ref(false)
  const overview = ref<ShippingOverview | null>(null)
  const list = ref<ShippingListItem[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)

  async function fetchAll() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [d1, d2] = dateRange.value
      const [ov, li] = await Promise.all([
        getShippingOverview(d1, d2),
        getShippingList(d1, d2, page.value, pageSize.value),
      ])
      overview.value = ov
      list.value = li.items
      total.value = li.total
    } catch (e: unknown) {
      ElMessage.error('加载发货数据失败: ' + (e instanceof Error ? e.message : '未知错误'))
    } finally {
      loading.value = false
    }
  }

  watch([dateRange, page, pageSize], () => { fetchAll() }, { immediate: true })

  const detailLoading = ref(false)
  const detail = ref<ShippingDetail | null>(null)
  async function fetchDetail(orderCode: string) {
    detailLoading.value = true
    try { detail.value = await getShippingDetail(orderCode) }
    catch (e: unknown) { ElMessage.error('加载发货详情失败: ' + (e instanceof Error ? e.message : '未知错误')) }
    finally { detailLoading.value = false }
  }
  function clearDetail() { detail.value = null }

  return { loading, overview, list, total, page, pageSize, detailLoading, detail, fetchDetail, clearDetail, fetchAll }
}
