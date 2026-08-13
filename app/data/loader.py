"""Reads Phase 3's already-computed analytics output (`data/processed/`) and
Phase 2's raw landed records (`data/raw/`) directly with pandas/pyarrow, once
at process start, and holds it in memory for the API layer to serve.

**Why read cached Parquet instead of re-running the PySpark pipeline per
request**: `analytics/src/cross_cloud_spend_trace_analytics/pipeline.py`
already computed every real number this dashboard shows (decision 0003) --
spinning up a local Spark session per HTTP request would be slow, heavy
(a JVM per worker), and would recompute results that don't change between
requests (the raw store only grows when a collector is re-run). Reading the
same Parquet files the pipeline already wrote, with pandas, is the simplest
architecture that is still real: every number served here is the literal
output of Phase 3's real pipeline run against Ethan's real ingested data,
not synthesized or faked at the API layer. See
docs/decisions/0006-phase5-dashboard-api-architecture.md.

If Ethan re-runs collectors/the pipeline later, restarting this process (or
calling `reload()`) picks up the new `run_date=`/`ingested_date=` partition
automatically -- no code change needed.
"""
from __future__ import annotations

import glob
import json
import math
import os
from dataclasses import dataclass, field
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import pandas as pd

_HERE = Path(__file__).resolve()
PROJECT_ROOT = _HERE.parent.parent.parent
DATA_ROOT = Path(os.environ.get("CCST_DATA_ROOT", PROJECT_ROOT / "data"))
RAW_ROOT = DATA_ROOT / "raw"
PROCESSED_ROOT = DATA_ROOT / "processed"


def _latest_partition_files(table_root: Path, partition_prefix: str) -> list[Path]:
    """Every table is partitioned `table_root/<partition_prefix>=YYYY-MM-DD/`.
    Reads the *latest* partition only (matching how the Phase 3 pipeline
    itself is a point-in-time run) -- real files, not synthetic."""
    if not table_root.is_dir():
        return []
    partitions = sorted(table_root.glob(f"{partition_prefix}=*"))
    if not partitions:
        return []
    latest = partitions[-1]
    return sorted(latest.glob("*.parquet"))


def _read_latest(table_root: Path, partition_prefix: str) -> pd.DataFrame:
    files = _latest_partition_files(table_root, partition_prefix)
    if not files:
        return pd.DataFrame()
    frames = [pd.read_parquet(f) for f in files]
    return pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]


def _read_all_partitions(table_root: Path, partition_prefix: str) -> pd.DataFrame:
    """Unlike _read_latest, reads every dated partition and concatenates --
    used for raw tables where a collector may have run more than once and
    every real landed record should count, not just the newest run."""
    if not table_root.is_dir():
        return pd.DataFrame()
    files = sorted(table_root.glob(f"{partition_prefix}=*/*.parquet"))
    if not files:
        return pd.DataFrame()
    frames = [pd.read_parquet(f) for f in files]
    return pd.concat(frames, ignore_index=True)


def _clean(value: Any) -> Any:
    """JSON-safe conversion: NaN/NaT -> None, numpy scalars -> native,
    dates/timestamps -> ISO strings, arrays -> lists."""
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        if pd.isna(value):
            return None
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    try:
        import numpy as np

        if isinstance(value, np.ndarray):
            return [_clean(v) for v in value.tolist()]
        if isinstance(value, np.generic):
            v = value.item()
            if isinstance(v, float) and math.isnan(v):
                return None
            return v
    except ImportError:
        pass
    if isinstance(value, float) and pd.isna(value):
        return None
    return value


def df_records(df: pd.DataFrame) -> list[dict[str, Any]]:
    if df.empty:
        return []
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


