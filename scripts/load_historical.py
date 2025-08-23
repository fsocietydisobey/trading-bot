#!/usr/bin/env python3
import os
import sys
import time
import click
# scripts/load_historical.py
#!/usr/bin/env python3
import os
import sys
import time
import click

# Ensure project root on path when running via docker compose
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.common.polygon import list_aggregates
from services.common.influx import write_points_batch, point_from_bar
from config.settings import settings

@click.command()
@click.option("--symbol", required=True, help="Ticker symbol (e.g., X:BTCUSD)")
@click.option("--granularity", type=click.Choice(["day", "minute"]), default="day")
@click.option("--start", "start_date", required=True, help="Start date (YYYY-MM-DD)")
@click.option("--end", "end_date", required=True, help="End date (YYYY-MM-DD)")
@click.option("--adjusted", type=bool, default=True, help="Use adjusted aggregates")
@click.option("--batch-size", type=int, default=5000, help="Influx write batch size")
def load(symbol, granularity, start_date, end_date, adjusted, batch_size):
    api_key = settings.POLYGON_API_KEY
    if not api_key:
        raise click.UsageError("POLYGON_API_KEY env var is required")

    measurement = "aggs_1d" if granularity == "day" else "aggs_1m"
    tags = {"symbol": symbol, "source": "polygon", "adjusted": str(adjusted).lower()}

    click.echo(f"Fetching {granularity} aggregates for {symbol} {start_date} -> {end_date} (adjusted={adjusted})")
    total = 0
    batch = []

    for bar in list_aggregates(
        api_key=api_key,
        symbol=symbol,
        multiplier=1,
        timespan=granularity,
        start=start_date,
        end=end_date,
        adjusted=adjusted,
        sort="asc",
        limit=50000,
    ):
        pt = point_from_bar(measurement, tags, bar)
        batch.append(pt)
        if len(batch) >= batch_size:
            write_points_batch(batch)
            total += len(batch)
            batch.clear()
            time.sleep(0.05)

    if batch:
        write_points_batch(batch)
        total += len(batch)

    click.echo(f"Done. Wrote {total} points to Influx '{settings.INFLUX_BUCKET}' in measurement '{measurement}'.")

if __name__ == "__main__":
    load()
