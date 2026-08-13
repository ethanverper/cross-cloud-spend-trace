"""Live integration tests against the real Snowflake ACCOUNT_USAGE views (no
mocking). Requires `SNOWFLAKE_ACCOUNT`/`SNOWFLAKE_USER`/`SNOWFLAKE_PASSWORD`
(see `.env.example`); skipped entirely if unset.

ACCOUNT_USAGE has documented ~45min-3hr latency for new activity — these
tests assert the collector *runs successfully against live Snowflake* and
returns well-formed records, not that a specific number of rows comes back
(an empty result is a valid, non-bug outcome if run too soon after Phase 1's
test queries).
"""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from a local .env before the skipif below reads it

pytestmark = pytest.mark.skipif(
    not os.environ.get("SNOWFLAKE_ACCOUNT")
    or not os.environ.get("SNOWFLAKE_USER")
    or not os.environ.get("SNOWFLAKE_PASSWORD"),
    reason="SNOWFLAKE_ACCOUNT/SNOWFLAKE_USER/SNOWFLAKE_PASSWORD not set — skipping live Snowflake tests",
)


@pytest.fixture(scope="module")
def conn():
    from snowflake_collector.client import connect

    connection = connect()
    yield connection
    connection.close()


def test_query_history_returns_well_formed_records(conn):
    from snowflake_collector.collect import collect_query_history

    records = collect_query_history(conn, lookback_days=14)
    assert isinstance(records, list)
    for record in records:
        assert record.source == "snowflake"
        assert record.resource_type == "query"
        assert record.resource_id
        assert record.cost_usd is None  # ACCOUNT_USAGE has no dollar-cost column
        assert record.usage_unit == "milliseconds"


def test_warehouse_metering_history_returns_well_formed_records(conn):
    from snowflake_collector.collect import collect_warehouse_metering_history

    records = collect_warehouse_metering_history(conn, lookback_days=14)
    assert isinstance(records, list)
    for record in records:
        assert record.resource_type == "warehouse_metering_hour"
        assert record.usage_unit == "credits"
        if record.usage_quantity is not None:
            assert record.usage_quantity >= 0


def test_connection_reaches_spend_lens_warehouse_and_role(conn):
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT CURRENT_WAREHOUSE(), CURRENT_ROLE()")
        warehouse, role = cursor.fetchone()
    finally:
        cursor.close()
    assert warehouse == os.environ.get("SNOWFLAKE_WAREHOUSE", "SPEND_LENS_WH")
    assert role == os.environ.get("SNOWFLAKE_ROLE", "SPEND_LENS_READER")
