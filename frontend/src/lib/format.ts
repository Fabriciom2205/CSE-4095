const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const usdCompact = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  notation: "compact",
  maximumFractionDigits: 1,
});
const pct = new Intl.NumberFormat("en-US", { style: "percent", minimumFractionDigits: 1, maximumFractionDigits: 1 });
const qty = new Intl.NumberFormat("en-US", { maximumFractionDigits: 4 });

/** "$1,234.56", always unsigned. Use formatSignedUsd for +/− display. */
export const formatUsd = (n: number) => usd.format(Math.abs(n));
export const formatUsdCompact = (n: number) => usdCompact.format(n);
export const formatQty = (n: number) => qty.format(n);
export const formatPct = (n: number) => pct.format(Math.abs(n));

/** Uses a true minus sign (U+2212) so negatives line up with tabular figures. */
export const sign = (n: number) => (n > 0 ? "+" : n < 0 ? "−" : "");
export const formatSignedUsd = (n: number) => `${sign(n)}${formatUsd(n)}`;
export const formatSignedPct = (n: number) => `${sign(n)}${formatPct(n)}`;

export const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
export const formatShortDate = (iso: string) =>
  new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
export const formatTime = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

/** "2 min ago", "3 hr ago", "Nov 4". */
export function formatRelative(iso: string, now: Date): string {
  const diff = Math.max(0, now.getTime() - new Date(iso).getTime());
  const min = Math.round(diff / 60_000);
  if (min < 1) return "just now";
  if (min < 60) return `${min} min ago`;
  const hr = Math.round(min / 60);
  if (hr < 24) return `${hr} hr ago`;
  return formatShortDate(iso);
}
