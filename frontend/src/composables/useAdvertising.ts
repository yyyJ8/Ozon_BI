import { ref, computed, watch, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { AdCampaignSummary, AdDailyStat, AdSkuDetail, AdSummary } from '@/types'
import { getAdCampaigns, getAdSummary, getAdCampaignDaily, getAdSkuDetail } from '@/api'

/** 安全转数字：API 可能返回 Decimal 字符串或数字 */
function n(v: unknown): number {
  return typeof v === 'number' ? v : Number(v ?? 0)
}

export function useAdvertising(dateRange: Ref<[string, string] | null>) {
  const loading = ref(false)

  const campaigns = ref<AdCampaignSummary[]>([])
  const adSummary = ref<AdSummary | null>(null)

  // 缓存
  const campaignDaily = ref<Record<string, AdDailyStat[]>>({})
  const loadingDaily = ref<Record<string, boolean>>({})
  const skuDetails = ref<Record<number, AdSkuDetail[]>>({})

  // ── 汇总卡 ──────────────────────────────────────
  const summaryCards = computed(() => {
    if (!adSummary.value) return []
    const c = campaigns.value.filter(x => n(x.total_spend) > 0)
    const totalImpressions = c.reduce((s, x) => s + n((x as any).total_impressions), 0)
    const totalClicks = c.reduce((s, x) => s + n((x as any).total_clicks), 0)
    const ts = n(adSummary.value.total_spend)
    const tc = totalClicks
    const ti = totalImpressions
    return [
      { label: '总花费', value: ts, prefix: '₽', color: '#f56c6c' },
      { label: '展示量', value: ti, prefix: '', color: '#409eff' },
      { label: '点击量', value: tc, prefix: '', color: '#67c23a' },
      { label: 'CTR', value: ti > 0 ? (tc / ti * 100) : 0, prefix: '', suffix: '%', color: '#e6a23c', decimals: 2 },
      { label: '广告订单', value: adSummary.value.total_orders_count, prefix: '', color: '#909399' },
      { label: '广告收入', value: adSummary.value.total_orders_sum, prefix: '₽', color: '#67c23a' },
    ]
  })

  // ── 活动表 ──────────────────────────────────────
  const campaignTable = computed(() => {
    return campaigns.value
      .filter(c => n(c.total_spend) > 0)
      .map(c => ({
        campaign_id: c.campaign_id,
        title: c.title || c.campaign_id,
        campaign_type: c.campaign_type,
        spend: n(c.total_spend),
        impressions: n((c as any).total_impressions),
        clicks: n((c as any).total_clicks),
        orders: n(c.total_orders),
        orders_sum: n(c.total_orders_sum),
        sku_id: c.mapped_sku_id,
        offer_id: c.mapped_offer_id,
      }))
      .sort((a, b) => b.spend - a.spend)
  })

  // ── SKU 表（按 SKU 汇总去重）───────────────────
  const skuTable = computed(() => {
    const map = new Map<number, {
      sku_id: number
      sku_name: string | null
      impressions: number; clicks: number; add_to_cart: number
      spend: number; sold_units: number; sales_promotion: number
      ctr_sum: number; avg_cpc_sum: number; drr_sum: number
      day_count: number
    }>()
    for (const [skuId, details] of Object.entries(skuDetails.value)) {
      const sid = Number(skuId)
      let agg = map.get(sid)
      if (!agg) {
        agg = { sku_id: sid, sku_name: null, impressions: 0, clicks: 0, add_to_cart: 0, spend: 0, sold_units: 0, sales_promotion: 0, ctr_sum: 0, avg_cpc_sum: 0, drr_sum: 0, day_count: 0 }
        map.set(sid, agg)
      }
      for (const d of details) {
        agg.sku_name = d.sku_name || agg.sku_name
        agg.impressions += n(d.impressions)
        agg.clicks += n(d.clicks)
        agg.add_to_cart += n(d.add_to_cart)
        agg.spend += n(d.spend)
        agg.sold_units += n(d.sold_units)
        agg.sales_promotion += n(d.sales_promotion)
        if (d.ctr != null) agg.ctr_sum += n(d.ctr)
        if (d.avg_cpc != null) agg.avg_cpc_sum += n(d.avg_cpc)
        if (d.drr_total != null) agg.drr_sum += n(d.drr_total)
        agg.day_count += 1
      }
    }
    const seen = new Set<number>()
    return Array.from(map.values())
      .filter(a => {
        if (seen.has(a.sku_id)) return false
        seen.add(a.sku_id)
        return true
      })
      .map(a => ({
        sku_id: a.sku_id,
        sku_name: a.sku_name,
        impressions: a.impressions,
        clicks: a.clicks,
        ctr: a.day_count > 0 ? a.ctr_sum / a.day_count : null,
        add_to_cart: a.add_to_cart,
        avg_cpc: a.day_count > 0 ? a.avg_cpc_sum / a.day_count : null,
        spend: a.spend,
        sold_units: a.sold_units,
        sales_promotion: a.sales_promotion,
        drr_total: a.day_count > 0 ? a.drr_sum / a.day_count : null,
      }))
      .sort((a, b) => b.spend - a.spend)
  })

  // ── 折线图数据：CTR / 加购率 / CVR (%) ──────────
  const chartData = computed(() => {
    const map = new Map<string, { impressions: number; clicks: number; add_to_cart: number; orders: number }>()
    for (const rows of Object.values(campaignDaily.value)) {
      for (const r of rows) {
        const d = map.get(r.stat_date) || { impressions: 0, clicks: 0, add_to_cart: 0, orders: 0 }
        d.impressions += n(r.impressions)
        d.clicks += n(r.clicks)
        d.orders += n(r.orders_count)
        map.set(r.stat_date, d)
      }
    }
    // 叠加 SKU 明细的加购数
    for (const details of Object.values(skuDetails.value)) {
      for (const d of details) {
        const entry = map.get(d.stat_date) || { impressions: 0, clicks: 0, add_to_cart: 0, orders: 0 }
        entry.add_to_cart += n(d.add_to_cart)
        map.set(d.stat_date, entry)
      }
    }
    return Array.from(map.entries())
      .map(([date, v]) => ({
        date: date.slice(5),
        ctr: v.impressions > 0 ? (v.clicks / v.impressions * 100) : 0,
        cart_rate: v.clicks > 0 ? (v.add_to_cart / v.clicks * 100) : 0,
        cvr: v.clicks > 0 ? (v.orders / v.clicks * 100) : 0,
      }))
      .sort((a, b) => a.date.localeCompare(b.date))
  })

  // ── 加载 ────────────────────────────────────────
  async function fetchAll() {
    if (!dateRange.value) return
    loading.value = true
    try {
      const [df, dt] = dateRange.value
      const [camps, sum] = await Promise.all([
        getAdCampaigns(df, dt),
        getAdSummary(df, dt),
      ])
      campaigns.value = camps
      adSummary.value = sum

      // 加载活动日明细（用于 chart 的 impressions/clicks/orders）
      const topIds = camps.filter(c => c.total_spend > 0).slice(0, 15).map(c => c.campaign_id)
      for (const cid of topIds) {
        fetchCampaignDaily(cid)
      }
      // 加载 SKU 详情（加购等）
      const mapped = camps.filter(c => c.mapped_sku_id)
      for (const c of mapped) {
        if (c.mapped_sku_id) fetchSkuDetail(c.mapped_sku_id)
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '未知错误'
      ElMessage.error('加载广告数据失败: ' + msg)
    } finally {
      loading.value = false
    }
  }

  async function fetchCampaignDaily(campaignId: string) {
    if (!dateRange.value || loadingDaily.value[campaignId]) return
    loadingDaily.value[campaignId] = true
    try {
      const [df, dt] = dateRange.value
      campaignDaily.value[campaignId] = await getAdCampaignDaily(campaignId, df, dt)
    } catch {
      campaignDaily.value[campaignId] = []
    } finally {
      loadingDaily.value[campaignId] = false
    }
  }

  async function fetchSkuDetail(skuId: number) {
    if (!dateRange.value || skuDetails.value[skuId]) return
    skuDetails.value[skuId] = []
    try {
      const [df, dt] = dateRange.value
      skuDetails.value[skuId] = await getAdSkuDetail(skuId, df, dt)
    } catch {
      skuDetails.value[skuId] = []
    }
  }

  // 日期变化时重新加载
  watch(dateRange, () => {
    if (dateRange.value) {
      campaignDaily.value = {}
      skuDetails.value = {}
      fetchAll()
    }
  }, { immediate: true })

  return {
    loading,
    campaigns, adSummary,
    campaignDaily, loadingDaily,
    skuDetails,
    summaryCards, campaignTable, skuTable, chartData,
    fetchAll, fetchCampaignDaily,
  }
}
