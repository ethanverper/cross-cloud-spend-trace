"""Live integration tests against the real AWS Cost Explorer API (no
mocking), per this project's own precedent
(`projects/finance/factor-lens/tests/test_data_integration.py`). These make
real API calls using the `spend-lens-collector` IAM user's credentials and
require `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` to be set (a local
`.env`, see `.env.example`). If those aren't set, every test here is
skipped rather than failing the rest of the suite.
"""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from a local .env before the skipif below reads it

pytestmark = pytest.mark.skipif(
    not os.environ.get("AWS_ACCESS_KEY_ID") or not os.environ.get("AWS_SECRET_ACCESS_KEY"),
    reason="AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY not set — skipping live AWS Cost Explorer tests",
)


@pytest.fixture(scope="module")
def client():
    from aws_collector.client import cost_explorer_client

    return cost_explorer_client()


def test_cost_and_usage_returns_live_structured_data(client):
    from aws_collector.collect import collect_cost_and_usage

    records = collect_cost_and_usage(client, lookback_days=30)
    # A brand-new account with minimal test activity may have zero cost rows
    # for some days, but Cost Explorer should always return *some* rows for
    # a 30-day window once enabled (per Phase 1, it needs ~24h to warm up).
    assert isinstance(records, list)
    for record in records:
        assert record.source == "aws"
        assert record.resource_type == "cost_explorer_daily_service"
        assert record.cost_basis == "billed"
        assert record.cost_usd is not None
        assert record.cost_usd >= 0


def test_cost_forecast_returns_live_data(client):
    from aws_collector.collect import collect_cost_forecast

    records = collect_cost_forecast(client)
    assert len(records) == 1
    forecast = records[0]
    assert forecast.resource_type == "cost_forecast"
    assert forecast.cost_basis == "forecast"
    assert forecast.cost_usd is not None
    assert forecast.cost_usd >= 0


def test_service_dimension_values_returns_live_data(client):
    from aws_collector.collect import collect_service_dimension_values

    records = collect_service_dimension_values(client, lookback_days=30)
    assert isinstance(records, list)
    for record in records:
        assert record.resource_type == "service_dimension_value"
        assert record.service
