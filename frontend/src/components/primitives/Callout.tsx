import type { ReactNode } from "react"
import { AlertTriangle, Info } from "lucide-react"
import { cn } from "@/lib/utils"

/** Always-visible aside for a caveat/definition/correction a reader would
 * form a wrong mental model without -- per project-standards rule 15's own
 * callout-vs-footnote test. Never used for genuinely optional depth (that's
 * FootnoteMarker). */
export function Callout({
  children,
  tone = "caveat",
  className,
}: {
  children: ReactNode
  tone?: "caveat" | "info"
  className?: string
}) {
  const Icon = tone === "caveat" ? AlertTriangle : Info
  return (
    <div
      className={cn(
        "flex gap-3 rounded-md border px-4 py-3 text-sm leading-relaxed",
        tone === "caveat"
          ? "border-amber-500/25 bg-amber-500/[0.06] text-foreground/90"
          : "border-signal/25 bg-signal/[0.06] text-foreground/90",
        className,
      )}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", tone === "caveat" ? "text-amber-500" : "text-signal")} aria-hidden />
      <div>{children}</div>
    </div>
  )
}
