import { useEffect, useState } from "react";

const TOKENS = {
  gain: "--color-gain",
  loss: "--color-loss",
  accent: "--color-accent",
  grid: "--chart-grid",
  text: "--color-text",
  textSecondary: "--color-text-secondary",
  surface: "--color-surface",
  border: "--color-border",
  series1: "--chart-1",
  series2: "--chart-2",
  series3: "--chart-3",
  series4: "--chart-4",
  series5: "--chart-5",
  series6: "--chart-6",
} as const;

export type ChartColors = Record<keyof typeof TOKENS, string>;

function read(): ChartColors {
  const css = getComputedStyle(document.documentElement);
  const out = {} as ChartColors;
  for (const [key, token] of Object.entries(TOKENS)) {
    out[key as keyof ChartColors] = css.getPropertyValue(token).trim();
  }
  return out;
}

/**
 * Recharts writes colors as SVG attributes, where CSS var() does not resolve,
 * so read the resolved token values and refresh them when the theme changes.
 */
export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(read);

  useEffect(() => {
    const update = () => setColors(read());
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
    mq?.addEventListener("change", update);
    return () => {
      observer.disconnect();
      mq?.removeEventListener("change", update);
    };
  }, []);

  return colors;
}

export const seriesColors = (c: ChartColors) => [c.series1, c.series2, c.series3, c.series4, c.series5, c.series6];
