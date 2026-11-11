import { useId, type ReactNode } from "react";
import styles from "./Card.module.css";

interface CardProps {
  title?: string;
  subtitle?: string;
  /** Content shown at the right of the header (toggle, link, ...). */
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  padded?: boolean;
}

export function Card({ title, subtitle, action, children, className, padded = true }: CardProps) {
  const headingId = useId();
  return (
    <section
      className={[styles.card, padded ? styles.padded : "", className ?? ""].join(" ")}
      aria-labelledby={title ? headingId : undefined}
    >
      {(title || action) && (
        <header className={styles.header}>
          <div>
            {title && (
              <h2 id={headingId} className={styles.title}>
                {title}
              </h2>
            )}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {action && <div className={styles.action}>{action}</div>}
        </header>
      )}
      {children}
    </section>
  );
}
