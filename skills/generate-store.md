# /generate-store

Generate a Pinia store with setup syntax and TypeScript.

## Usage
```
/generate-store cart
/generate-store auth --actions "login, logout, register"
```

## Instructions

1. Create file in `stores/` directory as `use___Store.ts`

2. Use this template:
```ts
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const use___Store = defineStore('___', () => {
  // State
  const items = ref<Item[]>([])
  const loading = ref(false)
  const error = ref<string>()

  // Getters (computed)
  const count = computed(() => items.value.length)
  const isEmpty = computed(() => items.value.length === 0)

  // Actions
  async function fetch() {
    loading.value = true
    error.value = undefined
    try {
      items.value = await $fetch('/api/___')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch'
    } finally {
      loading.value = false
    }
  }

  function reset() {
    items.value = []
    error.value = undefined
  }

  return {
    // State
    items,
    loading,
    error,
    // Getters
    count,
    isEmpty,
    // Actions
    fetch,
    reset,
  }
})
```

3. Rules:
   - Always use setup syntax (`defineStore('name', () => { ... })`)
   - Name pattern: `use___Store`
   - Export all state, getters, and actions
   - Use `storeToRefs()` in components when destructuring
