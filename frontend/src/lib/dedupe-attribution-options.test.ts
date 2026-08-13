import { describe, expect, it } from "vitest"
import { dedupeAttributionOptions } from "./dedupe-attribution-options"
import type { AttributionOption } from "./api"

// Real shape hit live: two Snowflake rows with different attribution_kind
// ("query" and "warehouse") sharing the same attribution_key
// ("SPEND_LENS_WH") -- verified via GET /api/filters against the real
// ingested data, and confirmed to throw a real React duplicate-key console
// error in the Inputs page's job/query <Select> before this fix.
describe("dedupeAttributionOptions", () => {
  it("collapses rows that share (source, attribution_key) across different kinds", () => {
    const input: AttributionOption[] = [
      { source: "snowflake", attribution_kind: "query", attribution_key: "SPEND_LENS_WH", label: "SPEND_LENS_WH" },
      { source: "snowflake", attribution_kind: "warehouse", attribution_key: "SPEND_LENS_WH", label: "SPEND_LENS_WH" },
      { source: "snowflake", attribution_kind: "query", attribution_key: "01c659a4-abc", label: "SELECT 1" },
    ]
    const result = dedupeAttributionOptions(input)
    expect(result).toHaveLength(2)
    expect(result[0].attribution_key).toBe("SPEND_LENS_WH")
    expect(result[0].attribution_kind).toBe("query")
  })

  it("keeps the same attribution_key distinct across different sources", () => {
    const input: AttributionOption[] = [
      { source: "snowflake", attribution_kind: "warehouse", attribution_key: "X", label: "X" },
      { source: "databricks", attribution_kind: "job", attribution_key: "X", label: "X" },
    ]
    expect(dedupeAttributionOptions(input)).toHaveLength(2)
  })

  it("returns an empty array unchanged", () => {
    expect(dedupeAttributionOptions([])).toEqual([])
  })
})
