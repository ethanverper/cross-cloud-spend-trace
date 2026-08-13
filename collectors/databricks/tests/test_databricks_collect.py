"""Live integration tests against the real Databricks Jobs/Clusters API (no
mocking). Requires `DATABRICKS_HOST`/`DATABRICKS_TOKEN` (see
`.env.example`); skipped entirely if unset.

Deliberately does not test any `system.billing.usage` / Account Console
billing path -- Phase 1 confirmed neither is available on this trial
workspace, and this collector doesn't attempt that path at all.
"""
from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv

load_dotenv()  # populate os.environ from a local .env before the skipif below reads it

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABRICKS_HOST") or not os.environ.get("DATABRICKS_TOKEN"),
    reason="DATABRICKS_HOST/DATABRICKS_TOKEN not set — skipping live Databricks tests",
)


@pytest.fixture(scope="module")
def client():
    from databricks_collector.client import DatabricksClient

    return DatabricksClient()


def test_job_runs_returns_well_formed_records(client):
    from databricks_collector.collect import collect_job_runs

    records = collect_job_runs(client, limit=25)
    assert isinstance(records, list)
    for record in records:
        assert record.source == "databricks"
        assert record.resource_type == "job_run"
        assert record.resource_id
        assert record.usage_unit == "cluster_hours"
        # Cost is either a clearly-labeled estimate or explicitly absent --
        # never a bare number pretending to be real billing.
        if record.cost_usd is not None:
            assert record.cost_basis == "estimated_list_price"
            assert record.cost_usd >= 0


def test_cluster_events_lookup_does_not_error(client):
    from databricks_collector.collect import cluster_ids_from_job_runs, collect_cluster_events, collect_job_runs

    job_runs = collect_job_runs(client, limit=25)
    cluster_ids = cluster_ids_from_job_runs(job_runs)
    # A trial workspace's job clusters are commonly ephemeral (no durable
    # cluster_id survives past the run) -- an empty id list, and therefore
    # an empty event batch, is a valid outcome, not a failure.
    records = collect_cluster_events(client, cluster_ids) if cluster_ids else []
    assert isinstance(records, list)
    for record in records:
        assert record.resource_type == "cluster_event"
