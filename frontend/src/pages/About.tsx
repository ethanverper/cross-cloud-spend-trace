import { api } from "@/lib/api"
import { useFetch } from "@/lib/use-fetch"
import { PageHeader } from "@/components/layout/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Lead } from "@/components/primitives/Lead"
import { Bullets } from "@/components/primitives/Bullets"
import { Button } from "@/components/ui/button"
// lucide-react has no brand "Github" icon in this version -- use a generic
// external-link glyph instead, still real and meaningful here.
import { ExternalLink } from "lucide-react"

/** Secondary builder-credit placement (project-standards rule 9b, decision
 * 0005 section 8): the fuller real story, attributed to Ethan directly. */
export function About() {
  const { data, loading } = useFetch(() => api.meta(), [])

  return (
    <div>
      <PageHeader eyebrow="10 / About & Credits" title="About this project" />

      <div className="grid md:grid-cols-3 gap-6">
        <Card className="md:col-span-2">
          <CardContent className="space-y-4">
            <Lead>
              cross-cloud-spend-trace traces AWS, Snowflake, and Databricks spend back to the exact source that
              caused it, built end to end against real, live cloud accounts -- not synthetic data.
            </Lead>
            <Bullets
              items={[
                { id: "collectors", text: "Three independently Dockerized collectors, one per source, sharing a normalized schema via a uv workspace." },
                { id: "accounts", text: "Real AWS, Snowflake, and Databricks trial accounts, created and operated directly by Ethan -- no agent ever touched signup, payment, or login." },
                { id: "pipeline", text: "A real PySpark analytics core: unified spend model, leave-one-out z-score anomaly detection, run-rate/trend forecast, and a 4-rule optimization engine." },
                { id: "honesty", text: "Every documented gap (Databricks' cost-visibility blind spot, AWS's flat-cost non-anomaly, Snowflake's credits-only cost model) is disclosed as a real structural finding, not smoothed over." },
              ]}
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Builder</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loading && <Skeleton className="h-24 w-full" />}
            {data && (
              <>
                <p className="font-mono text-sm text-foreground">{data.builder_name}</p>
                <Button asChild variant="outline" size="sm" className="w-full justify-start">
                  <a href={data.builder_links.github} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-3.5 w-3.5 mr-2" /> GitHub profile
                  </a>
                </Button>
                <Button asChild variant="outline" size="sm" className="w-full justify-start">
                  <a href={data.repo_url} target="_blank" rel="noreferrer">
                    <ExternalLink className="h-3.5 w-3.5 mr-2" /> Project source
                  </a>
                </Button>
                <p className="text-xs text-muted-foreground font-mono pt-2 border-t border-border">
                  pipeline run_date={data.run_date}
                  <br />
                  meta generated {new Date(data.generated_at).toLocaleString()}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Dataset provenance</CardTitle>
        </CardHeader>
        <CardContent>
          {loading && <Skeleton className="h-40 w-full" />}
          <div className="space-y-3">
            {data?.provenance.map((p) => (
              <div key={p.table} className="flex flex-col sm:flex-row sm:items-baseline gap-1 sm:gap-4 text-sm border-b border-border/60 pb-3 last:border-0">
                <span className="font-mono text-xs text-signal shrink-0 w-48">{p.table}</span>
                <span className="text-muted-foreground text-xs leading-relaxed flex-1">{p.description}</span>
                <span className="font-mono text-xs text-foreground shrink-0">{p.real_record_count} rows</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
