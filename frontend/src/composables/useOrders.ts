import { ref, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { OrderOverview, OrderTrendItem, OrderListItem, OrderDetail } from '@/types'
import { getOrdersOverview, getOrdersTrend, getOrdersList, getOrderDetail } from '@/api'

export function useOrders(
  dateRange: Ref<[string, string] | null>,
  skuId: Ref<number | undefined> = ref(undefined),
) {
  const loading = ref(false)
  const overview = ref<OrderOverview | null>(null)
  const trend = ref<OrderTrendItem[]>([])
  const orderList = ref<OrderListItem[]>([])
  const listTotal = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const statusFilter = ref<string | undefined>(undefined)
  const schemaFilter = ref<string | undefined>(undefined)

  async function fetchAll() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [d1, d2] = dateRange.value
      const sid = skuId.value
      const [ov, tr, listResult] = await Promise.all([
        getOrdersOverview(d1, d2, sid),
        getOrdersTrend(d1, d2, sid),
        getOrdersList(
          d1, d2,
          statusFilter.value,
          schemaFilter.value,
          sid,
          currentPage.value,
          pageSize.value,
        ),
      ])
      overview.value = ov
      trend.value = tr
      orderList.value = listResult.items
      listTotal.value = listResult.total
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载订单数据失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  watch(
    [dateRange, skuId, currentPage, pageSize, statusFilter, schemaFilter],
    () => { fetchAll() },
    { immediate: true },
  )

  // 订单详情（按需加载）
  const detailLoading = ref(false)
  const selectedOrder = ref<OrderDetail | null>(null)

  async function fetchDetail(postingNumber: string) {
    detailLoading.value = true
    try {
      selectedOrder.value = await getOrderDetail(postingNumber)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载订单详情失败: ' + msg)
    } finally {
      detailLoading.value = false
    }
  }

  function clearDetail() {
    selectedOrder.value = null
  }

  return {
    loading, overview, trend,
    orderList, listTotal, currentPage, pageSize,
    statusFilter, schemaFilter,
    fetchAll,
    detailLoading, selectedOrder, fetchDetail, clearDetail,
  }
}