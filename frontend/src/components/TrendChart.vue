<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

export interface DailyPoint {
  date: string
  revenue: number
  net_profit: number
}

const props = defineProps<{
  data: DailyPoint[]
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chart || !props.data.length) return

  const dates = props.data.map(d => d.date.slice(5)) // MM-DD
  const revenues = props.data.map(d => d.revenue)
  const profits = props.data.map(d => d.net_profit)

  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        formatter: (params: echarts.TooltipComponentFormatterParams | echarts.TooltipComponentFormatterParams[]) => {
          const arr = Array.isArray(params) ? params : [params]
          let html = `<div style="font-size:13px;line-height:1.8">`
          html += `<div style="font-weight:600;margin-bottom:4px">${arr[0].axisValue}</div>`
          for (const p of arr) {
            const val = p.value as number
            const formatted = `₽ ${val.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            html += `<div style="display:flex;align-items:center;gap:6px">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${p.color}"></span>
              ${p.seriesName}: <strong>${formatted}</strong>
            </div>`
          }
          html += `</div>`
          return html
        },
      },
      legend: {
        data: ['收入', '净利润'],
        bottom: 0,
      },
      grid: {
        left: 60,
        right: 20,
        top: 20,
        bottom: 40,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: 11 },
      },
      yAxis: {
        type: 'value',
        axisLabel: {
          formatter: (v: number) => {
            if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M'
            if (v >= 1_000) return (v / 1_000).toFixed(2) + 'K'
            return v.toFixed(2)
          },
        },
      },
      series: [
        {
          name: '收入',
          type: 'line',
          data: revenues,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#409eff' },
          itemStyle: { color: '#409eff' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(64,158,255,0.25)' },
              { offset: 1, color: 'rgba(64,158,255,0.02)' },
            ]),
          },
        },
        {
          name: '净利润',
          type: 'line',
          data: profits,
          smooth: true,
          symbol: 'circle',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#67c23a' },
          itemStyle: { color: '#67c23a' },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(103,194,58,0.2)' },
              { offset: 1, color: 'rgba(103,194,58,0.02)' },
            ]),
          },
        },
      ],
    },
    true,
  )
}

onMounted(() => {
  chart = echarts.init(chartRef.value!)
  renderChart()
})

watch(
  () => props.data,
  () => renderChart(),
  { deep: true },
)

onUnmounted(() => {
  chart?.dispose()
})
</script>

<template>
  <div ref="chartRef" style="width: 100%; height: 320px" />
</template>
