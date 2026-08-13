import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/** A concrete worked case, visually set apart (bordered, slightly recessed
 * card) -- per project-standards rule 15. */
export function Example({
  title,
  children,
  className,
}: {
  title?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn("rounded-lg border border-border bg-muted/40 p-4", className)}>
      {title && (
        <div className="mb-2 font-mono text-[11px] uppercase tracking-wide text-muted-foreground">{title}</div>
      )}
      <div className="text-sm leading-relaxed text-foreground/90">{children}</div>
    </div>
  )
}
