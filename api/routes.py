from flask import Blueprint, request, jsonify
from config.settings import settings
from services.common.influx import query_flux
from datetime import datetime, timezone  # add

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

# ... existing code ...

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
        # Backend sanitation: drop invalid rows, coerce numbers, sort by time asc
        clean = []
        for r in rows or []:
            t = r.get("_time")
            if not t:
                continue
            # Normalize time to ISO string and epoch seconds
            try:
                if isinstance(t, str):
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                else:
                    # Influx client may return datetime already
                    dt = t if isinstance(t, datetime) else None
                    if dt is None:
                        continue
                dt = dt.astimezone(timezone.utc)
                iso = dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                tsec = int(dt.timestamp())
            except Exception:
                continue
            try:
                o = float(r.get("o"))
                h = float(r.get("h"))
                l = float(r.get("l"))
                c = float(r.get("c"))
            except Exception:
                continue
            out = {
                "_time": iso,
                "time_sec": tsec,
                "o": o,
                "h": h,
                "l": l,
                "c": c,
                "v": int(r.get("v", 0)) if r.get("v") is not None else 0,
                "vw": float(r.get("vw", 0.0)) if r.get("vw") is not None else 0.0,
                "n": int(r.get("n", 0)) if r.get("n") is not None else 0,
            }
            clean.append(out)
        clean.sort(key=lambda x: x["time_sec"])
        return jsonify(clean)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... existing code ...

@api_bp.get("/indicators")
def indicators():
    """
    Return technical indicators from ta_1d/ta_1m.
    Query params:
      - symbol: required, e.g., X:BTCUSD
      - granularity: day|minute (default: day)
      - start, end: ISO8601 timestamps, required
      - fields: optional comma-separated subset of [bb_l,bb_m,bb_u,macd,macds,macdh,rsi]
    """
    symbol = request.args.get("symbol")
    gran = request.args.get("granularity", "day")
    start = request.args.get("start")
    end = request.args.get("end")
    fields_param = request.args.get("fields", "")

    if not symbol or not start or not end:
        return jsonify({"error": "symbol, start, end required"}), 400

    measurement = "ta_1d" if gran == "day" else "ta_1m"
    all_fields = ["bb_l", "bb_m", "bb_u", "macd", "macds", "macdh", "rsi"]
    if fields_param.strip():
        req_fields = [f.strip() for f in fields_param.split(",") if f.strip()]
        keep_fields = [f for f in req_fields if f in all_fields]
        if not keep_fields:
            return jsonify({"error": "invalid fields; allowed: " + ",".join(all_fields)}), 400
    else:
        keep_fields = all_fields

    # Build Flux to pivot fields to columns and keep only requested ones
    cols = '","'.join(["_time"] + keep_fields)
    flux = f'''
from(bucket: "{settings.INFLUX_BUCKET}")
  |> range(start: time(v: "{start}"), stop: time(v: "{end}"))
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> filter(fn: (r) => r.symbol == "{symbol}")
  |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> keep(columns: ["{cols}"])
  |> sort(columns: ["_time"], desc: false)
'''
    try:
        rows = query_flux(flux)
        # Sanitize: drop rows with missing time; coerce numeric fields; sort asc
        clean = []
        for r in rows or []:
            t = r.get("_time")
            if not t:
                continue
            try:
                if isinstance(t, str):
                    dt = datetime.fromisoformat(t.replace("Z", "+00:00"))
                else:
                    dt = t if isinstance(t, datetime) else None
                    if dt is None:
                        continue
                dt = dt.astimezone(timezone.utc)
                iso = dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
                tsec = int(dt.timestamp())
            except Exception:
                continue
            out = {"_time": iso, "time_sec": tsec}
            any_valid = False
            for f in keep_fields:
                val = r.get(f)
                if val is None:
                    continue
                try:
                    out[f] = float(val)
                    any_valid = True
                except Exception:
                    pass
            if any_valid:
                clean.append(out)
        clean.sort(key=lambda x: x["time_sec"])
        return jsonify(clean)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
