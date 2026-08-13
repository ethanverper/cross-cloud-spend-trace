import { useMemo, useState } from "react"
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Button } from "@/components/ui/button"
import { StatHighlight } from "@/components/primitives/StatHighlight"
import { formatUsd } from "@/lib/format"
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion"

type Scenario = "real" | "constructed"

// Real AWS series (decision 0007, re-verified against
// data/processed/forecast_by_source/run_date=2026-08-12): flat
// $0.0000046448/day, 11 real observed days, run-rate and trend land on the
// literal same $0.0001439888 -- a genuine consequence of zero-variance
// real data, not a placeholder.
const REAL = {
  daysObserved: 11,
  daysInMonth: 31,
  runRatePerDay: 0.0000046448,
  trendSlopePerDay: 0.0000046448,
  trendIntercept: 0,
  runRateProjection: 0.0001439888,
  trendProjection: 0.0001439888,
}

// Explicitly-constructed growth example -- NOT real account data. Mirrors
// decision 0003's own precedent (test_trend_diverges_from_run_rate_on_
// constructed_growth) for demonstrating this divergence, since the real
// AWS series has no variance to show it with. Daily cost $10 -> $28 over
// 10 days; run-rate/trend slope+intercept computed with the exact same OLS
// method analytics/ uses (np.polyfit == regr_slope/regr_intercept),
// re-verified numerically for this doc.
const CONSTRUCTED = {
  daysObserved: 10,
  daysInMonth: 31,
  dailyCost: [10, 12, 14, 16, 18, 20, 22, 24, 26, 28],
  runRatePerDay: 19,
  trendSlopePerDay: 20,
  trendIntercept: -22,
  runRateProjection: 589,
  trendProjection: 598,
}

function buildSeries(scenario: Scenario) {
  const cfg = scenario === "real" ? REAL : CONSTRUCTED
  const observedCumulative: number[] =
    scenario === "real"
      ? Array.from({ length: REAL.daysObserved }, (_, i) => (i + 1) * REAL.runRatePerDay)
      : (() => {
          let running = 0
          return CONSTRUCTED.dailyCost.map((d) => (running += d))
        })()

  return Array.from({ length: cfg.daysInMonth }, (_, i) => {
    const day = i + 1
    return {
      day,
      observed: day <= cfg.daysObserved ? observedCumulative[day - 1] : null,
      runRate: cfg.runRatePerDay * day,
      trend: cfg.trendIntercept + cfg.trendSlopePerDay * day,
    }
  })
}

/**
 * Interactive check (project-standards rule 5, predict-then-reveal): toggle
 * between the real, genuinely flat AWS series (where run-rate and trend
 * agree almost exactly) and an explicitly-labeled constructed growth
 * example (where they diverge) -- demonstrating *why* two methods exist at
 * all, not just that they do.
 */
export function ForecastMethodCompare() {
  const [scenario, setScenario] = useState<Scenario>("real")
  const reduced = usePrefersReducedMotion()
  const cfg = scenario === "real" ? REAL : CONSTRUCTED
  const data = useMemo(() => buildSeries(scenario), [scenario])
  const isUsd = scenario === "real"
  const fmt = (n: number) => (isUsd ? formatUsd(n, { maxDecimals: 7 }) : `$${n.toFixed(0)}`)

  return (
    <div className="rounded-lg border border-border bg-muted/40 p-4 space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="font-mono text-[11px] uppercase tracking-wide text-muted-foreground">
          {scenario === "real" ? "Real AWS series — genuinely flat" : "Constructed example — not real data, growth pattern"}
        </div>
        <div className="flex gap-2">
          <Button
            type="button"
            size="sm"
            variant={scenario === "real" ? "default" : "outline"}
            onClick={() => setScenario("real")}
          >
            Real AWS data
          </Button>
          <Button
            type="button"
            size="sm"
            variant={scenario === "constructed" ? "default" : "outline"}
            onClick={() => setScenario("constructed")}
          >
            Constructed growth
          </Button>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
          <XAxis
            dataKey="day"
            tick={{ fontSize: 10, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={{ stroke: "var(--border)" }}
          />
          <YAxis
            tick={{ fontSize: 10, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }}
            tickLine={false}
            axisLine={false}
            width={64}
            tickFormatter={(v) => fmt(Number(v))}
          />
          <Tooltip
            contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontFamily: "var(--font-mono)", fontSize: 12 }}
            formatter={(value, name) => [fmt(Number(value)), name === "observed" ? "observed" : name === "runRate" ? "run-rate" : "trend"]}
            labelFormatter={(d) => `day ${d}`}
          />
          <Line type="monotone" dataKey="observed" stroke="var(--signal)" strokeWidth={2.25} dot={false} isAnimationActive={!reduced} />
          <Line type="monotone" dataKey="runRate" stroke="var(--muted-foreground)" strokeDasharray="4 4" strokeWidth={1.5} dot={false} isAnimationActive={!reduced} />
          <Line type="monotone" dataKey="trend" stroke="var(--source-databricks)" strokeDasharray="2 2" strokeWidth={1.5} dot={false} isAnimationActive={!reduced} />
        </LineChart>
      </ResponsiveContainer>

      <div className="flex flex-wrap items-center gap-6">
        <StatHighlight value={cfg.runRateProjection} label="run-rate → month end" color="var(--muted-foreground)" size="sm" countUp={false} format={fmt} />
        <StatHighlight value={cfg.trendProjection} label="trend → month end" color="var(--source-databricks)" size="sm" countUp={false} format={fmt} />
      </div>
      <p className="text-xs text-muted-foreground leading-relaxed">
        {scenario === "real"
          ? "On the real, zero-variance AWS series, both methods land on the identical $0.0001439888 -- an honest consequence of genuinely flat data, not proof the two methods always agree."
          : "On this constructed, clearly-labeled example, the trend line catches the day-over-day growth run-rate can't see, landing $9 higher at month end -- the actual reason a second method exists."}
      </p>
    </div>
  )
}
