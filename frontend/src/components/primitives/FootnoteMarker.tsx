import type { ReactNode } from "react"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"

/** Click-gated, for genuinely optional depth (a citation, a cross-reference
 * to a decision doc) that doesn't change the main claim's meaning -- per
 * project-standards rule 15's callout-vs-footnote test. */
export function FootnoteMarker({ label = "note", children }: { label?: string; children: ReactNode }) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Show ${label}`}
          className="inline-flex h-4 w-4 -translate-y-1 items-center justify-center rounded-full border border-muted-foreground/40 text-[10px] font-mono text-muted-foreground align-super hover:border-signal hover:text-signal transition-colors"
        >
          i
        </button>
      </PopoverTrigger>
      <PopoverContent className="max-w-xs text-sm leading-relaxed font-sans">{children}</PopoverContent>
    </Popover>
  )
}
