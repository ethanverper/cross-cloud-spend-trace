import type { SourceId } from "@/lib/api"
import { cn } from "@/lib/utils"

const LABELS: Record<SourceId, string> = { aws: "AWS", snowflake: "Snowflake", databricks: "Databricks" }
const COLORS: Record<SourceId, string> = {
  aws: "var(--source-aws)",
  snowflake: "var(--source-snowflake)",
  databricks: "var(--source-databricks)",
}

/** The colored-dot-plus-label pattern for source coding, per decision 0005's
 * Vantage research citation -- reused everywhere a chart, chip, table cell,
 * or TracePath node needs to say "this came from X." */
export function SourceBadge({ source, className }: { source: SourceId; className?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 font-mono text-xs", className)}>
      <span className="h-2 w-2 rounded-full shrink-0" style={{ backgroundColor: COLORS[source] }} aria-hidden />
      {LABELS[source]}
    </span>
  )
}

export function sourceColor(source: SourceId): string {
  return COLORS[source]
}

export function sourceLabel(source: SourceId): string {
  return LABELS[source]
}
