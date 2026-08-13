"""Snowflake connection for the `SPEND_LENS_SVC` service user / `SPEND_LENS_READER`
role — `IMPORTED PRIVILEGES` on the `SNOWFLAKE` database (ACCOUNT_USAGE) and
on `SNOWFLAKE_SAMPLE_DATA`, plus `USAGE` on the `SPEND_LENS_WH` warehouse.
Never `ACCOUNTADMIN` — see `docs/decisions/0001-...md` and Phase 1's roadmap
note on why per-schema grants were rejected on an imported/shared database.
"""
from __future__ import annotations

import os

import snowflake.connector

from spend_lens_common.config import require_env


def connect():
    return snowflake.connector.connect(
        account=require_env("SNOWFLAKE_ACCOUNT"),
        user=require_env("SNOWFLAKE_USER"),
        password=require_env("SNOWFLAKE_PASSWORD"),
        role=os.environ.get("SNOWFLAKE_ROLE", "SPEND_LENS_READER"),
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", "SPEND_LENS_WH"),
        database="SNOWFLAKE",
        schema="ACCOUNT_USAGE",
        client_session_keep_alive=False,
    )
