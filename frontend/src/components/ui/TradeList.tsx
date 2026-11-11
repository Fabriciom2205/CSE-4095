import type { Account, Trade } from "../../types";
import { formatQty, formatShortDate, formatTime, formatUsd } from "../../lib/format";
import { Chip } from "./Chip";
import styles from "./TradeList.module.css";

interface TradeListProps {
  trades: Trade[];
  accounts: Account[];
}

/** Compact list of trades for the dashboard. */
export function TradeList({ trades, accounts }: TradeListProps) {
  const accountName = (id: string) => accounts.find((a) => a.id === id)?.name ?? id;
  return (
    <ul className={styles.list}>
      {trades.map((t) => {
        const notional = t.quantity * t.price;
        return (
          <li key={t.id} className={styles.row}>
            <span className={styles.symbol} aria-hidden="true">
              {t.symbol.slice(0, 4)}
            </span>
            <div className={styles.main}>
              <div className={styles.line}>
                <span className={styles.title}>
                  {t.side} {t.symbol}
                </span>
                {t.source === "Agent" && <Chip tone="accent">Agent</Chip>}
              </div>
              <div className={styles.meta}>
                <span className="num">
                  {formatQty(t.quantity)} @ {formatUsd(t.price)}
                </span>
                <span aria-hidden="true">&middot;</span>
                <span>{accountName(t.accountId)}</span>
              </div>
            </div>
            <div className={styles.right}>
              {/* Buys are cash out, sells cash in: show as signed cash flow. */}
              <span className={`num ${styles.amount} ${t.side === "Sell" ? styles.in : ""}`}>
                {t.side === "Buy" ? "−" : "+"}
                {formatUsd(notional)}
              </span>
              <span className={styles.date}>
                <time dateTime={t.date}>
                  {formatShortDate(t.date)}, {formatTime(t.date)}
                </time>
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
