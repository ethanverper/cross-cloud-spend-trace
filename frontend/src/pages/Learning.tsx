import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Lead } from "@/components/primitives/Lead"
import { Bullets } from "@/components/primitives/Bullets"
import { Callout } from "@/components/primitives/Callout"
import { Example } from "@/components/primitives/Example"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { FootnoteMarker } from "@/components/primitives/FootnoteMarker"
import { TracePath } from "@/components/primitives/TracePath"
import { ZScoreExplorer } from "@/components/learning/ZScoreExplorer"
import { ForecastMethodCompare } from "@/components/learning/ForecastMethodCompare"
import { Link } from "react-router-dom"

/**
 * Learning (project-standards rule 5 / rule 15) -- dual-register (plain
 * language + technical) walkthroughs of the three real methods this
 * dashboard actually runs. Content and decomposition plan owned by
 * `educator` per decision 0007, implemented here verbatim against that
 * plan, not improvised. Every number below is re-verified directly against
 * data/processed/*\/run_date=2026-08-12/*.parquet -- see decision 0007's
 * "Real numbers, re-verified" section.
 */
export function Learning() {
  return (
    <div>
      <PageHeader
        eyebrow="08 / Learning"
        title="How the mechanism actually works"
        description="Plain language first, then the precise technical definition -- always grounded in this project's own already-computed numbers, never a generic textbook example."
      />

      <div className="space-y-6">
        <Lead>
          Every anomaly, forecast, and suggestion this dashboard shows comes from one of three real, documented
          methods -- this page walks through each one using this project's own actual results, not stand-ins.
        </Lead>

        <Bullets
          items={[
            {
              id: "anomaly",
              text: (
                <>
                  <span className="text-foreground font-medium">Anomaly detection</span> -- a leave-one-out z-score
                  that genuinely fired on real Snowflake query history (<span className="font-mono text-xs">z=20.90</span>).
                </>
              ),
            },
            {
              id: "forecast",
              text: (
                <>
                  <span className="text-foreground font-medium">Month-end forecast</span> -- run-rate + trend,
                  reconciled against AWS's own real native forecast, not overridden by it.
                </>
              ),
            },
            {
              id: "rules",
              text: (
                <>
                  <span className="text-foreground font-medium">Optimization rules</span> -- 4 checks against real
                  ingested metadata, all 4 firing on real data (8 suggestion rows).
                </>
              ),
            },
          ]}
        />

        <Accordion type="single" collapsible defaultValue="anomaly" className="border border-border rounded-lg px-4">
          {/* Card 1 -- Anomaly Detection */}
          <AccordionItem value="anomaly">
            <AccordionTrigger>
              <div className="flex items-center justify-between w-full pr-2">
                <span className="text-base font-semibold">Anomaly Detection -- leave-one-out z-score</span>
                <span className="font-mono text-xs text-[var(--anomaly)] shrink-0 ml-3">z=20.90 real</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-1">
                <Lead className="text-base md:text-lg">
                  Every value gets compared to everything else like it -- and it isn't allowed to grade its own test.
                </Lead>

                <Bullets
                  items={[
                    {
                      id: "why-not-threshold",
                      text: (
                        <>
                          A fixed dollar threshold only works at one order of magnitude. This project's real AWS bill
                          is <span className="font-mono text-xs">$0.0000046/day</span>; a production account could be
                          six orders of magnitude larger. One dollar cutoff can't serve both -- a z-score (standard
                          deviations from a group's own baseline) works identically at any scale.
                        </>
                      ),
                    },
                    {
                      id: "leave-one-out",
                      text: (
                        <>
                          <span className="font-mono text-xs">z = (x - mean) / stddev</span>, where the mean/stddev
                          are computed from every <em>other</em> row in the same group (same day, same warehouse) --
                          the row being scored never contributes to its own baseline.
                        </>
                      ),
                    },
                    {
                      id: "honest-statuses",
                      text: (
                        <>
                          Groups too small to baseline against report{" "}
                          <span className="font-mono text-xs">insufficient_baseline</span> explicitly rather than a
                          fabricated score -- real: 5 of the 167 real Snowflake queries hit this.
                        </>
                      ),
                    },
                  ]}
                />

                <Callout>
                  Why leave-one-out, not a naive in-group z-score: scoring a row against a baseline that{" "}
                  <em>includes</em> itself lets a genuine outlier drag the mean/stddev toward it, muting the very
                  signal being measured. Excluding the row from its own baseline is what actually lets a real spike
                  register a high score instead of being partially absorbed by it.
                </Callout>

                <Example title="Real worked example">
                  <div className="space-y-3">
                    <p>
                      An unfiltered <span className="font-mono text-xs">CUSTOMER JOIN ORDERS ... LIMIT 20</span>{" "}
                      query ran 11,899ms against a same-day baseline of 47 other real queries (mean 260.6ms, stddev
                      557.0ms) on <span className="font-mono text-xs">SPEND_LENS_WH</span>.
                    </p>
                    <TracePath
                      nodes={[
                        { label: "snowflake", sublabel: "ACCOUNT_USAGE", color: "var(--source-snowflake)" },
                        { label: "SPEND_LENS_WH", sublabel: "warehouse", color: "var(--source-snowflake)" },
                        { label: "CUSTOMER JOIN ORDERS...", sublabel: "SELECT", color: "var(--source-snowflake)" },
                        { label: "11,899ms", sublabel: "duration", color: "var(--anomaly)" },
                      ]}
                    />
                  </div>
                </Example>

                <ZScoreExplorer />

                <p className="text-xs text-muted-foreground">
                  Full formula derivation and decision record:{" "}
                  <Link to="/references" className="underline underline-offset-2 hover:text-signal">
                    References & Formulas
                  </Link>
                  <FootnoteMarker label="anomaly decision">
                    See <span className="font-mono">docs/decisions/0003</span> ("Anomaly detection: leave-one-out
                    z-score, not a hardcoded dollar amount") for the full real-data verification table, including
                    the two genuine outliers and every honest negative result (AWS's flat cost, Databricks'
                    single-row baseline).
                  </FootnoteMarker>
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Card 2 -- Forecast */}
          <AccordionItem value="forecast">
            <AccordionTrigger>
              <div className="flex items-center justify-between w-full pr-2">
                <span className="text-base font-semibold">Month-End Forecast -- run-rate + trend, reconciled with AWS</span>
                <span className="font-mono text-xs text-signal shrink-0 ml-3">$0.000144 projected</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-1">
                <Lead className="text-base md:text-lg">
                  Two independent ways to guess the month's final bill from a partial month of data -- computed the
                  same way for every source, since only AWS has its own built-in forecast.
                </Lead>

                <Bullets
                  items={[
                    {
                      id: "run-rate",
                      text: (
                        <>
                          <span className="text-foreground font-medium">Run-rate</span> -- assume spending stays flat
                          at its average-so-far and extend that average to the end of the month.{" "}
                          <span className="font-mono text-xs">(total_so_far / days_observed) * days_in_month</span>.
                        </>
                      ),
                    },
                    {
                      id: "trend",
                      text: (
                        <>
                          <span className="text-foreground font-medium">Trend</span> -- fit a line
                          (<span className="font-mono text-xs">regr_slope</span>/
                          <span className="font-mono text-xs">regr_intercept</span>) to the actual day-to-day
                          trajectory and extend that line instead -- catches growth or decline a flat average would
                          miss.
                        </>
                      ),
                    },
                    {
                      id: "why-reconciled",
                      text: (
                        <>
                          Computed independently for every source, not just AWS -- Snowflake and Databricks have no
                          native forecast API at all, so a source-specific approach would leave two of three sources
                          with no forecast whatsoever. AWS's own real forecast is surfaced alongside for comparison,
                          never overridden.
                        </>
                      ),
                    },
                  ]}
                />

                <Callout>
                  Not a true apples-to-apples comparison: AWS's own native forecast (<span className="font-mono text-xs">$0.0000511</span>)
                  covers only 2026-08-13 → 2026-09-01, while our whole-month run-rate (<span className="font-mono text-xs">$0.0001440</span>)
                  projects all of August from partial data. Different period windows -- surfaced side by side anyway,
                  because at sub-cent amounts the gap isn't meaningful either way, but reading it as a disagreement
                  between methods would be the wrong takeaway.
                </Callout>

                <Example title="Real numbers, side by side">
                  <div className="flex flex-wrap items-center gap-6">
                    <StatHighlight value={0.0001439888} label="our whole-month projection" color="var(--signal)" size="sm" countUp={false} format={(n) => `$${n.toFixed(7)}`} />
                    <StatHighlight value={0.0000510928} label="AWS's own native forecast" color="var(--source-aws)" size="sm" countUp={false} format={(n) => `$${n.toFixed(7)}`} />
                  </div>
                </Example>

                <ForecastMethodCompare />

                <p className="text-xs text-muted-foreground">
                  Full formula derivation and decision record:{" "}
                  <Link to="/references" className="underline underline-offset-2 hover:text-signal">
                    References & Formulas
                  </Link>
                  <FootnoteMarker label="forecast decision">
                    See <span className="font-mono">docs/decisions/0003</span> ("Forecast: independent, uniform
                    run-rate + trend, reconciled") for the full real derivation, including why Snowflake gets a real
                    non-dollar credits run-rate instead of a fabricated $0.
                  </FootnoteMarker>
                </p>
              </div>
            </AccordionContent>
          </AccordionItem>

          {/* Card 3 -- Optimization Rules */}
          <AccordionItem value="rules">
            <AccordionTrigger>
              <div className="flex items-center justify-between w-full pr-2">
                <span className="text-base font-semibold">Optimization Rules -- 4 checks against real ingested metadata</span>
                <span className="font-mono text-xs text-[var(--savings)] shrink-0 ml-3">8 real suggestions</span>
              </div>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-4 pt-1">
                <Lead className="text-base md:text-lg">
                  Four specific checks against fields the collectors actually land -- not generic "reduce your cloud
                  bill" advice.
                </Lead>

                <Callout>
                  The roadmap's own headline example ("this Databricks job re-scans the full table; partitioning
                  would cut cost by X%") could not be built as literally specified -- the Databricks Jobs API carries
                  no query/table/scan metadata at all on this trial tier, only cluster/runtime data. Named here
                  directly so it's clear why that exact rule isn't below, not silently dropped.
                </Callout>

                <Tabs defaultValue="repeated">
                  {/* Real labels here ("Repeated Query"/"Unfiltered Scan"/etc.) run
                      longer than Results.tsx's own Tabs usage -- clip at a 375px
                      viewport without this. Same fix TracePath already uses
                      (decision 0006): horizontal scroll, not compression. */}
                  <div className="overflow-x-auto -mx-1 px-1">
                    <TabsList className="w-max">
                      <TabsTrigger value="repeated">Repeated Query</TabsTrigger>
                      <TabsTrigger value="unfiltered">Unfiltered Scan</TabsTrigger>
                      <TabsTrigger value="idle">Idle Resource</TabsTrigger>
                      <TabsTrigger value="gap">Databricks Gap</TabsTrigger>
                    </TabsList>
                  </div>

                  <TabsContent value="repeated" className="space-y-3 mt-4">
                    <p className="text-sm text-foreground/90">
                      Fires when the exact same query text runs more than once on the same warehouse -- a
                      caching/materialization gap, not a rule of thumb.
                    </p>
                    <Example title="Real evidence">
                      <span className="font-mono text-xs whitespace-pre-line">
                        {`SELECT O_ORDERSTATUS, COUNT(*), AVG(O_TOTALPRICE)\nFROM SNOWFLAKE_SAMPLE_DATA.TPCH_SF1.ORDERS GROUP BY O_ORDERSTATUS;`}
                      </span>
                      <p className="mt-2">ran 7 times on SPEND_LENS_WH, 2,527ms total warehouse time.</p>
                    </Example>
                    <StatHighlight value={86} label="% of runtime flagged redundant" color="var(--savings)" size="sm" countUp={false} format={(n) => `${n.toFixed(0)}%`} />
                  </TabsContent>

                  <TabsContent value="unfiltered" className="space-y-3 mt-4">
                    <p className="text-sm text-foreground/90">
                      Fires when a query has no <span className="font-mono text-xs">WHERE</span> clause against a
                      known table -- 5 real matches in this project's Snowflake history.
                    </p>
                    <Callout>
                      Not quantified, on purpose: <span className="font-mono text-xs">bytes_scanned</span> alone
                      can't derive a real savings % without the table's row/partition distribution -- stating one
                      would be a guess, not a computed number.
                    </Callout>
                  </TabsContent>

                  <TabsContent value="idle" className="space-y-3 mt-4">
                    <p className="text-sm text-foreground/90">
                      Fires when a resource's daily cost is flat (zero variance) across 14+ consecutive days -- the
                      signature of an always-on, unlifecycled resource rather than active, variable usage.
                    </p>
                    <Example title="Real evidence">
                      Amazon S3 cost flat at $0.00000464/day across 14 real observed days, $0.000065 accumulated.
                    </Example>
                    <StatHighlight value={100} label="% conditionally avoidable, if unneeded" color="var(--savings)" size="sm" countUp={false} format={(n) => `up to ${n.toFixed(0)}%`} />
                  </TabsContent>

                  <TabsContent value="gap" className="space-y-3 mt-4">
                    <p className="text-sm text-foreground/90">
                      Fires when a Databricks run lands with <span className="font-mono text-xs">cost_usd=None</span>{" "}
                      -- a visibility gap, not a dollar figure to quantify.
                    </p>
                    <Example title="Real evidence">
                      Job 101154624149862, run 1043255749606564, completed (SUCCESS) in 31s with no resolvable node
                      type -- serverless compute exposes no instance type to price against.
                    </Example>
                    <Callout>
                      Not quantified: this is a real cost-attribution blind spot, not a number this pipeline can ever
                      derive from the Jobs API alone on this trial tier.
                    </Callout>
                  </TabsContent>
                </Tabs>
              </div>
            </AccordionContent>
          </AccordionItem>
        </Accordion>

        <Card>
          <CardContent className="flex items-center justify-between flex-wrap gap-3">
            <p className="text-sm text-muted-foreground">
              New project-specific terms used above are defined in full in the Glossary.
            </p>
            <Link to="/glossary" className="text-sm font-mono text-signal underline underline-offset-2 hover:text-signal/80">
              Open Glossary →
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
