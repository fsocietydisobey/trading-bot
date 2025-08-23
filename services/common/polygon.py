import time
import json
import math
import urllib.parse
import urllib.request
import urllib.error


def _polygon_get(url, timeout=30):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def list_aggregates(
        api_key,
        symbol,
        multiplier,
        timespan,
        start,
        end,
        adjusted=True,
        sort="asc",
        limit=50000,
        backoff_initial=0.5,
        backoff_max=8.0,
):
    """
    Generator over Polygon aggregate bars (REST).
    Normalizes output to a dict with open, high, low, close, volume, vwap, transactions, timestamp (ns).
    """
    base = f"https://api.polygon.io/v2/aggs/ticker/{urllib.parse.quote(symbol)}/range/{multiplier}/{timespan}/{start}/{end}"
    params = {
        "adjusted": str(adjusted).lower(),
        "sort": sort,
        "limit": str(limit),
        "apiKey": api_key,
    }
    url = base + "?" + urllib.parse.urlencode(params)

    backoff = backoff_initial
    next_url = url

    while next_url:
        try:
            data = _polygon_get(next_url)
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(backoff)
                backoff = min(backoff * 2, backoff_max)
                continue
            body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Polygon error: {e.code} {body}") from e

        results = data.get("results") or []
        for r in results:
            # Polygon fields: t=timestamp(ms), o,h,l,c,v, vw, n
            ts_ms = int(r.get("t"))
            yield {
                "symbol": symbol,
                "timestamp": ts_ms * 1_000_000,  # ns
                "open": float(r.get("o", 0.0)),
                "high": float(r.get("h", 0.0)),
                "low": float(r.get("l", 0.0)),
                "close": float(r.get("c", 0.0)),
                "volume": int(r.get("v", 0)),
                "vwap": float(r.get("vw", 0.0)),
                "transactions": int(r.get("n", 0)),
            }

        # Pagination: use "next_url" if present
        next_url = data.get("next_url")
        if next_url:
            # next_url is partial; append apiKey
            sep = "&" if "?" in next_url else "?"
            next_url = f"https://api.polygon.io{next_url}{sep}apiKey={api_key}"


def normalize_ws_aggregate(ev):
    """
    Normalize a Polygon XA (aggregate) event into a bar dict compatible with point_bar.
    Example fields from Polygon XA:
      ev: 'XA', pair: 'X:BTCUSD', o,h,l,c,v, vw, n, s (start ms), e (end ms)
    """
    if ev.get("ev") != "XA":
        return None
    ts_ms = int(ev.get("s") or ev.get("t") or 0)
    return {
        "symbol": ev.get("pair"),
        "timestamp": ts_ms * 1_000_000,  # ns
        "open": float(ev.get("o", 0.0)),
        "high": float(ev.get("h", 0.0)),
        "low": float(ev.get("l", 0.0)),
        "close": float(ev.get("c", 0.0)),
        "volume": int(ev.get("v", 0)),
        "vwap": float(ev.get("vw", 0.0)),
        "transactions": int(ev.get("n", 0)),
    }
