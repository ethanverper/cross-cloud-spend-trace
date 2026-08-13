// Typed client for the Phase 5 JSON API (app/api/routes.py). Every shape
// here mirrors app/api/schemas.py directly -- no field is invented on the
// frontend that the backend doesn't actually send.

export type SourceId = "aws" | "snowflake" | "databricks"

export interface SourceChip {
  source: SourceId
  label: string
  color: string
  record_count: number
  note: string
}

export interface ConceptChip {
  id: string
  title: string
  description: string
}

export interface TracePathStep {
  label: string
  sublabel: string | null
  color: string
}

export interface TracePathPreview {
  steps: TracePathStep[]
  metric_label: string
  metric_value: string
  z_score: number | null
}

export interface ForecastSparkPoint {
  day: number
  cumulative_cost_usd: number
}

export interface ForecastPreview {
  source: string
  unit: string
  days_observed: number
  run_rate_month_end_projection: number
  series: ForecastSparkPoint[]
}

export interface OverviewResponse {
  mechanism_statement: string
  sources: SourceChip[]
  concepts: ConceptChip[]
  headline_anomaly: TracePathPreview | null
  forecast_preview: ForecastPreview | null
  total_records: number
  run_date: string | null
  generated_at: string
}

export interface FilterOption {
  value: string
  label: string
  color?: string | null
  count?: number | null
}

export interface AttributionOption {
  source: SourceId
  attribution_kind: string
  attribution_key: string
  label: string
}

export interface FiltersResponse {
  sources: FilterOption[]
  date_range: { min: string | null; max: string | null }
  attribution_kinds: FilterOption[]
  attribution_options: AttributionOption[]
  source_note: string
}

// Row shapes below intentionally stay loose (Record<string, unknown>-ish
// with the fields we know we render) -- the real columns genuinely differ
// per source (see app/api/schemas.py's own docstring on this).
export interface SpendBySourceDateRow {
  source: SourceId
  usage_date: string
  cost_usd_total: number | null
  record_count: number
  records_with_cost: number
  cost_bases_present: string[]
}

export interface SpendByAttributionRow {
  source: SourceId
  attribution_kind: string
  attribution_key: string
  usage_date: string
  cost_usd_total: number | null
  usage_quantity_total: number | null
  usage_unit: string | null
  record_count: number
}

export interface SpendTotalRow {
  source: SourceId
  total_cost_usd: number | null
  total_records: number
  days_observed: number
}

export interface SpendResponse {
  by_source_date: SpendBySourceDateRow[]
  by_attribution: SpendByAttributionRow[]
  totals_by_source: SpendTotalRow[]
}

export interface CostAnomalyRow {
  source: SourceId
  attribution_kind: string
  attribution_key: string
  usage_date: string
  cost_usd_total: number | null
  z_score: number | null
  baseline_mean: number | null
  baseline_stddev: number | null
  group_n_other: number | null
  status: string
  anomaly: boolean
}

export interface SnowflakeAnomalyRow {
  resource_id: string
  usage_date: string
  attribution_key: string
  query_type: string | null
  query_text_preview: string | null
  usage_quantity: number | null
  usage_unit: string | null
  baseline_mean: number | null
  baseline_stddev: number | null
  group_n_other: number | null
  z_score: number | null
  status: string
  anomaly: boolean
}

export interface AnomaliesResponse {
  cost_anomalies: CostAnomalyRow[]
  snowflake_duration_anomalies: SnowflakeAnomalyRow[]
  anomaly_count: number
  scored_count: number
}

export interface ForecastBySourceRow {
  source: SourceId
  days_observed: number
  total_so_far: number
  run_rate_per_day: number
  run_rate_month_end_projection: number
  trend_month_end_projection: number
  days_in_month: number
  status: string
  confidence: string
}

export interface ForecastNativeUnitRow {
  source: SourceId
  usage_unit: string
  days_observed: number
  total_so_far: number
  run_rate_per_day: number
  days_in_month: number
  run_rate_month_end_projection: number
}

export interface ForecastResponse {
  by_source: ForecastBySourceRow[]
  combined: Record<string, unknown> | null
  native_units: ForecastNativeUnitRow[]
  aws_reconciled: {
    aws_native_forecast_usd: number
    aws_native_forecast_period_start: string
    aws_native_forecast_period_end: string
    run_rate_month_end_projection: number
    [k: string]: unknown
  } | null
}

export interface OptimizationSuggestion {
  rule_id: string
  source: SourceId
  attribution_key: string
  resource_ids_sample: string
  evidence: string
  suggestion: string
  estimated_impact: string
  quantified: "yes" | "no"
}

export interface OptimizationsResponse {
  suggestions: OptimizationSuggestion[]
  quantified_count: number
  total_count: number
}

export interface DatasetProvenance {
  table: string
  source: SourceId
  real_record_count: number
  description: string
}

export interface MetaResponse {
  run_date: string | null
  generated_at: string
  provenance: DatasetProvenance[]
  builder_name: string
  builder_links: Record<string, string>
  repo_url: string
}

const BASE = "/api"

async function getJSON<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, v)
    }
  }
  const res = await fetch(url.toString().replace(window.location.origin, ""))
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  overview: () => getJSON<OverviewResponse>("/overview"),
  filters: () => getJSON<FiltersResponse>("/filters"),
  spend: (params: { source?: string; attribution_kind?: string; start?: string; end?: string }) =>
    getJSON<SpendResponse>("/spend", params),
  anomalies: (params: { source?: string }) => getJSON<AnomaliesResponse>("/anomalies", params),
  forecast: () => getJSON<ForecastResponse>("/forecast"),
  optimizations: (params: { source?: string }) => getJSON<OptimizationsResponse>("/optimizations", params),
  meta: () => getJSON<MetaResponse>("/meta"),
}
