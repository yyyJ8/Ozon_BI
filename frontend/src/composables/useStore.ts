import { ref, watch } from 'vue'
import type { Store } from '@/types'

const selectedStoreId = ref<number>(1)
const stores = ref<Store[]>([])

export function useStore() {
  async function fetchStores() {
    try {
      const res = await fetch('/api/v1/stores')
      if (res.ok) {
        stores.value = await res.json()
      }
    } catch { /* ignore */ }
  }

  function setStoreId(id: number) {
    selectedStoreId.value = id
  }

  return {
    selectedStoreId,
    stores,
    fetchStores,
    setStoreId,
  }
}
