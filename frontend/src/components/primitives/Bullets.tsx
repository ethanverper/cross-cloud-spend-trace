import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export interface BulletItem {
  id: string
  text: ReactNode
}

/** Any enumerable set of points -- never a comma-separated list inside a
 * paragraph (project-standards rule 15). */
export function Bullets({ items, className }: { items: BulletItem[]; className?: string }) {
  return (
    <ul className={cn("space-y-2.5", className)}>
      {items.map((item) => (
        <li key={item.id} className="flex gap-3 text-sm md:text-base leading-relaxed text-foreground/90">
          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-signal" aria-hidden />
          <span>{item.text}</span>
        </li>
      ))}
    </ul>
  )
}
