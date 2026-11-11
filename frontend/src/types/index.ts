export type Sector =
  | "Technology"
  | "Financials"
  | "Energy"
  | "Healthcare"
  | "Consumer"
  | "Index ETF"
  | "Cash";

export type Side = "Buy" | "Sell";

export interface Position {
  symbol: string;
  name: string;
  sector: Sector;
  quantity: number;
  avgCost: number;
  lastPrice: number;
  /** Price change today, as a fraction (0.012 = +1.2%). */
  dayChangePct: number;
}

export interface Trade {
  id: string;
  /** ISO date-time string. */
  date: string;
  symbol: string;
  side: Side;
  quantity: number;
  price: number;
  accountId: string;
  sector: Sector;
  /** Who initiated it: a human or the agent (after risk checks). */
  source: "Manual" | "Agent";
}

export type AccountKind = "Brokerage" | "Paper" | "Cash" | "Retirement";

export interface Account {
  id: string;
  name: string;
  institution: string;
  kind: AccountKind;
  mask: string;
  balance: number;
  buyingPower: number;
  dayChange: number;
  /** ISO date-time string. */
  lastSynced: string;
  status: "Connected" | "Needs attention";
}

export interface RiskLimit {
  id: string;
  label: string;
  description: string;
  current: number;
  limit: number;
  unit: "usd" | "pct" | "ratio";
}

export interface PortfolioPoint {
  /** ISO date string (yyyy-mm-dd). */
  date: string;
  value: number;
}

export type FilingForm = "10-K" | "10-Q" | "8-K" | "DEF 14A" | "S-1";

export interface Filing {
  id: string;
  symbol: string;
  company: string;
  form: FilingForm;
  /** ISO date string. */
  filedAt: string;
  title: string;
  summary: string;
  url: string;
}

export interface MonthlyPnl {
  month: string;
  realized: number;
  unrealized: number;
}
