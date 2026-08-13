"""Maps `ACCOUNT_USAGE.QUERY_HISTORY` and `ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY`
rows onto `UsageRecord`s.

Neither view carries a dollar-cost column — Snowflake bills in warehouse
credits, and the credit-to-dollar rate isn't exposed to a read-only role.
`cost_usd`/`cost_basis` are left `None` here; `usage_quantity` carries the
real Snowflake-native unit instead (query elapsed milliseconds, or
warehouse credits) so Phase 3's aggregation can apply a known credit rate
later without this collector guessing one.

Both queries read from `ACCOUNT_USAGE`, which has documented ~45min-3hr
latency for new activity (see the roadmap's Phase 1 assumptions) — an
empty/short result here is expected if run too soon after generating test
query activity, not a bug.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone

import snowflake.connector

from cross_cloud_spend_trace_common.schema import UsageRecord

logger = logging.getLogger(__name__)

SOURCE = "snowflake"

QUERY_TEXT_PREVIEW_LIMIT = 500

QUERY_HISTORY_SQL = """
    SELECT QUERY_ID, QUERY_TEXT, QUERY_TYPE, DATABASE_NAME, SCHEMA_NAME,
           WAREHOUSE_NAME, WAREHOUSE_SIZE, EXECUTION_STATUS,
           START_TIME, END_TIME, TOTAL_ELAPSED_TIME,
           BYTES_SCANNED, ROWS_PRODUCED, CREDITS_USED_CLOUD_SERVICES
    FROM SNOWFLAKE.ACCOUNT_USAGE.QUERY_HISTORY
    WHERE START_TIME >= DATEADD(day, %(lookback_days)s, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    LIMIT %(row_limit)s
"""

WAREHOUSE_METERING_SQL = """
    SELECT WAREHOUSE_NAME, START_TIME, END_TIME,
           CREDITS_USED, CREDITS_USED_COMPUTE, CREDITS_USED_CLOUD_SERVICES
    FROM SNOWFLAKE.ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY
    WHERE START_TIME >= DATEADD(day, %(lookback_days)s, CURRENT_TIMESTAMP())
    ORDER BY START_TIME DESC
    LIMIT %(row_limit)s
"""


def _as_float(value) -> float | None:
    return None if value is None else float(value)


def collect_query_history(
    conn: snowflake.connector.SnowflakeConnection,
    *,
    lookback_days: int = 7,
    row_limit: int = 1000,
) -> list[UsageRecord]:
    now = datetime.now(timezone.utc)
    cursor = conn.cursor(snowflake.connector.DictCursor)
    try:
        cursor.execute(QUERY_HISTORY_SQL, {"lookback_days": -lookback_days, "row_limit": row_limit})
        rows = cursor.fetchall()
    finally:
        cursor.close()

    records: list[UsageRecord] = []
    for row in rows:
        start_time = row.get("START_TIME")
        query_text = row.get("QUERY_TEXT") or ""
        records.append(
            UsageRecord(
                source=SOURCE,
                resource_type="query",
                resource_id=row["QUERY_ID"],
                account_identifier=row.get("WAREHOUSE_NAME"),
                usage_date=start_time.date() if start_time else date.today(),
                period_start=start_time,
                period_end=row.get("END_TIME"),
                service=row.get("WAREHOUSE_NAME"),
                cost_usd=None,
                cost_basis=None,
                usage_quantity=_as_float(row.get("TOTAL_ELAPSED_TIME")),
                usage_unit="milliseconds",
                raw_metadata={
                    "query_type": row.get("QUERY_TYPE"),
                    "execution_status": row.get("EXECUTION_STATUS"),
                    "database_name": row.get("DATABASE_NAME"),
                    "schema_name": row.get("SCHEMA_NAME"),
                    "warehouse_size": row.get("WAREHOUSE_SIZE"),
                    "bytes_scanned": _as_float(row.get("BYTES_SCANNED")),
                    "rows_produced": _as_float(row.get("ROWS_PRODUCED")),
                    "credits_used_cloud_services": _as_float(row.get("CREDITS_USED_CLOUD_SERVICES")),
                    "query_text_preview": query_text[:QUERY_TEXT_PREVIEW_LIMIT],
                },
                ingested_at=now,
            )
        )
    logger.info("snowflake: fetched %d query_history records", len(records))
    return records


def collect_warehouse_metering_history(
    conn: snowflake.connector.SnowflakeConnection,
    *,
    lookback_days: int = 7,
    row_limit: int = 1000,
) -> list[UsageRecord]:
    now = datetime.now(timezone.utc)
    cursor = conn.cursor(snowflake.connector.DictCursor)
    try:
        cursor.execute(WAREHOUSE_METERING_SQL, {"lookback_days": -lookback_days, "row_limit": row_limit})
        rows = cursor.fetchall()
    finally:
        cursor.close()

    records: list[UsageRecord] = []
    for row in rows:
        start_time = row.get("START_TIME")
        warehouse = row.get("WAREHOUSE_NAME")
        records.append(
            UsageRecord(
                source=SOURCE,
                resource_type="warehouse_metering_hour",
                resource_id=f"{warehouse}::{start_time.isoformat() if start_time else 'unknown'}",
                account_identifier=warehouse,
                usage_date=start_time.date() if start_time else date.today(),
                period_start=start_time,
                period_end=row.get("END_TIME"),
                service=warehouse,
                cost_usd=None,
                cost_basis=None,
                usage_quantity=_as_float(row.get("CREDITS_USED")),
                usage_unit="credits",
                raw_metadata={
                    "credits_used_compute": _as_float(row.get("CREDITS_USED_COMPUTE")),
                    "credits_used_cloud_services": _as_float(row.get("CREDITS_USED_CLOUD_SERVICES")),
                },
                ingested_at=now,
            )
        )
    logger.info("snowflake: fetched %d warehouse_metering_history records", len(records))
    return records
