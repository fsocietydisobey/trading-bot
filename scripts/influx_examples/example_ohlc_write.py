import sys
from typing import List, Dict, Any
from influxdb_client import Point, WritePrecision
from db.influx import write_points_batch

def to_ns(sec: int) -> int:
    return sec * 1_000_000_000

def build_points(symbol: str, interval: str, exchange: str, candles: List[Dict[str, Any]]) -> List[Point]:
    points = []
    for c in candles:
        p = (
            Point("ohlc")
            .tag("symbol", symbol)
            .tag("exchange", exchange)
            .tag("interval", interval)
            .field("open", float(c["open"]))
            .field("high", float(c["high"]))
            .field("low", float(c["low"]))
            .field("close", float(c["close"]))
            .field("volume", float(c.get("volume", 0.0)))
            .field("trades", int(c.get("trades", 0)))
            .time(to_ns(int(c["time_sec"])), WritePrecision.NS)
        )
        points.append(p)
    return points

def main():
    # Example payload (replace with real Kraken OHLC data)
    symbol = "BTC/USD"
    interval = "1m"
    exchange = "kraken"
    candles = [
        {"time_sec": 1755802620, "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "volume": 10.2, "trades": 42},
        {"time_sec": 1755802680, "open": 1.5, "high": 2.1, "low": 1.2, "close": 1.9, "volume": 7.3, "trades": 21},
    ]

    points = build_points(symbol, interval, exchange, candles)
    write_points_batch(points)
    print(f"Wrote {len(points)} candles for {symbol} {interval} ({exchange})")

if __name__ == "__main__":
    sys.exit(main())