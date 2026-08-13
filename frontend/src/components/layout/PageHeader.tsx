import type { ReactNode } from "react"

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string
  title: string
  description?: ReactNode
  actions?: ReactNode
}) {
  return (
    <div className="mb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
      <div>
        {eyebrow && <div className="font-mono text-xs uppercase tracking-wider text-signal mb-2">{eyebrow}</div>}
        <h1 className="text-3xl md:text-4xl font-bold tracking-tight text-foreground">{title}</h1>
        {description && <div className="mt-2 max-w-2xl text-muted-foreground">{description}</div>}
      </div>
      {actions && <div className="shrink-0">{actions}</div>}
    </div>
  )
}
