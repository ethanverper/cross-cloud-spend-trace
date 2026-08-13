"""Reads the shared raw store (`data/raw/<source>/<table>/ingested_date=.../*.parquet`)
into one typed Spark DataFrame.

Portable by construction: every function here takes an existing
`SparkSession` rather than constructing one, so the exact same code runs
against a local `pyspark` session (see `pipeline.py`) or a Databricks
notebook's ambient `spark` global (see `databricks_notebook.py`) — only the
`raw_dir` path differs (a local filesystem path vs. a `dbfs:/...` path).
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F

from .schema import RAW_STORE_SCHEMA


def read_raw_store(spark: SparkSession, raw_dir: str) -> DataFrame:
    """Reads every `<source>/<table>/ingested_date=.../*.parquet` file under
    `raw_dir` as one schema-consistent DataFrame, with `usage_date` /
    `period_start` / `period_end` / `ingested_at` parsed into real
    date/timestamp types and `raw_metadata` left as a JSON string (parsed
    on demand via `get_json_object`/`from_json` by callers that need
    specific keys — see `unified_model.py`).

    `source`/`table`/`ingested_date` partition columns are re-derived from
    `input_file_name()` rather than relying on Spark's Hive-style partition
    discovery, because the raw store's own `source`/`resource_type` columns
    already carry this information per-row (written by the collector, not
    inferred from the path) — using the row's own columns is one fewer
    thing that can drift from the directory layout.
    """
    # A second, real gotcha on top of the null-type one described above:
    # pyarrow doesn't always pick a `double`/`null` physical Parquet type
    # for an all-null float column — the Databricks `job_runs` file (whose
    # single real row has `cost_usd=None`, see decision 0002 item 6) was
    # physically written as Parquet `INT32`. Spark's default *vectorized*
    # Parquet reader refuses to widen `INT32` -> the schema's `double` at
    # read time (`SchemaColumnConvertNotSupportedException`), even though
    # the column is fully nullable and this specific file has zero non-null
    # values. The non-vectorized reader handles this promotion correctly,
    # so it's disabled for this read rather than special-casing the
    # Databricks file — a future partition file could hit the same
    # int-vs-double mismatch from any source, not just this one.
    spark.conf.set("spark.sql.parquet.enableVectorizedReader", "false")
    glob_path = raw_dir.rstrip("/") + "/*/*/*/*.parquet"
    df = spark.read.schema(RAW_STORE_SCHEMA).parquet(glob_path)

    return (
        df.withColumn("usage_date", F.to_date("usage_date"))
        .withColumn("period_start", F.to_timestamp("period_start"))
        .withColumn("period_end", F.to_timestamp("period_end"))
        .withColumn("ingested_at", F.to_timestamp("ingested_at"))
    )


def metadata_field(df: DataFrame, key: str, as_double: bool = False):
    """Pulls one key out of the `raw_metadata` JSON-string column as a
    Column expression, e.g. `metadata_field(df, "bytes_scanned", as_double=True)`.
    Returns `None`/`null` for rows whose metadata doesn't have that key
    rather than raising — different sources populate different keys."""
    expr = F.get_json_object(F.col("raw_metadata"), f"$.{key}")
    return expr.cast("double") if as_double else expr


__all__ = ["read_raw_store", "metadata_field"]
