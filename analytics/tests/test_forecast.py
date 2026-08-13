from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from cross_cloud_spend_trace_analytics.forecast import (
    daily_cost_actuals,
    month_end_forecast,
    native_unit_forecast,
    reconcile_with_aws_native_forecast,
)
from cross_cloud_spend_trace_analytics.ingest import read_raw_store
from cross_cloud_spend_trace_analytics.unified_model import enrich_events

REAL_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


# --- Synthetic: run-rate/trend math correctness --------------------------


def test_run_rate_projection_on_constructed_flat_series(spark):
    rows = [
        ("demo", d, cost, "billed")
        for d, cost in zip(["2026-02-01", "2026-02-02", "2026-02-03", "2026-02-04"], [10.0] * 4)
    ]
    df = spark.createDataFrame(rows, ["source", "usage_date", "cost_usd", "cost_basis"])
    df = df.withColumn("usage_date", df.usage_date.cast("date"))

    out = month_end_forecast(df, as_of=date(2026, 2, 4)).collect()
    assert len(out) == 1
    row = out[0]
    assert row.days_observed == 4
    assert row.total_so_far == pytest.approx(40.0)
    assert row.run_rate_per_day == pytest.approx(10.0)
    assert row.days_in_month == 28  # Feb 2026 is not a leap year
    assert row.run_rate_month_end_projection == pytest.approx(280.0)
    assert row.status == "ok"


def test_trend_diverges_from_run_rate_on_constructed_growth(spark):
    # Cost doubling each day — trend (fit to the growth curve) should
    # project higher than the flat historical-average run-rate.
    rows = [
        ("demo", d, cost, "billed")
        for d, cost in zip(
            ["2026-03-01", "2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05"],
            [1.0, 2.0, 3.0, 4.0, 5.0],
        )
    ]
    df = spark.createDataFrame(rows, ["source", "usage_date", "cost_usd", "cost_basis"])
    df = df.withColumn("usage_date", df.usage_date.cast("date"))

    row = month_end_forecast(df, as_of=date(2026, 3, 5)).collect()[0]
    assert row.run_rate_month_end_projection == pytest.approx(
        (15.0 / 5) * 31
    )  # avg 3/day * 31 days = 93
    # Cumulative = 1,3,6,10,15 at day 1..5 -> slope=3.5, intercept=-3.5
    # trend at day 31 = -3.5 + 3.5*31 = 105.0
    assert row.trend_month_end_projection == pytest.approx(105.0, rel=1e-6)
    assert row.trend_month_end_projection > row.run_rate_month_end_projection


def test_insufficient_history_below_two_days(spark):
    rows = [("demo", "2026-04-01", 5.0, "billed")]
    df = spark.createDataFrame(rows, ["source", "usage_date", "cost_usd", "cost_basis"])
    df = df.withColumn("usage_date", df.usage_date.cast("date"))
    row = month_end_forecast(df, as_of=date(2026, 4, 1)).collect()[0]
    assert row.days_observed == 1
    assert row.trend_month_end_projection is None
    assert row.confidence == "low"
    # run-rate is still computable from a single day, just low-confidence
    assert row.run_rate_month_end_projection == pytest.approx(5.0 * 30)


def test_no_cost_data_status_when_group_has_none(spark):
    from pyspark.sql.types import DoubleType, StringType, StructField, StructType

    schema = StructType(
        [
            StructField("source", StringType(), True),
            StructField("usage_date", StringType(), True),
            StructField("cost_usd", DoubleType(), True),
            StructField("cost_basis", StringType(), True),
        ]
    )
    rows = [("snowflake", "2026-04-01", None, None)]
    df = spark.createDataFrame(rows, schema)
    df = df.withColumn("usage_date", df.usage_date.cast("date"))
    out = month_end_forecast(df, as_of=date(2026, 4, 1)).collect()
    # No rows survive daily_cost_actuals() (cost_usd is null / cost_basis
    # doesn't match ACTUAL_COST_BASES) so there's nothing to group —
    # confirms this doesn't silently fabricate a $0 row.
    assert out == []


# --- Real data -------------------------------------------------------


REAL = pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)


@REAL
def test_real_aws_month_end_forecast(spark):
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    # Real: the AWS collector landed 11 real August days (Aug 1-11 2026)
    # of flat $0.0000046448/day S3 cost — see docs/roadmap.md Phase 2 entry.
    row = month_end_forecast(df, as_of=date(2026, 8, 12), group_cols=["source"]).filter(
        "source = 'aws'"
    ).collect()[0]
    assert row.days_observed == 11
    assert row.status == "ok"
    assert row.run_rate_per_day == pytest.approx(4.6448e-6, rel=1e-3)
    assert row.run_rate_month_end_projection == pytest.approx(4.6448e-6 * 31, rel=1e-3)
    # Perfectly flat daily cost -> trend extrapolation should agree with
    # run-rate almost exactly (this is the real, honest "they coincide
    # because the real data has zero day-to-day variance" case — see
    # docs/decisions/0003).
    assert row.trend_month_end_projection == pytest.approx(
        row.run_rate_month_end_projection, rel=1e-6
    )


@REAL
def test_real_snowflake_and_databricks_have_no_cost_data(spark):
    """Honest negative result: Snowflake's collector never populates
    cost_usd (decision 0002 item 5) and Databricks' one real run has
    cost_usd=None (decision 0002 item 6) — confirms neither source
    contributes a fabricated forecast row."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    rows = {
        r.source: r for r in month_end_forecast(df, as_of=date(2026, 8, 12)).collect()
    }
    assert "snowflake" not in rows
    assert "databricks" not in rows


@REAL
def test_real_snowflake_native_unit_run_rate(spark):
    """Snowflake has no dollar cost but does have real credit burn —
    native_unit_forecast() should still produce a real (non-dollar)
    run-rate from the actual WAREHOUSE_METERING_HISTORY data."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    rows = native_unit_forecast(df, as_of=date(2026, 8, 12)).filter(
        "source = 'snowflake' and usage_unit = 'credits'"
    ).collect()
    assert len(rows) == 1
    assert rows[0].total_so_far > 0


@REAL
def test_real_combined_forecast_equals_aws_only(spark):
    """Combined (all sources) forecast should equal AWS's forecast today,
    explicitly — not silently imply Snowflake/Databricks contributed
    dollars they don't have."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    combined = month_end_forecast(df, as_of=date(2026, 8, 12), group_cols=[]).collect()
    aws_only = (
        month_end_forecast(df, as_of=date(2026, 8, 12), group_cols=["source"])
        .filter("source = 'aws'")
        .collect()
    )
    assert len(combined) == 1
    assert combined[0].run_rate_month_end_projection == pytest.approx(
        aws_only[0].run_rate_month_end_projection, rel=1e-9
    )


@REAL
def test_real_aws_native_forecast_reconciliation(spark):
    """AWS's own real, already-landed Cost Explorer forecast record
    (data/raw/aws/cost_forecast) surfaced alongside our computed
    projection for comparison, not blindly trusted or discarded."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    aws_row = month_end_forecast(df, as_of=date(2026, 8, 12), group_cols=["source"]).filter(
        "source = 'aws'"
    )
    reconciled = reconcile_with_aws_native_forecast(aws_row, df).collect()[0]
    # Real value landed by the AWS collector in Phase 2 (see
    # docs/roadmap.md): Cost Explorer's own forecast for 2026-08-13 ->
    # 2026-09-01 was $0.0000511.
    assert reconciled.aws_native_forecast_usd == pytest.approx(5.10928e-5, rel=1e-3)
