"""Explicit PySpark schema for the raw store, mirroring
`spend_lens_common.schema.UsageRecord` field-for-field.

Real gotcha hit building this: `spark.read.parquet("data/raw/*/*/*/*.parquet")`
without an explicit schema fails Spark's Parquet schema-merge step. Each
collector's Parquet file was written independently by pandas/pyarrow from
whatever rows that one run actually produced — columns that were `None` for
every row in a given file (e.g. `cost_usd` on every Snowflake `query_history`
row, since that collector deliberately leaves cost null — see decision 0002
item 5) get written by pyarrow as Parquet's `null` physical type for that
file. When Spark merges schemas across files, a `null`-typed column in one
file colliding with a `double`-typed column in another is exactly the kind
of mismatch `mergeSchema` cannot always resolve cleanly, and relying on
whichever file Spark happens to infer from first is fragile. Applying one
explicit, fully-nullable `StructType` up front (used for every partition
read) sidesteps the whole class of problem — every column is read with a
known, fixed type regardless of what a given file's rows happened to
contain.
"""
from __future__ import annotations

from pyspark.sql.types import (
    DoubleType,
    StringType,
    StructField,
    StructType,
    TimestampType,
)

# `usage_date`/`period_start`/`period_end`/`ingested_at` are written by
# `spend_lens_common.storage.write_records` via `model_dump(mode="json")`,
# which serializes dates/datetimes to ISO-8601 strings — so on disk these
# are Parquet `string` columns, not native date/timestamp columns. Reading
# them as `StringType` here and parsing explicitly in `ingest.py` (rather
# than hoping Spark's parquet reader infers a timestamp type) is the same
# "don't rely on inference" reasoning as the null-type issue above.
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
        StructField("raw_metadata", StringType(), True),  # JSON string
        StructField("ingested_at", StringType(), True),
    ]
)

__all__ = ["RAW_STORE_SCHEMA"]
