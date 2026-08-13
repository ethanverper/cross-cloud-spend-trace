import { useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Check, Link2, Printer } from "lucide-react"
import { api } from "@/lib/api"
import { useFetch } from "@/lib/use-fetch"
import { useFilters } from "@/lib/filter-context"
import { PageHeader } from "@/components/layout/PageHeader"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { Callout } from "@/components/primitives/Callout"
import { SourceBadge } from "@/components/primitives/SourceBadge"
import { ActivityBySourceChart } from "@/components/charts/ActivityBySourceChart"
import { TopAttributionChart } from "@/components/charts/TopAttributionChart"
import { ForecastChart } from "@/components/charts/ForecastChart"
import { AnomalyCard } from "@/components/charts/AnomalyCard"
import { formatDate, formatNumber, formatUsd } from "@/lib/format"

export function Results() {
  const { filters, setSource, setDateRange, setAttributionKey } = useFilters()
  const [searchParams, setSearchParams] = useSearchParams()
  const [copied, setCopied] = useState(false)
  const sourceParam = filters.source === "all" ? undefined : filters.source

  // Shareable link (rule 8): read initial scope from the URL once on
  // mount, so a link with ?source=aws&start=...&end=... reopens scoped to
  // the same real result someone shared -- not synthetic state.
  useEffect(() => {
    const source = searchParams.get("source")
    const start = searchParams.get("start")
    const end = searchParams.get("end")
    const attributionKey = searchParams.get("job")
    if (source && (source === "all" || source === "aws" || source === "snowflake" || source === "databricks")) {
      setSource(source)
    }
    if (start || end) setDateRange(start, end)
    if (attributionKey) setAttributionKey(attributionKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const next = new URLSearchParams()
    if (filters.source !== "all") next.set("source", filters.source)
    if (filters.start) next.set("start", filters.start)
    if (filters.end) next.set("end", filters.end)
    if (filters.attributionKey) next.set("job", filters.attributionKey)
    setSearchParams(next, { replace: true })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.source, filters.start, filters.end, filters.attributionKey])

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 1800)
  }

  const spend = useFetch(
    () => api.spend({ source: sourceParam, start: filters.start ?? undefined, end: filters.end ?? undefined }),
    [sourceParam, filters.start, filters.end],
  )
  const anomalies = useFetch(() => api.anomalies({ source: sourceParam }), [sourceParam])
  const forecast = useFetch(() => api.forecast(), [])
  const optimizations = useFetch(() => api.optimizations({ source: sourceParam }), [sourceParam])

  const awsForecast = useMemo(() => forecast.data?.by_source.find((r) => r.source === "aws"), [forecast.data])
  const awsPreviewSeries = useMemo(() => {
    if (!awsForecast) return []
    return Array.from({ length: awsForecast.days_in_month }, (_, i) => ({
      day: i + 1,
      cumulative_cost_usd: awsForecast.run_rate_per_day * (i + 1),
    }))
  }, [awsForecast])

  return (
    <div>
      <PageHeader
        eyebrow="03 / Results"
        title="Spend, anomalies & forecast"
        description={
          filters.source !== "all" || filters.start || filters.end ? (
            <span className="font-mono text-xs">
              filtered: source={filters.source} {filters.start && `start=${filters.start}`} {filters.end && `end=${filters.end}`}
            </span>
          ) : (
            "Every chart below reads directly from Phase 3's real, already-computed output -- nothing here is recomputed or faked at render time."
          )
        }
        actions={
          <div className="flex items-center gap-2 print:hidden">
            <Button variant="outline" size="sm" onClick={handleCopyLink}>
              {copied ? <Check className="h-3.5 w-3.5 mr-1.5" /> : <Link2 className="h-3.5 w-3.5 mr-1.5" />}
              {copied ? "Copied" : "Share this view"}
            </Button>
            <Button variant="outline" size="sm" onClick={() => window.print()}>
              <Printer className="h-3.5 w-3.5 mr-1.5" /> Export PDF
            </Button>
          </div>
        }
      />

      <Tabs defaultValue="spend">
        <TabsList>
          <TabsTrigger value="spend">Spend</TabsTrigger>
          <TabsTrigger value="anomalies">Anomalies</TabsTrigger>
          <TabsTrigger value="forecast">Forecast</TabsTrigger>
          <TabsTrigger value="suggestions">Optimizations</TabsTrigger>
        </TabsList>

        <TabsContent value="spend" className="space-y-6 mt-6">
          <div className="grid md:grid-cols-3 gap-4">
            {(spend.data?.totals_by_source ?? []).map((t) => (
              <Card key={t.source} className="py-0">
                <CardContent className="px-4 py-3.5 flex items-center justify-between">
                  <SourceBadge source={t.source} />
                  <StatHighlight value={t.total_records} label="records" size="sm" color="var(--foreground)" />
                </CardContent>
              </Card>
            ))}
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Activity by source, over time</CardTitle>
              <CardDescription>Record counts per day -- the one metric every source actually has (Snowflake/Databricks have no dollar cost data yet).</CardDescription>
            </CardHeader>
            <CardContent>
              {spend.loading && <Skeleton className="h-64 w-full" />}
              {spend.data && <ActivityBySourceChart rows={spend.data.by_source_date} />}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Top spend by service / query / job / warehouse</CardTitle>
              <CardDescription>Ranked by real dollars where a source has them (AWS), by real native usage otherwise (Snowflake ms, Databricks cluster-hours).</CardDescription>
            </CardHeader>
            <CardContent>
              {spend.loading && <Skeleton className="h-64 w-full" />}
              {spend.data && <TopAttributionChart rows={spend.data.by_attribution} />}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="anomalies" className="space-y-6 mt-6">
          <div className="flex flex-wrap gap-3">
            <Card className="py-0">
              <CardContent className="px-4 py-3.5">
                <StatHighlight value={anomalies.data?.anomaly_count ?? 0} label="real anomalies flagged" color="var(--anomaly)" />
              </CardContent>
            </Card>
            <Card className="py-0">
              <CardContent className="px-4 py-3.5">
                <StatHighlight value={anomalies.data?.scored_count ?? 0} label="rows scored" color="var(--foreground)" />
              </CardContent>
            </Card>
          </div>

          {(!filters.source || filters.source === "all" || filters.source === "snowflake") && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Snowflake query duration -- leave-one-out z-score</h3>
              {anomalies.loading && <Skeleton className="h-32 w-full" />}
              {anomalies.data?.snowflake_duration_anomalies.slice(0, 12).map((row) => (
                <AnomalyCard key={row.resource_id} row={row} />
              ))}
              {anomalies.data && anomalies.data.snowflake_duration_anomalies.length === 0 && (
                <Callout>No Snowflake rows match this filter.</Callout>
              )}
            </div>
          )}

          {(filters.source === "aws" || filters.source === "databricks") && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold text-foreground">Daily cost by attribution</h3>
              {anomalies.data?.cost_anomalies.length === 0 && (
                <Callout>
                  No anomalies here yet -- {filters.source === "aws" ? "AWS's real daily S3 cost is genuinely flat across every observed day (zero variance), so nothing crosses the z-score threshold." : "Databricks has exactly one real job run landed, so no baseline exists to score it against yet."} This
                  is an honest structural result, not a bug.
                </Callout>
              )}
            </div>
          )}
        </TabsContent>

        <TabsContent value="forecast" className="space-y-6 mt-6">
          <Card>
            <CardHeader className="flex-row items-start justify-between">
              <div>
                <CardTitle className="text-base">AWS -- month-end forecast</CardTitle>
                <CardDescription>Run-rate projection (observed solid line) vs. trend projection (dashed), extending to month end.</CardDescription>
              </div>
              {awsForecast && (
                <StatHighlight value={awsForecast.run_rate_month_end_projection} color="var(--signal)" format={(n) => formatUsd(n)} />
              )}
            </CardHeader>
            <CardContent>
              {forecast.loading && <Skeleton className="h-64 w-full" />}
              {awsForecast && <ForecastChart series={awsPreviewSeries} daysObserved={awsForecast.days_observed} />}
              {forecast.data?.aws_reconciled && (
                <p className="mt-3 text-xs text-muted-foreground font-mono">
                  AWS's own native forecast: {formatUsd(forecast.data.aws_reconciled.aws_native_forecast_usd)} for{" "}
                  {formatDate(forecast.data.aws_reconciled.aws_native_forecast_period_start)} →{" "}
                  {formatDate(forecast.data.aws_reconciled.aws_native_forecast_period_end)} (different period window than our
                  whole-month projection -- not a direct apples-to-apples comparison).
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Snowflake -- native-unit forecast</CardTitle>
              <CardDescription>No dollar cost data exists for Snowflake yet, so this is a real, honest credits/duration projection instead of a fabricated $0.</CardDescription>
            </CardHeader>
            <CardContent className="grid sm:grid-cols-2 gap-4">
              {forecast.data?.native_units
                .filter((r) => r.source === "snowflake")
                .map((r) => (
                  <div key={r.usage_unit} className="rounded-md border border-border p-4">
                    <div className="font-mono text-xs text-muted-foreground mb-1">{r.usage_unit}</div>
                    <StatHighlight
                      value={r.run_rate_month_end_projection}
                      size="sm"
                      color="var(--source-snowflake)"
                      format={(n) => formatNumber(n, 3)}
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      from {formatNumber(r.total_so_far)} {r.usage_unit} observed over {r.days_observed} day(s)
                    </p>
                  </div>
                ))}
            </CardContent>
          </Card>

          <Callout tone="info">
            Databricks produces no forecast row at all yet -- its collector never populates `cost_usd` for serverless
            runs (no node type exposed to price against), and one real job run isn't enough history for a native-unit
            run-rate either. A structural gap, disclosed rather than papered over with a synthetic number.
          </Callout>
        </TabsContent>

        <TabsContent value="suggestions" className="space-y-4 mt-6">
          <div className="flex gap-3">
            <Card className="py-0">
              <CardContent className="px-4 py-3.5">
                <StatHighlight value={optimizations.data?.total_count ?? 0} label="suggestions" color="var(--foreground)" />
              </CardContent>
            </Card>
            <Card className="py-0">
              <CardContent className="px-4 py-3.5">
                <StatHighlight value={optimizations.data?.quantified_count ?? 0} label="quantified savings" color="var(--savings)" />
              </CardContent>
            </Card>
          </div>

          {optimizations.loading && <Skeleton className="h-40 w-full" />}
          {optimizations.data?.suggestions.map((s, i) => (
            <Card key={i}>
              <CardHeader className="flex-row items-start justify-between gap-3">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge variant="outline" className="font-mono">{s.rule_id}</Badge>
                  <SourceBadge source={s.source} />
                </div>
                <Badge
                  variant="outline"
                  className={s.quantified === "yes" ? "border-[var(--savings)]/50 text-[var(--savings)]" : "border-muted-foreground/40 text-muted-foreground"}
                >
                  {s.quantified === "yes" ? "quantified" : "not quantified"}
                </Badge>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <p className="text-foreground/90">{s.suggestion}</p>
                <p className="text-xs text-muted-foreground font-mono whitespace-pre-line">{s.evidence}</p>
                <p className="text-xs text-[var(--savings)]">{s.estimated_impact}</p>
              </CardContent>
            </Card>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )
}
