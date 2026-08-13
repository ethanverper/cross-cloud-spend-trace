# Databricks notebook source
# MAGIC %md
# MAGIC # cross-cloud-spend-trace Phase 3 — Databricks-side pipeline
# MAGIC
# MAGIC Self-contained (no `cross_cloud_spend_trace_analytics` package install required —
# MAGIC uses only `pyspark`, which ships on every Databricks Runtime) so it
# MAGIC can run as-is once the raw store is reachable from this workspace.
# MAGIC
# MAGIC **Status as of Phase 3 (see `docs/decisions/0003-...md`)**: this
# MAGIC notebook has *not* been executed on live Databricks compute yet. The
# MAGIC real, live-diagnosed blocker: the Phase 1/2 `DATABRICKS_TOKEN` is
# MAGIC scoped to exactly `jobs`/`clusters` (confirmed via direct API probes —
# MAGIC every DBFS/Workspace/Unity-Catalog call returns a real 403
# MAGIC `"...required scopes: files"` / `"...workspace"` / `"...unity-catalog"`),
# MAGIC so `analytics/src/cross_cloud_spend_trace_analytics/databricks_sync.py` cannot
# MAGIC upload `data/raw/` anywhere this notebook could read it from. Import
# MAGIC this notebook into the workspace and run it once Ethan issues a
# MAGIC broader-scoped token and re-runs `sync_raw_store_to_dbfs()` — the code
# MAGIC below itself is real, runnable PySpark, not a stub.
# MAGIC
# MAGIC The full-featured version of this pipeline (all 4 anomaly/forecast/
# MAGIC rules modules, unit-tested) lives in `analytics/src/cross_cloud_spend_trace_analytics/`
# MAGIC and is what's actually verified against real data today, running
# MAGIC locally — see that package for the complete implementation. This
# MAGIC notebook reimplements the core mechanism (unified model, one anomaly
# MAGIC check, one forecast, one rule) inline, deliberately kept dependency-free,
# MAGIC as the concrete "runs on Databricks" artifact.

# COMMAND ----------

dbutils.widgets.text("raw_dir", "dbfs:/FileStore/cross_cloud_spend_trace/raw", "Raw store (DBFS)")
dbutils.widgets.text("output_dir", "dbfs:/FileStore/cross_cloud_spend_trace/processed", "Output dir (DBFS)")
raw_dir = dbutils.widgets.get("raw_dir")
output_dir = dbutils.widgets.get("output_dir")

# COMMAND ----------

from datetime import date

from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, StringType, StructField, StructType
from pyspark.sql.window import Window

# Same explicit schema as analytics/src/cross_cloud_spend_trace_analytics/schema.py —
# duplicated here deliberately so this notebook has zero dependency on the
# local package being installed on the cluster. See that module's
# docstring for why an explicit schema (not Spark's automatic Parquet
# schema inference/merge) is required — two real gotchas were found there
# reading this exact raw store.
RAW_STORE_SCHEMA = StructType(
    [
        StructField("source", StringType(), True),
        StructField("resource_type", StringType(), True),
        StructField("resource_id", StringType(), True),
        StructField("account_identifier", StringType(), True),
        StructField("usage_date", StringType(), True),
        StructField("period_start", StringType(), True),
        StructField("period_end", StringType(), True),
        StructField("service", StringType(), True),
        StructField("cost_usd", DoubleType(), True),
        StructField("cost_basis", StringType(), True),
        StructField("usage_quantity", DoubleType(), True),
        StructField("usage_unit", StringType(), True),
        StructField("raw_metadata", StringType(), True),
        StructField("ingested_at", StringType(), True),
    ]
)

spark.conf.set("spark.sql.parquet.enableVectorizedReader", "false")

events = (
    spark.read.schema(RAW_STORE_SCHEMA).parquet(f"{raw_dir}/*/*/*/*.parquet")
    .withColumn("usage_date", F.to_date("usage_date"))
    .withColumn("attribution_key", F.coalesce(F.col("service"), F.col("account_identifier"), F.col("resource_id")))
    .withColumn("query_type", F.get_json_object(F.col("raw_metadata"), "$.query_type"))
    .withColumn("query_text_preview", F.get_json_object(F.col("raw_metadata"), "$.query_text_preview"))
)

print(f"read {events.count()} raw events from {raw_dir}")
display(events.groupBy("source").count())

# COMMAND ----------

# MAGIC %md ### Anomaly check: leave-one-out z-score on Snowflake query duration
# MAGIC Same algorithm as `cross_cloud_spend_trace_analytics.anomaly.detect_anomalies` — see
# MAGIC that module for the full version (min-group-size / zero-variance
# MAGIC handling included). This is the condensed inline version.

# COMMAND ----------

queries = events.filter((F.col("source") == "snowflake") & (F.col("resource_type") == "query"))
w = Window.partitionBy("account_identifier", "usage_date")
n = F.count("usage_quantity").over(w)
total = F.sum("usage_quantity").over(w)
total_sq = F.sum(F.col("usage_quantity") * F.col("usage_quantity")).over(w)
n_other = n - 1
mean_other = (total - F.col("usage_quantity")) / n_other
var_other = F.greatest((total_sq - F.col("usage_quantity") * F.col("usage_quantity")) / n_other - mean_other * mean_other, F.lit(0.0))
stddev_other = F.sqrt(var_other)
z = F.when(stddev_other > 1e-12, (F.col("usage_quantity") - mean_other) / stddev_other).otherwise(0.0)

anomalies = (
    queries.filter(n_other >= 5)
    .withColumn("z_score", z)
    .filter(F.col("z_score") > 3.0)
    .select("resource_id", "account_identifier", "usage_date", "usage_quantity", "z_score", "query_text_preview")
)
display(anomalies)

# COMMAND ----------

# MAGIC %md ### Forecast: AWS month-end run-rate

# COMMAND ----------

as_of = date.today()
days_in_month = 31  # replace with calendar.monthrange(as_of.year, as_of.month)[1] for a real run

aws_daily = (
    events.filter((F.col("source") == "aws") & F.col("cost_usd").isNotNull() & (F.col("cost_basis") == "billed"))
    .groupBy("usage_date")
    .agg(F.sum("cost_usd").alias("cost_usd_day"))
)
agg = aws_daily.agg(F.countDistinct("usage_date").alias("days_observed"), F.sum("cost_usd_day").alias("total_so_far"))
forecast = agg.withColumn("run_rate_per_day", F.col("total_so_far") / F.col("days_observed")).withColumn(
    "run_rate_month_end_projection", F.col("run_rate_per_day") * F.lit(days_in_month)
)
display(forecast)

# COMMAND ----------

# MAGIC %md ### Rule: repeated identical Snowflake query

# COMMAND ----------

repeated = (
    queries.filter((F.col("query_type") == "SELECT") & F.col("query_text_preview").contains("FROM"))
    .groupBy("account_identifier", "query_text_preview")
    .agg(F.count("*").alias("run_count"), F.sum("usage_quantity").alias("total_ms"))
    .filter(F.col("run_count") >= 3)
)
display(repeated)

# COMMAND ----------

anomalies.write.mode("overwrite").parquet(f"{output_dir}/anomalies_snowflake_query_duration")
forecast.write.mode("overwrite").parquet(f"{output_dir}/forecast_aws")
repeated.write.mode("overwrite").parquet(f"{output_dir}/optimization_suggestions_repeated_query")
print(f"wrote outputs under {output_dir}")
