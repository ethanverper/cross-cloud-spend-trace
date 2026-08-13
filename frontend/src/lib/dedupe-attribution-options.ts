import type { AttributionOption } from "./api"

/**
 * The Inputs page's filter state only carries a single `attributionKey`
 * (not `attribution_kind`), and a small number of real Snowflake rows
 * share the same key across two different attribution_kinds -- e.g. a
 * "query" row that fell back to its warehouse name as its key when no
 * per-query id/cost existed for that grain (real data, decision 0002/0003).
 * Deduping by (source, attribution_key) keeps both the <Select>'s `value`
 * prop and React's `key` prop genuinely unique, not just visually so --
 * this was a real bug (duplicate React key warning, verified live) before
 * this function existed inline in the component.
 */
export function dedupeAttributionOptions(options: AttributionOption[]): AttributionOption[] {
  const seen = new Set<string>()
  return options.filter((o) => {
    const dedupeKey = `${o.source}::${o.attribution_key}`
    if (seen.has(dedupeKey)) return false
    seen.add(dedupeKey)
    return true
  })
}
