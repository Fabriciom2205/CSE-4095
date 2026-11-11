/**
 * Data access layer. Every getter is async so the mock implementation can be
 * swapped for real HTTP / gRPC-web calls to the Python brain or Rust daemon
 * without touching the pages.
 */
import { accounts, filings, monthlyPnl, portfolioHistory, positions, riskLimits, trades } from "./mock";
import type { Account, Filing, MonthlyPnl, PortfolioPoint, Position, RiskLimit, Trade } from "../types";

const resolve = <T,>(value: T): Promise<T> => Promise.resolve(value);

export const api = {
  getPositions: (): Promise<Position[]> => resolve(positions),
  getAccounts: (): Promise<Account[]> => resolve(accounts),
  getTrades: (): Promise<Trade[]> => resolve(trades),
  getRiskLimits: (): Promise<RiskLimit[]> => resolve(riskLimits),
  getPortfolioHistory: (): Promise<PortfolioPoint[]> => resolve(portfolioHistory),
  getMonthlyPnl: (): Promise<MonthlyPnl[]> => resolve(monthlyPnl),
  /** Mock of the python-brain SEC search; filters the local filing list. */
  searchFilings: (query: string): Promise<Filing[]> => {
    const q = query.trim().toLowerCase();
    if (!q) return resolve(filings);
    return resolve(
      filings.filter((f) =>
        [f.symbol, f.company, f.form, f.title, f.summary].some((s) => s.toLowerCase().includes(q)),
      ),
    );
  },
};
