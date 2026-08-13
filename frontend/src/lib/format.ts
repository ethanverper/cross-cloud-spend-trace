// This project's real dollar amounts are sub-cent (decision 0003: AWS's
// real daily S3 cost is $0.0000046448) -- a standard 2-decimal currency
// formatter would round every real number here to "$0.00" and erase the
// actual data. Format at real precision instead, consistent with the
// identity's own register (decision 0005: "dollar figures to six decimal
// places" is Mono-native content, not a display bug to smooth over).

export function formatUsd(value: number | null | undefined, opts?: { maxDecimals?: number }): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  // Default to 10 decimals -- the real AWS daily figure this project cites
  // everywhere ($0.0000046448) has significant digits out to the 10th
  // decimal place; a smaller default would silently truncate it, which is
  // exactly the bug a real test (format.test.ts) caught.
  const maxDecimals = opts?.maxDecimals ?? 10
  if (value === 0) return "$0.00"
  const abs = Math.abs(value)
  if (abs >= 1) {
    return `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
  }
  return `$${value.toFixed(maxDecimals).replace(/0+$/, "").replace(/\.$/, ".0")}`
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  return value.toLocaleString(undefined, { maximumFractionDigits: decimals })
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—"
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}

export function formatZScore(z: number | null | undefined): string {
  if (z === null || z === undefined || Number.isNaN(z)) return "—"
  return `z=${z.toFixed(2)}`
}
