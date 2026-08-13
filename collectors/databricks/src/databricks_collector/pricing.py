"""A deliberately small, clearly-labeled cost *estimate* for Databricks job
runs, built from public on-demand list prices — not real billing data.

Phase 1 confirmed `system.billing.usage` has zero tables and the Account
Console billing API requires a paid-plan upgrade on this trial workspace
(`docs/roadmap.md`'s Phase 1 entry). There is no real dollar figure this
collector can read. What it *can* read from the Jobs/Clusters APIs is
runtime and instance type, so this applies a rough, published-rate proxy —
every record produced with it carries `cost_basis="estimated_list_price"`
and a `pricing_note` explaining exactly how the number was derived, so nothing
downstream can mistake it for an actual invoice line.

Rates are approximate AWS on-demand US-East list prices (2026) for instance
types Databricks commonly assigns to job/all-purpose clusters, plus a flat
approximation of Databricks' own Jobs Compute list DBU rate. Update this
table if real workspace instance types diverge, or replace it entirely once
a future Databricks plan tier exposes real billing data.
"""
from __future__ import annotations

INSTANCE_HOURLY_USD: dict[str, float] = {
    "i3.xlarge": 0.312,
    "i3.2xlarge": 0.624,
    "m5.large": 0.096,
    "m5.xlarge": 0.192,
    "m5.2xlarge": 0.384,
    "m4.large": 0.10,
    "r5.xlarge": 0.252,
    "c5.xlarge": 0.17,
    "Standard_DS3_v2": 0.229,
    "Standard_DS4_v2": 0.458,
}
DEFAULT_INSTANCE_HOURLY_USD = 0.20
JOBS_COMPUTE_DBU_RATE_USD = 0.15


def estimate_cost(
    node_type_id: str | None,
    num_workers: int | None,
    runtime_hours: float,
) -> tuple[float | None, str | None, str]:
    """Returns (cost_usd, cost_basis, pricing_note). `cost_usd`/`cost_basis`
    are None when there isn't enough information to even guess — that's a
    valid outcome (e.g. serverless compute with no node type exposed), not
    an error."""
    if runtime_hours <= 0:
        return None, None, "no runtime recorded for this run"
    if not node_type_id:
        return None, None, "no cluster/node-type info available on this run (serverless compute or a purged cluster)"

    hourly_rate = INSTANCE_HOURLY_USD.get(node_type_id, DEFAULT_INSTANCE_HOURLY_USD)
    node_count = (num_workers or 0) + 1  # + 1 for the driver node
    instance_cost = hourly_rate * node_count * runtime_hours
    dbu_cost = JOBS_COMPUTE_DBU_RATE_USD * node_count * runtime_hours
    total = round(instance_cost + dbu_cost, 4)

    rate_note = f"${hourly_rate}/h instance list price" if node_type_id in INSTANCE_HOURLY_USD else (
        f"${hourly_rate}/h fallback rate (unmapped node_type_id={node_type_id!r})"
    )
    note = (
        f"estimated: {node_count} node(s) x {runtime_hours:.3f}h x "
        f"({rate_note} + ${JOBS_COMPUTE_DBU_RATE_USD}/h Jobs Compute DBU list price)"
    )
    return total, "estimated_list_price", note
