import { api } from "@/lib/api"
import { useFetch } from "@/lib/use-fetch"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Lead } from "@/components/primitives/Lead"
import { Bullets, type BulletItem } from "@/components/primitives/Bullets"
import { Callout } from "@/components/primitives/Callout"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { Example } from "@/components/primitives/Example"
import { formatUsd, formatZScore } from "@/lib/format"

/**
 * Interpretation & Key Takeaways (project-standards rule 9a) -- owned by
 * business-intelligence per decision 0001's explicit ownership reassignment
 * (this project has no quant-analyst statistical-model mandate, it's pure
 * cost aggregation and reporting). Content decomposition
 * (Lead/StatHighlight/Bullets/Example/Callout) was planned in writing
 * *before* this component was built -- see the scratchpad decomposition
 * plan referenced in docs/decisions/0006-phase5-dashboard-api-architecture.md
 * -- specifically so this project doesn't repeat Factor Attribution Lens's
 * own documented mistake (rule 15's first real sweep shipped every other
 * section as real components and still shipped this exact section as
 * untouched paragraph prose, caught late by Ethan).
 *
 * Hard limit, enforced throughout: interpretation only, never prescription
 * -- "worth investigating," never "you should migrate/add/buy."
 */
export function Interpretation() {
  const overview = useFetch(() => api.overview(), [])
  const anomalies = useFetch(() => api.anomalies({}), [])
  const optimizations = useFetch(() => api.optimizations({}), [])
  const forecast = useFetch(() => api.forecast(), [])

  const loading = overview.loading || anomalies.loading || optimizations.loading || forecast.loading

  const headlineZ = overview.data?.headline_anomaly?.z_score ?? null
  const repeatedQuery = optimizations.data?.suggestions.find((s) => s.rule_id === "repeated_identical_query")
  const totalRecords = overview.data?.total_records ?? null
  const awsForecast = forecast.data?.by_source.find((r) => r.source === "aws")
  const awsReconciled = forecast.data?.aws_reconciled

  const bullets: BulletItem[] = [
    {
      id: "join-outlier",
      text: (
        <>
          The <code className="font-mono text-xs px-1 py-0.5 rounded bg-muted">CUSTOMER JOIN ORDERS</code> query that
          triggered the headline anomaly is an unbounded join filtered only by a trailing <code className="font-mono text-xs px-1 py-0.5 rounded bg-muted">LIMIT 20</code> --
          not a borderline call, an order-of-magnitude outlier at{" "}
          {headlineZ !== null ? formatZScore(headlineZ) : "…"}. Worth investigating whether the same join-then-limit
          pattern recurs elsewhere in the warehouse before it runs against real data volume.
        </>
      ),
    },
    {
      id: "redundant-query",
      text: repeatedQuery ? (
        <>
          <span className="text-foreground">{repeatedQuery.estimated_impact}</span> Implies a caching or
          materialization gap worth investigating before assuming the underlying compute cost is irreducible.
        </>
      ) : (
        "The repeated-query optimization rule flags redundant re-execution as a caching/materialization gap worth investigating."
      ),
    },
    {
      id: "aws-flat",
      text: (
        <>
          AWS's own real daily cost is flat across every observed day (zero variance) -- the anomaly detector's
          silence there is a genuine negative result, not a coverage gap. Worth revisiting once real production-scale
          AWS usage exists to actually vary day to day.
        </>
      ),
    },
    {
      id: "databricks-blind-spot",
      text: (
        <>
          Databricks' one real job run landed with no cost estimate at all -- serverless compute exposes no node type
          to price against, a genuine cost-visibility blind spot, not a missing feature. Worth investigating whether
          the team's actual Databricks usage pattern (serverless vs. provisioned clusters) is one finance could ever
          get a real dollar figure from without a workspace or billing-API change.
        </>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        eyebrow="04 / Interpretation & Key Takeaways"
        title="What this spend pattern implies"
        description="Synthesis of the real results above -- what stands out, what's noteworthy, what's worth investigating. Never a recommendation to buy, migrate, or change infrastructure."
      />

      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-8 w-2/3" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {!loading && (
        <Card className="border-signal/20">
          <CardContent className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-start gap-6">
              <div className="flex-1 space-y-3">
                <Lead>
                  The real signal here isn't dollar magnitude -- it's that the same detection mechanism that would
                  catch a five-figure spike in production already caught a genuine, extreme outlier at whatever
                  (small) scale this account runs at today.
                </Lead>
              </div>
              {headlineZ !== null && (
                <StatHighlight value={headlineZ} label="headline anomaly z-score" color="var(--anomaly)" size="lg" />
              )}
            </div>

            <Bullets items={bullets} />

            <Example title="Worked case -- the redundant-query finding">
              {repeatedQuery ? (
                <p className="whitespace-pre-line">{repeatedQuery.evidence}</p>
              ) : (
                <Skeleton className="h-16 w-full" />
              )}
            </Example>

            {awsForecast && awsReconciled && (
              <Example title="Worked case -- two independent forecasts, sanity-checked against each other">
                <p>
                  Our own run-rate projection ({formatUsd(awsForecast.run_rate_month_end_projection)}) and AWS's own
                  native Cost Explorer forecast ({formatUsd(awsReconciled.aws_native_forecast_usd as number)}) land in
                  the same order of magnitude despite covering different period windows -- worth keeping as a
                  cross-check once real dollar amounts are large enough for the gap between the two methods to
                  actually matter.
                </p>
              </Example>
            )}

            <Callout>
              This section describes what the data implies and what's worth investigating further -- it is never
              prescriptive advice. It does not tell anyone to migrate off serverless compute, add a WHERE clause, or
              change infrastructure; those are decisions for the team that owns the actual workload, made with more
              context than this dashboard has.
            </Callout>

            {totalRecords !== null && (
              <div className="flex items-center gap-3 pt-2 border-t border-border">
                <StatHighlight value={totalRecords} label="real events, mechanism proved end-to-end" color="var(--foreground)" size="sm" />
                <p className="text-xs text-muted-foreground">
                  Nothing in this interpretation required a large account to demonstrate -- the same z-score,
                  forecast, and rules engine apply unchanged at any real scale.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
