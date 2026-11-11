import { useDeferredValue, useState } from "react";
import { ExternalLink, FileSearch, Search, Sparkles } from "lucide-react";
import { api } from "../data/api";
import { useAsync } from "../hooks/useAsync";
import { Card } from "../components/ui/Card";
import { Chip } from "../components/ui/Chip";
import { EmptyState } from "../components/ui/EmptyState";
import { formatDate } from "../lib/format";
import page from "./page.module.css";
import styles from "./Research.module.css";

export function Research() {
  const [query, setQuery] = useState("");
  const deferred = useDeferredValue(query);
  const { data: filings } = useAsync(() => api.searchFilings(deferred), [deferred]);

  return (
    <div className={page.stack}>
      <div className={page.header}>
        <div>
          <h1 className={page.title}>Research</h1>
          <p className={page.lede}>Recent SEC EDGAR filings for holdings. Search by ticker, company, form type, or keyword.</p>
        </div>
      </div>

      <div className={styles.notice} role="note">
        <Sparkles size={16} aria-hidden="true" />
        <span>
          Sample data: these filings and summaries are made up for the demo and are not real SEC disclosures. The live
          version will query the python-brain SEC EDGAR agent for full-text search and filing summaries.
        </span>
      </div>

      <div className={styles.search}>
        <Search size={18} className={styles.searchIcon} aria-hidden="true" />
        <label htmlFor="filing-search" className="visually-hidden">
          Search filings
        </label>
        <input
          id="filing-search"
          type="search"
          placeholder="e.g. NVDA, 10-Q, buyback"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className={styles.input}
        />
      </div>

      {!filings ? (
        <p className={page.loading}>Searching…</p>
      ) : filings.length === 0 ? (
        <Card>
          <EmptyState icon={<FileSearch size={20} />} title={`No filings match “${deferred}”`}>
            Try a ticker such as AAPL or a form type such as 8-K.
          </EmptyState>
        </Card>
      ) : (
        <ul className={styles.list} aria-live="polite">
          {filings.map((f) => (
            <li key={f.id}>
              <Card className={styles.filing}>
                <div className={styles.meta}>
                  <span className={styles.ticker}>{f.symbol}</span>
                  <Chip tone={f.form === "8-K" ? "accent" : "neutral"}>{f.form}</Chip>
                  <time dateTime={f.filedAt} className={`${page.muted} ${page.small}`}>
                    Filed {formatDate(`${f.filedAt}T12:00:00`)}
                  </time>
                </div>
                <h2 className={styles.title}>{f.title}</h2>
                <p className={`${page.muted} ${page.small}`}>{f.company}</p>
                <p className={styles.summary}>{f.summary}</p>
                <a href={f.url} target="_blank" rel="noreferrer" className={page.link}>
                  View on EDGAR <ExternalLink size={13} aria-hidden="true" />
                  <span className="visually-hidden"> (opens in a new tab)</span>
                </a>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
