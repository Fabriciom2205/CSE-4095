import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { BottomTabBar } from "./BottomTabBar";
import { useTheme } from "../../hooks/useTheme";
import styles from "./AppShell.module.css";

export function AppShell() {
  const { theme, toggle } = useTheme();
  return (
    <>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <Sidebar />
      <div className={styles.column}>
        <TopBar theme={theme} onToggleTheme={toggle} />
        <main id="main" tabIndex={-1} className={styles.main}>
          <Outlet />
        </main>
      </div>
      <BottomTabBar />
    </>
  );
}
