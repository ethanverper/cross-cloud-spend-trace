"""Maps Databricks Jobs API + Clusters API responses onto `UsageRecord`s.

Cost proxy, not real billing (Phase 1 finding, see `pricing.py`):
`collect_job_runs` reads job-run history (`/api/2.1/jobs/runs/list` +
`/api/2.1/jobs/runs/get`), resolves each run's cluster instance type via
`/api/2.0/clusters/get` when it isn't already inlined in the run detail,
and applies `pricing.estimate_cost` to runtime + instance type.
`collect_cluster_events` separately lands raw cluster lifecycle events
(`/api/2.0/clusters/events`) for audit/drill-down — not converted to cost,
just the runtime facts a later Spark job could use to build a better
estimate.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import requests

from cross_cloud_spend_trace_common.schema import UsageRecord

from .client import DatabricksClient
from .pricing import estimate_cost

logger = logging.getLogger(__name__)

SOURCE = "databricks"


def _epoch_ms_to_datetime(epoch_ms: int | None) -> datetime | None:
    if not epoch_ms:
        return None
    return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)


def list_job_runs(client: DatabricksClient, *, limit: int = 50) -> list[dict]:
    runs: list[dict] = []
    offset = 0
    while len(runs) < limit:
        page_size = min(25, limit - len(runs))
        page = client.get("/api/2.1/jobs/runs/list", limit=page_size, offset=offset, expand_tasks=True)
        page_runs = page.get("runs", [])
        runs.extend(page_runs)
        if not page.get("has_more") or not page_runs:
            break
        offset += len(page_runs)
    return runs


def _extract_cluster_info(
    client: DatabricksClient, run_detail: dict
) -> tuple[str | None, int | None, str, str | None]:
    """Returns (node_type_id, num_workers, cluster_source, cluster_id).
    `cluster_id` is only populated when the run used (or reused) a durable
    cluster we can later query `/api/2.0/clusters/events` against —
    job-scoped ephemeral clusters created fresh per run don't carry one
    worth tracking here."""
    cluster_spec = run_detail.get("cluster_spec") or {}
    new_cluster = cluster_spec.get("new_cluster")
    if new_cluster:
        return new_cluster.get("node_type_id"), new_cluster.get("num_workers"), "job_new_cluster", None

    for task in run_detail.get("tasks") or []:
        task_cluster = task.get("new_cluster")
        if task_cluster:
            return task_cluster.get("node_type_id"), task_cluster.get("num_workers"), "task_new_cluster", None

    cluster_instance = run_detail.get("cluster_instance") or {}
    cluster_id = cluster_instance.get("cluster_id")
    if cluster_id:
        try:
            cluster = client.get("/api/2.0/clusters/get", cluster_id=cluster_id)
            return cluster.get("node_type_id"), cluster.get("num_workers"), "existing_cluster_lookup", cluster_id
        except requests.HTTPError as exc:
            logger.warning("databricks: cluster lookup failed for cluster_id=%s: %s", cluster_id, exc)
            return None, None, "cluster_lookup_failed", cluster_id

    return None, None, "no_cluster_info_available", None


def collect_job_runs(client: DatabricksClient, *, limit: int = 50) -> list[UsageRecord]:
    now = datetime.now(timezone.utc)
    runs = list_job_runs(client, limit=limit)

    records: list[UsageRecord] = []
    for run in runs:
        run_id = run["run_id"]
        detail = client.get("/api/2.1/jobs/runs/get", run_id=run_id)

        start_dt = _epoch_ms_to_datetime(detail.get("start_time")) or now
        duration_ms = detail.get("run_duration") or 0
        end_dt = start_dt + timedelta(milliseconds=duration_ms) if duration_ms else None
        runtime_hours = duration_ms / 1000 / 3600

        node_type_id, num_workers, cluster_source, cluster_id = _extract_cluster_info(client, detail)
        cost_usd, cost_basis, pricing_note = estimate_cost(node_type_id, num_workers, runtime_hours)

        state = detail.get("state", {})
        records.append(
            UsageRecord(
                source=SOURCE,
                resource_type="job_run",
                resource_id=str(run_id),
                account_identifier=str(detail.get("job_id") or run.get("job_id") or ""),
                usage_date=start_dt.date(),
                period_start=start_dt,
                period_end=end_dt,
                service=detail.get("run_name") or run.get("run_name"),
                cost_usd=cost_usd,
                cost_basis=cost_basis,
                usage_quantity=round(runtime_hours, 4),
                usage_unit="cluster_hours",
                raw_metadata={
                    "job_id": detail.get("job_id"),
                    "life_cycle_state": state.get("life_cycle_state"),
                    "result_state": state.get("result_state"),
                    "state_message": state.get("state_message"),
                    "node_type_id": node_type_id,
                    "num_workers": num_workers,
                    "cluster_source": cluster_source,
                    "cluster_id": cluster_id,
                    "pricing_note": pricing_note,
                    "run_page_url": detail.get("run_page_url") or run.get("run_page_url"),
                },
                ingested_at=now,
            )
        )
    logger.info("databricks: fetched %d job_run records", len(records))
    return records


def cluster_ids_from_job_runs(job_run_records: list[UsageRecord]) -> list[str]:
    """The durable cluster IDs observed across a batch of `job_run` records
    -- runs against ephemeral, job-scoped clusters (the common case for a
    trial workspace's job/task clusters) won't contribute one."""
    seen: set[str] = set()
    for record in job_run_records:
        cluster_id = record.raw_metadata.get("cluster_id")
        if cluster_id:
            seen.add(cluster_id)
    return sorted(seen)


def collect_cluster_events(client: DatabricksClient, cluster_ids: list[str], *, limit: int = 50) -> list[UsageRecord]:
    """Lands raw cluster lifecycle events for the given cluster IDs. Not
    every trial-tier job run has a durable `cluster_id` to query against
    (ephemeral job clusters can be purged quickly) -- an empty result for a
    given cluster is expected, not an error."""
    now = datetime.now(timezone.utc)
    records: list[UsageRecord] = []

    for cluster_id in cluster_ids:
        try:
            # Unlike the other Jobs/Clusters endpoints used in this module,
            # /api/2.0/clusters/events is a POST with a JSON body, not a GET
            # with query params (confirmed against Databricks' own API docs).
            response = client.post("/api/2.0/clusters/events", json={"cluster_id": cluster_id, "limit": limit})
        except requests.HTTPError as exc:
            logger.warning("databricks: cluster events lookup failed for cluster_id=%s: %s", cluster_id, exc)
            continue

        for event in response.get("events", []):
            event_dt = _epoch_ms_to_datetime(event.get("timestamp")) or now
            records.append(
                UsageRecord(
                    source=SOURCE,
                    resource_type="cluster_event",
                    resource_id=f"{cluster_id}::{event.get('timestamp')}",
                    account_identifier=cluster_id,
                    usage_date=event_dt.date(),
                    period_start=event_dt,
                    raw_metadata={
                        "type": event.get("type"),
                        "details": event.get("details", {}),
                    },
                    ingested_at=now,
                )
            )
    logger.info("databricks: fetched %d cluster_event records across %d cluster(s)", len(records), len(cluster_ids))
    return records
