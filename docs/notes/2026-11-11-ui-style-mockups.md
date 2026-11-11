# Worklog: UI Restyle — Private Ledger + Apple-style Glass

* **Date:** 2026-11-11
* **Contributor / Agent:** Claude Code (Opus 5.5)
* **Branch:** test/mcp-server
* **Status:** Completed

---

## Objective
The user wanted the frontend to look more distinctive. We built live, switchable mockups of two directions, **Private Ledger** and **Swiss Brutalist**. The user picked Ledger and asked to add glass in the style of Apple's Liquid Glass. Ledger is now the only design, and the mockup scaffolding has been removed.

---

## Changes Implemented
* [`frontend/src/styles/tokens.css`](../../frontend/src/styles/tokens.css): Ledger palette in light and dark. Light uses cream paper `#F6F1E7`, ink, burgundy `#7A1F2E`, and brass `#A8864A` (`--color-brass-text` for text). It also sets `--font-display` (Fraunces), square paper corners (`--radius: 2px`), and no card shadows. New glass tokens: `--glass-bg`, `--glass-bg-strong`, `--glass-border`, `--glass-edge`, `--glass-lens`, `--glass-blur`, `--glass-shadow`, `--glass-sheen`, `--radius-glass`, `--radius-lens`, `--chrome-gap`. New `--ambient` / `--grain` give the background soft color.
* [`frontend/src/styles/global.css`](../../frontend/src/styles/global.css):
  * `body::before` draws the fixed ambient color and paper grain.
  * New global `.glass` material: translucent background, backdrop blur/saturate, hairline border, and a specular rim drawn with a masked gradient in `::before`.
  * Fallbacks: no `backdrop-filter` support → denser background; `prefers-reduced-transparency` → solid surface; `forced-colors` → no rim and a system border.
* Glass chrome, applied with `composes: glass from global;`:
  * [Sidebar](../../frontend/src/components/layout/Sidebar.module.css): a floating inset panel; the active link sits on a brighter lens.
  * [TopBar](../../frontend/src/components/layout/TopBar.module.css): sticky floating bar with a capsule search field.
  * [BottomTabBar](../../frontend/src/components/layout/BottomTabBar.module.css): floating iOS-style capsule with a lens on the active tab.
  * [SegmentedControl](../../frontend/src/components/ui/SegmentedControl.module.css): glass capsule; the selected option is a burgundy pill.
  * Chart tooltips in [charts.module.css](../../frontend/src/components/charts/charts.module.css).
* Ledger typography and rules were folded into the base component CSS: Card, StatTile, Money, Button, Chip, ProgressBar, TradeList, and the page/Dashboard/Trades/Risk modules. That covers Fraunces headings and figures, small-caps labels, double rules under headers, dotted row rules, and faint banding on the Trades table.
* [`Monogram.tsx`](../../frontend/src/components/ui/Monogram.tsx): engraved "M" seal, used in the sidebar and the mobile top bar.
* Removed: `style-ledger.css`, `style-brutalist.css`, `hooks/useStyle.ts`, `components/dev/StyleSwitcher`, the `data-style` observer in `useChartColors`, and `@fontsource-variable/space-grotesk`.
* Added dependency: `@fontsource-variable/fraunces@5.3.0`, imported via `opsz.css` so `font-variation-settings: "opsz"` works.

---

## Key Decisions & Context
* **Glass follows Apple's rule: chrome only.** Navigation and controls float above content as glass. Data cards stay on solid paper so figures stay legible. Making the cards glass too would hurt contrast on financial data.
* **Glass needs something to refract.** A flat cream background makes glass look like plain tinted panels, so `--ambient` adds faint burgundy, brass, and green glows behind everything.
* **Paper is square, glass is round.** Content keeps 2px corners. Glass chrome uses `--radius-glass` (22px) and pill shapes.
* `composes` isn't allowed inside `@media`, so `BottomTabBar .bar` composes glass at the top level and stays `display: none` on desktop.
* `--sidebar-width` is now 256px. It includes the 12px `--chrome-gap` on each side of the floating panel.

---

## Known Gotchas, Blockers & Environment Issues
* **Chrome is now installed**, so `playwright-cli open` works with its default browser. The `--browser=msedge` workaround from the scaffold note is no longer needed.
* A dev server was already on 5173, so this session's server ran on 5174.
* Small caps are synthesized: Inter has no `smcp` feature, and Fraunces is only used for display text.
* Verified in Chrome 157: `npm run build` passes. Dashboard renders at 1440px in light and dark, including the scrolled state with content blurring under the top bar and the glass chart tooltip, and at 375px with the floating tab bar. No horizontal scroll and no console errors or warnings.

