# /generate-component

Generate a Vue 3 component with TypeScript, following project conventions.

## Usage
```
/generate-component UserProfile
/generate-component DataTable --props "columns:Column[], rows:any[]" --emits "select, delete"
```

## Instructions

1. Create the component file in the appropriate directory:
   - `components/ui/` for base UI components
   - `components/` for feature components

2. Use this template:
```vue
<script setup lang="ts">
// Props
interface Props {
  // typed props here
}
const props = withDefaults(defineProps<Props>(), {
  // defaults here
})

// Emits
const emit = defineEmits<{
  (e: 'eventName', payload: Type): void
}>()

// Composables & state
// ...

// Computed
// ...

// Methods
// ...
</script>

<template>
  <div>
    <!-- component markup -->
  </div>
</template>
```

3. Rules:
   - Always `<script setup lang="ts">`
   - Define Props interface inline above defineProps
   - Use `withDefaults()` if defaults needed
   - No Options API, no `this`
   - Extract complex logic to composables
