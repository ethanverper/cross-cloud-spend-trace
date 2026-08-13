"""Task 4 — optimization-suggestion rules engine.

Every rule here reads real fields the Phase 1/2 collectors actually landed
(`query_text_preview`, `bytes_scanned`, `cost_usd`, `node_type_id`, ...) and
states its evidence using the real numbers found, not templated text with
blanks filled in. Where a dollar/percent savings figure can honestly be
derived from what's actually in the data, a rule computes and states one;
where it can't (the data simply doesn't carry what's needed to quantify
it), the rule says so explicitly instead of inventing a number — see each
rule's docstring for which case it is.

**Explicit, honest gap versus the roadmap's own headline example**: the
roadmap's illustrative rule is "this Databricks job re-scans the full
table every run; partitioning would cut cost by X%". That specific rule
cannot be implemented against what this project's Databricks collector is
actually able to land: per decision 0002 item 6, the Databricks trial
workspace exposes no `system.billing.usage` and no query/table/scan-level
metadata anywhere in the Jobs API — only cluster/runtime metadata (job id,
run duration, node type if a provisioned cluster was used). There is no
field in `raw_metadata` that could ever tell this pipeline whether a job
re-scanned a full table. Writing that rule anyway, so it always silently
returns zero suggestions, would look like coverage that doesn't actually
exist. `databricks_cost_visibility_gap` below is the closest honestly-
groundable substitute: a real Databricks-specific FinOps finding (a cost
attribution blind spot, evidenced by the run's own `pricing_note`), not
the literal table-scan rule.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
)

SUGGESTION_SCHEMA = StructType(
    [
        StructField("rule_id", StringType(), False),
        StructField("source", StringType(), False),
        StructField("attribution_key", StringType(), True),
        StructField("resource_ids_sample", StringType(), True),
        StructField("evidence", StringType(), False),
        StructField("suggestion", StringType(), False),
        StructField("estimated_impact", StringType(), False),
        StructField("quantified", StringType(), False),  # "yes" | "no"
    ]
)

# Snowsight/UI-chrome query patterns to exclude from query-content rules —
# these are artifacts of using the web UI (Phase 1's own setup process),
# not real workload queries, and including them would misrepresent
# "data-grounded" findings as being about actual usage.
_UI_CHROME_QUERY_PREFIXES = [
    "SELECT CURRENT_USER",
    "SELECT is_database_role_in_session",
    "SELECT SYSTEM$",
    "CALL SYSTEM$",
    "USE SECONDARY ROLES",
    "SHOW ",
    "DESCRIBE ",
    "PUT ",
    "GET ",
    "LIST ",
    "REMOVE ",
]


def _is_ui_chrome_query(col: str = "query_text_preview"):
    cond = F.lit(False)
    for prefix in _UI_CHROME_QUERY_PREFIXES:
        cond = cond | F.col(col).startswith(prefix)
    return cond


def repeated_identical_query(df: DataFrame, min_repeats: int = 3) -> DataFrame:
    """Snowflake: the exact same real SELECT text executed >= `min_repeats`
    times on the same warehouse. Real signature of a query result that
    could be cached or materialized instead of re-executed from scratch
    each time. **Quantified**: the % of that query's total observed
    warehouse time attributable to the (min_repeats - 1) redundant re-runs
    — i.e. what's avoidable if every run after the first served a cached/
    materialized result instead, an explicit, stated assumption rather
    than a black-box number.
    """
    queries = df.filter(
        (F.col("source") == "snowflake")
        & (F.col("resource_type") == "query")
        & (F.col("query_type") == "SELECT")
        & (~_is_ui_chrome_query())
        & F.col("query_text_preview").contains("FROM")
    )

    grouped = (
        queries.groupBy("account_identifier", "query_text_preview")
        .agg(
            F.count("*").alias("run_count"),
            F.sum("usage_quantity").alias("total_ms"),
            F.avg("usage_quantity").alias("avg_ms"),
            F.collect_set("resource_id").alias("query_ids"),
        )
        .filter(F.col("run_count") >= min_repeats)
    )

    return grouped.select(
        F.lit("repeated_identical_query").alias("rule_id"),
        F.lit("snowflake").alias("source"),
        F.col("account_identifier").alias("attribution_key"),
        F.array_join(F.slice(F.col("query_ids"), 1, 3), ", ").alias("resource_ids_sample"),
        F.concat(
            F.lit("Exact query text ran "),
            F.col("run_count").cast("string"),
            F.lit(" times on warehouse "),
            F.col("account_identifier"),
            F.lit(" (total "),
            F.round(F.col("total_ms"), 1).cast("string"),
            F.lit("ms warehouse time, avg "),
            F.round(F.col("avg_ms"), 1).cast("string"),
            F.lit("ms/run): "),
            F.substring(F.col("query_text_preview"), 1, 160),
        ).alias("evidence"),
        F.lit(
            "Cache or materialize this query's result instead of re-executing it on every "
            "call — e.g. a materialized view / scheduled table refresh, or confirming "
            "Snowflake's own result cache isn't being bypassed (a differing session, "
            "warehouse restart, or an intervening DDL change on the underlying table all "
            "invalidate it)."
        ).alias("suggestion"),
        F.concat(
            F.lit("Up to "),
            F.round((F.col("run_count") - 1) / F.col("run_count") * 100, 0).cast("string"),
            F.lit("% of the "),
            F.round(F.col("total_ms"), 1).cast("string"),
            F.lit("ms observed for this query is redundant re-execution "),
            F.lit("(assumes the first run establishes a cache/materialization "),
            F.lit("that every later identical run could have used instead)."),
        ).alias("estimated_impact"),
        F.lit("yes").alias("quantified"),
    )


def unfiltered_table_scan(df: DataFrame) -> DataFrame:
    """Snowflake: a real SELECT against an actual data table
    (`SNOWFLAKE_SAMPLE_DATA` in this dataset — the only real table source
    Phase 1 loaded) with no `WHERE` clause anywhere in the visible query
    text. Deduplicated by (warehouse, query text) — one suggestion per
    distinct unfiltered query pattern, not one per individual run (that's
    already `repeated_identical_query`'s job). **Not quantified**: Query
    History's `bytes_scanned` reflects what this specific run scanned, not
    what a filtered version *would* have scanned instead — that depends on
    the underlying table's data distribution/clustering, which isn't
    captured anywhere in this raw store, so no percentage is stated (that
    would be a guess, not a derived number)."""
    queries = df.filter(
        (F.col("source") == "snowflake")
        & (F.col("resource_type") == "query")
        & (F.col("query_type") == "SELECT")
        & F.col("query_text_preview").contains("FROM")
        & F.col("query_text_preview").contains("SNOWFLAKE_SAMPLE_DATA")
        & (~F.upper(F.col("query_text_preview")).contains("WHERE"))
    )

    grouped = queries.groupBy("account_identifier", "query_text_preview").agg(
        F.count("*").alias("run_count"),
        F.sum(F.coalesce(F.col("bytes_scanned"), F.lit(0.0))).alias("bytes_scanned_total"),
        F.collect_set("resource_id").alias("query_ids"),
    )

    return grouped.select(
        F.lit("unfiltered_table_scan").alias("rule_id"),
        F.lit("snowflake").alias("source"),
        F.col("account_identifier").alias("attribution_key"),
        F.array_join(F.slice(F.col("query_ids"), 1, 3), ", ").alias("resource_ids_sample"),
        F.concat(
            F.lit("Ran "),
            F.col("run_count").cast("string"),
            F.lit(" time(s) with no WHERE clause on warehouse "),
            F.col("account_identifier"),
            F.lit(" (bytes_scanned total across those runs: "),
            F.round(F.col("bytes_scanned_total"), 0).cast("string"),
            F.lit("): "),
            F.substring(F.col("query_text_preview"), 1, 160),
        ).alias("evidence"),
        F.lit(
            "Add a filter predicate (WHERE clause) or a clustering key on the scanned table "
            "so Snowflake can prune partitions instead of scanning the full table on every run."
        ).alias("suggestion"),
        F.lit(
            "Not quantified: the real savings from adding a filter depends on the underlying "
            "table's row/partition distribution, which Query History's bytes_scanned for these "
            "runs doesn't expose — stating a percentage here would be a guess, not a derived "
            "number."
        ).alias("estimated_impact"),
        F.lit("no").alias("quantified"),
    )


def idle_flat_cost_resource(df: DataFrame, min_consecutive_days: int = 7) -> DataFrame:
    """AWS: a service whose daily cost is nonzero but has **zero
    variance** across >= `min_consecutive_days` distinct days in the
    window — the real signature of an always-on charge (unlifecycled
    storage, an idle-but-provisioned resource) rather than active,
    varying usage. **Quantified**: 100% of the accumulated cost over the
    observed window is stated as recoverable *if* the resource turns out
    to be unneeded — an explicit conditional, not a claim it's definitely
    waste."""
    daily = (
        df.filter((F.col("source") == "aws") & (F.col("resource_type") == "cost_explorer_daily_service"))
        .filter(F.col("cost_usd") > 0)
        .groupBy("service")
        .agg(
            F.countDistinct("usage_date").alias("days"),
            F.stddev_pop("cost_usd").alias("cost_stddev"),
            F.avg("cost_usd").alias("cost_avg"),
            F.sum("cost_usd").alias("cost_total"),
        )
        .filter((F.col("days") >= min_consecutive_days) & (F.coalesce(F.col("cost_stddev"), F.lit(0.0)) < 1e-12))
    )

    return daily.select(
        F.lit("idle_flat_cost_resource").alias("rule_id"),
        F.lit("aws").alias("source"),
        F.col("service").alias("attribution_key"),
        F.lit(None).cast("string").alias("resource_ids_sample"),
        F.concat(
            F.col("service"),
            F.lit(" cost was flat at $"),
            F.format_number(F.col("cost_avg"), 8),
            F.lit("/day across "),
            F.col("days").cast("string"),
            F.lit(" distinct observed days with zero variance (total $"),
            F.format_number(F.col("cost_total"), 6),
            F.lit(" over the window)."),
        ).alias("evidence"),
        F.lit(
            "A perfectly flat recurring charge over many days is the classic signature of an "
            "always-on / unlifecycled resource (e.g. S3 objects with no lifecycle/expiration "
            "policy) rather than active, variable usage. Review whether this resource is still "
            "needed; if not, delete it or add a lifecycle policy."
        ).alias("suggestion"),
        F.concat(
            F.lit("Up to 100% of the $"),
            F.format_number(F.col("cost_total"), 6),
            F.lit(" accumulated over the observed window is avoidable if this resource is "),
            F.lit("confirmed unnecessary (conditional — this rule only detects the flat-cost "),
            F.lit("pattern, not whether the resource is actually needed)."),
        ).alias("estimated_impact"),
        F.lit("yes").alias("quantified"),
    )


def databricks_cost_visibility_gap(df: DataFrame) -> DataFrame:
    """Databricks: a job run where `cost_usd` is null because no cluster/
    node-type info was available (serverless compute, or a purged
    cluster — decision 0002 item 6). This is a real FinOps finding in its
    own right (a cost-attribution blind spot), stated with the run's own
    real duration — the closest honestly-groundable substitute for the
    roadmap's illustrative "full table rescan" rule, which this data
    source has no fields to ever evaluate (see this module's docstring).
    **Not quantified**: there's no dollar figure to compute a percentage
    against — that's exactly the gap being flagged."""
    runs = df.filter(
        (F.col("source") == "databricks")
        & (F.col("resource_type") == "job_run")
        & F.col("cost_usd").isNull()
    ).withColumn(
        "duration_seconds",
        (F.unix_timestamp("period_end") - F.unix_timestamp("period_start")),
    )

    return runs.select(
        F.lit("databricks_cost_visibility_gap").alias("rule_id"),
        F.lit("databricks").alias("source"),
        F.col("account_identifier").alias("attribution_key"),
        F.col("resource_id").alias("resource_ids_sample"),
        F.concat(
            F.lit("Job "),
            F.col("account_identifier"),
            F.lit(" run "),
            F.col("resource_id"),
            F.lit(" completed ("),
            F.coalesce(F.col("result_state"), F.lit("unknown result")),
            F.lit(") in "),
            F.col("duration_seconds").cast("string"),
            F.lit("s with no resolvable node_type_id (cluster_source="),
            F.coalesce(F.col("cluster_source"), F.lit("unknown")),
            F.lit(") — cost_usd could not be estimated for this run."),
        ).alias("evidence"),
        F.lit(
            "This pipeline can't attribute a dollar cost to this run because the Jobs API "
            "exposed no instance-type info for the cluster it ran on (typical for serverless "
            "compute). If cost visibility on this job matters, either run it on a provisioned "
            "cluster with a known node type (this collector's pricing table can then estimate "
            "cost from runtime), or track it directly via Databricks' own serverless usage/"
            "billing view, which this Jobs-API-only collector cannot reach on this trial tier."
        ).alias("suggestion"),
        F.lit(
            "Not quantified: this is a visibility gap, not a cost figure — there is no dollar "
            "amount in the data to state a percentage against."
        ).alias("estimated_impact"),
        F.lit("no").alias("quantified"),
    )


_ALL_RULES = [
    repeated_identical_query,
    unfiltered_table_scan,
    idle_flat_cost_resource,
    databricks_cost_visibility_gap,
]


def run_all_rules(spark: SparkSession, df: DataFrame) -> DataFrame:
    """Runs every rule and unions the results into one suggestions table.
    Starts from an explicitly-typed empty DataFrame (`SUGGESTION_SCHEMA`)
    so the result always has a stable schema even if every rule produces
    zero rows against a given dataset (a real, valid outcome — see this
    module's docstring on rule coverage vs. this project's current data)."""
    result = spark.createDataFrame([], SUGGESTION_SCHEMA)
    for rule in _ALL_RULES:
        result = result.unionByName(rule(df))
    return result


__all__ = [
    "SUGGESTION_SCHEMA",
    "repeated_identical_query",
    "unfiltered_table_scan",
    "idle_flat_cost_resource",
    "databricks_cost_visibility_gap",
    "run_all_rules",
]
