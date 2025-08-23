# blueprints/data.py (example usage)
from flask import Blueprint, jsonify, request
from influxdb_client import Point, WritePrecision
from config.settings import settings  # use centralized settings
# Prefer canonical helpers from services/common/influx
from services.common.influx import query_flux

data_bp = Blueprint("data", __name__)


@data_bp.route("/ohlc/write", methods=["POST"])
def write_ohlc():
    body = request.get_json()
    # expects symbol, interval, exchange, time_sec, open, high, low, close, volume, trades
    p = (
        Point("ohlc")
        .tag("symbol", body["symbol"])
        .tag("exchange", body["exchange"])
        .tag("interval", body["interval"])
        .field("open", float(body["open"]))
        .field("high", float(body["high"]))
        .field("low", float(body["low"]))
        .field("close", float(body["close"]))
        .field("volume", float(body.get("volume", 0.0)))
        .field("trades", int(body.get("trades", 0)))
        .time(int(body["time_sec"]) * 1_000_000_000, WritePrecision.NS)
    )
    # Use the canonical batch helper
    from services.common.influx import write_points_batch
    write_points_batch([p])
    return jsonify({"status": "ok"})


@data_bp.route("/ohlc/last", methods=["GET"])
def last_ohlc():
    symbol = request.args.get("symbol", "BTC/USD")
    interval = request.args.get("interval", "1m")
    n = int(request.args.get("n", "100"))
    query = f'''
from(bucket: "{settings.INFLUX_BUCKET}")
  |> range(start: -30d)
  |> filter(fn: (r) => r["_measurement"] == "ohlc")
  |> filter(fn: (r) => r["symbol"] == "{symbol}")
  |> filter(fn: (r) => r["interval"] == "{interval}")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: {n})
  |> sort(columns: ["_time"], desc: false)
'''
    rows = query_flux(query)
    return jsonify(rows)
