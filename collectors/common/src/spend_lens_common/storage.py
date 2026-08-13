"""Writes a batch of `UsageRecord`s to the shared raw store as Parquet.

Layout: `<output_dir>/<source>/<table>/ingested_date=YYYY-MM-DD/<table>-<id>.parquet`
— partitioned by source, table, and ingestion date, the same partitioning
scheme Spark's `spark.read.parquet(...)` understands natively (partition
columns are inferred from the `key=value` directory names), so Phase 3's
PySpark job can read the whole raw store with one call:
`spark.read.parquet("data/raw/*/*/*")`.

`raw_metadata` is stored as a JSON string column rather than a native
Parquet struct — each source's records carry a different set of metadata
keys, and a struct column requires one consistent schema across every row
written to a file. A JSON string avoids that constraint entirely; anything
reading it downstream (Spark's `from_json`, or plain `json.loads` in
pandas) can parse it back out.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd

from .schema import UsageRecord


def write_records(
    records: list[UsageRecord],
    *,
    source: str,
    table: str,
    output_dir: Path,
) -> Path | None:
    """Writes `records` as one Parquet file. Returns the file path written,
    or None if `records` was empty (nothing to write — not an error; a
    source with zero activity in the queried window is a valid outcome)."""
    if not records:
        return None

    rows = []
    for record in records:
        row = record.model_dump(mode="json")
        row["raw_metadata"] = json.dumps(row["raw_metadata"], default=str)
        rows.append(row)

    df = pd.DataFrame(rows)
    ingested_date = date.today().isoformat()
    partition_dir = Path(output_dir) / source / table / f"ingested_date={ingested_date}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    path = partition_dir / f"{table}-{uuid4().hex[:8]}.parquet"
    df.to_parquet(path, index=False, engine="pyarrow")
    return path
