import json
import asyncio
import logging
import websockets

from config.settings import settings
from services.common.influx import get_influxdb_client, get_write_api, point_from_bar
from services.common.polygon import normalize_ws_aggregate

logger = logging.getLogger("polygon_ws")
logging.basicConfig(level=logging.INFO)

# Polygon Crypto WebSocket endpoint. XA events (aggregate bars) are emitted here.
POLYGON_WS = "wss://socket.polygon.io/crypto"

async def stream_polygon(queue, symbols):
    """
    Open a persistent WebSocket connection to Polygon, subscribe to aggregate (XA) events
    for the provided symbols, batch received bars into InfluxDB points, write them periodically,
    and push a compact payload to an internal asyncio queue for fan-out to clients.

    Args:
        queue: asyncio.Queue where compact bar payloads are put for downstream broadcasting.
        symbols: iterable of symbol strings, e.g., ["X:BTCUSD", "X:ETHUSD"].
    """
    api_key = settings.POLYGON_API_KEY
    if not api_key:
        # Fail fast if the API key is not configured
        raise RuntimeError("POLYGON_API_KEY env var is required")

    # Build subscription string for XA (aggregate) channel, e.g., "XA.X:BTCUSD,XA.X:ETHUSD"
    subs = ",".join([f"XA.{s}" for s in symbols])

    # Prepare Influx write API once and reuse the client (lower overhead vs. reconnecting each write)
    client, org, bucket = get_influxdb_client()
    write_api = get_write_api(client, mode="sync")  # synchronous write API for simplicity
    measurement = "aggs_stream"                     # measurement name used in InfluxDB
    default_tags = {"source": "polygon"}            # static tags applied to every point

    try:
        # Reconnect loop: if the WS drops or errors, wait briefly and reconnect
        while True:
            try:
                # Maintain a websocket with periodic pings to keep the connection alive
                async with websockets.connect(POLYGON_WS, ping_interval=20) as ws:
                    # Authenticate and subscribe to XA events for requested symbols
                    await ws.send(json.dumps({"action": "auth", "params": api_key}))
                    await ws.send(json.dumps({"action": "subscribe", "params": subs}))
                    logger.info("Connected and subscribed: %s", subs)

                    # Buffer of Influx points to batch-write for efficiency
                    batch_points = []
                    # Timestamp used to ensure periodic flushing even if the batch is small
                    last_flush = asyncio.get_event_loop().time()

                    # Main receive loop: Polygon sends JSON strings (arrays of events)
                    async for msg in ws:
                        try:
                            data = json.loads(msg)
                        except json.JSONDecodeError:
                            # Ignore malformed messages
                            continue

                        # Polygon typically sends a list of events in one frame
                        if isinstance(data, list):
                            for item in data:
                                # We only care about XA (aggregate) events
                                if item.get("ev") == "XA":
                                    # Normalize Polygon payload to our internal bar dict schema
                                    bar = normalize_ws_aggregate(item)
                                    if not bar:
                                        # Skip if normalization failed or event is not XA
                                        continue

                                    # Build tags per point (symbol-specific + defaults)
                                    tags = {"symbol": bar["symbol"]}
                                    tags.update(default_tags)

                                    # Convert the bar dict into an InfluxDB Point
                                    pt = point_from_bar(measurement, tags, bar)
                                    batch_points.append(pt)

                                    # Also enqueue a compact payload for downstream fan-out (e.g., to WebSocket clients)
                                    await queue.put({
                                        "type": "agg",
                                        "symbol": bar["symbol"],
                                        "t": bar["timestamp"],  # ns
                                        "o": bar["open"],
                                        "h": bar["high"],
                                        "l": bar["low"],
                                        "c": bar["close"],
                                        "v": bar.get("volume", 0),
                                    })

                        # Periodically flush to Influx:
                        # - when batch size reaches 1000 points (throughput optimization)
                        # - or at least every 250 ms (latency bound for near-real-time visibility)
                        now = asyncio.get_event_loop().time()
                        if batch_points and (len(batch_points) >= 1000 or (now - last_flush) > 0.25):
                            write_api.write(bucket=bucket, org=org, record=batch_points)
                            batch_points.clear()
                            last_flush = now

            except Exception as e:
                # Log error and back off briefly before attempting to reconnect.
                # The jitter helps avoid coordinated reconnect storms.
                logger.exception("WS error, reconnecting shortly: %s", e)
                await asyncio.sleep(2.0 + 2.0 * (asyncio.get_event_loop().time() % 1.0))  # jitter
    finally:
        # Ensure the Influx client is closed on task cancellation/shutdown
        client.close()

async def main():
    """
    Entrypoint for running this module directly.
    Reads symbols from settings, creates a queue, and starts the stream.
    """
    # Parse comma-separated symbols from configuration, stripping whitespace and empties
    symbols = [s.strip() for s in settings.STREAM_SYMBOLS.split(",") if s.strip()]

    # Internal queue used to pass compact events to a broadcaster or other consumer
    q = asyncio.Queue(maxsize=10000)

    # Run the streaming task (will loop and reconnect as needed)
    await stream_polygon(queue=q, symbols=symbols)

if __name__ == "__main__":
    # Start the asyncio event loop and run main()
    asyncio.run(main())
