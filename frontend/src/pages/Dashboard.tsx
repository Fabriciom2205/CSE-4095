import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../data/api";
import { AS_OF } from "../data/mock";
import { useAsync } from "../hooks/useAsync";
import { Card } from "../components/ui/Card";
import { Money } from "../components/ui/Money";
import { SegmentedControl } from "../components/ui/SegmentedControl";
import { StatTile } from "../components/ui/StatTile";
import { TradeList } from "../components/ui/TradeList";
import { TrendChart } from "../components/charts/TrendChart";
import { AllocationChart } from "../components/charts/AllocationChart";
import { PnlBars } from "../components/charts/PnlBars";
import { formatSignedPct, formatSignedUsd, formatUsd } from "../lib/format";
import page from "./page.module.css";
import styles from "./Dashboard.module.css";

const RANGES = ["30D", "90D", "1Y"] as const;
type Range = (typeof RANGES)[number];
const RANGE_DAYS: Record<Range, number> = { "30D": 30, "90D": 90, "1Y": 365 };

async function loadDashboard() {
  const [history, positions, accounts, trades, pnl] = await Promise.all([
    api.getPortfolioHistory(),
    api.getPositions(),
    api.getAccounts(),
    api.getTrades(),
    api.getMonthlyPnl(),
  ]);
  return { history, positions, accounts, trades, pnl };
}

export function Dashboard() {
  const { data } = useAsync(loadDashboard);
  const [range, setRange] = useState<Range>("90D");

  const derived = useMemo(() => {
    if (!data) return null;
    const { history, positions, accounts, pnl } = data;
    const series = history.slice(-(RANGE_DAYS[range] + 1));
    const current = history[history.length - 1].value;
    const rangeChange = current - series[0].value;
    const realAccounts = accounts.filter((a) => a.kind !== "Paper");
    const dayChange = realAccounts.reduce((s, a) => s + a.dayChange, 0);
    const cash = realAccounts.reduce((s, a) => s + a.buyingPower, 0);
    const marketValue = positions.reduce((s, p) => s + p.quantity * p.lastPrice, 0);
    const costBasis = positions.reduce((s, p) => s + p.quantity * p.avgCost, 0);
    const bySector = new Map<string, number>();
    for (const p of positions) bySector.set(p.sector, (bySector.get(p.sector) ?? 0) + p.quantity * p.lastPrice);
    const allocation = [...bySector.entries()]
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value);
    const month = pnl[pnl.length - 1];
    const movers = [...positions].sort((a, b) => Math.abs(b.dayChangePct) - Math.abs(a.dayChangePct)).slice(0, 4);
    return { series, current, rangeChange, dayChange, cash, marketValue, costBasis, allocation, month, movers };
  }, [data, range]);

  if (!data || !derived) return <p className={page.loading}>Loading portfolio…</p>;

  const { series, current, rangeChange, dayChange, cash, marketValue, costBasis, allocation, month, movers } = derived;
  const rangePct = rangeChange / (current - rangeChange);

  return (
    <div className={page.stack}>
      <div className={page.header}>
        <div>
          <h1 className={page.title}>Dashboard</h1>
          <p className={page.lede}>
            As of {AS_OF.toLocaleString("en-US", { dateStyle: "medium", timeStyle: "short" })} ET
          </p>
        </div>
      </div>

      <div className={styles.topGrid}>
        <Card className={styles.balanceCard}>
          <p className={styles.eyebrow}>Net liquidation value</p>
          <Money value={current} size="display" />
          <p className={styles.dayLine}>
            <Money value={dayChange} mode="signed" size="sm" />
            <span className={page.muted}> today</span>
          </p>
          <div className={styles.balanceStats}>
            <StatTile label="Invested" value={<Money value={marketValue} />} />
            <StatTile label="Buying power" value={<Money value={cash} />} />
            <StatTile
              label="Unrealized"
              value={<Money value={marketValue - costBasis} mode="signed" />}
              detail={formatSignedPct((marketValue - costBasis) / costBasis)}
            />
          </div>
        </Card>

        <Card
          title="Portfolio value"
          subtitle={`${formatSignedUsd(rangeChange)} (${formatSignedPct(rangePct)}) over ${range}`}
          action={<SegmentedControl options={RANGES} value={range} onChange={setRange} label="Chart range" />}
          className={styles.trendCard}
        >
          <TrendChart
            data={series}
            label={`Portfolio value over ${range}, from ${formatUsd(series[0].value)} to ${formatUsd(current)}`}
          />
        </Card>
      </div>

      <div className={page.grid3}>
        <Card title="This month" subtitle="Realized vs. unrealized P&L">
          <div className={styles.monthStats}>
            <StatTile label="Realized" value={<Money value={month.realized} mode="signed" size="lg" />} />
            <StatTile label="Unrealized" value={<Money value={month.unrealized} mode="signed" size="lg" />} />
          </div>
          <PnlBars data={data.pnl} height={160} />
        </Card>

        <Card title="Allocation" subtitle="Market value by sector">
          <AllocationChart data={allocation} />
        </Card>

        <Card title="Top movers" subtitle="Largest moves today">
          <ul className={styles.movers}>
            {movers.map((p) => (
              <li key={p.symbol} className={styles.mover}>
                <div>
                  <div className={styles.moverSymbol}>{p.symbol}</div>
                  <div className={`${page.muted} ${page.small}`}>{p.name}</div>
                </div>
                <div className={styles.moverRight}>
                  <Money value={p.lastPrice} size="sm" />
                  <Money value={p.dayChangePct} percent size="sm" />
                </div>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card
        title="Recent trades"
        action={
          <Link to="/trades" className={page.link}>
            View all
          </Link>
        }
      >
        <TradeList trades={data.trades.slice(0, 6)} accounts={data.accounts} />
      </Card>
    </div>
  );
}
