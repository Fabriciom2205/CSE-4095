import styles from "./ProgressBar.module.css";

export type LimitStatus = "ok" | "near" | "over";

/** ok below 80% of the limit, near from 80% to 100%, over above it. */
export function limitStatus(ratio: number): LimitStatus {
  if (ratio > 1) return "over";
  if (ratio >= 0.8) return "near";
  return "ok";
}

interface ProgressBarProps {
  /** current / limit; may exceed 1. */
  ratio: number;
  label: string;
  /** Human-readable value, e.g. "41.8% of 40.0%". */
  valueText: string;
}

export function ProgressBar({ ratio, label, valueText }: ProgressBarProps) {
  const status = limitStatus(ratio);
  const pct = Math.round(ratio * 100);
  return (
    <div
      className={styles.track}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.min(pct, 100)}
      aria-valuetext={valueText}
    >
      <div className={[styles.fill, styles[status]].join(" ")} style={{ width: `${Math.min(ratio, 1) * 100}%` }} />
      {/* Tick at the 80% warning threshold. */}
      <div className={styles.tick} style={{ left: "80%" }} aria-hidden="true" />
    </div>
  );
}
