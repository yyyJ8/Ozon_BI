import { ref, computed, watch } from 'vue'
import type { DateRangeInfo } from '@/types'
import { getDateRange } from '@/api'
import { useStore } from '@/composables/useStore'

/**
 * 子组件独立日期范围管理
 * 默认近30天（截止昨天），支持预设 + 自定义日期范围
 */
export function useLocalDateRange() {
  const { selectedStoreId } = useStore()

  // ── 日期预设 ──────────────────────────────────────────────
  const periodPreset = ref('30days')
  const showCustomDate = computed(() => periodPreset.value === 'custom')
  const availableRange = ref<DateRangeInfo | null>(null)

  // 默认：近30天 → 昨天
  function daysAgoStr(n: number): string {
    const d = new Date()
    d.setDate(d.getDate() - n)
    return d.toISOString().split('T')[0]
  }

  const today = daysAgoStr(0)
  const localDateRange = ref<[string, string]>([daysAgoStr(30), today])

  function applyPreset(preset: string) {
    periodPreset.value = preset
    if (preset === 'custom') return

    const t = daysAgoStr(0)
    const y = daysAgoStr(1)
    switch (preset) {
      case 'yesterday':
        localDateRange.value = [y, y]
        break
      case '7days':
        localDateRange.value = [daysAgoStr(7), t]
        break
      case '30days':
        localDateRange.value = [daysAgoStr(30), t]
        break
      case 'thisMonth': {
        // 本月 = 当月1号 → 昨天（今天数据不完整，沿用"终点用昨天"约定）
        const now = new Date()
        let start = daysAgoStr(now.getDate() - 1)  // 当月1号
        // 店铺数据最早日期晚于1号时，收紧起点到实际有数据的日期
        if (availableRange.value && availableRange.value.min_date > start) {
          start = availableRange.value.min_date
        }
        // 极端情况：今天就是1号（本月还没有完整天数）→ 回退为昨天单天
        if (start > y) start = y
        localDateRange.value = [start, y]
        break
      }
      case 'all':
      default:
        if (availableRange.value) {
          localDateRange.value = [availableRange.value.min_date, t]
        } else {
          localDateRange.value = [daysAgoStr(90), t]
        }
        break
    }
  }

  // 日期禁用：不选未来
  function disabledDate(time: Date): boolean {
    const d = time.toISOString().split('T')[0]
    const today = new Date().toISOString().split('T')[0]
    if (d > today) return true
    if (availableRange.value && d < availableRange.value.min_date) return true
    return false
  }

  // 获取可用日期范围（用于"全部"预设）
  async function fetchDateRange() {
    try {
      availableRange.value = await getDateRange(selectedStoreId.value)
    } catch {
      // 失败时保持 null，applyPreset('all') 会用 fallback
    }
  }

  // 初始化
  fetchDateRange()

  // 店铺切换 → 重新获取范围
  watch(selectedStoreId, () => {
    fetchDateRange()
    // 店铺切换后重置为近30天
    applyPreset('30days')
  })

  return {
    localDateRange,
    periodPreset,
    showCustomDate,
    availableRange,
    applyPreset,
    disabledDate,
  }
}
