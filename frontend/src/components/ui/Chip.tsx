import type { ReactNode } from "react";
import styles from "./Chip.module.css";

interface ChipProps {
  children: ReactNode;
  /** When provided, the chip is a toggle button. */
  selected?: boolean;
  onClick?: () => void;
  tone?: "neutral" | "gain" | "loss" | "warning" | "accent";
}

export function Chip({ children, selected, onClick, tone = "neutral" }: ChipProps) {
  if (onClick) {
    return (
      <button
        type="button"
        className={[styles.chip, styles.toggle, selected ? styles.selected : ""].join(" ")}
        aria-pressed={selected}
        onClick={onClick}
      >
        {children}
      </button>
    );
  }
  return <span className={[styles.chip, styles[tone]].join(" ")}>{children}</span>;
}
