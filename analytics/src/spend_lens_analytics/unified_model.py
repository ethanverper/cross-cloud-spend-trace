"""Task 1 — the unified spend-by-source/query/job/model data model.

Builds one normalized view out of the three sources' raw `UsageRecord`
rows, plus a handful of source-specific metadata fields pulled out of
`raw_metadata` that anomaly detection and the rules engine both need
(Snowflake's `query_type`/`bytes_scanned`/`query_text_preview`, Databricks'
`node_type_id`/`cluster_source`). No source-specific branching logic lives
outside this module — everything downstream (`anomaly.py`, `forecast.py`,
`rules.py`) reads the same enriched, normalized columns regardless of
source.
"""
from __future__ import annotations

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

from .ingest import metadata_field

# Real, honest note on "spend by ... model": the roadmap's phrasing
# ("spend-by-source/query/job/model") uses "model" in the generic FinOps
# sense (a cost driver taxonomy), not because any of the three live
# sources actually expose an LLM/model dimension — none do. The concrete
# attribution grains this data supports are: AWS by `service`, Snowflake
# by `query` (per `resource_id`) and by `warehouse` (`account_identifier`),
# Databricks by `job` (`account_identifier` = `job_id`). `attribution_key`
# below is the one normalized column that plays that role across all three.


def enrich_events(df: DataFrame) -> DataFrame:
    """Adds normalized attribution + a fixed set of source-specific
    metadata columns extracted from `raw_metadata`. Still one row per raw
    record — this is the "unified spend-by-source/query/job/model" event
    grain everything else aggregates from."""
    return (
        df.withColumn(
            "attribution_key",
            F.coalesce(F.col("service"), F.col("account_identifier"), F.col("resource_id")),
        )
        .withColumn(
            "attribution_kind",
            F.when(F.col("source") == "aws", F.lit("service"))
            .when(
                (F.col("source") == "snowflake") & (F.col("resource_type") == "query"),
                F.lit("query"),
            )
            .when(
                (F.col("source") == "snowflake")
                & (F.col("resource_type") == "warehouse_metering_hour"),
                F.lit("warehouse"),
            )
            .when(F.col("source") == "databricks", F.lit("job"))
            .otherwise(F.lit("other")),
        )
        # Snowflake query_history fields (null for other sources/tables)
        .withColumn("query_type", metadata_field(df, "query_type"))
        .withColumn("execution_status", metadata_field(df, "execution_status"))
        .withColumn("bytes_scanned", metadata_field(df, "bytes_scanned", as_double=True))
        .withColumn("query_text_preview", metadata_field(df, "query_text_preview"))
        # Databricks job_run fields (null for other sources/tables)
        .withColumn("node_type_id", metadata_field(df, "node_type_id"))
        .withColumn("cluster_source", metadata_field(df, "cluster_source"))
        .withColumn("life_cycle_state", metadata_field(df, "life_cycle_state"))
        .withColumn("result_state", metadata_field(df, "result_state"))
    )


def spend_by_source_date(df: DataFrame) -> DataFrame:
    """Daily aggregate per source: total known dollar cost (only rows with
    a non-null `cost_usd`), record count, and distinct `cost_basis` values
    present that day — the top-level "spend by source" rollup."""
    return (
        df.groupBy("source", "usage_date")
        .agg(
            F.sum("cost_usd").alias("cost_usd_total"),
            F.count("*").alias("record_count"),
            F.count(F.when(F.col("cost_usd").isNotNull(), 1)).alias("records_with_cost"),
            F.sort_array(F.collect_set("cost_basis")).alias("cost_bases_present"),
        )
        .orderBy("source", "usage_date")
    )


def spend_by_attribution(df: DataFrame) -> DataFrame:
    """Daily aggregate per (source, attribution_kind, attribution_key) —
    the core unified "spend by source/query/job/model" view: one row per
    service/warehouse/job per day, with dollar cost where known and native
    usage quantity (credits, ms, cluster-hours) where it isn't."""
    return (
        df.groupBy("source", "attribution_kind", "attribution_key", "usage_date")
        .agg(
            F.sum("cost_usd").alias("cost_usd_total"),
            F.sort_array(F.collect_set("cost_basis")).alias("cost_bases_present"),
            F.sum("usage_quantity").alias("usage_quantity_total"),
            F.first("usage_unit").alias("usage_unit"),
            F.count("*").alias("record_count"),
        )
        .orderBy("source", "attribution_kind", "attribution_key", "usage_date")
    )


__all__ = ["enrich_events", "spend_by_source_date", "spend_by_attribution"]
