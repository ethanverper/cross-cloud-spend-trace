import { createContext, useContext, useMemo, useState, type ReactNode } from "react"
import type { SourceId } from "./api"

// Rule 2: every field here is a constrained selection (dropdown-backed),
// never free text -- the Inputs page only ever writes a value it read from
// GET /api/filters, so nothing user-typed reaches the backend.
export interface DashboardFilters {
  source: SourceId | "all"
  start: string | null
  end: string | null
  attributionKey: string | null
}

const DEFAULT_FILTERS: DashboardFilters = {
  source: "all",
  start: null,
  end: null,
  attributionKey: null,
}

interface FilterContextValue {
  filters: DashboardFilters
  setSource: (source: DashboardFilters["source"]) => void
  setDateRange: (start: string | null, end: string | null) => void
  setAttributionKey: (key: string | null) => void
  reset: () => void
}

const FilterContext = createContext<FilterContextValue | null>(null)

export function FilterProvider({ children }: { children: ReactNode }) {
  const [filters, setFilters] = useState<DashboardFilters>(DEFAULT_FILTERS)

  const value = useMemo<FilterContextValue>(
    () => ({
      filters,
      setSource: (source) => setFilters((f) => ({ ...f, source, attributionKey: null })),
      setDateRange: (start, end) => setFilters((f) => ({ ...f, start, end })),
      setAttributionKey: (attributionKey) => setFilters((f) => ({ ...f, attributionKey })),
      reset: () => setFilters(DEFAULT_FILTERS),
    }),
    [filters],
  )

  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>
}

export function useFilters() {
  const ctx = useContext(FilterContext)
  if (!ctx) throw new Error("useFilters must be used within FilterProvider")
  return ctx
}
