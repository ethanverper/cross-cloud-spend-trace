"""Orchestrates the full Phase 3 pipeline: read raw store -> unified model
-> anomaly detection -> month-end forecast -> optimization rules -> write
`data/processed/`. Portable the same way every other module here is: pass
in an existing SparkSession (a Databricks notebook's ambient `spark`) or
let `run()` build a local one for a plain `python -m` invocation — see
`databricks_notebook.py` for the Databricks-side entrypoint that reuses
these exact same functions.
"""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from pyspark.sql import DataFrame, SparkSession

from .anomaly import detect_anomalies
from .forecast import (
    month_end_forecast,
    native_unit_forecast,
    reconcile_with_aws_native_forecast,
)
from .ingest import read_raw_store
from .rules import run_all_rules
from .unified_model import enrich_events, spend_by_attribution, spend_by_source_date

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_outputs(spark: SparkSession, events: DataFrame, as_of: date) -> dict[str, DataFrame]:
    """Runs every Phase 3 stage against an already-read+enriched events
    DataFrame and returns every named output table. Kept side-effect-free
    (no I/O) so tests can call it directly against small in-memory frames."""
    outputs: dict[str, DataFrame] = {}

    outputs["spend_by_source_date"] = spend_by_source_date(events)
    outputs["spend_by_attribution"] = spend_by_attribution(events)

    # Anomaly grain 1: real, currently-firing grain — each Snowflake query
    # scored against every other query run on the same warehouse the same
    # day (see docs/decisions/0003 for why this is the grain that actually
    # has enough volume/variance right now).
    snowflake_queries = events.filter(
        (events.source == "snowflake") & (events.resource_type == "query")
    )
    outputs["anomalies_snowflake_query_duration"] = detect_anomalies(
        snowflake_queries,
        group_cols=["account_identifier", "usage_date"],
        value_col="usage_quantity",
        z_threshold=3.0,
        min_group_size=5,
    )

    # Anomaly grain 2: structural, day-level cost per attribution key
    # across its own history — the grain the roadmap describes ("a
    # day/query/job whose cost is N stddevs above its own recent
    # baseline"), applied to every source uniformly. Currently mostly
    # reports "insufficient_baseline" for Databricks (1 run) and "normal"
    # for AWS (genuinely flat) — see docs/decisions/0003.
    outputs["anomalies_daily_cost_by_attribution"] = detect_anomalies(
        outputs["spend_by_attribution"],
        group_cols=["source", "attribution_key"],
        value_col="cost_usd_total",
        z_threshold=3.0,
        min_group_size=5,
    )

    outputs["forecast_by_source"] = month_end_forecast(events, as_of, group_cols=["source"])
    outputs["forecast_combined"] = month_end_forecast(events, as_of, group_cols=[])
    outputs["forecast_native_units"] = native_unit_forecast(events, as_of)

    aws_forecast_row = outputs["forecast_by_source"].filter("source = 'aws'")
    if aws_forecast_row.take(1):
        outputs["forecast_aws_reconciled"] = reconcile_with_aws_native_forecast(
            aws_forecast_row, events
        )

    outputs["optimization_suggestions"] = run_all_rules(spark, events)

    return outputs


def write_outputs(outputs: dict[str, DataFrame], output_dir: str, run_date: date) -> None:
    for name, df in outputs.items():
        path = f"{output_dir.rstrip('/')}/{name}/run_date={run_date.isoformat()}"
        df.coalesce(1).write.mode("overwrite").parquet(path)
        logger.info("wrote %s -> %s (%d rows)", name, path, df.count())


def run(
    raw_dir: str | None = None,
    output_dir: str | None = None,
    as_of: date | None = None,
    spark: SparkSession | None = None,
) -> dict[str, DataFrame]:
    """Local/plain-Python entrypoint (`python -m spend_lens_analytics.pipeline`).
    On Databricks, don't call this — use `databricks_notebook.py`, which
    calls `build_outputs`/`write_outputs` directly against the notebook's
    ambient `spark` session and a `dbfs:/...` path instead of constructing
    a new session or defaulting to a local filesystem path."""
    owns_session = spark is None
    if spark is None:
        spark = (
            SparkSession.builder.appName("spend-lens-phase3")
            .master("local[*]")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )

    repo_root = Path(__file__).resolve().parents[3]
    raw_dir = raw_dir or str(repo_root / "data" / "raw")
    output_dir = output_dir or str(repo_root / "data" / "processed")
    as_of = as_of or date.today()

    logger.info("reading raw store from %s", raw_dir)
    events = enrich_events(read_raw_store(spark, raw_dir))
    logger.info("read %d raw events", events.count())

    outputs = build_outputs(spark, events, as_of)
    write_outputs(outputs, output_dir, as_of)

    if owns_session:
        spark.stop()

    return outputs


if __name__ == "__main__":
    run()
