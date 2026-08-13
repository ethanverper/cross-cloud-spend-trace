import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Lead } from "@/components/primitives/Lead"
import { Callout } from "@/components/primitives/Callout"
import { Example } from "@/components/primitives/Example"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { Bullets } from "@/components/primitives/Bullets"

function FormulaBlock({ formula }: { formula: string }) {
  return (
    <pre className="rounded-md border border-border bg-muted/50 px-4 py-3 font-mono text-sm overflow-x-auto text-foreground">
      {formula}
    </pre>
  )
}

/** Content and decomposition plan owned by brand-creative per decision 0005
 * section 7 (Phase 4); implemented here verbatim. */
export function ReferencesFormulas() {
  return (
    <div>
      <PageHeader eyebrow="07 / References & Formulas" title="How every number is actually computed" />

      <div className="space-y-6">
        <Lead>Every number this product shows is computed by one of three documented methods, not a black box.</Lead>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">1. Leave-one-out z-score (anomaly detection)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormulaBlock
              formula={`z_i = (x_i - mean(x \\ {x_i})) / stddev(x \\ {x_i})

where "x \\ {x_i}" is every other observation in row i's
group (same day, same warehouse/service) -- i's own value is
excluded from its own baseline.`}
            />
            <Callout>
              Leave-one-out, not a naive in-group z-score: scoring a row against a baseline that includes itself lets
              a genuine outlier drag its own mean/stddev toward it, muting the very signal being measured. Excluding
              the row from its own baseline is what actually lets a real spike register a high score instead of being
              partially absorbed by it.
            </Callout>
            <Example title="Real worked example">
              <div className="flex flex-wrap items-center gap-6">
                <div>
                  <div className="text-xs text-muted-foreground">Query</div>
                  <div className="font-mono text-xs">unfiltered CUSTOMER JOIN ORDERS</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">duration vs. baseline</div>
                  <div className="font-mono text-xs">11,899ms vs. mean 260.6ms, stddev 557.0ms</div>
                </div>
                <StatHighlight value={20.9} label="z-score" color="var(--anomaly)" size="sm" />
              </div>
            </Example>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">2. Run-rate + trend (month-end forecast)</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FormulaBlock
              formula={`run_rate_forecast = (total_so_far / days_observed) * days_in_month

trend_forecast = intercept + slope * days_in_month
  where slope, intercept = regr_slope(y, x), regr_intercept(y, x)
  fit to cumulative cost (y) vs. day-of-month (x)`}
            />
            <p className="text-sm text-muted-foreground leading-relaxed">
              Computed independently and identically for every source (Spark SQL <code className="font-mono text-xs px-1 py-0.5 rounded bg-muted">regr_slope</code>/
              <code className="font-mono text-xs px-1 py-0.5 rounded bg-muted">regr_intercept</code>), rather than being AWS-forecast-API-specific -- Snowflake and
              Databricks have no native forecast API at all, so a source-specific approach would leave two of three
              sources with no forecast whatsoever. AWS's own real Cost Explorer forecast is surfaced alongside for
              comparison, never overridden by it.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">3. Optimization rules -- real trigger conditions</CardTitle>
          </CardHeader>
          <CardContent>
            <Bullets
              items={[
                {
                  id: "repeated",
                  text: (
                    <>
                      <span className="font-mono text-xs">repeated_identical_query</span> -- fires when the exact same
                      query text runs more than once on the same warehouse; quantifies the % of that query's total
                      runtime attributable to every run after the first.
                    </>
                  ),
                },
                {
                  id: "unfiltered",
                  text: (
                    <>
                      <span className="font-mono text-xs">unfiltered_table_scan</span> -- fires when a query has no
                      WHERE clause against a known table; not quantified (bytes_scanned alone can't derive a real %
                      without the table's row/partition distribution -- stating one would be a guess).
                    </>
                  ),
                },
                {
                  id: "idle",
                  text: (
                    <>
                      <span className="font-mono text-xs">idle_flat_cost_resource</span> -- fires when a resource's
                      daily cost is flat (zero variance) across &gt;= N consecutive days; quantifies up to 100% of
                      accumulated cost as conditionally avoidable if the resource is unneeded.
                    </>
                  ),
                },
                {
                  id: "gap",
                  text: (
                    <>
                      <span className="font-mono text-xs">databricks_cost_visibility_gap</span> -- fires when a
                      Databricks run lands with <span className="font-mono text-xs">cost_usd=None</span>; not
                      quantified (it's a visibility gap, not a dollar figure).
                    </>
                  ),
                },
              ]}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
