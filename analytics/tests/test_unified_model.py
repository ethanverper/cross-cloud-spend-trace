"""Verifies the unified data model against Ethan's real, live-ingested
Phase 1/2 raw store (`data/raw/`) — not synthetic fixtures. Skips (not
fails) if that data isn't present on the machine running the tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from spend_lens_analytics.ingest import read_raw_store
from spend_lens_analytics.unified_model import (
    enrich_events,
    spend_by_attribution,
    spend_by_source_date,
)

REAL_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"


@pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)
def test_reads_all_three_real_sources(spark):
    df = read_raw_store(spark, str(REAL_RAW_DIR))
    sources = {row.source for row in df.select("source").distinct().collect()}
    assert sources == {"aws", "snowflake", "databricks"}
    # Real row counts landed in Phase 2 (see docs/roadmap.md): 29 AWS daily
    # cost rows + 1 forecast + 3 dimension values, 167 Snowflake queries +
    # 4 warehouse-metering rows, 1 Databricks job run = 205 total.
    assert df.count() >= 200


@pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)
def test_enrich_events_extracts_real_snowflake_query_metadata(spark):
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    queries = df.filter((df.source == "snowflake") & (df.resource_type == "query"))
    assert queries.count() == 167

    # Real query text landed by the Snowflake collector against
    # SNOWFLAKE_SAMPLE_DATA.TPCH_SF1 in Phase 1 — confirms metadata_field()
    # actually parses raw_metadata JSON correctly, not just passes it through.
    select_count = queries.filter(queries.query_type == "SELECT").count()
    assert select_count == 92


@pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)
def test_spend_by_source_date_matches_real_aws_daily_cost(spark):
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    daily = spend_by_source_date(df)
    aws_rows = daily.filter(daily.source == "aws").collect()
    # Real AWS Cost Explorer data landed 14 distinct usage dates for the
    # cost_and_usage table, each with a real (if tiny) nonzero S3 cost —
    # see docs/roadmap.md Phase 2 entry.
    assert len(aws_rows) >= 14
    total = sum(r.cost_usd_total for r in aws_rows if r.cost_usd_total is not None)
    assert total > 0


@pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)
def test_spend_by_attribution_has_one_row_per_real_databricks_job(spark):
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    attributed = spend_by_attribution(df)
    db_rows = attributed.filter(attributed.source == "databricks").collect()
    # Real: exactly one Databricks job run landed in Phase 2
    # (job_id=101154624149862), so exactly one attribution row.
    assert len(db_rows) == 1
    assert db_rows[0].attribution_kind == "job"
