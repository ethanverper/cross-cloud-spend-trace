import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent } from "@/components/ui/card"
import { Lead } from "@/components/primitives/Lead"
import { Bullets } from "@/components/primitives/Bullets"
import { Callout } from "@/components/primitives/Callout"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { Example } from "@/components/primitives/Example"
import { FootnoteMarker } from "@/components/primitives/FootnoteMarker"

/**
 * Real World / Corporate Applications (project-standards rule 10) --
 * content and decomposition plan owned by brand-creative per decision
 * 0005 section 7 (Phase 4). Implemented here verbatim against that plan,
 * not improvised.
 */
export function RealWorld() {
  return (
    <div>
      <PageHeader eyebrow="05 / Real World" title="Real World & Corporate Applications" />

      <Card>
        <CardContent className="space-y-6">
          <Lead>
            FinOps for data infrastructure is now a named discipline with dedicated tooling, not a spreadsheet
            exercise.
          </Lead>

          <Bullets
            items={[
              {
                id: "platform-team",
                text: "A platform team catches a runaway Databricks job before month-end close, instead of finding it on the invoice three weeks later.",
              },
              {
                id: "data-eng-manager",
                text: "A data-engineering manager explaining a bill spike to finance cites the exact query and its z-score, not a shrug and a promise to look into it.",
              },
              {
                id: "sre-budget",
                text: "An SRE team sets a budget alert against a forecasted month-end number, computed from partial-month data, instead of reacting only after the actual invoice lands.",
              },
              {
                id: "onboarding",
                text: "A new data engineer traces an unfamiliar warehouse's cost history back to specific queries in minutes, instead of reverse-engineering it from raw billing exports.",
              },
            ]}
          />

          <Callout>
            This class of tool augments, but does not replace, a dedicated FinOps practice or team at real
            organizational scale -- it's a tracing and reporting layer, not a substitute for the governance,
            chargeback policy, and cross-team negotiation a mature FinOps function actually does.
          </Callout>

          <div className="flex items-center gap-2">
            <StatHighlight value="29%" label="of cloud spend is estimated waste" color="var(--signal)" size="md" countUp={false} />
            <FootnoteMarker label="citation">
              Flexera's 2026 State of the Cloud Report found estimated wasted cloud spend rose to 29% in 2026,
              reversing a five-year downward trend, attributed to the complexity AI workloads and new PaaS/SaaS
              offerings add to cost attribution.{" "}
              <a
                href="https://www.flexera.com/blog/finops/flexera-2026-state-of-the-cloud-report-the-convergence-of-cloud-and-value/"
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-2 hover:text-signal"
              >
                Flexera, 2026 State of the Cloud Report
              </a>
              .
            </FootnoteMarker>
          </div>

          <Example title="Worked case -- this project's own real optimization finding">
            A query on <span className="font-mono text-xs">SPEND_LENS_WH</span> ran 7 identical times, 2,527ms of
            total warehouse time, with no caching or materialization catching the repetition -- cross-cloud-spend-trace's
            own rules engine flagged 86% of that runtime as redundant re-execution, grounded in the real ingested
            query history, not a generic "consider caching" tip. This is the same shape of finding a platform team
            would want surfaced automatically, at real production scale, before it compounds across thousands of
            query runs a day.
          </Example>
        </CardContent>
      </Card>
    </div>
  )
}
