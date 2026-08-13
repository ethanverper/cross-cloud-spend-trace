import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { useMemo } from "react"
import type { ForecastSparkPoint } from "@/lib/api"
import { formatUsd } from "@/lib/format"
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion"

interface Props {
  series: ForecastSparkPoint[]
  daysObserved: number
  height?: number
}

/** Month-end forecast: the projected run-rate line "draws" in on first view,
 * left to right, extending past the real observed days into the forecast
 * region -- representing the projection literally extending into the
 * future (decision 0005's forecast-chart motion spec). Uses recharts' own
 * mount animation for the line-draw effect; disabled under
 * prefers-reduced-motion. */
export function ForecastChart({ series, daysObserved, height = 260 }: Props) {
  const reduced = usePrefersReducedMotion()

  const data = useMemo(
    () =>
      series.map((p) => ({
        day: p.day,
        observed: p.day <= daysObserved ? p.cumulative_cost_usd : null,
        projected: p.cumulative_cost_usd,
      })),
    [series, daysObserved],
  )

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 4 }}>
        <defs>
          <linearGradient id="observedFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--signal)" stopOpacity={0.35} />
            <stop offset="100%" stopColor="var(--signal)" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="day"
          tick={{ fontSize: 11, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }}
          tickLine={false}
          axisLine={{ stroke: "var(--border)" }}
          label={{ value: "day of month", position: "insideBottom", offset: -2, fontSize: 10, fill: "var(--muted-foreground)" }}
        />
        <YAxis
          tick={{ fontSize: 11, fill: "var(--muted-foreground)", fontFamily: "var(--font-mono)" }}
          tickLine={false}
          axisLine={false}
          width={70}
          tickFormatter={(v) => formatUsd(v, { maxDecimals: 5 })}
        />
        <Tooltip
          contentStyle={{
            background: "var(--popover)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontFamily: "var(--font-mono)",
            fontSize: 12,
          }}
          formatter={(value, name) => [formatUsd(typeof value === "number" ? value : Number(value)), name === "observed" ? "observed" : "projected"]}
          labelFormatter={(d) => `day ${d}`}
        />
        <Area
          type="monotone"
          dataKey="observed"
          stroke="none"
          fill="url(#observedFill)"
          isAnimationActive={!reduced}
          animationDuration={900}
        />
        <Line
          type="monotone"
          dataKey="projected"
          stroke="var(--muted-foreground)"
          strokeDasharray="4 4"
          strokeWidth={1.75}
          dot={false}
          isAnimationActive={!reduced}
          animationDuration={1100}
          animationEasing="ease-out"
        />
        <Line
          type="monotone"
          dataKey="observed"
          stroke="var(--signal)"
          strokeWidth={2.25}
          dot={false}
          isAnimationActive={!reduced}
          animationDuration={900}
          animationEasing="ease-out"
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
