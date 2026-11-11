import { Bar, BarChart, CartesianGrid, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipProps } from "recharts";
import type { MonthlyPnl } from "../../types";
import { useChartColors } from "../../hooks/useChartColors";
import { formatSignedUsd, formatUsdCompact } from "../../lib/format";
import styles from "./charts.module.css";

interface Row extends MonthlyPnl {
  total: number;
}

function PnlTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const r = payload[0].payload as Row;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>{r.month}</div>
      <div className="num">Total {formatSignedUsd(r.total)}</div>
      <div className={`num ${styles.tooltipMuted}`}>Realized {formatSignedUsd(r.realized)}</div>
      <div className={`num ${styles.tooltipMuted}`}>Unrealized {formatSignedUsd(r.unrealized)}</div>
    </div>
  );
}

/** Monthly total P&L bars: green for gains, red for losses. */
export function PnlBars({ data, height = 200 }: { data: MonthlyPnl[]; height?: number }) {
  const c = useChartColors();
  const rows: Row[] = data.map((d) => ({ ...d, total: d.realized + d.unrealized }));
  const summary = rows.map((r) => `${r.month} ${formatSignedUsd(r.total)}`).join(", ");

  return (
    <div className={styles.chart} role="img" aria-label={`Monthly profit and loss: ${summary}`} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={rows} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={c.grid} vertical={false} />
          <XAxis dataKey="month" tick={{ fill: c.textSecondary, fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis
            tickFormatter={(v: number) => formatUsdCompact(v)}
            tick={{ fill: c.textSecondary, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={56}
          />
          <ReferenceLine y={0} stroke={c.border} />
          <Tooltip content={<PnlTooltip />} cursor={{ fill: c.grid, opacity: 0.5 }} />
          <Bar dataKey="total" radius={[4, 4, 4, 4]} maxBarSize={36} isAnimationActive={false}>
            {rows.map((r) => (
              <Cell key={r.month} fill={r.total >= 0 ? c.gain : c.loss} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
