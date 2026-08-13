"""The normalized raw-store record every collector writes.

One shape, three sources. Each source's collector maps its own native
response (a Cost Explorer group-by row, a QUERY_HISTORY row, a Databricks
job run) onto this record before landing it — so Phase 3's PySpark job can
read `data/raw/*/*/*.parquet` as a single schema-consistent dataset instead
of writing per-source parsing logic.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class UsageRecord(BaseModel):
    """One unit of usage/cost/activity from a source, normalized.

    Not every source can populate every field (Snowflake's ACCOUNT_USAGE has
    no dollar-cost column; Databricks' Jobs API has no billing data at all
    on this trial tier) — `cost_usd`/`cost_basis` make the provenance of any
    dollar figure explicit rather than presenting an estimate as a bill.
    """

    source: str
    """One of "aws", "snowflake", "databricks"."""

    resource_type: str
    """What kind of record this is, e.g. "cost_explorer_daily_service",
    "query", "warehouse_metering_hour", "job_run"."""

    resource_id: str
    """Stable identifier for this record within its (source, resource_type)
    — a query ID, a job run ID, a "date::service" composite key for AWS's
    group-by rows (which have no native ID)."""

    account_identifier: str | None = None
    """AWS account / Snowflake warehouse / Databricks job ID this record
    belongs to, when the source exposes it without an extra privileged call."""

    usage_date: date
    """The calendar date this usage/cost applies to (UTC)."""

    period_start: datetime | None = None
    period_end: datetime | None = None

    service: str | None = None
    """The service/warehouse/job name driving this usage, when known."""

    cost_usd: float | None = None
    cost_basis: str | None = None
    """None (no cost data), "billed" (Cost Explorer's own dollar figure),
    "forecast" (Cost Explorer's forecast API), or "estimated_list_price"
    (Databricks proxy cost — public list-price rates applied to observed
    cluster runtime, not real billing data)."""

    usage_quantity: float | None = None
    usage_unit: str | None = None

    raw_metadata: dict[str, Any] = Field(default_factory=dict)
    """The source-specific fields worth keeping for drill-down/audit that
    don't map onto the normalized columns above."""

    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = {"extra": "forbid"}
