import { useEffect, useRef } from "react"
import gsap from "gsap"
import { cn } from "@/lib/utils"

/** Primary lockup, decision 0005 section 1: `cross-cloud/` in Geist Mono
 * (muted, the "namespace") immediately followed by `spend-trace` in Geist
 * Sans Bold (the actual mark). A single signal-cyan underline draws
 * left-to-right beneath `spend-trace` once on first paint -- the one
 * animated flourish in the whole lockup, literalizing "trace" as a line
 * being drawn under the product's own name. */
export function Wordmark({ size = "md", className }: { size?: "sm" | "md" | "lg"; className?: string }) {
  const underlineRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const el = underlineRef.current
    if (!el) return
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (reduced) {
      gsap.set(el, { scaleX: 1 })
      return
    }
    gsap.fromTo(el, { scaleX: 0, transformOrigin: "left center" }, { scaleX: 1, duration: 0.6, ease: "power2.out", delay: 0.15 })
  }, [])

  const sizes = {
    sm: { ns: "text-xs", mark: "text-sm" },
    md: { ns: "text-sm", mark: "text-lg" },
    lg: { ns: "text-base md:text-lg", mark: "text-2xl md:text-3xl" },
  }[size]

  return (
    <span className={cn("inline-flex items-baseline gap-0.5 select-none", className)}>
      <span className={cn("font-mono text-muted-foreground", sizes.ns)}>cross-cloud/</span>
      <span className="relative inline-block">
        <span className={cn("font-sans font-bold text-foreground", sizes.mark)}>spend-trace</span>
        <span ref={underlineRef} className="absolute -bottom-0.5 left-0 right-0 h-[2px] bg-signal" />
      </span>
    </span>
  )
}
