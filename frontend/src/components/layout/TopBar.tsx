import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, Moon, Search, Sun } from "lucide-react";
import { Button } from "../ui/Button";
import { Logo } from "../ui/Logo";
import type { Theme } from "../../hooks/useTheme";
import styles from "./TopBar.module.css";

interface TopBarProps {
  theme: Theme;
  onToggleTheme: () => void;
}

export function TopBar({ theme, onToggleTheme }: TopBarProps) {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    navigate(q ? `/trades?q=${encodeURIComponent(q)}` : "/trades");
  };

  return (
    <header className={styles.bar}>
      <Logo size={32} className={styles.mobileBrand} />
      <form role="search" className={styles.search} onSubmit={onSubmit}>
        <Search size={16} className={styles.searchIcon} aria-hidden="true" />
        <label htmlFor="global-search" className="visually-hidden">
          Search trades by symbol
        </label>
        <input
          id="global-search"
          type="search"
          placeholder="Search symbols, trades…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className={styles.input}
        />
      </form>
      <div className={styles.actions}>
        <span className={styles.market}>
          <span className={styles.marketDot} aria-hidden="true" />
          Market open
        </span>
        <Button
          variant="ghost"
          iconOnly
          aria-label={theme === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          icon={theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
          onClick={onToggleTheme}
        />
        <Button variant="ghost" iconOnly aria-label="Notifications (2 unread)" icon={<Bell size={18} />} />
        <button type="button" className={styles.avatar} aria-label="Open profile menu">
          MF
        </button>
      </div>
    </header>
  );
}