@dataclass
class Store:
    """Everything the API needs, loaded once."""

    # Phase 3 processed output
    spend_by_source_date: pd.DataFrame = field(default_factory=pd.DataFrame)
    spend_by_attribution: pd.DataFrame = field(default_factory=pd.DataFrame)
    anomalies_daily_cost: pd.DataFrame = field(default_factory=pd.DataFrame)
    anomalies_snowflake_duration: pd.DataFrame = field(default_factory=pd.DataFrame)
    forecast_by_source: pd.DataFrame = field(default_factory=pd.DataFrame)
    forecast_combined: pd.DataFrame = field(default_factory=pd.DataFrame)
    forecast_native_units: pd.DataFrame = field(default_factory=pd.DataFrame)
    forecast_aws_reconciled: pd.DataFrame = field(default_factory=pd.DataFrame)
    optimization_suggestions: pd.DataFrame = field(default_factory=pd.DataFrame)

    # Phase 2 raw counts (for the landing-screen source chips -- decision 0005 section 6)
    raw_counts: dict[str, int] = field(default_factory=dict)
    raw_databricks_job_runs: pd.DataFrame = field(default_factory=pd.DataFrame)

    run_date: str | None = None


def _load() -> Store:
    s = Store()

    s.spend_by_source_date = _read_latest(PROCESSED_ROOT / "spend_by_source_date", "run_date")
    s.spend_by_attribution = _read_latest(PROCESSED_ROOT / "spend_by_attribution", "run_date")
    s.anomalies_daily_cost = _read_latest(PROCESSED_ROOT / "anomalies_daily_cost_by_attribution", "run_date")
    s.anomalies_snowflake_duration = _read_latest(PROCESSED_ROOT / "anomalies_snowflake_query_duration", "run_date")
    s.forecast_by_source = _read_latest(PROCESSED_ROOT / "forecast_by_source", "run_date")
    s.forecast_combined = _read_latest(PROCESSED_ROOT / "forecast_combined", "run_date")
    s.forecast_native_units = _read_latest(PROCESSED_ROOT / "forecast_native_units", "run_date")
    s.forecast_aws_reconciled = _read_latest(PROCESSED_ROOT / "forecast_aws_reconciled", "run_date")
    s.optimization_suggestions = _read_latest(PROCESSED_ROOT / "optimization_suggestions", "run_date")

    partitions = sorted((PROCESSED_ROOT / "spend_by_source_date").glob("run_date=*")) if (
        PROCESSED_ROOT / "spend_by_source_date"
    ).is_dir() else []
    s.run_date = partitions[-1].name.split("=", 1)[1] if partitions else None

    aws_cost = _read_all_partitions(RAW_ROOT / "aws" / "cost_and_usage", "ingested_date")
    aws_forecast = _read_all_partitions(RAW_ROOT / "aws" / "cost_forecast", "ingested_date")
    aws_dims = _read_all_partitions(RAW_ROOT / "aws" / "service_dimension_values", "ingested_date")
    sf_query = _read_all_partitions(RAW_ROOT / "snowflake" / "query_history", "ingested_date")
    sf_wh = _read_all_partitions(RAW_ROOT / "snowflake" / "warehouse_metering_history", "ingested_date")
    db_runs = _read_all_partitions(RAW_ROOT / "databricks" / "job_runs", "ingested_date")

    s.raw_counts = {
        "aws_cost_and_usage": len(aws_cost),
        "aws_cost_forecast": len(aws_forecast),
        "aws_service_dimension_values": len(aws_dims),
        "snowflake_query_history": len(sf_query),
        "snowflake_warehouse_metering_history": len(sf_wh),
        "databricks_job_runs": len(db_runs),
    }
    s.raw_databricks_job_runs = db_runs

    return s


@lru_cache(maxsize=1)
def get_store() -> Store:
    return _load()


def reload_store() -> Store:
    get_store.cache_clear()
    return get_store()


def parse_raw_metadata(raw_metadata: Any) -> dict[str, Any]:
    if not raw_metadata or not isinstance(raw_metadata, str):
        return {}
    try:
        return json.loads(raw_metadata)
    except (json.JSONDecodeError, TypeError):
        return {}
