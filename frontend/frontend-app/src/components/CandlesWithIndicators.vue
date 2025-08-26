<template>
  <div class="mp-wrap" style="height: 900px">
    <div ref="container" class="mp-container" style="height: 100%"></div>
  </div>
</template>

<script setup lang="ts">
import {ref, onMounted, onBeforeUnmount, nextTick} from 'vue'
import {
  createChart,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  AreaSeries,        // + add AreaSeries for RSI fill
  type IChartApi,
  type Time,
  LineStyle,
} from 'lightweight-charts'
import {fetchCandles, fetchIndicators} from '@/services/api'

const container = ref<HTMLDivElement | null>(null)
const noData = ref(false)

const symbol = 'X:BTCUSD'
const gran: 'day' | 'minute' = 'day'
const start = '2023-01-01T00:00:00Z'
const end = '2023-12-31T23:59:59Z'

let chart: IChartApi | null = null
let ro: ResizeObserver | null = null

function paneWidth(el: HTMLElement) {
  const w = el.clientWidth || el.getBoundingClientRect().width
  return Math.max(360, Math.floor(w || window.innerWidth - 32))
}

// Helper: apply pane heights with a couple of animation-frame retries.
// In some builds panes() isn’t fully ready right after series are added.
function applyPaneHeights(priceH: number, macdH: number, rsiH: number, macdPaneIndex?: number, rsiPaneIndex?: number, tries = 3) {
  if (!chart) return
  const doApply = () => {
    const panesApi = (chart as any).panes?.()
    if (!Array.isArray(panesApi) || panesApi.length === 0) {
      if (tries > 0) requestAnimationFrame(() => applyPaneHeights(priceH, macdH, rsiH, macdPaneIndex, rsiPaneIndex, tries - 1))
      return
    }
    // Price pane
    if (panesApi[0]?.setHeight && priceH) panesApi[0].setHeight(priceH)
    // MACD pane
    if (macdPaneIndex !== undefined && panesApi[macdPaneIndex]?.setHeight && macdH) panesApi[macdPaneIndex].setHeight(macdH)
    // RSI pane
    if (rsiPaneIndex !== undefined && panesApi[rsiPaneIndex]?.setHeight && rsiH) panesApi[rsiPaneIndex].setHeight(rsiH)
  }
  // Apply, then re-apply next frame to catch late layout
  requestAnimationFrame(() => {
    doApply()
    requestAnimationFrame(doApply)
  })
}

