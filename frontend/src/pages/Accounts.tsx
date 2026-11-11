import { AlertCircle, Banknote, Building2, FlaskConical, PiggyBank, Plus, RefreshCw } from "lucide-react";
import { api } from "../data/api";
import { AS_OF } from "../data/mock";
import { useAsync } from "../hooks/useAsync";
import { Card } from "../components/ui/Card";
import { Chip } from "../components/ui/Chip";
import { Button } from "../components/ui/Button";
import { Money } from "../components/ui/Money";
import { formatRelative, formatUsd } from "../lib/format";
import type { AccountKind } from "../types";
import page from "./page.module.css";
import styles from "./Accounts.module.css";

const KIND_ICON: Record<AccountKind, JSX.Element> = {
  Brokerage: <Building2 size={20} />,
  Paper: <FlaskConical size={20} />,
  Retirement: <PiggyBank size={20} />,
  Cash: <Banknote size={20} />,
};

export function Accounts() {
  const { data: accounts } = useAsync(api.getAccounts);
  if (!accounts) return <p className={page.loading}>Loading accounts…</p>;

  const real = accounts.filter((a) => a.kind !== "Paper");
  const total = real.reduce((s, a) => s + a.balance, 0);
  const dayChange = real.reduce((s, a) => s + a.dayChange, 0);

  return (
    <div className={page.stack}>
      <div className={page.header}>
        <div>
          <h1 className={page.title}>Accounts</h1>
          <p className={page.lede}>
            <span className="num">{formatUsd(total)}</span> across {real.length} live accounts ·{" "}
            <Money value={dayChange} mode="signed" size="sm" /> today
          </p>
        </div>
        <Button variant="primary" icon={<Plus size={16} />}>
          Link account
        </Button>
      </div>

      <div className={page.grid2}>
        {accounts.map((a) => (
          <Card key={a.id} className={styles.account}>
            <div className={styles.top}>
              <span className={styles.icon} aria-hidden="true">
                {KIND_ICON[a.kind]}
              </span>
              <div className={styles.ident}>
                <h2 className={styles.name}>{a.name}</h2>
                <p className={`${page.muted} ${page.small}`}>
                  {a.institution} · {a.kind} ···· {a.mask}
                </p>
              </div>
              {a.kind === "Paper" && <Chip tone="neutral">Simulated</Chip>}
            </div>

            <div className={styles.balance}>
              <Money value={a.balance} size="lg" />
              <Money value={a.dayChange} mode="signed" size="sm" className={styles.change} />
            </div>

            <dl className={styles.details}>
              <div>
                <dt>Buying power</dt>
                <dd className="num">{formatUsd(a.buyingPower)}</dd>
              </div>
              <div>
                <dt>Last synced</dt>
                <dd>
                  <time dateTime={a.lastSynced}>{formatRelative(a.lastSynced, AS_OF)}</time>
                </dd>
              </div>
            </dl>

            <div className={styles.footer}>
              {a.status === "Connected" ? (
                <span className={styles.status}>
                  <span className={styles.dot} aria-hidden="true" />
                  Connected
                </span>
              ) : (
                <span className={`${styles.status} ${styles.attention}`}>
                  <AlertCircle size={14} aria-hidden="true" />
                  Re-authentication required
                </span>
              )}
              <Button variant="ghost" icon={<RefreshCw size={14} />} aria-label={`Sync ${a.name} now`}>
                Sync
              </Button>
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}
