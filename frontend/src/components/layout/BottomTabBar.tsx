import { NavLink } from "react-router-dom";
import { navItems } from "./nav";
import styles from "./BottomTabBar.module.css";

export function BottomTabBar() {
  return (
    <nav aria-label="Primary" className={styles.bar}>
      <ul className={styles.list}>
        {navItems.map(({ to, label, icon: Icon }) => (
          <li key={to}>
            <NavLink
              to={to}
              end={to === "/"}
              className={({ isActive }) => [styles.tab, isActive ? styles.active : ""].join(" ")}
            >
              <Icon size={20} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
