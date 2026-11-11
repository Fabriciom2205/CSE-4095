import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Search, SearchX } from "lucide-react";
import { api } from "../data/api";
import { sectors } from "../data/mock";
import { useAsync } from "../hooks/useAsync";
import { Card } from "../components/ui/Card";
import { Chip } from "../components/ui/Chip";
import { Button } from "../components/ui/Button";
import { EmptyState } from "../components/ui/EmptyState";
import { StatTile } from "../components/ui/StatTile";
import { formatDate, formatQty, formatTime, formatUsd } from "../lib/format";
import type { Sector, Side } from "../types";
import page from "./page.module.css";
import styles from "./Trades.module.css";

async function loadTrades() {
  const [trades, accounts] = await Promise.all([api.getTrades(), api.getAccounts()]);
  return { trades, accounts };
}

export function Trades() {
  const { data } = useAsync(loadTrades);
  const [params, setParams] = useSearchParams();
  const query = params.get("q") ?? "";
  const [side, setSide] = useState<Side | "All">("All");
  const [activeSectors, setActiveSectors] = useState<Set<Sector>>(new Set());
  const [accountId, setAccountId] = useState("all");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");

  const setQuery = (q: string) => {
    const next = new URLSearchParams(params);
    if (q) next.set("q", q);
    else next.delete("q");
    setParams(next, { replace: true });
  };

  const toggleSector = (s: Sector) =>
    setActiveSectors((prev) => {
      const next = new Set(prev);
      if (next.has(s)) next.delete(s);
      else next.add(s);
      return next;
    });

  const reset = () => {
    setQuery("");
    setSide("All");
    setActiveSectors(new Set());
    setAccountId("all");
    setFrom("");
    setTo("");
  };

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toUpperCase();
    return data.trades.filter((t) => {
      const day = t.date.slice(0, 10);
      return (
        (!q || t.symbol.includes(q)) &&
        (side === "All" || t.side === side) &&
        (activeSectors.size === 0 || activeSectors.has(t.sector)) &&
        (accountId === "all" || t.accountId === accountId) &&
        (!from || day >= from) &&
        (!to || day <= to)
      );
    });
  }, [data, query, side, activeSectors, accountId, from, to]);

  if (!data) return <p className={page.loading}>Loading trades…</p>;

  const accountName = (id: string) => data.accounts.find((a) => a.id === id)?.name ?? id;
  const bought = filtered.filter((t) => t.side === "Buy").reduce((s, t) => s + t.quantity * t.price, 0);
  const sold = filtered.filter((t) => t.side === "Sell").reduce((s, t) => s + t.quantity * t.price, 0);
  const filtersActive = query || side !== "All" || activeSectors.size || accountId !== "all" || from || to;

  return (
    <div className={page.stack}>
      <div className={page.header}>
        <div>
          <h1 className={page.title}>Trades</h1>
          <p className={page.lede}>Executed orders across all linked accounts, including agent-submitted trades.</p>
        </div>
      </div>

      <Card padded={false}>
        <div className={styles.filters}>
          <div className={styles.row}>
            <div className={styles.search}>
              <Search size={16} className={styles.searchIcon} aria-hidden="true" />
              <label htmlFor="trade-search" className="visually-hidden">
                Filter by symbol
              </label>
              <input
                id="trade-search"
                type="search"
                placeholder="Symbol, e.g. NVDA"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className={styles.input}
              />
            </div>
            <div className={styles.field}>
              <label htmlFor="account" className={styles.label}>
                Account
              </label>
              <select id="account" value={accountId} onChange={(e) => setAccountId(e.target.value)} className={styles.select}>
                <option value="all">All accounts</option>
                {data.accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name}
                  </option>
                ))}
              </select>
            </div>
            <fieldset className={styles.dates}>
              <legend className={styles.label}>Date range</legend>
              <label htmlFor="from" className="visually-hidden">
                From date
              </label>
              <input id="from" type="date" value={from} max={to || undefined} onChange={(e) => setFrom(e.target.value)} className={styles.input} />
              <span aria-hidden="true" className={page.muted}>
                –
              </span>
              <label htmlFor="to" className="visually-hidden">
                To date
              </label>
              <input id="to" type="date" value={to} min={from || undefined} onChange={(e) => setTo(e.target.value)} className={styles.input} />
            </fieldset>
          </div>
          <div className={styles.chips} role="group" aria-label="Filter by side">
            {(["All", "Buy", "Sell"] as const).map((s) => (
              <Chip key={s} selected={side === s} onClick={() => setSide(s)}>
                {s === "All" ? "All sides" : s}
              </Chip>
            ))}
            <span className={styles.divider} aria-hidden="true" />
            <div className={styles.chipGroup} role="group" aria-label="Filter by sector">
              {sectors.map((s) => (
                <Chip key={s} selected={activeSectors.has(s)} onClick={() => toggleSector(s)}>
                  {s}
                </Chip>
              ))}
            </div>
          </div>
        </div>

        <div className={styles.summary} aria-live="polite">
          <StatTile label="Trades" value={<span className="num">{filtered.length}</span>} />
          <StatTile label="Bought" value={<span className="num">{formatUsd(bought)}</span>} />
          <StatTile label="Sold" value={<span className="num">{formatUsd(sold)}</span>} />
          {filtersActive ? (
            <Button variant="ghost" onClick={reset} className={styles.reset}>
              Clear filters
            </Button>
          ) : null}
        </div>

        {filtered.length === 0 ? (
          <EmptyState icon={<SearchX size={20} />} title="No trades match these filters">
            Try a different symbol or widen the date range.
          </EmptyState>
        ) : (
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <caption className="visually-hidden">Trades, newest first</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Symbol</th>
                  <th scope="col">Side</th>
                  <th scope="col" className={styles.numCol}>Qty</th>
                  <th scope="col" className={styles.numCol}>Price</th>
                  <th scope="col">Account</th>
                  <th scope="col">Sector</th>
                  <th scope="col" className={styles.numCol}>Amount</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((t) => {
                  const notional = t.quantity * t.price;
                  return (
                    <tr key={t.id}>
                      <td data-label="Date">
                        <time dateTime={t.date}>{formatDate(t.date)}</time>
                        <span className={styles.time}>{formatTime(t.date)}</span>
                      </td>
                      <td data-label="Symbol" className={styles.symbol}>
                        {t.symbol}
                        {t.source === "Agent" && <Chip tone="accent">Agent</Chip>}
                      </td>
                      <td data-label="Side">
                        <Chip tone={t.side === "Buy" ? "neutral" : "gain"}>{t.side}</Chip>
                      </td>
                      <td data-label="Qty" className={`num ${styles.numCol}`}>{formatQty(t.quantity)}</td>
                      <td data-label="Price" className={`num ${styles.numCol}`}>{formatUsd(t.price)}</td>
                      <td data-label="Account">{accountName(t.accountId)}</td>
                      <td data-label="Sector">{t.sector}</td>
                      <td data-label="Amount" className={`num ${styles.numCol} ${styles.amount} ${t.side === "Sell" ? styles.in : ""}`}>
                        {t.side === "Buy" ? "−" : "+"}
                        {formatUsd(notional)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
