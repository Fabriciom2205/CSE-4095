import type { ReactNode } from "react";
import styles from "./StatTile.module.css";

interface StatTileProps {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
}

/** Small label + figure pair used inside cards. */
export function StatTile({ label, value, detail }: StatTileProps) {
  return (
    <div className={styles.tile}>
      <span className={styles.label}>{label}</span>
      <span className={styles.value}>{value}</span>
      {detail && <span className={styles.detail}>{detail}</span>}
    </div>
  );
}
