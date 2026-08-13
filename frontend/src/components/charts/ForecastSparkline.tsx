import { Line, LineChart, ResponsiveContainer } from "recharts"
import type { ForecastSparkPoint } from "@/lib/api"
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion"

/** Compact, axis-less version of ForecastChart for the landing screen's
 * "real result preview" (decision 0005 section 6, item 4). */
export function ForecastSparkline({ series, height = 56 }: { series: ForecastSparkPoint[]; height?: number }) {
  const reduced = usePrefersReducedMotion()
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={series} margin={{ top: 4, right: 2, left: 2, bottom: 4 }}>
        <Line
          type="monotone"
          dataKey="cumulative_cost_usd"
          stroke="var(--signal)"
          strokeWidth={2}
          dot={false}
          isAnimationActive={!reduced}
          animationDuration={1000}
          animationEasing="ease-out"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