---

## Follow-up: Mock Data Consistency
The user asked whether the mock data was accurate. It isn't real market data: prices, holdings and filings are all invented. It also contradicted itself across pages. For example, net liquidation was about $100k below invested plus cash, the Risk page showed a $3,120 daily loss on an up day, and tech exposure was "over limit" at a figure that didn't match the allocation chart. Fixed in [`frontend/src/data/mock.ts`](../../frontend/src/data/mock.ts):
* Account balances and day changes are now derived from `positions`. Positions are split 82/18 between the Live and IRA accounts, plus fixed cash, so **net liquidation = market value + cash**, and today's P&L equals the sum of position moves plus the sweep interest.
* `riskLimits` are computed from positions, accounts, portfolio history and today's agent trades. Only the limit values are configuration. Concentration and tech limits were set to 15% / 28%, so the demo still shows one "near" and one "over". All percentages are now **of net liquidation value**, and the descriptions say so.
* The Research page notice now says the filings and summaries are made up and are not real SEC disclosures.
* Still not reconciled (acceptable for a mock): trade history doesn't add up to current positions, trade prices are random ±6% of the last price, and monthly P&L is hand-entered.

---

## Follow-up: Navy Accent, Sailboat Logo, Clearer Glass
* **Accent changed from maroon to navy**, to match the planned logo (a blue sailboat). In [`tokens.css`](../../frontend/src/styles/tokens.css):
  * Light: `--color-accent` `#7a1f2e` → `#1f3a5f`, hover `#162b47`, tint `#e1e8f0`, tint text `#1a3352`.
  * Dark: accent `#e08a98` → `#8fb3de`, hover `#a9c6e8`, tint `#1e2a38`, tint text `#b9cfea`.
  * `--chart-1` follows the accent. `--chart-4` became `#4f7ca8` / `#5e7fa3` so it doesn't blend with the navy.
  * The ambient glow is navy instead of maroon. Brass and cream are unchanged.
  * `index.html` theme-color is now `#1F3A5F`.
* **Over-limit risk state now uses `--color-loss` (red)**, not the accent: the Risk chip, card border, footer text and the ProgressBar `.over` fill. With maroon, the brand color doubled as a warning. Navy doesn't, so a breached limit would have looked calm.
* **Placeholder logo:** [`Logo.tsx`](../../frontend/src/components/ui/Logo.tsx) is a blue sailboat in an engraved ring with a brass waterline. It replaced `Monogram.tsx` in the sidebar and mobile top bar. `public/favicon.svg` is a matching sailboat on a navy tile. Replace both with the final artwork when it's ready.
* **Clearer glass** (per the user):
  * `--glass-bg` alpha 0.58 → 0.3 (light) and 0.55 → 0.3 (dark).
  * `--glass-blur` `blur(22px) saturate(170%)` → `blur(10px) saturate(180%)`.
  * `--glass-border` alpha 0.55 → 0.7 (light) and 0.1 → 0.16 (dark).
  * `--glass-bg-strong` (tooltips) 0.82 / 0.85 → 0.72 / 0.75.

* **Cooler background to go with the navy** (per the user). The warm cream and the oxblood-brown dark mode were swapped for cool tones in `tokens.css`:
  * Light: bg `#eef2f6`, surface `#f9fbfc`, sunken `#e6ecf2`, borders `#d3dce6` / `#b4c1cf`, text `#15202e`, secondary text `#556273`.
  * Dark: bg `#0c1420`, surface `#131d2b`, sunken `#1b2738`, borders `#263447` / `#3a4c63`, text `#e8eef5`, secondary text `#9fb0c3`.
  * The glass tint, shadows, grain and ambient glows are also cooled, and the green glow became sky blue.
  * Brass is kept as the detail color.
  * The hard-coded warm shadows in the Sidebar and TopBar were converted too.

---

## Next Steps (Handoff Checklist)
* [ ] Replace the placeholder sailboat (`Logo.tsx`, `public/favicon.svg`) with final logo artwork
* [ ] Optional polish the user was offered: animated number count-ups, a ticker tape, staggered card fade-in on load
* [ ] Give Trades, Risk, Accounts and Research a quick visual pass in dark mode on mobile (the Dashboard was checked in detail)
* [ ] Frontend tests (Vitest + Playwright smoke test) and ESLint are still in the backlog
