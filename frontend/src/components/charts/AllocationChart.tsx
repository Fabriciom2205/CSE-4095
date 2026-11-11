import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip, type TooltipProps } from "recharts";
import { seriesColors, useChartColors } from "../../hooks/useChartColors";
import { formatPct, formatUsd } from "../../lib/format";
import styles from "./charts.module.css";

export interface AllocationSlice {
  name: string;
  value: number;
}

function SliceTooltip({ active, payload }: TooltipProps<number, string>) {
  if (!active || !payload?.length) return null;
  const p = payload[0];
  return (
    <div className={styles.tooltip}>
      <div className={styles.tooltipLabel}>{p.name}</div>
      <div className="num">{formatUsd(Number(p.value))}</div>
    </div>
  );
}

/** Donut plus a legend that doubles as the accessible text alternative. */
export function AllocationChart({ data }: { data: AllocationSlice[] }) {
  const c = useChartColors();
  const palette = seriesColors(c);
  const total = data.reduce((s, d) => s + d.value, 0);

  return (
    <div className={styles.allocation}>
      <div className={styles.donut} aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius="62%"
              outerRadius="100%"
              paddingAngle={1.5}
              stroke={c.surface}
              strokeWidth={2}
              isAnimationActive={false}
            >
              {data.map((d, i) => (
                <Cell key={d.name} fill={palette[i % palette.length]} />
              ))}
            </Pie>
            <Tooltip content={<SliceTooltip />} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className={styles.legend} aria-label="Allocation by sector">
        {data.map((d, i) => (
          <li key={d.name} className={styles.legendRow}>
            <span className={styles.swatch} style={{ background: palette[i % palette.length] }} aria-hidden="true" />
            <span className={styles.legendName}>{d.name}</span>
            <span className={`num ${styles.legendPct}`}>{formatPct(d.value / total)}</span>
            <span className={`num ${styles.legendValue}`}>{formatUsd(d.value)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
