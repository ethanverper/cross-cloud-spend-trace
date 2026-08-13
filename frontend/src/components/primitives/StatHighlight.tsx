import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

/** A pulled-out number/claim, Geist Mono, signal-cyan or source-color
 * depending on context. Counts up from 0 on first mount (decision 0005's
 * stat-tile motion spec) unless the value isn't a plain finite number.
 *
 * `format` controls how the animating number renders at each frame -- this
 * project's real dollar figures go to 6+ decimal places (decision 0005:
 * "$0.0000046448/day" is real content, not a display bug), so the default
 * naive "round to 3 decimals" would silently show "$0" for every genuine
 * sub-cent forecast/cost value. Pass `formatUsd`/`formatNumber` explicitly
 * for anything that small. */
export function StatHighlight({
  value,
  label,
  color = "var(--signal)",
  size = "md",
  countUp = true,
  format,
  className,
}: {
  value: string | number
  label?: string
  color?: string
  size?: "sm" | "md" | "lg"
  countUp?: boolean
  format?: (n: number) => string
  className?: string
}) {
  const canAnimate = countUp && typeof value === "number" && Number.isFinite(value)
  const numeric = typeof value === "number" ? value : 0
  const renderNumber = (n: number) => (format ? format(n) : Number.isInteger(n) ? String(n) : n.toPrecision(4).replace(/\.?0+$/, ""))
  const [display, setDisplay] = useState<string>(canAnimate ? renderNumber(0) : String(value))

  useEffect(() => {
    if (!canAnimate) {
      setDisplay(String(value))
      return
    }
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setDisplay(renderNumber(numeric))
      return
    }
    const duration = 700
    const start = performance.now()
    let raf = 0
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      const eased = 1 - Math.pow(1 - t, 3)
      setDisplay(renderNumber(numeric * eased))
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numeric, canAnimate])

  const sizeCls = size === "lg" ? "text-4xl md:text-5xl" : size === "sm" ? "text-xl" : "text-2xl md:text-3xl"

  return (
    <span className={cn("inline-flex flex-col", className)}>
      <span className={cn("font-mono font-semibold tabular-nums", sizeCls)} style={{ color }}>
        {display}
      </span>
      {label && <span className="text-xs text-muted-foreground mt-1">{label}</span>}
    </span>
  )
}
