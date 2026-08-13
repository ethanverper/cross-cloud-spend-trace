import type { ReactNode } from "react"
import { AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion"
import { Example } from "@/components/primitives/Example"

export interface GlossaryTerm {
  id: string
  term: string
  plain: ReactNode
  technical: ReactNode
  whereItShowsUp: ReactNode
}

/** One glossary entry, decomposed per decision 0007: a plain-language line,
 * a "Technical" block reusing Example's bordered/recessed treatment for the
 * more rigorous register (rather than inventing a new visual form), and a
 * short "where it shows up here" pointer. */
export function GlossaryEntry({ entry }: { entry: GlossaryTerm }) {
  return (
    <AccordionItem value={entry.id}>
      <AccordionTrigger>
        <span className="text-sm font-semibold font-mono">{entry.term}</span>
      </AccordionTrigger>
      <AccordionContent>
        <div className="space-y-3 pt-1">
          <p className="text-sm text-foreground/90 leading-relaxed">{entry.plain}</p>
          <Example title="Technical">{entry.technical}</Example>
          <p className="text-xs text-muted-foreground">
            <span className="font-mono uppercase tracking-wide text-[10px] mr-1.5">where it shows up here</span>
            {entry.whereItShowsUp}
          </p>
        </div>
      </AccordionContent>
    </AccordionItem>
  )
}
