"""Two layers, per the project's own verification standard: synthetic
unit tests for the anomaly math itself (a constructed outlier, since real
data may or may not contain one — see the real-data tests below for
whether it actually does), and a real-data test that checks whether
detect_anomalies() actually fires on Ethan's live-ingested Phase 1/2 data,
not just that it's structurally correct.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cross_cloud_spend_trace_analytics.anomaly import detect_anomalies
from cross_cloud_spend_trace_analytics.ingest import read_raw_store
from cross_cloud_spend_trace_analytics.unified_model import enrich_events

REAL_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


# --- Synthetic: math correctness ---------------------------------------


def test_flags_a_constructed_outlier(spark):
    # One group, 6 normal values clustered around 100, one way out at 1000.
    rows = [("g1", v) for v in [98.0, 101.0, 99.0, 102.0, 100.0, 1000.0]]
    df = spark.createDataFrame(rows, ["grp", "val"])
    out = detect_anomalies(
        df, group_cols=["grp"], value_col="val", z_threshold=3.0, min_group_size=3
    )
    results = {r.val: r for r in out.collect()}
    assert results[1000.0].status == "anomaly"
    assert results[1000.0].z_score > 3.0
    # The 5 normal values (each one's own leave-one-out baseline includes
    # the 1000.0 outlier, since it's "everyone else") should still not
    # cross the threshold themselves.
    for v in [98.0, 101.0, 99.0, 102.0, 100.0]:
        assert results[v].status != "anomaly"


def test_insufficient_baseline_below_min_group_size(spark):
    rows = [("g1", 1.0), ("g1", 2.0), ("g1", 1000.0)]  # only 3 rows total
    df = spark.createDataFrame(rows, ["grp", "val"])
    out = detect_anomalies(
        df, group_cols=["grp"], value_col="val", z_threshold=3.0, min_group_size=5
    )
    statuses = {r.status for r in out.collect()}
    assert statuses == {"insufficient_baseline"}


def test_zero_variance_baseline_is_not_an_anomaly(spark):
    # Every value identical (AWS's real flat-daily-cost pattern) — a value
    # equal to a zero-variance baseline must not divide-by-zero into an
    # anomaly.
    rows = [("g1", 5.0)] * 8
    df = spark.createDataFrame(rows, ["grp", "val"])
    out = detect_anomalies(
        df, group_cols=["grp"], value_col="val", z_threshold=3.0, min_group_size=3
    )
    for r in out.collect():
        assert r.status == "normal"
        assert r.z_score == 0.0


def test_zero_variance_baseline_with_one_real_deviation(spark):
    # 7 identical values + 1 that deviates from a zero-stddev baseline —
    # infinite z (any deviation from a perfectly flat baseline is
    # meaningful), correctly flagged rather than silently skipped.
    rows = [("g1", 5.0)] * 7 + [("g1", 5.5)]
    df = spark.createDataFrame(rows, ["grp", "val"])
    out = detect_anomalies(
        df, group_cols=["grp"], value_col="val", z_threshold=3.0, min_group_size=3
    )
    results = {r.val: r.status for r in out.collect()}
    assert results[5.5] == "anomaly"


# --- Real data: does it actually fire? ----------------------------------

pytestmark_real = pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)


@pytestmark_real
def test_real_snowflake_query_anomaly_actually_fires(spark):
    """This is the one grain with enough real volume/variance to actually
    demonstrate the mechanism firing on genuine data, not just structural
    correctness — see docs/decisions/0003 for the honest breakdown of
    which grains do/don't have enough data yet."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    queries = df.filter((df.source == "snowflake") & (df.resource_type == "query"))

    scored = detect_anomalies(
        queries,
        group_cols=["account_identifier", "usage_date"],
        value_col="usage_quantity",
        z_threshold=3.0,
        min_group_size=5,
    )
    anomalies = scored.filter(scored.status == "anomaly").collect()
    assert len(anomalies) >= 1

    # Real: query_id 01c659... (see docs/roadmap.md) on SPEND_LENS_WH, a
    # 3-table-free JOIN with LIMIT 20 and no WHERE clause, ran in ~11.9s
    # against a warehouse whose other same-day queries ran in tens to a
    # few thousand ms — a genuine, real statistical outlier.
    slowest = max(anomalies, key=lambda r: r.usage_quantity)
    assert slowest.usage_quantity > 10_000  # milliseconds
    assert slowest.z_score > 3.0


@pytestmark_real
def test_real_databricks_has_insufficient_baseline(spark):
    """Honest negative result: exactly one real Databricks job run exists
    in the live-ingested data so far, so its own-history baseline can never
    be computed — detect_anomalies() must say so explicitly rather than
    reporting a misleading "normal"."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    jobs = df.filter(df.source == "databricks")
    assert jobs.count() == 1

    scored = detect_anomalies(
        jobs,
        group_cols=["account_identifier"],
        value_col="usage_quantity",
        z_threshold=3.0,
        min_group_size=5,
    )
    statuses = [r.status for r in scored.collect()]
    assert statuses == ["insufficient_baseline"]


@pytestmark_real
def test_real_aws_daily_service_cost_has_no_anomaly_yet(spark):
    """Honest negative result: AWS's real daily S3 cost is exactly flat
    ($0.000005/day for 14 consecutive days, see docs/roadmap.md) — a
    genuinely zero-variance baseline, so nothing crosses the threshold.
    Structurally correct and exercised against real data; just nothing to
    flag yet because nothing in this window actually spiked."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    aws_daily = df.filter((df.source == "aws") & (df.resource_type == "cost_explorer_daily_service"))

    scored = detect_anomalies(
        aws_daily,
        group_cols=["service"],
        value_col="cost_usd",
        z_threshold=3.0,
        min_group_size=5,
    )
    anomalies = scored.filter(scored.status == "anomaly").collect()
    assert len(anomalies) == 0
