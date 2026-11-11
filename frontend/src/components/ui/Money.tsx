import { formatSignedPct, formatSignedUsd, formatUsd } from "../../lib/format";
import styles from "./Money.module.css";

interface MoneyProps {
  value: number;
  /** "signed" shows +/− and gain/loss color; "plain" is neutral. */
  mode?: "plain" | "signed";
  /** Format as percent (fraction input) instead of USD. */
  percent?: boolean;
  size?: "sm" | "md" | "lg" | "display";
  className?: string;
}

/** Money and percent figures: tabular numerals, sign + color for P&L. */
export function Money({ value, mode = "plain", percent, size = "md", className }: MoneyProps) {
  const text = percent ? formatSignedPct(value) : mode === "signed" ? formatSignedUsd(value) : formatUsd(value);
  const tone = mode === "signed" || percent ? (value > 0 ? styles.gain : value < 0 ? styles.loss : "") : "";
  return <span className={["num", styles.money, styles[size], tone, className ?? ""].join(" ")}>{text}</span>;
}
