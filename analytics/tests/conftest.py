from __future__ import annotations

from pathlib import Path

import pytest
from pyspark.sql import SparkSession

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_RAW_DIR = REPO_ROOT / "data" / "raw"


@pytest.fixture(scope="session")
def spark():
    session = (
        SparkSession.builder.appName("spend-lens-analytics-tests")
        .master("local[2]")
        .config("spark.ui.enabled", "false")
        .config("spark.sql.shuffle.partitions", "2")
        .getOrCreate()
    )
    session.sparkContext.setLogLevel("WARN")
    yield session
    session.stop()


@pytest.fixture(scope="session")
def has_real_raw_data() -> bool:
    """True only if Phase 1/2's real, live-ingested raw store is present on
    this machine — tests gated on this run against Ethan's real AWS/
    Snowflake/Databricks data, not a synthetic fixture."""
    return any(REAL_RAW_DIR.glob("*/*/*/*.parquet"))
