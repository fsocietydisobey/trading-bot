# db/influx.py
# Compatibility shim over services/common/influx.py so legacy imports keep working.
from influxdb_client import Point, WritePrecision  # re-export types used by callers

# Reuse the canonical helpers
from services.common.influx import (
    get_influxdb_client,
    get_write_api,
    point_from_bar,
    write_points_batch,
    write_points_batch_async,
    query_flux,
)

# Back-compat: single-point writer used by some call sites
def write_point(measurement=None, tags=None, fields=None, timestamp_ns=None):
    """
    Write a single point. Accepts either:
      - a pre-built influxdb_client.Point (preferred), or
      - measurement/tags/fields/timestamp_ns to build one.
    """
    if isinstance(measurement, Point):
        point = measurement
    else:
        # Build a Point from provided args
        p = Point(measurement or "measurement")
        for k, v in (tags or {}).items():
            p = p.tag(k, v)
        for k, v in (fields or {}).items():
            p = p.field(k, v)
        if timestamp_ns is not None:
            p = p.time(int(timestamp_ns), WritePrecision.NS)
        point = p
    write_points_batch([point])