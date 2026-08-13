import { useMemo } from "react"
import { Link } from "react-router-dom"
import { ArrowRight, RotateCcw } from "lucide-react"
import { api } from "@/lib/api"
import { useFetch } from "@/lib/use-fetch"
import { useFilters } from "@/lib/filter-context"
import { dedupeAttributionOptions } from "@/lib/dedupe-attribution-options"
import { PageHeader } from "@/components/layout/PageHeader"
import { Callout } from "@/components/primitives/Callout"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"

/**
 * Constrained inputs only (project-standards rule 2): every control here is
 * a dropdown or a date picker bounded by the real observed date range --
 * nothing free-text reaches the backend, and the API independently
 * re-validates source/date on every request (defense in depth, see
 * app/api/routes.py's own docstring).
 */
export function Inputs() {
  const { data, loading } = useFetch(() => api.filters(), [])
  const { filters, setSource, setDateRange, setAttributionKey, reset } = useFilters()

  const jobOptions = useMemo(() => {
    if (!data) return []
    const scoped = filters.source === "all" ? data.attribution_options : data.attribution_options.filter((o) => o.source === filters.source)
    return dedupeAttributionOptions(scoped)
  }, [data, filters.source])

  return (
    <div>
      <PageHeader
        eyebrow="02 / Inputs"
        title="Scope the dashboard"
        description="Every option below is read from the real ingested data (GET /api/filters) -- not a static list. Selections here carry through to Results."
      />

      {loading && <Skeleton className="h-72 w-full" />}

      {data && (
        <div className="grid md:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Source</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-xs font-mono text-muted-foreground">Cloud / warehouse source</Label>
                <Select value={filters.source} onValueChange={(v) => setSource(v as typeof filters.source)}>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="All sources" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All sources</SelectItem>
                    {data.sources.map((s) => (
                      <SelectItem key={s.value} value={s.value}>
                        <span className="inline-flex items-center gap-2">
                          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: s.color ?? undefined }} />
                          {s.label} ({s.count} real records)
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="text-xs font-mono text-muted-foreground">Job / query / attribution</Label>
                <Select
                  value={filters.attributionKey ?? "any"}
                  onValueChange={(v) => setAttributionKey(v === "any" ? null : v)}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Any" />
                  </SelectTrigger>
                  <SelectContent className="max-w-[420px]">
                    <SelectItem value="any">Any</SelectItem>
                    {jobOptions.slice(0, 200).map((o) => (
                      <SelectItem key={`${o.source}-${o.attribution_key}`} value={o.attribution_key}>
                        <span className="truncate">
                          [{o.attribution_kind}] {o.label}
                        </span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {filters.source === "databricks" && (
                  <Callout>
                    Databricks has exactly one real job run landed so far -- this list is thin because the real data
                    is thin, not because of a loading issue.
                  </Callout>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Date range</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-xs text-muted-foreground font-mono">
                real ingested window: {data.date_range.min} → {data.date_range.max}
              </p>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-muted-foreground">Start</Label>
                  <input
                    type="date"
                    className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    min={data.date_range.min ?? undefined}
                    max={data.date_range.max ?? undefined}
                    value={filters.start ?? ""}
                    onChange={(e) => setDateRange(e.target.value || null, filters.end)}
                  />
                </div>
                <div className="space-y-2">
                  <Label className="text-xs font-mono text-muted-foreground">End</Label>
                  <input
                    type="date"
                    className="w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    min={data.date_range.min ?? undefined}
                    max={data.date_range.max ?? undefined}
                    value={filters.end ?? ""}
                    onChange={(e) => setDateRange(filters.start, e.target.value || null)}
                  />
                </div>
              </div>

              <Callout tone="info">{data.source_note}</Callout>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="mt-6 flex items-center gap-3">
        <Button asChild className="bg-signal text-black hover:bg-signal/90 active:scale-[0.98] transition-transform">
          <Link to="/results">
            View results <ArrowRight className="ml-1.5 h-4 w-4" />
          </Link>
        </Button>
        <Button variant="ghost" onClick={reset} className="text-muted-foreground">
          <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Reset filters
        </Button>
      </div>
    </div>
  )
}
