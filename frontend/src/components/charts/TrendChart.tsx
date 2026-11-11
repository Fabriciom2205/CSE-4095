import { useId } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, type TooltipProps } from "recharts";
import type { PortfolioPoint } from "../../types";
import { useChartColors } from "../../hooks/useChartColors";
import { formatDate, formatShortDate, formatUsd, formatUsdCompact } from "../../lib/format";
import styles from "./charts.module.css";

interface TrendChartProps {
  data: PortfolioPoint[];
  /** Accessible description of what the chart shows. */
  label: string;
  height?: number;
}

function ChartTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload as PortfolioPoint;
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>{formatDate(point.date)}</div>
      <div className="num">{formatUsd(point.value)}</div>
    </div>
  );
}

/** Portfolio value over time. Line is green when the period is up, red when down. */
export function TrendChart({ data, label, height = 260 }: TrendChartProps) {
  const c = useChartColors();
  const gradientId = useId().replace(/:/g, "");
  const up = data.length < 2 || data[data.length - 1].value >= data[0].value;
  const stroke = up ? c.gain : c.loss;

  return (
    <div className={styles.chart} role="img" aria-label={label} style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={stroke} stopOpacity={0.18} />
              <stop offset="100%" stopColor={stroke} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke={c.grid} vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={formatShortDate}
            tick={{ fill: c.textSecondary, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => formatUsdCompact(v)}
            tick={{ fill: c.textSecondary, fontSize: 12 }}
            axisLine={false}
            tickLine={false}
            width={64}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: c.border }} />
          <Area
            type="monotone"
            dataKey="value"
            stroke={stroke}
            strokeWidth={2}
            fill={`url(#${gradientId})`}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: c.surface }}
            isAnimationActive={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
