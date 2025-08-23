from flask import Blueprint, request, jsonify
from config.settings import settings
from services.common.influx import query_flux

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.before_request
def _auth_guard():
    # If you want JWT auth here, import your middleware or perform header checks.
    # For now, keep it open or integrate your existing auth_middleware if desired.
    # Example:
    # from middleware.auth_middleware import token_required
    # This hook could be replaced by wrapping each route with @token_required
    pass

@api_bp.get("/snapshot")
def snapshot():
    symbol = request.args.get("symbol")
    if not symbol:
        return jsonify({"error": "symbol required"}), 400
    measurement = request.args.get("measurement", "aggs_1m")
    flux = f'''
from(bucket: "{settings.INFLUX_BUCKET}")
  |> range(start: -24h)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r.symbol == "{symbol}")
  |> filter(fn: (r) => r._field == "c")
  |> last()
'''
    try:
        rows = query_flux(flux)
        last_value = None
        if rows:
            last_row = rows[-1]
            last_value = last_row.get("_value")
        return jsonify({"symbol": symbol, "measurement": measurement, "last_close": last_value})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.get("/history")
def history():
    symbol = request.args.get("symbol")
    gran = request.args.get("granularity", "minute")
    start = request.args.get("start")
    end = request.args.get("end")
    if not symbol or not start or not end:
        return jsonify({"error": "symbol, start, end required"}), 400
    measurement = "aggs_1d" if gran == "day" else "aggs_1m"
    flux = f'''
from(bucket: "{settings.INFLUX_BUCKET}")
  |> range(start: time(v: "{start}"), stop: time(v: "{end}"))
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r.symbol == "{symbol}")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["_time","o","h","l","c","v","vw","n"])
'''
    try:
        rows = query_flux(flux)
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
