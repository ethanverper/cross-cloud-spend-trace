from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from spend_lens_common.schema import UsageRecord
from spend_lens_common.storage import write_records


def _record(**overrides) -> UsageRecord:
    defaults = dict(
        source="aws",
        resource_type="cost_explorer_daily_service",
        resource_id="2026-08-01::AmazonS3",
        usage_date=date(2026, 8, 1),
        service="AmazonS3",
        cost_usd=0.01,
        cost_basis="billed",
        usage_quantity=3.0,
        usage_unit="GB-Month",
        raw_metadata={"nested": {"a": 1}, "decimal_like": 1.5},
        ingested_at=datetime(2026, 8, 12, 12, 0, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return UsageRecord(**defaults)


def test_write_records_returns_none_for_empty_batch(tmp_path: Path):
    result = write_records([], source="aws", table="cost_and_usage", output_dir=tmp_path)
    assert result is None
    assert list(tmp_path.iterdir()) == []


def test_write_records_lands_readable_partitioned_parquet(tmp_path: Path):
    records = [_record(), _record(resource_id="2026-08-02::AWSLambda", service="AWSLambda")]
    path = write_records(records, source="aws", table="cost_and_usage", output_dir=tmp_path)

    assert path is not None
    assert path.exists()
    assert path.parent.name == f"ingested_date={date.today().isoformat()}"
    assert path.parent.parent.name == "cost_and_usage"
    assert path.parent.parent.parent.name == "aws"

    df = pd.read_parquet(path)
    assert len(df) == 2
    assert set(df["service"]) == {"AmazonS3", "AWSLambda"}
    # raw_metadata must round-trip as valid JSON, not a native struct column
    # (heterogeneous per-source metadata shapes rule out a fixed struct schema).
    parsed = json.loads(df.iloc[0]["raw_metadata"])
    assert parsed == {"nested": {"a": 1}, "decimal_like": 1.5}


def test_multiple_sources_land_in_independent_partitions(tmp_path: Path):
    write_records([_record()], source="aws", table="cost_and_usage", output_dir=tmp_path)
    write_records(
        [_record(source="snowflake", resource_type="query", resource_id="abc123")],
        source="snowflake",
        table="query_history",
        output_dir=tmp_path,
    )
    assert (tmp_path / "aws" / "cost_and_usage").exists()
    assert (tmp_path / "snowflake" / "query_history").exists()
