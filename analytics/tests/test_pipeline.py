"""End-to-end pipeline test — runs the full Phase 3 pipeline (unified
model -> anomalies -> forecast -> rules) against Ethan's real, live-
ingested Phase 1/2 raw store and writes real output Parquet under a
temporary directory, then checks the outputs are actually populated with
real numbers (not just that it didn't crash)."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

REAL_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
REAL = pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)


@REAL
def test_full_pipeline_against_real_data(spark, tmp_path):
    from spend_lens_analytics.pipeline import run

    outputs = run(
        raw_dir=str(REAL_RAW_DIR),
        output_dir=str(tmp_path / "processed"),
        as_of=date(2026, 8, 12),
        spark=spark,
    )

    expected_tables = {
        "spend_by_source_date",
        "spend_by_attribution",
        "anomalies_snowflake_query_duration",
        "anomalies_daily_cost_by_attribution",
        "forecast_by_source",
        "forecast_combined",
        "forecast_native_units",
        "forecast_aws_reconciled",
        "optimization_suggestions",
    }
    assert expected_tables <= set(outputs.keys())

    # Written to disk for real, per-table, partitioned by run_date like the
    # raw store's own ingested_date convention.
    for name in expected_tables:
        written = list((tmp_path / "processed" / name / "run_date=2026-08-12").glob("*.parquet"))
        assert written, f"expected a real parquet file for {name}"

    # Spot-check real content, not just presence.
    suggestions = outputs["optimization_suggestions"].collect()
    assert len(suggestions) >= 4  # all 4 rules fired on this real dataset

    anomalies = outputs["anomalies_snowflake_query_duration"].filter(
        "status = 'anomaly'"
    ).collect()
    assert len(anomalies) >= 1

    aws_forecast = outputs["forecast_by_source"].filter("source = 'aws'").collect()
    assert len(aws_forecast) == 1
    assert aws_forecast[0].run_rate_month_end_projection > 0
