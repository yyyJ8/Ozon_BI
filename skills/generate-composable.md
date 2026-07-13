# /generate-composable

Generate a Vue 3 composable with TypeScript.

## Usage
```
/generate-composable useSearch --params "query: string, options?: SearchOptions"
/generate-composable useAuth
```

## Instructions

1. Create file in `composables/` directory

2. Use this template:
```ts
import { ref, computed, watch, type MaybeRef, toValue } from 'vue'

interface Use___Options {
  // options
}

interface Use___Return {
  // return type
}

export function use___(
  param: MaybeRef<string>,
  options: Use___Options = {}
): Use___Return {
  // State
  const data = ref()
  const error = ref<string>()
  const loading = ref(false)

  // Core logic
  async function execute() {
    loading.value = true
    error.value = undefined
    try {
      // implementation
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Unknown error'
    } finally {
      loading.value = false
    }
  }

  // Auto-execute on param change (if reactive)
  watch(() => toValue(param), execute, { immediate: true })

  return {
    data: readonly(data),
    error: readonly(error),
    loading: readonly(loading),
    execute,
  }
}
```

3. Rules:
   - Accept `MaybeRef<T>` params for flexibility
   - Return readonly refs for state
   - Return functions for actions
   - Use `{ data, error, loading }` pattern for async
   - Handle cleanup with `onUnmounted` if needed
