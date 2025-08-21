import os
import sys
from db.influx import query_flux

def last_n_candles(symbol: str, interval: str, n: int = 100):
    bucket = os.environ.get("INFLUX_BUCKET")
    query = f'''
from(bucket: "{bucket}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "ohlc")
  |> filter(fn: (r) => r["symbol"] == "{symbol}")
  |> filter(fn: (r) => r["interval"] == "{interval}")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {n})
  |> sort(columns: ["_time"], desc: false)
'''
    return query_flux(query)

def main():
    symbol = "BTC/USD"
    interval = "1m"
    rows = last_n_candles(symbol, interval, n=5)
    for r in rows:
        # r contains keys like _time, symbol, interval, open, high, low, close, volume, trades
        print(r)

if __name__ == "__main__":
    sys.exit(main())