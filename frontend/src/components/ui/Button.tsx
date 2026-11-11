import type { ButtonHTMLAttributes, ReactNode } from "react";
import styles from "./Button.module.css";

type Variant = "primary" | "secondary" | "ghost";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  icon?: ReactNode;
  /** Icon-only button: requires aria-label. */
  iconOnly?: boolean;
}

export function Button({ variant = "secondary", icon, iconOnly, className, children, type = "button", ...rest }: ButtonProps) {
  return (
    <button
      type={type}
      className={[styles.button, styles[variant], iconOnly ? styles.iconOnly : "", className ?? ""].join(" ")}
      {...rest}
    >
      {icon && <span className={styles.icon} aria-hidden="true">{icon}</span>}
      {!iconOnly && children}
    </button>
  );
}
