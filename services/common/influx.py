# Uses official InfluxDB Python client but keeps the same function names
# services/common/influx.py
import asyncio
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from config.settings import settings


def get_influxdb_client():
    url = settings.INFLUX_URL
    token = settings.INFLUX_TOKEN
    org = settings.INFLUX_ORG
    bucket = settings.INFLUX_BUCKET
    if not all([url, token, org, bucket]):
        raise RuntimeError("InfluxDB settings missing (INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET)")
    client = InfluxDBClient(url=url, token=token, org=org)
    return client, org, bucket


def get_write_api(client=None, mode="sync"):
    if client is None:
        client, _, _ = get_influxdb_client()
    if mode == "async":
        return client.write_api(write_options=ASYNCHRONOUS)
    return client.write_api(write_options=SYNCHRONOUS)


def point_from_bar(measurement, tags, bar):
    p = Point(measurement)
    for k, v in (tags or {}).items():
        p = p.tag(k, v)
    p = (
        p.field("o", float(bar["open"]))
        .field("h", float(bar["high"]))
        .field("l", float(bar["low"]))
        .field("c", float(bar["close"]))
        .field("v", int(bar.get("volume", 0)))
        .field("vw", float(bar.get("vwap", 0.0)))
        .field("n", int(bar.get("transactions", 0)))
    )
    # bar["timestamp"] expected in ns
    p = p.time(int(bar["timestamp"]), WritePrecision.NS)
    return p


def write_points_batch(points):
    if not points:
        return
    client, org, bucket = get_influxdb_client()
    try:
        write_api = get_write_api(client, mode="sync")
        write_api.write(bucket=bucket, org=org, record=points)
    finally:
        client.close()


def write_points_batch_async(points):
    if not points:
        return
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, write_points_batch, points)


def query_flux(query):
    client, org, _ = get_influxdb_client()
    try:
        result = client.query_api().query(org=org, query=query)
        rows = []
        for table in result:
            for record in table.records:
                rows.append(record.values)
        return rows
    finally:
        client.close()
