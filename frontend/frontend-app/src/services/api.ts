// typescript
// src/services/api.ts
import axios from 'axios'

const BASE = 'http://localhost:5000'

// helper: parse ISO string -> epoch seconds; returns null if invalid
function toEpochSec(t: any): number | null {
  const ms = Date.parse(typeof t === 'string' ? t : String(t))
  return Number.isNaN(ms) ? null : Math.floor(ms / 1000)
}

export async function fetchCandles(symbol: string, gran: 'day' | 'minute', start: string, end: string) {
  const url = `${BASE}/api/history`
  const { data } = await axios.get(url, {
    params: { symbol, granularity: gran, start, end },
  })

  const candles = (Array.isArray(data) ? data : [])
    .map((r: any) => {
      const time = toEpochSec(r?._time)
      const open = Number(r?.o)
      const high = Number(r?.h)
      const low = Number(r?.l)
      const close = Number(r?.c)
      // filter out any invalid numbers
      if (
        time == null ||
        Number.isNaN(open) ||
        Number.isNaN(high) ||
        Number.isNaN(low) ||
        Number.isNaN(close)
      ) return null
      return {
        time,
        open,
        high,
        low,
        close,
        volume: Number.isNaN(Number(r?.v)) ? 0 : Number(r?.v),
      }
    })
    .filter((x: any) => x !== null)
    // sort strictly ascending by time
    .sort((a: any, b: any) => a.time - b.time)

  return candles
}

export async function fetchIndicators(symbol: string, gran: 'day' | 'minute', start: string, end: string, fields?: string[]) {
  const url = `${BASE}/api/indicators`
  const { data } = await axios.get(url, {
    params: {
      symbol,
      granularity: gran,
      start,
      end,
      ...(fields && fields.length ? { fields: fields.join(',') } : {}),
    },
  })

  const rows = (Array.isArray(data) ? data : [])
    .map((r: any) => ({ ...r, __t: toEpochSec(r?._time) }))
    .filter((r: any) => r.__t != null)
    .sort((a: any, b: any) => a.__t - b.__t)

  const toLine = (key: string) =>
    rows
      .filter((r: any) => r[key] != null && !Number.isNaN(Number(r[key])))
      .map((r: any) => ({ time: r.__t, value: Number(r[key]) }))

  const bb_l = toLine('bb_l')
  const bb_m = toLine('bb_m')
  const bb_u = toLine('bb_u')
  const macd = toLine('macd')
  const macds = toLine('macds')
  const macdh = toLine('macdh')
  const rsi = toLine('rsi')

  return { bb_l, bb_m, bb_u, macd, macds, macdh, rsi }
}
