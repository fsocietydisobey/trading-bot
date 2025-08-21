# db/influx.py
import os
from typing import Dict, Any, List, Optional
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

def get_influxdb_client():
    url = os.environ.get("INFLUX_URL")
    token = os.environ.get("INFLUX_TOKEN")
    org = os.environ.get("INFLUX_ORG")
    bucket = os.environ.get("INFLUX_BUCKET")
    if not all([url, token, org, bucket]):
        raise RuntimeError("InfluxDB env vars missing (INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET)")
    client = InfluxDBClient(url=url, token=token, org=org)
    return client, org, bucket

def write_point(
    measurement: str,
    tags: Dict[str, str],
    fields: Dict[str, Any],
    timestamp_ns: Optional[int] = None  # pass ns epoch for precise control
):
    client, org, bucket = get_influxdb_client()
    try:
        p = Point(measurement)
        for k, v in (tags or {}).items():
            p = p.tag(k, v)
        for k, v in (fields or {}).items():
            p = p.field(k, v)
        if timestamp_ns is not None:
            p = p.time(timestamp_ns, WritePrecision.NS)
        # else: client sets server time
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=bucket, org=org, record=p)
    finally:
        client.close()

def write_points_batch(points: List[Point]):
    client, org, bucket = get_influxdb_client()
    try:
        write_api = client.write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=bucket, org=org, record=points)
    finally:
        client.close()

def query_flux(query: str) -> List[dict]:
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