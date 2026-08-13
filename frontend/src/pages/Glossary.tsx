import { Link } from "react-router-dom"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Accordion } from "@/components/ui/accordion"
import { Lead } from "@/components/primitives/Lead"
import { FootnoteMarker } from "@/components/primitives/FootnoteMarker"
import { GlossaryEntry, type GlossaryTerm } from "@/components/learning/GlossaryEntry"

const STATS_TERMS: GlossaryTerm[] = [
  {
    id: "cost-attribution",
    term: "Cost attribution",
    plain: "Figuring out exactly which query, job, or resource a dollar of spend belongs to -- not just which cloud account it landed in.",
    technical: (
      <>
        Joining raw billing/usage records to a resource-level identifier (this project's{" "}
        <span className="font-mono text-xs">attribution_key</span>/<span className="font-mono text-xs">attribution_kind</span>{" "}
        fields) so spend can be grouped and ranked by cause, not just by source-level total.
      </>
    ),
    whereItShowsUp: (
      <>
        <span className="font-mono text-xs">unified_model.py</span>'s unified event view; the{" "}
        <Link to="/results" className="underline underline-offset-2 hover:text-signal">
          Results
        </Link>{" "}
        page's "Top spend by service / query / job / warehouse" ranking.
      </>
    ),
  },
  {
    id: "leave-one-out-zscore",
    term: "Leave-one-out z-score",
    plain: "How many standard deviations a value is from a baseline that was computed without that value's own influence on it.",
    technical: (
      <>
        <span className="font-mono text-xs">z = (x - mean) / stddev</span>, where mean/stddev are computed from every
        other row in the same group, excluding the row being scored -- prevents a genuine outlier from dragging its
        own baseline toward it and muting the signal.
      </>
    ),
    whereItShowsUp: (
      <>
        The real 20.90-z Snowflake anomaly, walked through in full on{" "}
        <Link to="/learning" className="underline underline-offset-2 hover:text-signal">
          Learning
        </Link>
        .
      </>
    ),
  },
  {
    id: "anomaly-threshold",
    term: "Anomaly threshold (z_threshold)",
    plain: "How extreme a value needs to be before it counts as a real anomaly, not just ordinary variation.",
    technical: (
      <>
        The <span className="font-mono text-xs">|z| ≥ 3.0</span> cutoff above which{" "}
        <span className="font-mono text-xs">anomaly.detect_anomalies()</span> sets{" "}
        <span className="font-mono text-xs">anomaly=True</span> -- a standard "3-sigma" convention balancing false
        positives against missing genuine spikes.
      </>
    ),
    whereItShowsUp: "The badges on every anomaly card in Results → Anomalies.",
  },
  {
    id: "run-rate-forecast",
    term: "Run-rate forecast",
    plain: "Assume spending stays flat at its average-so-far, and stretch that average out to the end of the month.",
    technical: (
      <>
        <span className="font-mono text-xs">(total_so_far / days_observed) * days_in_month</span> -- the simplest of
        the two forecast methods this project computes, real for AWS at{" "}
        <span className="font-mono text-xs">$0.0001439888</span> projected from 11 real observed days.
      </>
    ),
    whereItShowsUp: (
      <>
        <Link to="/results" className="underline underline-offset-2 hover:text-signal">
          Results → Forecast
        </Link>
        , and the interactive compare on{" "}
        <Link to="/learning" className="underline underline-offset-2 hover:text-signal">
          Learning
        </Link>
        .
      </>
    ),
  },
  {
    id: "trend-forecast",
    term: "Trend forecast (regr_slope / regr_intercept)",
    plain: "Fit a line to the actual day-to-day trajectory of spend, and extend that line forward instead of just averaging.",
    technical: (
      <>
        Spark SQL's <span className="font-mono text-xs">regr_slope</span>/<span className="font-mono text-xs">regr_intercept</span>{" "}
        aggregate functions fit an OLS line to cumulative cost vs. day-of-month; catches growth or decline a flat
        run-rate average would miss.
      </>
    ),
    whereItShowsUp: "Results → Forecast (dashed projection line); Learning's forecast card.",
  },
  {
    id: "native-unit-forecast",
    term: "Native-unit forecast",
    plain: "A forecast in whatever unit a source actually has -- like Snowflake credits -- instead of a dollar figure, for sources with no cost data.",
    technical: (
      <>
        <span className="font-mono text-xs">native_unit_forecast()</span> run-rate-projects a source's real
        non-dollar <span className="font-mono text-xs">usage_unit</span> rather than fabricating a $0 -- real
        Snowflake credit burn (0.222666 credits observed) projects to ~6.9 credits/month.
      </>
    ),
    whereItShowsUp: "Results → Forecast, Snowflake card.",
  },
  {
    id: "optimization-suggestion",
    term: "Optimization suggestion / rules engine",
    plain: "A specific, evidence-backed recommendation grounded in fields this project's collectors actually landed -- not generic cost-savings advice.",
    technical: (
      <>
        4 rules in <span className="font-mono text-xs">rules.py</span>, each reading real{" "}
        <span className="font-mono text-xs">raw_metadata</span> fields; every rule that fires includes its exact
        evidence string and, where derivable, a quantified estimated impact.
      </>
    ),
    whereItShowsUp: (
      <>
        <Link to="/results" className="underline underline-offset-2 hover:text-signal">
          Results → Optimizations
        </Link>{" "}
        (8 real rows) and Learning's rules card.
      </>
    ),
  },
]

