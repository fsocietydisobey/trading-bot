#!/usr/bin/env python3
import os
import sys
import click
from typing import Optional

# Local imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.load_historical import load as load_cmd


@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option("--symbols", required=True, help="Comma-separated list, e.g., X:BTCUSD,X:ETHUSD")
@click.option("--granularity", type=click.Choice(["day", "minute"]), default="day")
@click.option("--start", "start_date", required=True)
@click.option("--end", "end_date", required=True)
@click.option("--adjusted", type=bool, default=True)
@click.option("--batch-size", type=int, default=5000)
@click.pass_context
def backfill(ctx: click.Context, symbols: str, granularity: str, start_date: str, end_date: str, adjusted: bool,
             batch_size: int):
    """
    Runs the historical loader for multiple symbols sequentially.
    """
    sym_list = [s.strip() for s in symbols.split(",") if s.strip()]
    for s in sym_list:
        click.echo(f"=== Backfilling {s} ===")
        # Reuse load_historical CLI function programmatically
        ctx.invoke(
            load_cmd,
            symbol=s,
            granularity=granularity,
            start_date=start_date,
            end_date=end_date,
            adjusted=adjusted,
            batch_size=batch_size,
        )
        click.echo(f"=== Done {s} ===")


if __name__ == "__main__":
    backfill()
