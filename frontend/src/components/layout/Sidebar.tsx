import { NavLink } from "react-router-dom";
import { navItems } from "./nav";
import { Logo } from "../ui/Logo";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <Logo className={styles.seal} />
        <span className={styles.name}>The Monroe Fund</span>
      </div>
      <nav aria-label="Primary">
        <ul className={styles.list}>
          {navItems.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === "/"}
                className={({ isActive }) => [styles.link, isActive ? styles.active : ""].join(" ")}
              >
                <Icon size={18} strokeWidth={2} aria-hidden="true" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className={styles.footer}>
        <span className={styles.dot} aria-hidden="true" />
        Mock data &middot; not live
      </div>
    </aside>
  );
}
