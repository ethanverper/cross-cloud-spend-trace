import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { SpendBySourceDateRow } from "@/lib/api"
import { sourceColor, sourceLabel } from "@/components/primitives/SourceBadge"
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion"

/** Stacked-bar-by-source chart form (decision 0005's Datadog research
 * citation: "the stacked-bar-by-source chart form as the primary 'where
 * did the money go' visual"). Charted on **record count**, not dollars --
 * Snowflake and Databricks genuinely have no cost_usd data yet (decision
 * 0002/0003), so a dollar-only chart would silently zero them out. Record
 * volume is the one metric every source actually has, so this is the
 * honest "activity by source" view; AWS's real dollar figures get their
 * own chart (ForecastChart) where they're not competing with sources that
 * have none. */
export function ActivityBySourceChart({ rows, height = 260 }: { rows: SpendBySourceDateRow[]; height?: number }) {
  const reduced = usePrefersReducedMotion()

  const data = useMemo(() => {
    const byDate = new Map<string, Record<string, number | string>>()
    for (const r of rows) {
      const entry = byDate.get(r.usage_date) ?? { usage_date: r.usage_date, aws: 0, snowflake: 0, databricks: 0 }
      entry[r.source] = (entry[r.source] as number) + r.record_count
      byDate.set(r.usage_date, entry)
    }
    return [...byDate.values()].sort((a, b) => String(a.usage_date).localeCompare(String(b.usage_date)))
  }, [rows])

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="usage_date"
          tick={{ fontSize: 10, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis tick={{ fontSize: 11, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }} tickLine={false} axisLine={false} width={32} allowDecimals={false} />
        <Tooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 12 }}
          labelFormatter={(d) => `date ${d}`}
        />
        <Legend
          formatter={(value: string) => <span style={{ color: "var(--muted-foreground)", fontFamily: "var(--font-mono)", fontSize: 12 }}>{sourceLabel(value as "aws" | "snowflake" | "databricks")}</span>}
        />
        <Bar dataKey="aws" stackId="records" fill={sourceColor("aws")} isAnimationActive={!reduced} radius={[0, 0, 0, 0]} />
        <Bar dataKey="snowflake" stackId="records" fill={sourceColor("snowflake")} isAnimationActive={!reduced} />
        <Bar dataKey="databricks" stackId="records" fill={sourceColor("databricks")} isAnimationActive={!reduced} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}
