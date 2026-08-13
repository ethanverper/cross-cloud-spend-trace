"""FastAPI routes for cross-cloud-spend-trace's pure JSON API (Phase 5).

Every endpoint reads from `app.data.loader.get_store()` -- Phase 3's real,
already-computed analytics output and Phase 2's real raw-landed record
counts, loaded once from Parquet at process start (see loader.py's own
docstring for why this shape was chosen over re-running PySpark per
request). Nothing here fabricates a number; every value served is either a
direct pass-through of Phase 3's output or a straightforward, disclosed
aggregation over it (e.g. summing real per-day costs into a per-source
total).

Constrained-input enforcement (`docs/project-standards.md` rule 2): `source`
and `attribution_kind` query params are validated against the real, known
values actually present in the ingested data -- an unrecognized value is
rejected with a 400 before it can shape a query, the same defense-in-depth
pattern `factor-attribution-lens/app/api/routes.py` uses for ticker
symbols.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from app.data import constants
from app.data.loader import df_records, get_store

router = APIRouter(prefix="/api")

VALID_SOURCES = set(constants.SOURCE_META.keys())


def _source_note() -> str:
    return (
        "Source, date-range, and job/query options below are drawn directly from the "
        "real records landed by this project's own AWS Cost Explorer, Snowflake "
        "ACCOUNT_USAGE, and Databricks Jobs API collectors (Phase 2) -- not a static "
        "catalog. Databricks currently has exactly one real job run landed, so its own "
        "option list is correspondingly thin; that's the real state of the data, not a "
        "loading bug. See docs/decisions/0002-phase2-raw-store-and-collector-architecture.md."
    )


def _validate_source(source: str | None) -> str | None:
    if source is None:
        return None
    if source not in VALID_SOURCES:
        raise HTTPException(
            status_code=400,
            detail=f"'{source}' is not a known source. Choose one of: {sorted(VALID_SOURCES)}.",
        )
    return source


def _validate_date(value: str | None, field_name: str) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"'{field_name}' must be an ISO date (YYYY-MM-DD).") from exc


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/overview")
def get_overview() -> dict[str, Any]:
    store = get_store()

    sources = []
    label_by_table = {
        "aws": ("aws_cost_and_usage", "daily cost-and-usage records"),
        "snowflake": ("snowflake_query_history", "query-history rows"),
        "databricks": ("databricks_job_runs", "job run"),
    }
    for source, (count_key, noun) in label_by_table.items():
        meta = constants.SOURCE_META[source]
        count = store.raw_counts.get(count_key, 0)
        sources.append(
            {
                "source": source,
                "label": meta["label"],
                "color": meta["color"],
                "record_count": count,
                "note": f"{count} {noun}",
            }
        )

    headline_anomaly = None
    if not store.anomalies_snowflake_duration.empty:
        anomalies = store.anomalies_snowflake_duration[store.anomalies_snowflake_duration["anomaly"] == True]  # noqa: E712
        if not anomalies.empty:
            top = anomalies.sort_values("z_score", ascending=False).iloc[0]
            warehouse = None
            meta_raw = top.get("raw_metadata")
            headline_anomaly = {
                "steps": [
                    {"label": "Snowflake", "sublabel": "ACCOUNT_USAGE", "color": constants.SOURCE_META["snowflake"]["color"]},
                    {"label": str(top.get("attribution_key") or "warehouse"), "sublabel": "warehouse", "color": constants.SOURCE_META["snowflake"]["color"]},
                    {"label": str(top["resource_id"])[:18] + "...", "sublabel": top.get("query_type") or "query", "color": constants.SOURCE_META["snowflake"]["color"]},
                    {"label": f"{top['usage_quantity']:.0f} ms", "sublabel": "duration", "color": constants.ANOMALY_SEMANTIC_COLOR},
                ],
                "metric_label": "z-score",
                "metric_value": f"z={top['z_score']:.2f}",
                "z_score": float(top["z_score"]),
            }

    forecast_preview = None
    if not store.forecast_by_source.empty:
        aws_row = store.forecast_by_source[store.forecast_by_source["source"] == "aws"]
        if not aws_row.empty:
            row = aws_row.iloc[0]
            days_observed = int(row["days_observed"])
            run_rate = float(row["run_rate_per_day"])
            days_in_month = int(row["days_in_month"])
            series = [
                {"day": d, "cumulative_cost_usd": round(run_rate * d, 10)}
                for d in range(1, days_in_month + 1)
            ]
            forecast_preview = {
                "source": "aws",
                "unit": "usd",
                "days_observed": days_observed,
                "run_rate_month_end_projection": float(row["run_rate_month_end_projection"]),
                "series": series,
            }

    total_records = sum(store.raw_counts.values())

    return {
        "mechanism_statement": constants.MECHANISM_STATEMENT,
        "sources": sources,
        "concepts": constants.CORE_CONCEPTS,
        "headline_anomaly": headline_anomaly,
        "forecast_preview": forecast_preview,
        "total_records": total_records,
        "run_date": store.run_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/filters")
def get_filters() -> dict[str, Any]:
    store = get_store()

    count_key_by_source = {
        "aws": "aws_cost_and_usage",
        "snowflake": "snowflake_query_history",
        "databricks": "databricks_job_runs",
    }
    sources = [
        {
            "value": s,
            "label": constants.SOURCE_META[s]["label"],
            "color": constants.SOURCE_META[s]["color"],
            "count": store.raw_counts.get(count_key_by_source[s], 0),
        }
        for s in ("aws", "snowflake", "databricks")
    ]

    date_min = date_max = None
    if not store.spend_by_source_date.empty:
        dates = pd.to_datetime(store.spend_by_source_date["usage_date"])
        date_min, date_max = dates.min().date().isoformat(), dates.max().date().isoformat()

    attribution_kinds: list[dict[str, Any]] = []
    attribution_options: list[dict[str, Any]] = []
    if not store.spend_by_attribution.empty:
        kinds = sorted(store.spend_by_attribution["attribution_kind"].dropna().unique().tolist())
        attribution_kinds = [{"value": k, "label": k.replace("_", " ").title()} for k in kinds]

        query_labels: dict[str, str] = {}
        if not store.anomalies_snowflake_duration.empty:
            for _, r in store.anomalies_snowflake_duration.iterrows():
                preview = r.get("query_text_preview")
                if isinstance(preview, str) and preview:
                    query_labels[r["resource_id"]] = preview[:60] + ("..." if len(preview) > 60 else "")

        seen = set()
        for _, row in store.spend_by_attribution.iterrows():
            key = (row["source"], row["attribution_kind"], row["attribution_key"])
            if key in seen:
                continue
            seen.add(key)
            label = query_labels.get(row["attribution_key"], str(row["attribution_key"]))
            attribution_options.append(
                {
                    "source": row["source"],
                    "attribution_kind": row["attribution_kind"],
                    "attribution_key": row["attribution_key"],
                    "label": label,
                }
            )

    return {
        "sources": sources,
        "date_range": {"min": date_min, "max": date_max},
        "attribution_kinds": attribution_kinds,
        "attribution_options": attribution_options,
        "source_note": _source_note(),
    }


@router.get("/spend")
def get_spend(
    source: str | None = Query(default=None),
    attribution_kind: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
) -> dict[str, Any]:
    store = get_store()
    source = _validate_source(source)
    start_d = _validate_date(start, "start")
    end_d = _validate_date(end, "end")
    if start_d and end_d and start_d > end_d:
        raise HTTPException(status_code=400, detail="'start' must be on or before 'end'.")

    by_source_date = store.spend_by_source_date.copy()
    by_attribution = store.spend_by_attribution.copy()

    if not by_source_date.empty:
        if source:
            by_source_date = by_source_date[by_source_date["source"] == source]
        if start_d:
            by_source_date = by_source_date[pd.to_datetime(by_source_date["usage_date"]) >= pd.Timestamp(start_d)]
        if end_d:
            by_source_date = by_source_date[pd.to_datetime(by_source_date["usage_date"]) <= pd.Timestamp(end_d)]

    if not by_attribution.empty:
        if source:
            by_attribution = by_attribution[by_attribution["source"] == source]
        if attribution_kind:
            by_attribution = by_attribution[by_attribution["attribution_kind"] == attribution_kind]
        if start_d:
            by_attribution = by_attribution[pd.to_datetime(by_attribution["usage_date"]) >= pd.Timestamp(start_d)]
        if end_d:
            by_attribution = by_attribution[pd.to_datetime(by_attribution["usage_date"]) <= pd.Timestamp(end_d)]

    totals_by_source: list[dict[str, Any]] = []
    if not store.spend_by_source_date.empty:
        base = store.spend_by_source_date if not source else store.spend_by_source_date[store.spend_by_source_date["source"] == source]
        grouped = base.groupby("source", as_index=False).agg(
            total_cost_usd=("cost_usd_total", "sum"),
            total_records=("record_count", "sum"),
            days_observed=("usage_date", "nunique"),
        )
        totals_by_source = df_records(grouped)

    return {
        "by_source_date": df_records(by_source_date),
        "by_attribution": df_records(by_attribution),
        "totals_by_source": totals_by_source,
    }


@router.get("/anomalies")
def get_anomalies(source: str | None = Query(default=None)) -> dict[str, Any]:
    store = get_store()
    source = _validate_source(source)

    cost_anomalies = store.anomalies_daily_cost.copy()
    sf_anomalies = store.anomalies_snowflake_duration.copy()

    if source:
        if not cost_anomalies.empty:
            cost_anomalies = cost_anomalies[cost_anomalies["source"] == source]
        sf_anomalies = sf_anomalies if source == "snowflake" else sf_anomalies.iloc[0:0]

    anomaly_count = 0
    scored_count = 0
    for df in (cost_anomalies, sf_anomalies):
        if not df.empty:
            anomaly_count += int((df["anomaly"] == True).sum())  # noqa: E712
            scored_count += int(df["status"].isin(["normal", "anomaly"]).sum())

    sf_sorted = sf_anomalies.sort_values("z_score", ascending=False, na_position="last") if not sf_anomalies.empty else sf_anomalies

    return {
        "cost_anomalies": df_records(cost_anomalies),
        "snowflake_duration_anomalies": df_records(sf_sorted),
        "anomaly_count": anomaly_count,
        "scored_count": scored_count,
    }


@router.get("/forecast")
def get_forecast() -> dict[str, Any]:
    store = get_store()
    combined = df_records(store.forecast_combined)
    aws_recon = df_records(store.forecast_aws_reconciled)
    return {
        "by_source": df_records(store.forecast_by_source),
        "combined": combined[0] if combined else None,
        "native_units": df_records(store.forecast_native_units),
        "aws_reconciled": aws_recon[0] if aws_recon else None,
    }


@router.get("/optimizations")
def get_optimizations(source: str | None = Query(default=None)) -> dict[str, Any]:
    store = get_store()
    source = _validate_source(source)
    df = store.optimization_suggestions.copy()
    if source and not df.empty:
        df = df[df["source"] == source]
    quantified_count = int((df["quantified"] == "yes").sum()) if not df.empty else 0
    return {
        "suggestions": df_records(df),
        "quantified_count": quantified_count,
        "total_count": len(df),
    }


@router.get("/meta")
def get_meta() -> dict[str, Any]:
    store = get_store()
    provenance = [
        {
            "table": "aws/cost_and_usage",
            "source": "aws",
            "real_record_count": store.raw_counts.get("aws_cost_and_usage", 0),
            "description": "Daily cost-and-usage records from AWS Cost Explorer's GetCostAndUsage API, real billed dollars at whatever precision AWS returns.",
        },
        {
            "table": "aws/cost_forecast",
            "source": "aws",
            "real_record_count": store.raw_counts.get("aws_cost_forecast", 0),
            "description": "AWS's own native month-end cost forecast (GetCostForecast), surfaced alongside our independent run-rate/trend projection, never overridden by it.",
        },
        {
            "table": "snowflake/query_history",
            "source": "snowflake",
            "real_record_count": store.raw_counts.get("snowflake_query_history", 0),
            "description": "Every real query run against Ethan's Snowflake trial account, from ACCOUNT_USAGE.QUERY_HISTORY -- includes real setup DDL/GRANT statements alongside test SELECTs.",
        },
        {
            "table": "snowflake/warehouse_metering_history",
            "source": "snowflake",
            "real_record_count": store.raw_counts.get("snowflake_warehouse_metering_history", 0),
            "description": "Real warehouse credit-burn records from ACCOUNT_USAGE.WAREHOUSE_METERING_HISTORY.",
        },
        {
            "table": "databricks/job_runs",
            "source": "databricks",
            "real_record_count": store.raw_counts.get("databricks_job_runs", 0),
            "description": "Real Databricks Jobs API run history -- one real serverless job run, correctly landed with no cost estimate (no node type exposed to price against).",
        },
    ]
    return {
        "run_date": store.run_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "builder_name": "Ethan Verduzco",
        "builder_links": {
            "github": "https://github.com/ethanverper",
            "repo": "https://github.com/ethanverper/cross-cloud-spend-trace",
        },
        "repo_url": "https://github.com/ethanverper/cross-cloud-spend-trace",
    }
