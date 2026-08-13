"""Pydantic response models for the Phase 5 JSON API.

Aggregate/wrapper shapes are typed explicitly. Individual row payloads
(spend/anomaly/optimization rows) stay `dict[str, Any]` deliberately --
their real columns genuinely differ per source (a Snowflake anomaly row
carries `query_text_preview`/`baseline_stddev`; an AWS spend row carries
`cost_bases_present`; a Databricks row carries `pricing_note`) because
that's what the actual collectors land (decision 0002), and flattening
them into one artificial union type would either drop real fields or
paper over genuine per-source differences with nulls. `loader.df_records`
already makes every value JSON-safe.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class SourceChip(BaseModel):
    source: str
    label: str
    color: str
    record_count: int
    note: str


class ConceptChip(BaseModel):
    id: str
    title: str
    description: str


class TracePathStep(BaseModel):
    label: str
    sublabel: str | None = None
    color: str


class TracePathPreview(BaseModel):
    steps: list[TracePathStep]
    metric_label: str
    metric_value: str
    z_score: float | None = None


class ForecastSparkPoint(BaseModel):
    day: int
    cumulative_cost_usd: float


class ForecastPreview(BaseModel):
    source: str
    unit: str
    days_observed: int
    run_rate_month_end_projection: float
    series: list[ForecastSparkPoint]


class OverviewResponse(BaseModel):
    mechanism_statement: str
    sources: list[SourceChip]
    concepts: list[ConceptChip]
    headline_anomaly: TracePathPreview | None
    forecast_preview: ForecastPreview | None
    total_records: int
    run_date: str | None
    generated_at: str


class FilterOption(BaseModel):
    value: str
    label: str
    color: str | None = None
    count: int | None = None


class AttributionOption(BaseModel):
    source: str
    attribution_kind: str
    attribution_key: str
    label: str


class FiltersResponse(BaseModel):
    sources: list[FilterOption]
    date_range: dict[str, str | None]
    attribution_kinds: list[FilterOption]
    attribution_options: list[AttributionOption]
    source_note: str


class SpendResponse(BaseModel):
    by_source_date: list[dict[str, Any]]
    by_attribution: list[dict[str, Any]]
    totals_by_source: list[dict[str, Any]]


class AnomaliesResponse(BaseModel):
    cost_anomalies: list[dict[str, Any]]
    snowflake_duration_anomalies: list[dict[str, Any]]
    anomaly_count: int
    scored_count: int


class ForecastResponse(BaseModel):
    by_source: list[dict[str, Any]]
    combined: dict[str, Any] | None
    native_units: list[dict[str, Any]]
    aws_reconciled: dict[str, Any] | None


class OptimizationsResponse(BaseModel):
    suggestions: list[dict[str, Any]]
    quantified_count: int
    total_count: int


class DatasetProvenance(BaseModel):
    table: str
    source: str
    real_record_count: int
    description: str


class MetaResponse(BaseModel):
    run_date: str | None
    generated_at: str
    provenance: list[DatasetProvenance]
    builder_name: str
    builder_links: dict[str, str]
    repo_url: str
