# Worklog: Frontend Scaffold (React + TypeScript UI with mock data)

* **Date:** 2026-11-11
* **Contributor / Agent:** Claude Code (Opus 5.5)
* **Branch:** test/mcp-server
* **Status:** Completed

---

## Objective
Create the first version of the web client in `frontend/`. The user supplied a personal-finance UI spec. We kept its layout, visual direction and accessibility requirements, adapted the screens to The Monroe Fund trading platform, and used the stack from ARCHITECTURE.md §2.1 (TypeScript + React) instead of the spec's Tailwind.

---

## Changes Implemented
* [`frontend/package.json`](../../frontend/package.json), [`vite.config.ts`](../../frontend/vite.config.ts), [`tsconfig.json`](../../frontend/tsconfig.json), [`index.html`](../../frontend/index.html): Vite + React 18 + strict TypeScript. Dependencies are `react-router-dom`, `recharts`, `lucide-react`, and `@fontsource-variable/inter` (self-hosted font, no CDN). Recharts is split into its own chunk.
* [`frontend/src/styles/tokens.css`](../../frontend/src/styles/tokens.css): design tokens (colors, spacing, radius, shadows) for light and dark themes. Dark applies via `prefers-color-scheme` or `data-theme="dark"`.
* [`frontend/src/styles/global.css`](../../frontend/src/styles/global.css): reset, `:focus-visible` ring, `.num` (tabular numerals), skip link, reduced motion.
* [`frontend/src/types/index.ts`](../../frontend/src/types/index.ts): `Position`, `Trade`, `Account`, `RiskLimit`, `Filing`, `PortfolioPoint`, `MonthlyPnl`.
* [`frontend/src/data/mock.ts`](../../frontend/src/data/mock.ts): deterministic mock data (seeded PRNG, fixed `AS_OF` date).
* [`frontend/src/data/api.ts`](../../frontend/src/data/api.ts): async data layer. **This is the only place to swap mock data for real HTTP/gRPC-web calls.**
* [`frontend/src/hooks/`](../../frontend/src/hooks/): `useAsync`, `useTheme` (persisted toggle), and `useChartColors`, which resolves CSS tokens for Recharts because SVG attributes can't use `var()`.
* [`frontend/src/components/`](../../frontend/src/components/): `layout/` (AppShell, Sidebar, TopBar, BottomTabBar), `ui/` (Card, Button, Chip, Money, ProgressBar, SegmentedControl, StatTile, EmptyState, TradeList), `charts/` (TrendChart, AllocationChart, PnlBars). Every component has a colocated `.module.css` file.
* [`frontend/src/pages/`](../../frontend/src/pages/): Dashboard, Trades (search/side/sector/account/date filters; the table becomes stacked cards on mobile), Risk (limit cards turn amber at 80% and burgundy when over), Accounts, Research (mock SEC filings).
* [`README.md`](../../README.md): added a Frontend section with run instructions.

---

## Key Decisions & Context
* **Domain:** adapted to trading. "Transactions" became Trades, "Budgets" became Risk limits (deterministic pre-trade checks), bank accounts became broker accounts (Alpaca live/paper, IRA, cash sweep), and we added a Research page for SEC filings.
* **Styling:** CSS Modules plus CSS-variable tokens. No Tailwind, per the user, and no extra styling dependency.
* **Colors:** brand accent is burgundy `#7A1F2E` (dark mode `#D9788A`). It's used only for primary buttons, the active nav item, focus rings, and over-limit states. Gains and losses use standard green `#137333` and red `#C5221F` (dark mode `#4CC26A` / `#F26B5E`), always shown with a +/− sign. These values were chosen to meet WCAG AA text contrast on both card backgrounds. The spec's `#2E7D5B`-style green was swapped for a darker standard green to pass contrast.
* **Data:** mock only. python-brain has no HTTP API yet.
* **Paper trading** is excluded from net liquidation totals.

---

## Known Gotchas, Blockers & Environment Issues
* `playwright-cli open` defaults to Chrome, which isn't installed on this machine. Use `playwright-cli open --browser=msedge`.
* Recharts is ~565 kB minified (~160 kB gzip). It has its own chunk, and `chunkSizeWarningLimit` is raised to 700.
* Verified: `npm run build` passes; all 5 routes render at 1440px and 375px (no horizontal scroll); dark mode works; the console shows no errors or warnings; Tab focus is visible.

---

## Next Steps (Handoff Checklist)
* [ ] Add an HTTP endpoint to python-brain (e.g. FastAPI) for SEC search and wire `api.searchFilings` to it
* [ ] Add component/unit tests (Vitest + Testing Library) and a Playwright smoke test for the routes
* [ ] Replace mock positions/accounts with Alpaca data once the gRPC/REST contracts exist
* [ ] Add a lint setup (ESLint + typescript-eslint)
