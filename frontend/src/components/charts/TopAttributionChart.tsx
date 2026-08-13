import { useMemo } from "react"
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import type { SpendByAttributionRow } from "@/lib/api"
import { sourceColor } from "@/components/primitives/SourceBadge"
import { formatNumber, formatUsd } from "@/lib/format"
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion"

/** Ranks attribution rows (service / query / job / warehouse -- "spend by
 * ... query/job/model" per the roadmap's Phase 5 requirement) by whichever
 * metric this source actually has: real dollars where they exist (AWS),
 * real native usage quantity otherwise (Snowflake ms/credits, Databricks
 * cluster-hours) -- never a fabricated dollar figure for a source that
 * doesn't have one (decision 0002/0003). */
export function TopAttributionChart({ rows, limit = 8, height = 280 }: { rows: SpendByAttributionRow[]; limit?: number; height?: number }) {
  const reduced = usePrefersReducedMotion()

  const { data, usesCost, unit } = useMemo(() => {
    const totals = new Map<string, { key: string; source: string; cost: number; qty: number; unit: string }>()
    for (const r of rows) {
      const k = `${r.source}::${r.attribution_key}`
      const existing = totals.get(k) ?? { key: r.attribution_key, source: r.source, cost: 0, qty: 0, unit: r.usage_unit ?? "" }
      existing.cost += r.cost_usd_total ?? 0
      existing.qty += r.usage_quantity_total ?? 0
      if (r.usage_unit) existing.unit = r.usage_unit
      totals.set(k, existing)
    }
    const list = [...totals.values()]
    const anyCost = list.some((r) => r.cost > 0)
    const metricKey = anyCost ? "cost" : "qty"
    const sorted = list.sort((a, b) => b[metricKey] - a[metricKey]).slice(0, limit)
    const commonUnit = anyCost ? "usd" : sorted[0]?.unit || ""
    return {
      data: sorted.map((r) => ({
        ...r,
        label: r.key.length > 22 ? r.key.slice(0, 22) + "…" : r.key,
        value: anyCost ? r.cost : r.qty,
      })),
      usesCost: anyCost,
      unit: commonUnit,
    }
  }, [rows, limit])

  if (data.length === 0) {
    return <div className="flex h-40 items-center justify-center text-sm text-muted-foreground">No attribution rows for this filter.</div>
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 24, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 10, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          tickFormatter={(v: number) => (usesCost ? formatUsd(v, { maxDecimals: 5 }) : formatNumber(v, 0))}
        />
        <YAxis
          type="category"
          dataKey="label"
          width={150}
          tick={{ fontSize: 11, fill: "var(--foreground)", fontFamily: "var(--font-mono)" }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 12 }}
          formatter={(value) => {
            const n = typeof value === "number" ? value : Number(value)
            return [usesCost ? formatUsd(n) : `${formatNumber(n)} ${unit}`, usesCost ? "cost" : unit]
          }}
          labelFormatter={(label) => String(label)}
        />
        <Bar dataKey="value" isAnimationActive={!reduced} radius={[0, 3, 3, 0]}>
          {data.map((row, i) => (
            <Cell key={i} fill={sourceColor(row.source as "aws" | "snowflake" | "databricks")} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
