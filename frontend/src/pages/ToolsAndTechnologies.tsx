import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Lead } from "@/components/primitives/Lead"

interface ToolEntry {
  name: string
  usage: string
}

interface ToolGroup {
  category: string
  entries: ToolEntry[]
}

// Content owned by brand-creative per decision 0005 section 7 ("must read
// like a hiring-manager checklist, not a tag cloud" -- project-standards
// rule 13). Implemented here verbatim against that plan.
const GROUPS: ToolGroup[] = [
  {
    category: "Languages",
    entries: [
      { name: "Python", usage: "Every collector, the analytics core, all test suites -- the one language spanning this entire monorepo." },
      { name: "TypeScript", usage: "The Phase 5 dashboard end to end, strict mode, no implicit any." },
    ],
  },
  {
    category: "Data / Analytics",
    entries: [
      { name: "PySpark", usage: "The unified spend model, leave-one-out z-score anomaly detection, regr_slope/regr_intercept trend forecast, and the 4-rule optimization engine -- the actual statistical/aggregation core, not a keyword." },
      { name: "Parquet", usage: "Partitioned raw store (data/raw/<source>/<table>/ingested_date=...), schema-enforced reads with an explicit StructType to avoid two real, live-discovered schema-inference bugs (decision 0003)." },
      { name: "pandas / pyarrow", usage: "Phase 5's API layer reads the same real Parquet output directly for serving, no re-run of PySpark per request (decision 0006)." },
    ],
  },
  {
    category: "Cloud / Infra",
    entries: [
      { name: "AWS Cost Explorer API + boto3", usage: "Real daily cost-and-usage ingestion, month-end forecast, service dimension values -- 29 real records live-verified against Ethan's own account." },
      { name: "Snowflake Connector + ACCOUNT_USAGE", usage: "Real query-history cost attribution across 167 real query rows, including the genuine z=20.90 anomaly." },
      { name: "Databricks Jobs API", usage: "Real job-run ingestion (1 real serverless job run), plus a DBFS sync utility built and live-tested against a real, diagnosed token-scope 403." },
      { name: "Docker", usage: "Three independently containerized collectors, one per source, each with its own Dockerfile from a shared uv workspace." },
      { name: "uv workspaces", usage: "Six-member monorepo (three collectors, common, analytics, and this Phase 5 API) sharing one lockfile." },
    ],
  },
  {
    category: "Frontend",
    entries: [
      { name: "React + Vite + TypeScript", usage: "The dashboard's actual runtime -- component-based, typed against the real API response shapes in app/api/schemas.py." },
      { name: "Tailwind CSS v4 + shadcn/ui", usage: "The full component system (Tabs, Card, Select, Popover, Sheet) -- no hand-rolled CSS for structural UI." },
      { name: "Recharts", usage: "Every chart (activity-by-source, top-attribution, month-end forecast) -- real interactive charting, not hand-drawn SVG." },
      { name: "GSAP", usage: "The TracePath connector-draw animation and the wordmark's trace-underline -- the identity's one place of real, non-trivial motion implementation (decision 0005)." },
      { name: "FastAPI", usage: "The pure JSON API (app/) serving Phase 3's real computed output, and the built frontend's static assets in production." },
    ],
  },
]

export function ToolsAndTechnologies() {
  return (
    <div>
      <PageHeader eyebrow="06 / Tools & Technologies" title="What this was actually built with" />
      <Lead className="mb-6">
        Grouped by category, with one line per entry tying it to how it was actually used in this project -- not a
        tag cloud.
      </Lead>

      <div className="grid md:grid-cols-2 gap-5">
        {GROUPS.map((group) => (
          <Card key={group.category}>
            <CardHeader>
              <CardTitle className="text-base font-mono">{group.category}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {group.entries.map((entry) => (
                <div key={entry.name}>
                  <div className="text-sm font-semibold text-foreground">{entry.name}</div>
                  <div className="text-xs text-muted-foreground leading-relaxed mt-0.5">{entry.usage}</div>
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
