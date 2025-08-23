import json
import logging
import asyncio
import websockets

from config.settings import settings
from services.streamer.polygon_ws import stream_polygon
from services.common.auth import verify_jwt

logger = logging.getLogger("fanout_ws")
logging.basicConfig(level=logging.INFO)


class Hub:
    def __init__(self):
        self.clients = set()

    async def register(self, ws):
        self.clients.add(ws)

    async def unregister(self, ws):
        self.clients.discard(ws)

    async def broadcast(self, message):
        if not self.clients:
            return
        dead = []
        payload = json.dumps(message)
        for ws in list(self.clients):
            try:
                await ws.send(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.unregister(ws)


async def client_handler(ws, path, hub):
    # Simple JWT auth via header or ?token=
    token = None
    try:
        auth_header = ws.request_headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        else:
            if "?" in path:
                from urllib.parse import parse_qs, urlparse
                qs = parse_qs(urlparse(path).query)
                token = (qs.get("token") or [None])[0]
        verify_jwt(token)
    except Exception:
        await ws.close(code=4401, reason="Unauthorized")
        return

    await hub.register(ws)
    try:
        async for _ in ws:
            pass  # push-only server
    finally:
        await hub.unregister(ws)


async def run():
    hub = Hub()
    queue = asyncio.Queue(maxsize=20000)

    symbols = [s.strip() for s in settings.STREAM_SYMBOLS.split(",") if s.strip()]

    async def fanout_loop():
        while True:
            msg = await queue.get()
            await hub.broadcast(msg)

    host, port = settings.WS_BIND_HOST, settings.WS_BIND_PORT
    server = await websockets.serve(lambda ws, path: client_handler(ws, path, hub), host, port)
    logger.info("Fanout WS server listening on ws://%s:%s", host, port)

    streamer_task = asyncio.create_task(stream_polygon(queue=queue, symbols=symbols))
    fanout_task = asyncio.create_task(fanout_loop())

    await asyncio.gather(server.wait_closed(), streamer_task, fanout_task)


if __name__ == "__main__":
    asyncio.run(run())
