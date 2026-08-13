"""Fixed, non-data-derived constants: the three-source palette and labels
from decision 0005 (Phase 4 brand identity), and the mechanism/concept copy
for the landing screen (decision 0005 section 6). Everything that *can* be
computed from real ingested data lives in loader.py instead -- this file is
only for the things that are genuinely fixed identity/copy, not numbers.
"""
from __future__ import annotations

SOURCE_META: dict[str, dict[str, str]] = {
    "aws": {
        "label": "AWS",
        "color": "#F59E0B",
        "full_name": "Amazon Web Services",
        "surface": "Cost Explorer / Billing API",
    },
    "snowflake": {
        "label": "Snowflake",
        "color": "#38BDF8",
        "full_name": "Snowflake",
        "surface": "ACCOUNT_USAGE (QUERY_HISTORY, WAREHOUSE_METERING_HISTORY)",
    },
    "databricks": {
        "label": "Databricks",
        "color": "#FB7185",
        "full_name": "Databricks",
        "surface": "Jobs API (job-run history)",
    },
}

MECHANISM_STATEMENT = (
    "cross-cloud-spend-trace traces AWS, Snowflake, and Databricks spend back to the "
    "exact query, job, or pipeline that caused it, and forecasts what the month will "
    "cost before the invoice arrives."
)

CORE_CONCEPTS = [
    {
        "id": "attribution",
        "title": "Cost Attribution",
        "description": "Every dollar (or credit, or cluster-hour) is tied to the exact service, query, or job that produced it -- not just a source-level total.",
    },
    {
        "id": "anomaly",
        "title": "Anomaly Detection",
        "description": "A leave-one-out z-score flags genuine statistical outliers against same-day, same-group baselines -- not a hardcoded dollar threshold.",
    },
    {
        "id": "forecast",
        "title": "Month-End Forecast",
        "description": "Run-rate and trend projections estimate the full month's bill from partial data, reconciled against AWS's own native forecast where available.",
    },
    {
        "id": "optimization",
        "title": "Optimization Rules",
        "description": "A rules engine flags concrete, evidence-backed savings opportunities grounded in the actual ingested metadata -- never generic advice.",
    },
]

ANOMALY_SEMANTIC_COLOR = "#EF4444"
SAVINGS_SEMANTIC_COLOR = "#34D399"
ACCENT_COLOR = "#22D3EE"
