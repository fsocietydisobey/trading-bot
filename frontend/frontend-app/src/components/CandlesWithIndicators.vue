<!-- vue -->
<!-- src/components/CandlesWithIndicators.vue -->
<template>
  <div class="charts-wrap">
    <div v-if="noData" class="empty">
      No data for selected range.
    </div>
    <template v-else>
      <div ref="priceEl" class="pane price-pane"></div>
      <div ref="macdEl"  class="pane macd-pane"></div>
      <div ref="rsiEl"   class="pane rsi-pane"></div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
} from 'lightweight-charts'
import { fetchCandles, fetchIndicators } from '@/services/api'

const priceEl = ref<HTMLDivElement | null>(null)
const macdEl  = ref<HTMLDivElement | null>(null)
const rsiEl   = ref<HTMLDivElement | null>(null)
const noData = ref(false)

const symbol = 'X:BTCUSD'
const gran: 'day' | 'minute' = 'day'
const start = '2023-01-01T00:00:00Z'
const end   = '2023-12-31T23:59:59Z'

let priceChart: any
let macdChart: any
let rsiChart: any
let ro: ResizeObserver | null = null

function paneWidth(el: HTMLElement) {
  // Try element width, fall back to parent, then window width
  const w = el.clientWidth || el.getBoundingClientRect().width
  const parent = el.parentElement
  return Math.max(320, Math.floor(w || (parent?.clientWidth || window.innerWidth - 32)))
}

onMounted(async () => {
  await nextTick()
  if (!priceEl.value || !macdEl.value || !rsiEl.value) return

  // Fetch first to know if we have data
  const [candles, ind] = await Promise.all([
    fetchCandles(symbol, gran, start, end),
    fetchIndicators(symbol, gran, start, end, ['bb_l','bb_m','bb_u','macd','macds','macdh','rsi']),
  ])
  console.log("*****",candles)
  if (!candles.length) {
    noData.value = true
    return
  }

  const baseOpts = {
    layout: { background: { color: '#111' }, textColor: '#eee' },
    grid: { vertLines: { color: '#222' }, horzLines: { color: '#222' } },
    timeScale: { timeVisible: true, secondsVisible: false, borderVisible: false },
    rightPriceScale: { borderVisible: false },
    crosshair: { mode: 0 },
  } as const

  // Create charts with explicit width and height
  priceChart = createChart(priceEl.value, { ...baseOpts, width: paneWidth(priceEl.value), height: 420 })
  const candleSeries = priceChart.addSeries(CandlestickSeries, {
    upColor: '#26a69a', downColor: '#ef5350', wickUpColor: '#26a69a', wickDownColor: '#ef5350', borderVisible: false,
  })
  const bbUpper = priceChart.addSeries(LineSeries, { color: '#ffa726', lineWidth: 1 })
  const bbMiddle = priceChart.addSeries(LineSeries, { color: '#90caf9', lineWidth: 1 })
  const bbLower = priceChart.addSeries(LineSeries, { color: '#ffa726', lineWidth: 1 })

  macdChart = createChart(macdEl.value,  { ...baseOpts, width: paneWidth(macdEl.value),  height: 160 })
  const macdLine   = macdChart.addSeries(LineSeries, { color: '#ab47bc', lineWidth: 1 })
  const macdSignal = macdChart.addSeries(LineSeries, { color: '#ff7043', lineWidth: 1 })
  const macdHist   = macdChart.addSeries(HistogramSeries, { color: '#66bb6a' })

  rsiChart  = createChart(rsiEl.value,   { ...baseOpts, width: paneWidth(rsiEl.value),   height: 140 })
  const rsiLine = rsiChart.addSeries(LineSeries, { color: '#29b6f6', lineWidth: 1 })

  // Set data (candles guaranteed non-empty here)
  candleSeries.setData(candles)
  if (ind.bb_u?.length) bbUpper.setData(ind.bb_u)
  if (ind.bb_m?.length) bbMiddle.setData(ind.bb_m)
  if (ind.bb_l?.length) bbLower.setData(ind.bb_l)
  if (ind.macd?.length) macdLine.setData(ind.macd)
  if (ind.macds?.length) macdSignal.setData(ind.macds)
  if (ind.macdh?.length) macdHist.setData(ind.macdh)
  if (ind.rsi?.length) rsiLine.setData(ind.rsi)

  // Sync timescales
  const sync = (src: any, dsts: any[]) => {
    src.timeScale().subscribeVisibleTimeRangeChange((range: any) => {
      if (!range) return
      dsts.forEach(d => d.timeScale().setVisibleRange(range))
    })
  }
  sync(priceChart, [macdChart, rsiChart])
  sync(macdChart, [priceChart, rsiChart])
  sync(rsiChart, [priceChart, macdChart])

  priceChart.timeScale().fitContent()
  macdChart.timeScale().fitContent()
  rsiChart.timeScale().fitContent()

  // Resize observer to react to container width changes
  ro = new ResizeObserver(() => {
    if (!priceEl.value || !macdEl.value || !rsiEl.value) return
    priceChart.applyOptions({ width: paneWidth(priceEl.value) })
    macdChart.applyOptions({ width: paneWidth(macdEl.value) })
    rsiChart.applyOptions({ width: paneWidth(rsiEl.value) })
  })
  ro.observe(priceEl.value)
  ro.observe(macdEl.value)
  ro.observe(rsiEl.value)
})

onBeforeUnmount(() => {
  if (ro) { ro.disconnect(); ro = null }
  if (priceChart) priceChart.remove()
  if (macdChart) macdChart.remove()
  if (rsiChart) rsiChart.remove()
})
</script>

<style scoped>
.charts-wrap {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}
.pane {
  width: 100%;
  background: #111;
}
.price-pane { height: 420px; }
.macd-pane  { height: 160px; margin-top: 12px; }
.rsi-pane   { height: 140px; margin-top: 12px; }
.empty {
  color: #bbb;
  padding: 24px;
  text-align: center;
  background: #111;
  border-radius: 8px;
}
</style>
