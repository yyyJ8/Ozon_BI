<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'

export interface DailyPoint {
  date: string
  revenue: number
  net_profit: number
  ordered_units: number
}

const props = defineProps<{
  data: DailyPoint[]
}>()

const chartRef = ref<HTMLDivElement>()
let chart: echarts.ECharts | null = null

function renderChart() {
  if (!chart || !props.data.length) return

  const dates = props.data.map(d => d.date.slice(5)) // MM-DD
  const ordered = props.data.map(d => d.ordered_units)
  const revenues = props.data.map(d => d.revenue)
  const profits = props.data.map(d => d.net_profit)

  chart.setOption(
    {
      tooltip: {
        trigger: 'axis',
        formatter: (params: any) => {
          const arr = Array.isArray(params) ? params : [params]
          let html = `<div style="font-size:13px;line-height:1.8">`
          html += `<div style="font-weight:600;margin-bottom:4px">${arr[0].axisValue}</div>`
          for (const p of arr) {
            const val = p.value as number
            let formatted: string
            if (p.seriesName === '总单量') {
              formatted = `${val.toLocaleString()} 单`
            } else {
              formatted = `₽ ${val.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
            }
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
        data: ['总单量', '总销售额', '总利润'],
        bottom: 0,
      },
      grid: {
        left: 60,
        right: 60,
        top: 20,
        bottom: 40,
      },
      xAxis: {
        type: 'category',
        data: dates,
        axisLabel: { fontSize: 11 },
      },
      yAxis: [
        {
          type: 'value',
          name: '金额 (₽)',
          axisLabel: {
            formatter: (v: number) => {
              if (v >= 1_000_000) return (v / 1_000_000).toFixed(2) + 'M'
              if (v >= 1_000) return (v / 1_000).toFixed(2) + 'K'
              return v.toFixed(2)
            },
          },
        },
        {
          type: 'value',
          name: '单量',
          min: 0,
          minInterval: 1,
          axisLabel: {
            formatter: (v: number) => `${v}`,
          },
        },
      ],
      series: [
        {
          name: '总单量',
          type: 'line',
          yAxisIndex: 1,
          data: ordered,
          smooth: true,
          symbol: 'diamond',
          symbolSize: 6,
          lineStyle: { width: 2, color: '#e6a23c' },
          itemStyle: { color: '#e6a23c' },
        },
        {
          name: '总销售额',
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
          name: '总利润',
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
