``` bash
# Show services/containers in the current compose project
docker compose ps

# Only IDs (handy for counting)
docker compose ps -q

# Count running containers in this project
docker compose ps -q | wc -l
```
List all running containers on the host (not just Compose)
``` bash
docker ps
docker ps -q | wc -l
```
List all containers (including stopped) for this project
``` bash
docker compose ps -a
```
See processes inside containers (per-service breakdown)
``` bash
docker compose top
```
See logs
``` bash
# All services (follow)
docker compose logs -f

# Specific service (follow)
docker compose logs -f frontend
docker compose logs -f app
docker compose logs -f mongo
docker compose logs -f influxdb
```
Start/stop
``` bash
# Start in background
docker compose up -d

# Stop containers (keep them)
docker compose stop

# Stop and remove containers, networks, and volumes created by compose
docker compose down
docker compose down -v   # also remove named/anonymous volumes
```
Exec a shell in a running service
``` bash
docker compose exec frontend sh
docker compose exec app sh
docker compose exec mongo sh
```
List compose projects on the host (if multiple)
``` bash
docker compose ls
```

## AI Assistant
Got it. Here’s a quick, practical guide to how your containers fit together and answers to the most common questions you’re likely to have with this setup.
What containers you have (per docker-compose.yml)
- app: Python backend (Flask). Built from your root Dockerfile.
- mongo: MongoDB database (official image).
- influxdb: InfluxDB v2 (official image).
- streamer: Your Python WebSocket streamer (reuses the same app image; runs a different command).
- frontend: Node-based dev server (Vite) for the Vue/Vuetify app. Runs on port 5173.
- node_cli: Helper container to open a Node shell in the frontend folder for one-off npm commands.

