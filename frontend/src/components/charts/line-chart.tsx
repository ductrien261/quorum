"use client";

import {
  AreaSeries,
  ColorType,
  createChart,
  CrosshairMode,
  LineSeries,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useSession } from "@/lib/session";

import { cssColor } from "./theme";

export interface Series {
  name: string;
  color: string; // token name, e.g. "brand"
  points: { date: string; value: number }[];
  area?: boolean;
  dashed?: boolean;
}

const ts = (iso: string) => (Date.parse(iso + "T00:00:00Z") / 1000) as UTCTimestamp;

export function LineChart({
  series,
  height = 260,
  format = (v: number) => v.toFixed(2),
}: {
  series: Series[];
  height?: number;
  format?: (v: number) => string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { dark } = useSession();

  useEffect(() => {
    if (!ref.current || series.every((s) => s.points.length === 0)) return;
    const chart = createChart(ref.current, {
      height,
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: cssColor("surface") },
        textColor: cssColor("ink-2"),
        fontFamily: '"Be Vietnam Pro", system-ui, sans-serif',
        fontSize: 11,
        attributionLogo: false,
      },
      grid: { vertLines: { visible: false }, horzLines: { color: cssColor("line-soft") } },
      rightPriceScale: { borderColor: cssColor("line") },
      timeScale: { borderColor: cssColor("line") },
      crosshair: { mode: CrosshairMode.Magnet },
      localization: { priceFormatter: format, dateFormat: "dd/MM/yyyy", locale: "vi-VN" },
      handleScroll: false,
      handleScale: false,
    });
    for (const s of series) {
      const color = cssColor(s.color);
      const data = s.points.map((p) => ({ time: ts(p.date), value: p.value }));
      if (s.area) {
        const a = chart.addSeries(AreaSeries, {
          lineColor: color,
          topColor: cssColor(s.color, 0.18),
          bottomColor: cssColor(s.color, 0.01),
          lineWidth: 2,
          priceLineVisible: false,
          title: "",
        });
        a.setData(data);
      } else {
        const l = chart.addSeries(LineSeries, {
          color,
          lineWidth: 2,
          lineStyle: s.dashed ? 2 : 0,
          priceLineVisible: false,
          lastValueVisible: true,
          title: "",
        });
        l.setData(data);
      }
    }
    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [series, height, format, dark]);

  return <div ref={ref} style={{ height }} />;
}