const PLATFORM_TERMS: GlossaryTerm[] = [
  {
    id: "aws-cost-explorer",
    term: "AWS Cost Explorer",
    plain: "AWS's own built-in tool and API for querying historical cost/usage and getting a native month-end forecast.",
    technical: (
      <>
        <span className="font-mono text-xs">ce:GetCostAndUsage</span>,{" "}
        <span className="font-mono text-xs">ce:GetCostForecast</span>,{" "}
        <span className="font-mono text-xs">ce:GetDimensionValues</span> -- the exact three read-only Cost Explorer
        actions this project's IAM policy is scoped to, nothing broader.
      </>
    ),
    whereItShowsUp: "29 real daily cost-and-usage records + 1 real forecast record, ingested by collectors/aws.",
  },
  {
    id: "snowflake-account-usage",
    term: "Snowflake ACCOUNT_USAGE",
    plain: "A set of built-in system views Snowflake exposes showing exactly what every warehouse and query actually did and cost, in credits.",
    technical: (
      <>
        <span className="font-mono text-xs">QUERY_HISTORY</span> and{" "}
        <span className="font-mono text-xs">WAREHOUSE_METERING_HISTORY</span> views under the shared{" "}
        <span className="font-mono text-xs">SNOWFLAKE</span> database, reachable via{" "}
        <span className="font-mono text-xs">IMPORTED PRIVILEGES</span> (not per-schema grants -- imported/shared
        databases reject those).
      </>
    ),
    whereItShowsUp: "167 real QUERY_HISTORY rows, 4 real WAREHOUSE_METERING_HISTORY rows, ingested by collectors/snowflake.",
  },
  {
    id: "snowflake-warehouse",
    term: "Snowflake virtual warehouse",
    plain: "The actual compute engine that runs a Snowflake query and burns credits while it's running.",
    technical: (
      <>
        An independently sizeable and suspendable compute cluster --{" "}
        <span className="font-mono text-xs">SPEND_LENS_WH</span> (X-Small, 60s auto-suspend) is this project's own
        real dedicated warehouse.
      </>
    ),
    whereItShowsUp: "Every source→warehouse→query TracePath breadcrumb in Results and Learning.",
  },
  {
    id: "databricks-jobs-api",
    term: "Databricks Jobs API",
    plain: "The surface this project reads Databricks activity from, since no billing API is available on this trial workspace's tier.",
    technical: (
      <>
        <span className="font-mono text-xs">jobs/runs/list</span> +{" "}
        <span className="font-mono text-xs">jobs/runs/get</span> +{" "}
        <span className="font-mono text-xs">clusters/get</span>/<span className="font-mono text-xs">events</span> --
        carries no query/table-scan metadata at all, only cluster/runtime data (job id, duration, node type if
        provisioned).
      </>
    ),
    whereItShowsUp: "The 1 real job run this project has ingested (job_id=101154624149862).",
  },
  {
    id: "dbfs",
    term: "DBFS (Databricks File System)",
    plain: "A place to upload files into a Databricks workspace so cloud compute there can actually read them.",
    technical: (
      <>
        The REST upload surface (<span className="font-mono text-xs">create</span>/
        <span className="font-mono text-xs">add-block</span>/<span className="font-mono text-xs">close</span>)
        <span className="font-mono text-xs"> databricks_sync.py</span> targets -- currently blocked by a real,
        diagnosed <span className="font-mono text-xs">403</span> token-scope gap (this project's token is scoped to
        exactly <span className="font-mono text-xs">jobs</span>+<span className="font-mono text-xs">clusters</span>,
        no <span className="font-mono text-xs">files</span> scope).
      </>
    ),
    whereItShowsUp: (
      <>
        <FootnoteMarker label="decision reference">
          Full diagnosis in <span className="font-mono">docs/decisions/0003</span>, section 5.
        </FootnoteMarker>{" "}
        -- not yet reachable from this app's UI directly.
      </>
    ),
  },
  {
    id: "finops",
    term: "FinOps",
    plain: "The discipline of a company actually knowing and controlling what its cloud/data spend is going toward, instead of just paying whatever the invoice says.",
    technical:
      "A named, cross-functional practice (engineering + finance) for real-time cost visibility, attribution, forecasting, and optimization of cloud spend at scale -- the discipline this whole project is a small, real instance of.",
    whereItShowsUp: (
      <>
        <Link to="/real-world" className="underline underline-offset-2 hover:text-signal">
          Real World & Corporate Applications
        </Link>{" "}
        (real cited 2026 Flexera stat: 29% estimated cloud waste).
      </>
    ),
  },
]

/**
 * Glossary (project-standards rule 5 / rule 15) -- every project-specific
 * term this dashboard uses, in both registers. Content and decomposition
 * plan owned by `educator` per decision 0007, implemented here verbatim.
 */
export function Glossary() {
  return (
    <div>
      <PageHeader
        eyebrow="09 / Glossary"
        title="Every term this dashboard uses, defined"
        description="Plain language and technical, cross-referenced to where each one is actually computed -- not a generic dictionary."
      />

      <div className="space-y-6">
        <Lead>
          These are the terms genuinely load-bearing in this project's own real pipeline -- finance-specific terms
          (alpha, beta, Sharpe ratio, etc.) live in Cowork OS's portfolio-wide glossary instead, since they belong to
          a different project.
        </Lead>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-mono">Statistics & Forecasting Methods</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible>
              {STATS_TERMS.map((entry) => (
                <GlossaryEntry key={entry.id} entry={entry} />
              ))}
            </Accordion>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base font-mono">Cloud / Data Platform Concepts</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="single" collapsible>
              {PLATFORM_TERMS.map((entry) => (
                <GlossaryEntry key={entry.id} entry={entry} />
              ))}
            </Accordion>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