About the two frontend modes
- Dev mode (current compose frontend service)
    - Uses image: node:20, mounts ./frontend/frontend-app, runs npm run dev, binds 0.0.0.0, exposes 5173.
    - Pros: hot reload, simple local development.
    - Where to access: [http://localhost:5173](http://localhost:5173)

- Prod mode (your frontend/Dockerfile)
    - Multi-stage build: Node builds assets → Nginx serves static files.
    - Pros: small, fast static server; no Node/npm at runtime.
    - Where to access (if you use it): map container 80 to a host port (e.g., 8080).

How to switch between Dev and Prod for the frontend
- Dev (Vite): keep your current compose frontend service as-is (Node image, command runs npm dev).
- Prod (Nginx):
    - Change the frontend service to build from ./frontend and remove npm dev command, user, and volume.
    - Example:
        - ports: "8080:80"
        - build: ./frontend
        - no volumes, no working_dir, no user.

    - Run with docker compose up -d --build frontend, then open [http://localhost:8080](http://localhost:8080).

Installing npm packages
- Node shell with project mounted:
    - docker compose run --rm node_cli
    - Inside: npm install [--save-dev]

- Or exec into dev server:
    - docker compose exec frontend sh
    - Inside: npm install [--save-dev]

- Tip: make sure your frontend folder is owned by your host user to avoid EACCES:
    - sudo chown -R "(id -u)":"(id -g)" ./frontend/frontend-app
    - export HOST_UID=(id -u); export HOST_GID=(id -g) before compose commands

Common pitfalls and fixes
- npm not found in frontend: means you’re running the Nginx image (prod) but trying to run npm (dev). Use Node image for dev; use the Nginx image for prod—and don’t run npm in prod containers.
- EACCES writing package-lock.json or node_modules: host folder permissions mismatch. chown the frontend folder and run containers as your user (user: {HOST_UID}:{HOST_GID}).
- App not loading at localhost:3000: Vite defaults to 5173; Vue CLI used 8080. Use the port your dev server actually binds to (5173 with Vite).
- Mounting node_modules: avoid mounting a separate node_modules path. Either let it live under the project folder on the host, or use a named Docker volume specifically for node_modules.

How containers talk to each other (networking)
- Services share a default Docker network. Use service names as hosts:
    - Backend to InfluxDB: [http://influxdb:8086](http://influxdb:8086)
    - Backend to MongoDB: mongodb://mongo:27017/...

- The frontend (dev server) talks to the backend via [http://localhost:5000](http://localhost:5000) from your browser. If you call from inside a container, use [http://app:5000](http://app:5000).

Useful commands to manage containers quickly
- See what’s running: docker compose ps
- Logs: docker compose logs -f frontend (or app, mongo, influxdb)
- Start/stop:
    - docker compose up -d frontend
    - docker compose stop frontend

- Rebuild specific: docker compose build frontend
- Clean slate for compose project (removes containers/networks/volumes defined here): docker compose down -v

If you share your specific questions (e.g., “how do I X with container Y?”), I’ll tailor exact commands for your workflow.


## Me
So, for the flask/influx/mongo I just run docker compose up --build right?

## AI Assistant
Yes. From your project root, this will build images and start everything defined in docker-compose.yml:
- Build and start all services in background:
``` bash
docker compose up --build -d
```
If you only want the backend stack (Flask + InfluxDB + Mongo + streamer) without the frontend:
``` bash
docker compose up --build -d app mongo influxdb streamer
```
Useful follow-ups:
- Check what’s running:
``` bash
docker compose ps
```
- Tail logs (service-specific):
``` bash
docker compose logs -f app
docker compose logs -f influxdb
docker compose logs -f mongo
docker compose logs -f streamer
```
- Health endpoints:
    - Flask app: [http://localhost:5000/health](http://localhost:5000/health)
    - Influx API (UI): [http://localhost:8086](http://localhost:8086)

To stop later:
``` bash
docker compose stop    # stop containers, keep them
# or
docker compose down    # stop and remove containers/network (keeps named volumes)
```

*******

How to run (examples)
- Daily indicators:
``` bash
docker compose run --rm app python scripts/compute_indicators.py \
  --symbol X:BTCUSD --granularity day \
  --start 2023-01-01T00:00:00Z --end 2023-12-31T23:59:59Z
```
- Minute indicators:
``` bash
docker compose run --rm app python scripts/compute_indicators.py \
  --symbol X:BTCUSD --granularity minute \
  --start 2023-08-01T00:00:00Z --end 2023-08-07T23:59:59Z
```

Here’s how to test the indicators API in Postman.
Prereqs
- Backend is running: docker compose up -d app
- InfluxDB has indicator data in ta_1d/ta_1m (you already ran the compute_indicators script)
- Base URL: [http://localhost:5000](http://localhost:5000)

Endpoint
- Method: GET
- URL: [http://localhost:5000/api/indicators](http://localhost:5000/api/indicators)
- Query params:
    - symbol: required. Example: X:BTCUSD
    - granularity: day or minute (default day)
    - start: ISO8601 start time. Example: 2023-01-01T00:00:00Z
    - end: ISO8601 end time. Example: 2023-12-31T23:59:59Z
    - fields: optional comma-separated list among bb_l, bb_m, bb_u, macd, macds, macdh, rsi

Postman setup
1. New request → GET.
2. URL: [http://localhost:5000/api/indicators](http://localhost:5000/api/indicators)
3. Params tab:
    - symbol = X:BTCUSD
    - granularity = day
    - start = 2023-01-01T00:00:00Z
    - end = 2023-12-31T23:59:59Z
    - fields = bb_l,bb_m,bb_u,macd,macds,macdh,rsi (optional)

4. Send.

Example requests
- Full set (daily): [http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=day&start=2023-01-01T00:00:00Z&end=2023-12-31T23:59:59Z](http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=day&start=2023-01-01T00:00:00Z&end=2023-12-31T23:59:59Z)
- Subset of fields (minute): [http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=minute&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&fields=rsi,macd,macds](http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=minute&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&fields=rsi,macd,macds)

What you should see
- JSON array of rows (each row is a record with _time and requested fields). Example shape:

Common issues
- 400 error: “symbol, start, end required”
    - Ensure all three params are set.

- Empty array:
    - No indicator data in the given time range; verify you computed and wrote indicators for that symbol/granularity.

- Wrong granularity:
    - day reads from ta_1d, minute reads from ta_1m. Use the same you computed.

- Time format:
    - Use ISO8601 (e.g., 2023-01-01T00:00:00Z). Avoid bare dates unless the route supports them.

Quick curl equivalents
- Full daily: curl "[http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=day&start=2023-01-01T00:00:00Z&end=2023-12-31T23:59:59Z](http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=day&start=2023-01-01T00:00:00Z&end=2023-12-31T23:59:59Z)"
- Minute subset: curl "[http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=minute&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&fields=rsi,macd,macds](http://localhost:5000/api/indicators?symbol=X:BTCUSD&granularity=minute&start=2025-01-01T00:00:00Z&end=2025-01-02T00:00:00Z&fields=rsi,macd,macds)"

Tip
- If you later protect APIs with JWT, add an Authorization header in Postman: Authorization: Bearer
