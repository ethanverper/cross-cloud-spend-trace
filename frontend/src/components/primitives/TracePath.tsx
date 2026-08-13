import { useEffect, useRef } from "react"
import gsap from "gsap"
import { cn } from "@/lib/utils"

export interface TracePathNode {
  label: string
  sublabel?: string | null
  color: string
}

/**
 * cross-cloud-spend-trace's own signature primitive (decision 0005,
 * "Motion / microinteraction language"): a connected breadcrumb of
 * source -> job/query -> cost. A thin signal-cyan connector line draws
 * left-to-right between each node on mount (GSAP, ~250ms ease-out per
 * node, staggered) -- literally drawing the trace the product's name
 * promises, not decoration. Reused everywhere a specific attribution needs
 * to be shown concretely rather than described in prose.
 *
 * Layout note: nodes never flex-shrink below their content width (a fixed
 * connector width, not flex:1, sits between them) -- on a narrow viewport
 * the whole path scrolls horizontally instead of compressing node labels
 * into each other. An earlier flex:1-per-node layout let node content
 * overlap illegibly at mobile widths; this is the fix.
 */
export function TracePath({
  nodes,
  className,
  replayKey,
}: {
  nodes: TracePathNode[]
  className?: string
  /** Change this value to replay the draw animation (e.g. on hover/expand). */
  replayKey?: string | number
}) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const connectors = container.querySelectorAll<HTMLElement>("[data-trace-connector]")
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (reduced) {
      connectors.forEach((c) => gsap.set(c, { scaleX: 1 }))
      return
    }
    gsap.set(connectors, { scaleX: 0, transformOrigin: "left center" })
    const tl = gsap.timeline()
    tl.to(connectors, { scaleX: 1, duration: 0.25, ease: "power2.out", stagger: 0.12 })
    return () => {
      tl.kill()
    }
  }, [nodes.length, replayKey])

  return (
    <div className={cn("w-full overflow-x-auto", className)}>
      <div ref={containerRef} className="flex items-center w-max min-w-full py-0.5">
        {nodes.map((node, i) => (
          <div key={`${node.label}-${i}`} className="flex items-center shrink-0">
            <div className="flex flex-col items-start shrink-0">
              <div className="flex items-center gap-1.5">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ backgroundColor: node.color, boxShadow: `0 0 0 3px color-mix(in oklab, ${node.color} 20%, transparent)` }}
                  aria-hidden
                />
                <span className="font-mono text-xs md:text-sm text-foreground truncate max-w-[120px] md:max-w-[200px]" title={node.label}>
                  {node.label}
                </span>
              </div>
              {node.sublabel && (
                <span className="text-[10px] md:text-xs text-muted-foreground ml-3.5 truncate max-w-[120px] md:max-w-[200px]">
                  {node.sublabel}
                </span>
              )}
            </div>
            {i < nodes.length - 1 && (
              <div className="relative h-px w-8 md:w-12 mx-2 md:mx-3 shrink-0 bg-border">
                <div
                  data-trace-connector
                  className="absolute inset-0 h-px bg-signal"
                  style={{ transformOrigin: "left center" }}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
