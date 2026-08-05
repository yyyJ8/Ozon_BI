import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { DirectSkuItem, DirectSkuUpdate, DirectShipmentItem, DirectShipmentUpdate, DirectFileItem } from '@/types'
import {
  getDirectSkuList, createDirectSku, updateDirectSku, deleteDirectSku,
  getDirectShipmentList, createDirectShipment, updateDirectShipment, deleteDirectShipment,
  getDirectFiles, uploadDirectFile, deleteDirectFile,
} from '@/api'

// ============================================================
// SKU 基础数据
// ============================================================

export function useDirectSku() {
  const loading = ref(false)
  const list = ref<DirectSkuItem[]>([])
  const total = ref(0)
  const search = ref('')

  async function fetchAll() {
    loading.value = true
    try {
      const res = await getDirectSkuList(1, 0, search.value || undefined)
      list.value = res.items
      total.value = res.total
    } catch (e: unknown) {
      ElMessage.error('加载SKU数据失败: ' + (e instanceof Error ? e.message : '未知错误'))
    } finally {
      loading.value = false
    }
  }

  async function create(body: DirectSkuUpdate): Promise<DirectSkuItem | null> {
    try {
      const item = await createDirectSku(body)
      ElMessage.success('新增成功')
      await fetchAll()
      return item
    } catch (e: unknown) {
      ElMessage.error('新增失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return null
    }
  }

  async function update(id: number, body: DirectSkuUpdate): Promise<DirectSkuItem | null> {
    try {
      const item = await updateDirectSku(id, body)
      ElMessage.success('更新成功')
      await fetchAll()
      return item
    } catch (e: unknown) {
      ElMessage.error('更新失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return null
    }
  }

  async function remove(id: number): Promise<boolean> {
    try {
      await deleteDirectSku(id)
      ElMessage.success('已删除')
      await fetchAll()
      return true
    } catch (e: unknown) {
      ElMessage.error('删除失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return false
    }
  }

  function onSearch() { fetchAll() }

  return { loading, list, total, search, fetchAll, create, update, remove, onSearch }
}


// ============================================================
// 直发跟进表
// ============================================================

export function useDirectShipment() {
  const loading = ref(false)
  const list = ref<DirectShipmentItem[]>([])
  const total = ref(0)
  const search = ref('')
  const dateRange = ref<[string, string] | null>(null)

  async function fetchAll() {
    loading.value = true
    try {
      const d1 = dateRange.value ? dateRange.value[0] : undefined
      const d2 = dateRange.value ? dateRange.value[1] : undefined
      const res = await getDirectShipmentList(1, 0, search.value || undefined, d1, d2)
      list.value = res.items
      total.value = res.total
    } catch (e: unknown) {
      ElMessage.error('加载发货数据失败: ' + (e instanceof Error ? e.message : '未知错误'))
    } finally {
      loading.value = false
    }
  }

  async function create(body: DirectShipmentUpdate): Promise<DirectShipmentItem | null> {
    try {
      const item = await createDirectShipment(body)
      ElMessage.success('新增成功')
      await fetchAll()
      return item
    } catch (e: unknown) {
      ElMessage.error('新增失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return null
    }
  }

  async function update(id: number, body: DirectShipmentUpdate): Promise<DirectShipmentItem | null> {
    try {
      const item = await updateDirectShipment(id, body)
      ElMessage.success('更新成功')
      await fetchAll()
      return item
    } catch (e: unknown) {
      ElMessage.error('更新失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return null
    }
  }

  async function remove(id: number): Promise<boolean> {
    try {
      await deleteDirectShipment(id)
      ElMessage.success('已删除')
      await fetchAll()
      return true
    } catch (e: unknown) {
      ElMessage.error('删除失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return false
    }
  }

  function onSearch() { fetchAll() }

  return { loading, list, total, search, dateRange, fetchAll, create, update, remove, onSearch }
}


// ============================================================
// 文件管理
// ============================================================

export function useDirectFiles() {
  const files = ref<DirectFileItem[]>([])
  const uploading = ref(false)

  async function fetchFiles(sourceTable: string, sku: string, prNo?: string) {
    try {
      files.value = await getDirectFiles(sourceTable, sku, prNo)
    } catch {
      files.value = []
    }
  }

  async function upload(file: File, sourceTable: string, sku: string, prNo?: string): Promise<DirectFileItem | null> {
    uploading.value = true
    try {
      const item = await uploadDirectFile(file, sourceTable, sku, prNo)
      ElMessage.success('文件上传成功')
      await fetchFiles(sourceTable, sku, prNo)
      return item
    } catch (e: unknown) {
      ElMessage.error('上传失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return null
    } finally {
      uploading.value = false
    }
  }

  async function remove(fileId: number, sourceTable: string, sku: string, prNo?: string): Promise<boolean> {
    try {
      await deleteDirectFile(fileId)
      ElMessage.success('文件已删除')
      await fetchFiles(sourceTable, sku, prNo)
      return true
    } catch (e: unknown) {
      ElMessage.error('删除失败: ' + (e instanceof Error ? e.message : '未知错误'))
      return false
    }
  }

  return { files, uploading, fetchFiles, upload, remove }
}
