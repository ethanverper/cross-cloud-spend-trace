import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TracePath, type TracePathNode } from "@/components/primitives/TracePath"
import type { SnowflakeAnomalyRow } from "@/lib/api"
import { formatZScore } from "@/lib/format"
import { cn } from "@/lib/utils"

export function AnomalyCard({ row, className }: { row: SnowflakeAnomalyRow; className?: string }) {
  const nodes: TracePathNode[] = [
    { label: "snowflake", sublabel: "ACCOUNT_USAGE", color: "var(--source-snowflake)" },
    { label: row.attribution_key, sublabel: "warehouse", color: "var(--source-snowflake)" },
    { label: row.resource_id.slice(0, 18) + "...", sublabel: row.query_type ?? "query", color: "var(--source-snowflake)" },
    { label: `${row.usage_quantity?.toFixed(0)} ms`, sublabel: "duration", color: row.anomaly ? "var(--anomaly)" : "var(--muted-foreground)" },
  ]

  return (
    <Card className={cn("border-border", row.anomaly && "border-[var(--anomaly)]/40 animate-anomaly-pulse-once", className)}>
      <CardContent className="pt-0 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="font-mono text-xs text-muted-foreground truncate">{row.query_text_preview}</p>
          </div>
          <Badge
            variant="outline"
            className={cn(
              "font-mono shrink-0",
              row.anomaly
                ? "border-[var(--anomaly)] text-[var(--anomaly)]"
                : row.status === "insufficient_baseline"
                  ? "border-muted-foreground/40 text-muted-foreground"
                  : "border-[var(--savings)]/50 text-[var(--savings)]",
            )}
          >
            {row.anomaly ? formatZScore(row.z_score) : row.status.replace("_", " ")}
          </Badge>
        </div>
        <TracePath nodes={nodes} />
        {row.status !== "insufficient_baseline" && row.baseline_mean !== null && (
          <p className="text-xs text-muted-foreground font-mono">
            baseline: {row.baseline_mean.toFixed(1)}ms mean / {row.baseline_stddev?.toFixed(1)}ms stddev over {row.group_n_other} other same-day queries
          </p>
        )}
      </CardContent>
    </Card>
  )
}