onMounted(async () => {
  await nextTick()
  if (!container.value) return

  const [candles, ind] = await Promise.all([
    fetchCandles(symbol, gran, start, end),
    fetchIndicators(symbol, gran, start, end, ['bb_l', 'bb_m', 'bb_u', 'macd', 'macds', 'macdh', 'rsi']),
  ])
  if (!candles.length) {
    noData.value = true
    return
  }

  const hasMACD = (ind.macd?.length || 0) > 0 || (ind.macds?.length || 0) > 0 || (ind.macdh?.length || 0) > 0
  const hasRSI = (ind.rsi?.length || 0) > 0

  // Target heights
  const priceH = 420
  const macdH = hasMACD ? 280 : 0
  const rsiH = hasRSI ? 160 : 0
  const totalH = priceH + macdH + rsiH || priceH

  chart = createChart(container.value, {
    width: paneWidth(container.value),
    height: totalH,
    layout: {
      background: {color: '#111'},
      textColor: '#eee',
      panes: {
        separatorColor: '#f22c3d',
        separatorHoverColor: 'rgba(255, 0, 0, 0.15)',
        enableResize: true,
      },
    },
    grid: {vertLines: {color: '#222'}, horzLines: {color: '#222'}},
    rightPriceScale: {borderVisible: false},
    timeScale: {timeVisible: true, secondsVisible: false, borderVisible: false},
    crosshair: {mode: 0},
  })

  // Price pane
  const candleSeries = chart.addSeries(CandlestickSeries, {
    upColor: '#26a69a',
    downColor: '#ef5350',
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
    borderVisible: false,
  })
  candleSeries.setData(candles as any)
  if (ind.bb_u?.length) chart.addSeries(LineSeries, {color: '#ffa726', lineWidth: 1}).setData(ind.bb_u as any)
  if (ind.bb_m?.length) chart.addSeries(LineSeries, {color: '#90caf9', lineWidth: 1}).setData(ind.bb_m as any)
  if (ind.bb_l?.length) chart.addSeries(LineSeries, {color: '#ffa726', lineWidth: 1}).setData(ind.bb_l as any)

  // Decide pane indices
  let macdPaneIndex: number | undefined = undefined
  let rsiPaneIndex: number | undefined = undefined
  if (hasMACD) macdPaneIndex = 1
  if (hasRSI) rsiPaneIndex = hasMACD ? 2 : 1

  // MACD pane
  if (hasMACD && macdPaneIndex !== undefined) {
    if (ind.macdh?.length)
      chart.addSeries(HistogramSeries, {color: 'rgba(102,187,106,0.45)'}, macdPaneIndex).setData(ind.macdh as any)
    if (ind.macd?.length)
      chart.addSeries(LineSeries, {color: '#ab47bc', lineWidth: 2}, macdPaneIndex).setData(ind.macd as any)
    if (ind.macds?.length)
      chart.addSeries(LineSeries, {color: '#ff7043', lineWidth: 2}, macdPaneIndex).setData(ind.macds as any)
    const firstTime = candles[0].time as Time
    const lastTime = candles[candles.length - 1].time as Time
    chart.addSeries(
      LineSeries,
      {color: '#999', lineWidth: 1, lineStyle: LineStyle.Dashed},
      macdPaneIndex
    ).setData([{time: firstTime, value: 0}, {time: lastTime, value: 0}] as any)
  }

  // RSI pane (with dashed guides at 30/70 and a light grey band fill between them)
  if (hasRSI && rsiPaneIndex !== undefined) {
    // Main RSI line (you can keep AreaSeries here too; we’ll add band layers separately)
    chart.addSeries(LineSeries, {color: '#29b6f6', lineWidth: 2}, rsiPaneIndex).setData(ind.rsi as any)

    const firstTime = candles[0].time as Time
    const lastTime = candles[candles.length - 1].time as Time
    const span = [{time: firstTime, value: 0}, {time: lastTime, value: 0}]

    // Band layer 1: fill everything BELOW 70 with light grey (semi-transparent)
    chart.addSeries(
      AreaSeries,
      {
        lineColor: 'rgba(0,0,0,0)',     // hide line
        topColor: 'rgba(200,200,200,0.22)',  // light grey
        bottomColor: 'rgba(200,200,200,0.22)',
      },
      rsiPaneIndex
    ).setData([
      {time: firstTime, value: 70},
      {time: lastTime, value: 70},
    ] as any)

    // Band layer 2 (mask): cover everything BELOW 30 with background color,
    // which leaves only 30..70 visible from the first layer.
    chart.addSeries(
      AreaSeries,
      {
        lineColor: 'rgba(0,0,0,0)',     // hide line
        topColor: '#111',               // pane background color
        bottomColor: '#111',
      },
      rsiPaneIndex
    ).setData([
      {time: firstTime, value: 30},
      {time: lastTime, value: 30},
    ] as any)

    // Dashed 30/70 guide lines
    const guide = (v: number) => [{time: firstTime, value: v}, {time: lastTime, value: v}]
    chart.addSeries(
      LineSeries,
      {color: '#aaaaaa', lineWidth: 1, lineStyle: LineStyle.Dashed},
      rsiPaneIndex
    ).setData(guide(30) as any)

    chart.addSeries(
      LineSeries,
      {color: '#aaaaaa', lineWidth: 1, lineStyle: LineStyle.Dashed},
      rsiPaneIndex
    ).setData(guide(70) as any)

    // Optional: midline at 50
    chart.addSeries(
      LineSeries,
      {color: '#8e24aa', lineWidth: 1},
      rsiPaneIndex
    ).setData(guide(50) as any)
  }

  // Apply pane heights after panes/series exist and layout settles
  applyPaneHeights(priceH, macdH, rsiH, macdPaneIndex, rsiPaneIndex)

  // Resize: update width and re-apply pane heights (to keep proportions)
  const onResize = () => {
    if (!container.value || !chart) return
    chart.applyOptions({width: paneWidth(container.value)})
    applyPaneHeights(priceH, macdH, rsiH, macdPaneIndex, rsiPaneIndex, 1)
  }
  ro = new ResizeObserver(onResize)
  ro.observe(container.value)
})

onBeforeUnmount(() => {
  if (ro) {
    ro.disconnect();
    ro = null
  }
  if (chart) {
    chart.remove();
    chart = null
  }
})
</script>

<style scoped>
.mp-wrap {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
}

.mp-container {
  width: 100%;
  background: #111;
}

.empty {
  color: #bbb;
  padding: 24px;
  text-align: center;
  background: #111;
  border-radius: 8px;
  margin-top: 12px;
}
</style>
