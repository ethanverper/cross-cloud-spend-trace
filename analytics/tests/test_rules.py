"""Rules engine tests. Real-data tests are the primary verification per
the project's standard — this rules engine was specifically designed
against what Ethan's actual ingested data contains (see rules.py's
docstring for the honest gap versus the roadmap's literal Databricks
example). Synthetic tests cover quantification math edge cases."""
from __future__ import annotations

from pathlib import Path

import pytest

from cross_cloud_spend_trace_analytics.ingest import read_raw_store
from cross_cloud_spend_trace_analytics.rules import (
    databricks_cost_visibility_gap,
    idle_flat_cost_resource,
    repeated_identical_query,
    run_all_rules,
    unfiltered_table_scan,
)
from cross_cloud_spend_trace_analytics.unified_model import enrich_events

REAL_RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
REAL = pytest.mark.skipif(
    not any(REAL_RAW_DIR.glob("*/*/*/*.parquet")),
    reason="No real data/raw store present — run the Phase 2 collectors first.",
)


@REAL
def test_repeated_identical_query_fires_on_real_orderstatus_query(spark):
    """Real: 'SELECT O_ORDERSTATUS, COUNT(*), AVG(O_TOTALPRICE) FROM
    SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS GROUP BY O_ORDERSTATUS;' ran
    exactly 7 times on SPEND_LENS_WH per Phase 1's real test activity."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    hits = repeated_identical_query(df).collect()
    matches = [r for r in hits if "O_ORDERSTATUS" in r.evidence]
    assert len(matches) == 1
    row = matches[0]
    assert "7 times" in row.evidence
    assert row.attribution_key == "SPEND_LENS_WH"
    assert row.quantified == "yes"
    # 6/7 runs are the "redundant" ones -> ~86%
    assert "86%" in row.estimated_impact or "86.0%" in row.estimated_impact


@REAL
def test_unfiltered_table_scan_fires_on_real_select_star(spark):
    """Real: 'SELECT * FROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.CUSTOMER LIMIT
    100;' has no WHERE clause."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    hits = unfiltered_table_scan(df).collect()
    assert len(hits) >= 1
    assert all(r.quantified == "no" for r in hits)
    texts = [r.evidence for r in hits]
    assert any("CUSTOMER LIMIT 100" in t for t in texts)


@REAL
def test_idle_flat_cost_resource_fires_on_real_s3_charge(spark):
    """Real: AWS S3 cost was flat at $0.0000046448/day for 14 consecutive
    days — see docs/roadmap.md Phase 2 entry."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    hits = idle_flat_cost_resource(df).collect()
    s3 = [r for r in hits if "Simple Storage" in r.attribution_key]
    assert len(s3) == 1
    assert "14 distinct observed days" in s3[0].evidence
    assert s3[0].quantified == "yes"


@REAL
def test_databricks_cost_visibility_gap_fires_on_real_serverless_run(spark):
    """Real: the one landed Databricks job run has cost_usd=None because
    it ran on serverless compute with no resolvable node_type_id — decision
    0002 item 6."""
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    hits = databricks_cost_visibility_gap(df).collect()
    assert len(hits) == 1
    assert hits[0].attribution_key == "101154624149862"
    assert hits[0].quantified == "no"


@REAL
def test_run_all_rules_produces_a_stable_schema_and_real_suggestions(spark):
    df = enrich_events(read_raw_store(spark, str(REAL_RAW_DIR)))
    all_suggestions = run_all_rules(spark, df)
    assert set(all_suggestions.columns) == {
        "rule_id",
        "source",
        "attribution_key",
        "resource_ids_sample",
        "evidence",
        "suggestion",
        "estimated_impact",
        "quantified",
    }
    rows = all_suggestions.collect()
    rule_ids_fired = {r.rule_id for r in rows}
    # Honest coverage check: all 4 rules should fire at least once against
    # this real dataset (this is the current dataset's actual coverage —
    # not a guarantee every rule always fires on every dataset).
    assert rule_ids_fired == {
        "repeated_identical_query",
        "unfiltered_table_scan",
        "idle_flat_cost_resource",
        "databricks_cost_visibility_gap",
    }


# --- Synthetic: quantification math -------------------------------------


def test_repeated_identical_query_percentage_math_on_constructed_data(spark):
    from pyspark.sql.types import DoubleType, StringType, StructField, StructType

    schema = StructType(
        [
            StructField("source", StringType(), True),
            StructField("resource_type", StringType(), True),
            StructField("query_type", StringType(), True),
            StructField("account_identifier", StringType(), True),
            StructField("query_text_preview", StringType(), True),
            StructField("usage_quantity", DoubleType(), True),
            StructField("resource_id", StringType(), True),
        ]
    )
    text = "SELECT x FROM real_table"
    rows = [
        ("snowflake", "query", "SELECT", "WH1", text, 100.0, f"q{i}") for i in range(4)
    ]
    df = spark.createDataFrame(rows, schema)
    hits = repeated_identical_query(df, min_repeats=3).collect()
    assert len(hits) == 1
    # 3/4 runs redundant = 75%
    assert "75.0%" in hits[0].estimated_impact
