import { Link } from "react-router-dom"
import { ArrowRight } from "lucide-react"
import { api } from "@/lib/api"
import { useFetch } from "@/lib/use-fetch"
import { Wordmark } from "@/components/layout/Wordmark"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { TracePath } from "@/components/primitives/TracePath"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { ForecastSparkline } from "@/components/charts/ForecastSparkline"
import { formatUsd } from "@/lib/format"
import { cn } from "@/lib/utils"

/**
 * Rule-14 landing screen (decision 0005 section 6): opens already populated
 * with real Phase 1-3 data -- no "connect your account" step. Everything
 * below is visible without scrolling on a normal viewport: the mechanism
 * statement, three real-data source chips, the four core-concept chips, a
 * genuine result preview (the real z=20.90 anomaly + AWS's real forecast
 * sparkline), and one CTA into the populated dashboard.
 */
export function Overview() {
  const { data, loading, error } = useFetch(() => api.overview(), [])

  return (
    <div className="flex flex-col gap-8">
      <section className="flex flex-col items-start gap-5">
        <Wordmark size="lg" />
        {loading && <Skeleton className="h-8 w-full max-w-2xl" />}
        {error && <p className="text-sm text-destructive">Couldn't reach the API: {error}</p>}
        {data && (
          <p className="max-w-2xl text-lg md:text-xl leading-relaxed text-foreground/90">
            {data.mechanism_statement}
          </p>
        )}

        <Button asChild size="lg" className="mt-1 bg-signal text-black hover:bg-signal/90 active:scale-[0.98] transition-transform">
          <Link to="/results">
            Trace real spend <ArrowRight className="ml-1.5 h-4 w-4" />
          </Link>
        </Button>
      </section>

      <section aria-label="Connected sources" className="flex flex-wrap gap-3">
        {loading &&
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-14 w-56 rounded-lg" />)}
        {data?.sources.map((s) => (
          <Card key={s.source} className="flex-1 min-w-[180px] py-0">
            <CardContent className="flex items-center gap-3 px-4 py-3.5">
              <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: s.color }} aria-hidden />
              <div className="min-w-0">
                <div className="font-semibold text-sm text-foreground">{s.label}</div>
                <div className="font-mono text-xs text-muted-foreground truncate">{s.note}</div>
              </div>
            </CardContent>
          </Card>
        ))}
      </section>

      <section aria-label="Core concepts" className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {(loading ? Array.from({ length: 4 }) : data?.concepts ?? []).map((c, i) =>
          c ? (
            <Card key={(c as { id: string }).id} className="py-0">
              <CardContent className="px-4 py-3.5">
                <div className="text-sm font-semibold text-foreground mb-1">{(c as { title: string }).title}</div>
                <div className="text-xs text-muted-foreground leading-relaxed">{(c as { description: string }).description}</div>
              </CardContent>
            </Card>
          ) : (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ),
        )}
      </section>

      <section aria-label="Real result preview" className="grid md:grid-cols-2 gap-4">
        <Card>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">Real anomaly, already detected</span>
              {data?.headline_anomaly && <StatHighlight value={data.headline_anomaly.z_score ?? 0} color="var(--anomaly)" size="sm" />}
            </div>
            {loading && <Skeleton className="h-16 w-full" />}
            {data?.headline_anomaly && (
              <TracePath
                nodes={data.headline_anomaly.steps.map((s) => ({ label: s.label, sublabel: s.sublabel, color: s.color }))}
              />
            )}
            <p className="text-xs text-muted-foreground">
              A leave-one-out z-score against same-day, same-warehouse queries -- not a hardcoded threshold.{" "}
              <Link to="/references" className="underline underline-offset-2 hover:text-signal">
                See the formula
              </Link>
              .
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">AWS month-end forecast</span>
              {data?.forecast_preview && (
                <StatHighlight value={data.forecast_preview.run_rate_month_end_projection} color="var(--signal)" size="sm" format={(n) => formatUsd(n)} />
              )}
            </div>
            {loading && <Skeleton className="h-16 w-full" />}
            {data?.forecast_preview && (
              <>
                <ForecastSparkline series={data.forecast_preview.series} />
                <p className="text-xs text-muted-foreground">
                  Run-rate projection from {data.forecast_preview.days_observed} real observed days →{" "}
                  <span className="font-mono text-foreground">{formatUsd(data.forecast_preview.run_rate_month_end_projection)}</span> by
                  month end.
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </section>

      <p className={cn("text-xs text-muted-foreground font-mono", loading && "opacity-0")}>
        {data && `${data.total_records} real records ingested, pipeline run_date=${data.run_date}.`}
      </p>
    </div>
  )
}
