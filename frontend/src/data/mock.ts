import type {
  Account,
  Filing,
  MonthlyPnl,
  PortfolioPoint,
  Position,
  RiskLimit,
  Sector,
  Side,
  Trade,
} from "../types";

/** Fixed "now" so mock data is deterministic across reloads. */
export const AS_OF = new Date("2026-11-11T15:42:00-05:00");

/** Small seeded PRNG (mulberry32) so generated series are stable. */
function rng(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const isoDay = (d: Date) => d.toISOString().slice(0, 10);
const daysAgo = (n: number, hour = 10, minute = 0) => {
  const d = new Date(AS_OF);
  d.setDate(d.getDate() - n);
  d.setHours(hour, minute, 0, 0);
  return d;
};

export const positions: Position[] = [
  { symbol: "NVDA", name: "NVIDIA Corp.", sector: "Technology", quantity: 420, avgCost: 118.4, lastPrice: 192.36, dayChangePct: 0.0214 },
  { symbol: "MSFT", name: "Microsoft Corp.", sector: "Technology", quantity: 135, avgCost: 402.1, lastPrice: 498.72, dayChangePct: 0.0061 },
  { symbol: "AAPL", name: "Apple Inc.", sector: "Technology", quantity: 210, avgCost: 189.55, lastPrice: 241.18, dayChangePct: -0.0043 },
  { symbol: "AMZN", name: "Amazon.com Inc.", sector: "Consumer", quantity: 180, avgCost: 176.3, lastPrice: 221.04, dayChangePct: 0.0118 },
  { symbol: "COST", name: "Costco Wholesale", sector: "Consumer", quantity: 28, avgCost: 812.0, lastPrice: 934.6, dayChangePct: -0.0027 },
  { symbol: "JPM", name: "JPMorgan Chase & Co.", sector: "Financials", quantity: 160, avgCost: 196.8, lastPrice: 268.45, dayChangePct: 0.0072 },
  { symbol: "GS", name: "Goldman Sachs Group", sector: "Financials", quantity: 40, avgCost: 512.25, lastPrice: 611.9, dayChangePct: -0.0108 },
  { symbol: "XOM", name: "Exxon Mobil Corp.", sector: "Energy", quantity: 300, avgCost: 118.9, lastPrice: 109.42, dayChangePct: -0.0151 },
  { symbol: "UNH", name: "UnitedHealth Group", sector: "Healthcare", quantity: 45, avgCost: 548.0, lastPrice: 352.18, dayChangePct: 0.0034 },
  { symbol: "LLY", name: "Eli Lilly & Co.", sector: "Healthcare", quantity: 38, avgCost: 742.5, lastPrice: 821.33, dayChangePct: 0.0166 },
  { symbol: "SPY", name: "SPDR S&P 500 ETF", sector: "Index ETF", quantity: 95, avgCost: 512.6, lastPrice: 612.85, dayChangePct: 0.0039 },
  { symbol: "QQQ", name: "Invesco QQQ Trust", sector: "Index ETF", quantity: 60, avgCost: 438.2, lastPrice: 548.1, dayChangePct: 0.0057 },
];

const minutesAgo = (m: number) => new Date(AS_OF.getTime() - m * 60_000).toISOString();
const cents = (n: number) => Math.round(n * 100) / 100;

/*
 * Everything below is derived from `positions` so every page agrees:
 * net liquidation = market value of positions + cash, today's P&L comes from
 * each position's day move, and the risk figures are computed, not typed in.
 */

/** Market value of all positions. */
export const marketValue = positions.reduce((s, p) => s + p.quantity * p.lastPrice, 0);

/** Today's P&L per position: value now minus value at yesterday's close. */
const positionDayPnl = positions.reduce(
  (s, p) => s + p.quantity * p.lastPrice * (p.dayChangePct / (1 + p.dayChangePct)),
  0,
);

/** Positions are split between the live brokerage account and the IRA. */
const LIVE_SHARE = 0.82;
const LIVE_CASH = 96_420;
const IRA_CASH = 4_210;
const SWEEP_CASH = 61_250;
const SWEEP_INTEREST_TODAY = 7.98;

export const accounts: Account[] = [
  {
    id: "acc-alpaca-live",
    name: "Live Trading",
    institution: "Alpaca",
    kind: "Brokerage",
    mask: "4821",
    balance: cents(marketValue * LIVE_SHARE + LIVE_CASH),
    buyingPower: LIVE_CASH,
    dayChange: cents(positionDayPnl * LIVE_SHARE),
    lastSynced: minutesAgo(2),
    status: "Connected",
  },
  {
    id: "acc-alpaca-paper",
    name: "Paper Trading",
    institution: "Alpaca",
    kind: "Paper",
    mask: "0097",
    balance: 107_412.55,
    buyingPower: 214_825.1,
    dayChange: -612.4,
    lastSynced: minutesAgo(4),
    status: "Connected",
  },
  {
    id: "acc-ibkr-ira",
    name: "Roth IRA",
    institution: "Interactive Brokers",
    kind: "Retirement",
    mask: "7730",
    balance: cents(marketValue * (1 - LIVE_SHARE) + IRA_CASH),
    buyingPower: IRA_CASH,
    dayChange: cents(positionDayPnl * (1 - LIVE_SHARE)),
    lastSynced: minutesAgo(180),
    status: "Needs attention",
  },
  {
    id: "acc-treasury",
    name: "Treasury Cash Sweep",
    institution: "Alpaca",
    kind: "Cash",
    mask: "5512",
    balance: SWEEP_CASH,
    buyingPower: SWEEP_CASH,
    dayChange: SWEEP_INTEREST_TODAY,
    lastSynced: minutesAgo(26),
    status: "Connected",
  },
];

/** Total across real-money accounts (paper trading excluded). */
export const totalNetLiquidation = accounts
  .filter((a) => a.kind !== "Paper")
  .reduce((s, a) => s + a.balance, 0);

/** Daily portfolio value for the past year, ending at the current total. */
export const portfolioHistory: PortfolioPoint[] = (() => {
  const rand = rng(4095);
  const days = 365;
  const raw: number[] = [];
  let v = 100;
  for (let i = 0; i <= days; i++) {
    const drift = 0.0008;
    const shock = (rand() - 0.5) * 0.022;
    // A drawdown in late spring, then recovery.
    const regime = i > 170 && i < 205 ? -0.004 : 0;
    v *= 1 + drift + shock + regime;
    raw.push(v);
  }
  const scale = totalNetLiquidation / raw[raw.length - 1];
  return raw.map((r, i) => ({
    date: isoDay(daysAgo(days - i)),
    value: Math.round(r * scale * 100) / 100,
  }));
})();

const tradeAccountIds = ["acc-alpaca-live", "acc-alpaca-live", "acc-alpaca-live", "acc-alpaca-paper", "acc-ibkr-ira"];

export const trades: Trade[] = (() => {
  const rand = rng(1776);
  const out: Trade[] = [];
  const count = 72;
  for (let i = 0; i < count; i++) {
    const p = positions[Math.floor(rand() * positions.length)];
    const ago = Math.floor((i / count) * 120 + rand() * 1.5);
    const side: Side = rand() < 0.62 ? "Buy" : "Sell";
    const qty = Math.max(1, Math.round((rand() * 40 + 2) * (p.lastPrice > 500 ? 0.3 : 1)));
    const price = Math.round(p.lastPrice * (1 + (rand() - 0.5) * 0.12) * 100) / 100;
    out.push({
      id: `t-${1000 + i}`,
      date: daysAgo(ago, 9 + Math.floor(rand() * 7), Math.floor(rand() * 60)).toISOString(),
      symbol: p.symbol,
      side,
      quantity: qty,
      price,
      accountId: tradeAccountIds[Math.floor(rand() * tradeAccountIds.length)],
      sector: p.sector,
      source: rand() < 0.45 ? "Agent" : "Manual",
    });
  }
  return out.sort((a, b) => b.date.localeCompare(a.date));
})();

/** Risk figures computed from the data above; only the limits are configuration. */
export const riskLimits: RiskLimit[] = (() => {
  const largest = positions.reduce((a, b) => (b.quantity * b.lastPrice > a.quantity * a.lastPrice ? b : a));
  const techValue = positions
    .filter((p) => p.sector === "Technology")
    .reduce((s, p) => s + p.quantity * p.lastPrice, 0);
  const dayPnl = accounts.filter((a) => a.kind !== "Paper").reduce((s, a) => s + a.dayChange, 0);

  const last90 = portfolioHistory.slice(-91);
  let peak = 0;
  let maxDrawdown = 0;
  for (const { value } of last90) {
    peak = Math.max(peak, value);
    maxDrawdown = Math.max(maxDrawdown, (peak - value) / peak);
  }

  const today = AS_OF.toISOString().slice(0, 10);
  const agentNotionalToday = trades
    .filter((t) => t.source === "Agent" && t.date.slice(0, 10) === today)
    .reduce((s, t) => s + t.quantity * t.price, 0);

  return [
    {
      id: "conc",
      label: "Single-position concentration",
      description: `Largest holding (${largest.symbol}) as a share of net liquidation value`,
      current: (largest.quantity * largest.lastPrice) / totalNetLiquidation,
      limit: 0.15,
      unit: "pct",
    },
    {
      id: "tech",
      label: "Technology sector exposure",
      description: "Technology holdings as a share of net liquidation value",
      current: techValue / totalNetLiquidation,
      limit: 0.28,
      unit: "pct",
    },
    {
      id: "daily",
      label: "Daily loss limit",
      description: "Loss since yesterday's close (zero on an up day)",
      current: Math.max(0, -dayPnl),
      limit: 10_000,
      unit: "usd",
    },
    {
      id: "dd",
      label: "Max drawdown",
      description: "Peak-to-trough decline over the trailing 90 days",
      current: maxDrawdown,
      limit: 0.1,
      unit: "pct",
    },
    {
      id: "lev",
      label: "Gross leverage",
      description: "Gross exposure divided by net liquidation value",
      current: marketValue / totalNetLiquidation,
      limit: 1.5,
      unit: "ratio",
    },
    {
      id: "agent",
      label: "Agent order notional (today)",
      description: "Value of orders the agent has submitted today",
      current: agentNotionalToday,
      limit: 50_000,
      unit: "usd",
    },
  ];
})();

const edgar = (cik: string, type: string) =>
  `https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=${cik}&type=${encodeURIComponent(type)}`;

export const filings: Filing[] = [
  { id: "f2", symbol: "NVDA", company: "NVIDIA Corp.", form: "8-K", filedAt: "2026-11-06", title: "Announcement of accelerated share repurchase", summary: "Board authorized an additional $40B buyback; company reiterated Q4 data center guidance.", url: edgar("NVDA", "8-K") },
  { id: "f4", symbol: "JPM", company: "JPMorgan Chase & Co.", form: "8-K", filedAt: "2026-11-03", title: "Results of Federal Reserve stress capital buffer", summary: "Stress capital buffer set at 3.3%, down from 3.5%; no change to dividend plans.", url: edgar("JPM", "8-K") },
  { id: "f5", symbol: "XOM", company: "Exxon Mobil Corp.", form: "10-Q", filedAt: "2026-11-01", title: "Quarterly report for period ended Sep 30, 2026", summary: "Upstream earnings fell on lower realized crude prices; Permian output reached a record 1.6M boe/d.", url: edgar("XOM", "10-Q") },
  { id: "f7", symbol: "LLY", company: "Eli Lilly & Co.", form: "10-Q", filedAt: "2026-10-31", title: "Quarterly report for period ended Sep 30, 2026", summary: "Incretin franchise revenue up 58%; manufacturing capacity expansion in North Carolina on schedule.", url: edgar("LLY", "10-Q") },
  { id: "f1", symbol: "AAPL", company: "Apple Inc.", form: "10-K", filedAt: "2026-10-30", title: "Annual report for fiscal year ended Sep 26, 2026", summary: "Services revenue grew 13% year over year; risk factors add new language on App Store regulation in the EU and Japan.", url: edgar("AAPL", "10-K") },
  { id: "f3", symbol: "MSFT", company: "Microsoft Corp.", form: "10-Q", filedAt: "2026-10-29", title: "Quarterly report for period ended Sep 30, 2026", summary: "Azure growth of 34%; capital expenditures up 41% on AI infrastructure build-out.", url: edgar("MSFT", "10-Q") },
  { id: "f6", symbol: "UNH", company: "UnitedHealth Group", form: "8-K", filedAt: "2026-10-22", title: "Leadership changes and updated 2026 outlook", summary: "Medical cost ratio guidance raised to 89.5%; new CFO appointed effective December 1.", url: edgar("UNH", "8-K") },
  { id: "f8", symbol: "GS", company: "Goldman Sachs Group", form: "DEF 14A", filedAt: "2026-10-15", title: "Proxy statement for special meeting", summary: "Shareholders asked to approve amendments to the long-term incentive plan.", url: edgar("GS", "DEF 14A") },
];

export const monthlyPnl: MonthlyPnl[] = [
  { month: "Jun", realized: 4_210, unrealized: -8_930 },
  { month: "Jul", realized: 6_880, unrealized: 12_410 },
  { month: "Aug", realized: -2_150, unrealized: 9_320 },
  { month: "Sep", realized: 3_940, unrealized: -4_120 },
  { month: "Oct", realized: 8_515, unrealized: 15_760 },
  { month: "Nov", realized: 2_310, unrealized: 6_045 },
];

export const sectors: Sector[] = ["Technology", "Financials", "Energy", "Healthcare", "Consumer", "Index ETF"];
