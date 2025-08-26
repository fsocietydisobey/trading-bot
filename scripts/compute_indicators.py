#!/usr/bin/env python3
import os
import sys
import math
import click
import pandas as pd
import pandas_ta as ta

# Ensure project root on path when running via docker compose
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config.settings import settings
from services.common.influx import query_flux, write_points_batch
from influxdb_client import Point, WritePrecision


def _fetch_close_series(symbol, granularity, start, end):
    measurement = "aggs_1d" if granularity == "day" else "aggs_1m"
    flux = f'''
from(bucket: "{settings.INFLUX_BUCKET}")
  |> range(start: time(v: "{start}"), stop: time(v: "{end}"))
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r.symbol == "{symbol}")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time","c"])
'''
    rows = query_flux(flux)
    if not rows:
        return pd.DataFrame(columns=["_time", "c"])
    df = pd.DataFrame(rows)
    # Normalize column names if Flux returns different keys casing
    if "_time" not in df.columns:
        # try to find time column
        for k in df.columns:
            if k.lower() == "_time":
                df.rename(columns={k: "_time"}, inplace=True)
                break
    if "c" not in df.columns:
        raise RuntimeError("No 'c' (close) field found in queried data.")
    df["_time"] = pd.to_datetime(df["_time"])
    df.sort_values("_time", inplace=True)
    df.set_index("_time", inplace=True)
    return df[["c"]]


def _compute_indicators(df, bb_length, bb_std, macd_fast, macd_slow, macd_signal, rsi_length):
    out = pd.DataFrame(index=df.index)
    close = df["c"].astype(float)

    # Bollinger Bands (middle band is SMA)
    bb = ta.bbands(close, length=bb_length, std=bb_std)
    if bb is not None and not bb.empty:
        # bb columns typically: BBL_<len>_<std>.0, BBM_<len>_<std>.0, BBU_<len>_<std>.0
        out["bb_l"] = bb.iloc[:, 0]
        out["bb_m"] = bb.iloc[:, 1]
        out["bb_u"] = bb.iloc[:, 2]

    # MACD
    macd = ta.macd(close, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    if macd is not None and not macd.empty:
        # macd columns typically: MACD_<fast>_<slow>_<signal>, MACDs_<...>, MACDh_<...>
        out["macd"] = macd.iloc[:, 0]
        out["macds"] = macd.iloc[:, 1]
        out["macdh"] = macd.iloc[:, 2]

    # RSI
    rsi = ta.rsi(close, length=rsi_length)
    if rsi is not None and not rsi.empty:
        out["rsi"] = rsi

    return out


def _points_from_indicators(symbol, granularity, indicators):
    measurement = "ta_1d" if granularity == "day" else "ta_1m"
    tags = {"symbol": symbol, "source": "ta"}
    points = []
    for ts, row in indicators.iterrows():
        # Skip if all NaN (warm-up period)
        if row.isna().all():
            continue
        p = Point(measurement)
        for k, v in tags.items():
            p = p.tag(k, v)
        # Add fields only when not NaN
        for fname in ["bb_l", "bb_m", "bb_u", "macd", "macds", "macdh", "rsi"]:
            val = row.get(fname)
            if val is not None and not (isinstance(val, float) and math.isnan(val)):
                p = p.field(fname, float(val))
        # Time in ns
        p = p.time(int(pd.Timestamp(ts).value), WritePrecision.NS)
        points.append(p)
    return points


@click.command()
@click.option("--symbol", required=True, help="Ticker symbol (e.g., X:BTCUSD)")
@click.option("--granularity", type=click.Choice(["day", "minute"]), default="day")
@click.option("--start", "start_date", required=True, help="Start ISO8601 (e.g., 2023-01-01T00:00:00Z)")
@click.option("--end", "end_date", required=True, help="End ISO8601 (e.g., 2023-12-31T23:59:59Z)")
@click.option("--bb-length", type=int, default=20, show_default=True, help="Bollinger Bands length (SMA)")
@click.option("--bb-std", type=float, default=2.0, show_default=True, help="Bollinger Bands stddev")
@click.option("--macd-fast", type=int, default=12, show_default=True, help="MACD fast length")
@click.option("--macd-slow", type=int, default=26, show_default=True, help="MACD slow length")
@click.option("--macd-signal", type=int, default=9, show_default=True, help="MACD signal length")
@click.option("--rsi-length", type=int, default=14, show_default=True, help="RSI length")
def main(symbol, granularity, start_date, end_date, bb_length, bb_std, macd_fast, macd_slow, macd_signal, rsi_length):
    if not settings.INFLUX_URL or not settings.INFLUX_TOKEN or not settings.INFLUX_ORG or not settings.INFLUX_BUCKET:
        raise click.UsageError("InfluxDB settings missing (INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET).")

    click.echo(f"Loading close series for {symbol} [{granularity}] {start_date} -> {end_date} ...")
    df = _fetch_close_series(symbol, granularity, start_date, end_date)
    if df.empty:
        click.echo("No data found in Influx for the given range.")
        return

    click.echo("Computing indicators (BBANDS, MACD, RSI) ...")
    indicators = _compute_indicators(df, bb_length, bb_std, macd_fast, macd_slow, macd_signal, rsi_length)

    click.echo("Preparing points ...")
    points = _points_from_indicators(symbol, granularity, indicators)
    if not points:
        click.echo("Nothing to write (likely due to warm-up NaNs).")
        return

    click.echo(f"Writing {len(points)} indicator points to Influx measurement "
               f"{'ta_1d' if granularity=='day' else 'ta_1m'} ...")
    write_points_batch(points)
    click.echo("Done.")


if __name__ == "__main__":
    main()