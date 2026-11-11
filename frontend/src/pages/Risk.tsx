import { AlertTriangle, CheckCircle2, OctagonAlert } from "lucide-react";
import { api } from "../data/api";
import { useAsync } from "../hooks/useAsync";
import { Card } from "../components/ui/Card";
import { Chip } from "../components/ui/Chip";
import { ProgressBar, limitStatus, type LimitStatus } from "../components/ui/ProgressBar";
import { formatPct, formatUsd } from "../lib/format";
import type { RiskLimit } from "../types";
import page from "./page.module.css";
import styles from "./Risk.module.css";

const fmt = (n: number, unit: RiskLimit["unit"]) =>
  unit === "usd" ? formatUsd(n) : unit === "pct" ? formatPct(n) : `${n.toFixed(2)}×`;

const STATUS: Record<LimitStatus, { label: string; tone: "neutral" | "warning" | "loss"; icon: JSX.Element }> = {
  ok: { label: "Within limit", tone: "neutral", icon: <CheckCircle2 size={14} aria-hidden="true" /> },
  near: { label: "Near limit", tone: "warning", icon: <AlertTriangle size={14} aria-hidden="true" /> },
  over: { label: "Over limit", tone: "loss", icon: <OctagonAlert size={14} aria-hidden="true" /> },
};

export function Risk() {
  const { data: limits } = useAsync(api.getRiskLimits);
  if (!limits) return <p className={page.loading}>Loading risk limits…</p>;

  const counts = limits.reduce(
    (acc, l) => {
      acc[limitStatus(l.current / l.limit)]++;
      return acc;
    },
    { ok: 0, near: 0, over: 0 } as Record<LimitStatus, number>,
  );

  return (
    <div className={page.stack}>
      <div className={page.header}>
        <div>
          <h1 className={page.title}>Risk limits</h1>
          <p className={page.lede}>
            Deterministic pre-trade checks enforced by the Rust risk engine. Agent orders that would breach a limit are rejected.
          </p>
        </div>
        <div className={styles.counts} aria-label="Limit status summary">
          <Chip tone="neutral">{counts.ok} within</Chip>
          <Chip tone="warning">{counts.near} near</Chip>
          <Chip tone="loss">{counts.over} over</Chip>
        </div>
      </div>

      <div className={page.grid3}>
        {limits.map((l) => {
          const ratio = l.current / l.limit;
          const status = limitStatus(ratio);
          const s = STATUS[status];
          const remaining = l.limit - l.current;
          return (
            <Card key={l.id} className={[styles.limit, styles[status]].join(" ")}>
              <div className={styles.head}>
                <h2 className={styles.label}>{l.label}</h2>
                <Chip tone={s.tone}>
                  {s.icon}
                  {s.label}
                </Chip>
              </div>
              <p className={styles.desc}>{l.description}</p>
              <div className={styles.figures}>
                <span className={`num ${styles.current}`}>{fmt(l.current, l.unit)}</span>
                <span className={`num ${page.muted}`}>of {fmt(l.limit, l.unit)}</span>
              </div>
              <ProgressBar
                ratio={ratio}
                label={l.label}
                valueText={`${fmt(l.current, l.unit)} of ${fmt(l.limit, l.unit)} limit, ${s.label.toLowerCase()}`}
              />
              <p className={`${styles.foot} num`}>
                {remaining >= 0
                  ? `${fmt(remaining, l.unit)} headroom`
                  : `${fmt(-remaining, l.unit)} over — new orders in this bucket are blocked`}
              </p>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
