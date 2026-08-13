import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/** One-sentence "so what" -- always the first line of any section with more
 * than ~3 sentences of content (decision 0005 rule-15 plan / project-
 * standards rule 15). */
export function Lead({ children, className }: { children: ReactNode; className?: string }) {
  return <p className={cn("text-lg md:text-xl leading-relaxed text-foreground font-medium", className)}>{children}</p>
}
