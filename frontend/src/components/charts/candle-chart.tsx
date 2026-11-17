"use client";

import {
  CandlestickSeries,
  ColorType,
  createChart,
  CrosshairMode,
  HistogramSeries,
  type IChartApi,
  LineSeries,
  LineStyle,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

import type { Bar, RankPoint } from "@/lib/api";
import { day, pct, price, volume as fmtVol } from "@/lib/format";
import { bollinger, linearRegression, macd, rsi, type Series, sma } from "@/lib/indicators";
import { useSession } from "@/lib/session";

import { cssColor, vnPrice } from "./theme";

const ts = (iso: string) => (Date.parse(iso + "T00:00:00Z") / 1000) as UTCTimestamp;

export type IndicatorId = "ma20" | "ma50" | "ma200" | "bb" | "lr" | "rank" | "rsi" | "macd";

export const INDICATORS: { id: IndicatorId; label: string; hint: string; swatch: string; pane?: boolean }[] = [
  { id: "ma20", label: "MA20", hint: "Trung bình động 20 phiên (khoảng 1 tháng)", swatch: "bg-floor" },
  { id: "ma50", label: "MA50", hint: "Trung bình động 50 phiên (khoảng 1 quý)", swatch: "bg-ceil" },
  { id: "ma200", label: "MA200", hint: "Trung bình động 200 phiên, xu hướng dài hạn", swatch: "bg-ref" },
  { id: "bb", label: "Dải Bollinger", hint: "20 phiên, ±2 độ lệch chuẩn", swatch: "bg-ink-3" },
  { id: "lr", label: "Hồi quy tuyến tính", hint: "Đường xu hướng trên khoảng đang xem, kênh ±2σ", swatch: "bg-brand" },
  { id: "rank", label: "Hạng AI", hint: "Hạng Quorum theo từng phiên, hạng 1 ở trên", swatch: "bg-brand", pane: true },
  { id: "rsi", label: "RSI (14)", hint: "Trên 70 là quá mua, dưới 30 là quá bán", swatch: "bg-ceil", pane: true },
  { id: "macd", label: "MACD (12, 26, 9)", hint: "Đường MACD, đường tín hiệu và histogram", swatch: "bg-floor", pane: true },
];

const PANE_H = 110;

interface Legend {
  label: string;
  value: string;
  color: string;
}

/**
 * Price chart: candles + volume, optional overlays (MA, Bollinger, linear regression)
 * and optional panes underneath (AI rank, RSI, MACD).
 * `bars` should include extra history before the visible window so long averages are defined;
 * `visible` is how many of the latest sessions to show.
 */
export function CandleChart({
  bars,
  ranks,
  visible = 130,
  indicators = ["rank"],
  height = 420,
}: {
  bars: Bar[];
  ranks?: RankPoint[];
  visible?: number;
  indicators?: IndicatorId[];
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const { dark } = useSession();
  const on = useMemo(() => new Set(indicators), [indicators]);
  const hasRank = on.has("rank") && !!ranks && ranks.length > 1;
  const panes = (hasRank ? 1 : 0) + (on.has("rsi") ? 1 : 0) + (on.has("macd") ? 1 : 0);
  const total = height + panes * PANE_H;

  const calc = useMemo(() => {
    const c = bars.map((b) => b.close);
    const win = Math.max(20, Math.min(visible, bars.length));
    return {
      ma20: sma(c, 20),
      ma50: sma(c, 50),
      ma200: sma(c, 200),
      bb: bollinger(c, 20, 2),
      lr: bars.length > 5 ? linearRegression(c, win) : null,
      rsi: rsi(c, 14),
      macd: macd(c),
    };
  }, [bars, visible]);

  const rankMap = useMemo(() => new Map((ranks ?? []).map((r) => [r.as_of, r.rank])), [ranks]);

  useEffect(() => {
    if (!ref.current || bars.length === 0) return;
    const up = cssColor("up");
    const down = cssColor("down");
    const chart = createChart(ref.current, {
      height: total,
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: cssColor("surface") },
        textColor: cssColor("ink-2"),
        fontFamily: '"Be Vietnam Pro", system-ui, sans-serif',
        fontSize: 11,
        attributionLogo: false,
        panes: { separatorColor: cssColor("line"), separatorHoverColor: cssColor("line") },
      },
      grid: { vertLines: { color: cssColor("line-soft") }, horzLines: { color: cssColor("line-soft") } },
      rightPriceScale: { borderColor: cssColor("line") },
      timeScale: { borderColor: cssColor("line"), rightOffset: 2, barSpacing: 7 },
      crosshair: { mode: CrosshairMode.Normal },
      localization: { dateFormat: "dd/MM/yyyy", locale: "vi-VN" },
    });
    chartRef.current = chart;
    const t = bars.map((b) => ts(b.date));
    const line = (s: Series, from = 0) =>
      s.map((v, i) => (v == null ? { time: t[i + from] } : { time: t[i + from], value: v }));
    const quiet = { lastValueVisible: false, priceLineVisible: false, crosshairMarkerVisible: false } as const;
    const quietP = { ...quiet, priceFormat: { type: "custom" as const, formatter: (v: number) => vnPrice(v), minMove: 0.01 } };

    const pf = { type: "custom" as const, formatter: (v: number) => vnPrice(v), minMove: 0.01 };
    const candles = chart.addSeries(CandlestickSeries, { priceFormat: pf, upColor: up, downColor: down, wickUpColor: up, wickDownColor: down, borderVisible: false });
    candles.setData(bars.map((b, i) => ({ time: t[i], open: b.open, high: b.high, low: b.low, close: b.close })));

    const vol = chart.addSeries(HistogramSeries, { priceScaleId: "vol", priceFormat: { type: "volume" }, ...quiet });
    chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    vol.setData(bars.map((b, i) => ({ time: t[i], value: b.volume, color: i > 0 && b.close < bars[i - 1].close ? cssColor("down", 0.3) : cssColor("up", 0.3) })));

    if (on.has("bb")) {
      const c = cssColor("ink-3");
      chart.addSeries(LineSeries, { color: c, lineWidth: 1, ...quietP }).setData(line(calc.bb.upper));
      chart.addSeries(LineSeries, { color: c, lineWidth: 1, ...quietP }).setData(line(calc.bb.lower));
      chart.addSeries(LineSeries, { color: c, lineWidth: 1, lineStyle: LineStyle.Dotted, ...quietP }).setData(line(calc.bb.mid));
    }
    if (on.has("ma20")) chart.addSeries(LineSeries, { color: cssColor("floor"), lineWidth: 2, ...quietP }).setData(line(calc.ma20));
    if (on.has("ma50")) chart.addSeries(LineSeries, { color: cssColor("ceil"), lineWidth: 2, ...quietP }).setData(line(calc.ma50));
    if (on.has("ma200")) chart.addSeries(LineSeries, { color: cssColor("ref"), lineWidth: 2, ...quietP }).setData(line(calc.ma200));
    if (on.has("lr") && calc.lr) {
      const { offset, fit, upper, lower } = calc.lr;
      const c = cssColor("brand");
      chart.addSeries(LineSeries, { color: c, lineWidth: 2, ...quietP }).setData(line(fit, offset));
      chart.addSeries(LineSeries, { color: cssColor("brand", 0.55), lineWidth: 1, lineStyle: LineStyle.Dashed, ...quietP }).setData(line(upper, offset));
      chart.addSeries(LineSeries, { color: cssColor("brand", 0.55), lineWidth: 1, lineStyle: LineStyle.Dashed, ...quietP }).setData(line(lower, offset));
    }

    let pane = 0;
    if (hasRank) {
      pane += 1;
      const first = bars[0].date;
      const pts = (ranks ?? []).filter((r) => r.as_of >= first);
      const s = chart.addSeries(
        LineSeries,
        { color: cssColor("brand"), lineWidth: 1, priceFormat: { type: "custom", formatter: (v: number) => `#${Math.round(-v)}`, minMove: 1 }, priceLineVisible: false },
        pane,
      );
      s.setData(pts.map((r) => ({ time: ts(r.as_of), value: -r.rank })));
      s.createPriceLine({ price: -5, color: cssColor("brand", 0.5), lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: "top 5" });
    }
    if (on.has("rsi")) {
      pane += 1;
      const s = chart.addSeries(LineSeries, { color: cssColor("ceil"), lineWidth: 1, priceLineVisible: false, priceFormat: { type: "custom", formatter: (v: number) => v.toFixed(0), minMove: 1 } }, pane);
      s.setData(line(calc.rsi));
      [70, 30].forEach((p) => s.createPriceLine({ price: p, color: cssColor("ink-3"), lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: true, title: "" }));
    }
    if (on.has("macd")) {
      pane += 1;
      const fmt = { type: "custom" as const, formatter: (v: number) => v.toFixed(2), minMove: 0.01 };
      chart
        .addSeries(HistogramSeries, { priceFormat: fmt, ...quiet }, pane)
        .setData(calc.macd.hist.map((v, i) => (v == null ? { time: t[i] } : { time: t[i], value: v, color: v >= 0 ? cssColor("up", 0.5) : cssColor("down", 0.5) })));
      chart.addSeries(LineSeries, { color: cssColor("floor"), lineWidth: 1, priceFormat: fmt, ...quiet }, pane).setData(line(calc.macd.line));
      chart.addSeries(LineSeries, { color: cssColor("ref"), lineWidth: 1, priceFormat: fmt, ...quiet }, pane).setData(line(calc.macd.signal));
    }
    const ps = chart.panes();
    if (ps.length > 1) {
      ps[0].setStretchFactor(height / PANE_H);
      for (let i = 1; i < ps.length; i++) ps[i].setStretchFactor(1);
    }

    const byTime = new Map(t.map((x, i) => [x, i]));
    chart.subscribeCrosshairMove((p) => {
      const i = p.time ? byTime.get(p.time as UTCTimestamp) : undefined;
      setHoverIdx(i ?? null);
    });
    chart.timeScale().setVisibleLogicalRange({ from: Math.max(0, bars.length - visible), to: bars.length + 2 });
    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, ranks, visible, on, calc, hasRank, total, dark]);

  const i = hoverIdx ?? bars.length - 1;
  const b = bars[i];
  if (!b) return <div style={{ height: total }} />;
  const chg = i > 0 ? b.close / bars[i - 1].close - 1 : null;
  const f = (v: number | null | undefined) => (v == null ? "–" : price(v));
  const legend: Legend[] = [];
  if (on.has("ma20")) legend.push({ label: "MA20", value: f(calc.ma20[i]), color: "text-floor" });
  if (on.has("ma50")) legend.push({ label: "MA50", value: f(calc.ma50[i]), color: "text-ceil" });
  if (on.has("ma200")) legend.push({ label: "MA200", value: f(calc.ma200[i]), color: "text-ref" });
  if (on.has("bb")) legend.push({ label: "BB", value: `${f(calc.bb.lower[i])} – ${f(calc.bb.upper[i])}`, color: "text-ink-2" });
  if (on.has("lr") && calc.lr)
    legend.push({
      label: `Xu hướng ${Math.min(visible, bars.length)} phiên`,
      value: `${calc.lr.slope >= 0 ? "+" : ""}${(calc.lr.slope * 100).toFixed(2)}%/phiên, R² ${calc.lr.r2.toFixed(2)}`,
      color: "text-brand",
    });
  if (on.has("rsi")) legend.push({ label: "RSI", value: calc.rsi[i] == null ? "–" : (calc.rsi[i] as number).toFixed(1), color: "text-ceil" });
  if (on.has("macd"))
    legend.push({
      label: "MACD",
      value: calc.macd.line[i] == null ? "–" : `${(calc.macd.line[i] as number).toFixed(2)} / ${calc.macd.signal[i] == null ? "–" : (calc.macd.signal[i] as number).toFixed(2)}`,
      color: "text-floor",
    });
  const rank = rankMap.get(b.date);

  return (
    <div className="relative">
      <div className="num pointer-events-none absolute left-2 top-1.5 z-10 max-w-[calc(100%-70px)] bg-surface/85 px-1 text-xs text-ink-2">
        <div className="flex flex-wrap gap-x-3">
          <span className="text-ink">{day(b.date)}</span>
          <span>Mở {price(b.open)}</span>
          <span>Cao {price(b.high)}</span>
          <span>Thấp {price(b.low)}</span>
          <span>
            Đóng <span className="text-ink">{price(b.close)}</span>
          </span>
          <span className={chg == null ? "" : chg >= 0 ? "text-up" : "text-down"}>{pct(chg)}</span>
          <span>KL {fmtVol(b.volume)}</span>
          {hasRank && rank != null && <span className="text-brand">Hạng AI {rank}</span>}
        </div>
        {legend.length > 0 && (
          <div className="mt-0.5 flex flex-wrap gap-x-3">
            {legend.map((l) => (
              <span key={l.label}>
                <span className={l.color}>{l.label}</span> {l.value}
              </span>
            ))}
          </div>
        )}
      </div>
      <div ref={ref} style={{ height: total }} />
    </div>
  );
}

/** Dropdown with one checkbox per indicator. */
export function IndicatorMenu({ value, onChange }: { value: IndicatorId[]; onChange: (v: IndicatorId[]) => void }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === "Escape" : !box.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);
  const toggle = (id: IndicatorId) => onChange(value.includes(id) ? value.filter((x) => x !== id) : [...value, id]);
  const group = (title: string, items: typeof INDICATORS) => (
    <fieldset className="py-1.5">
      <legend className="px-3 pb-1 text-2xs text-ink-3">{title}</legend>
      {items.map((it) => (
        <label key={it.id} className="flex cursor-pointer items-start gap-2.5 px-3 py-1.5 hover:bg-sunken">
          <input type="checkbox" checked={value.includes(it.id)} onChange={() => toggle(it.id)} className="mt-0.5 accent-[rgb(var(--brand))]" />
          <span className={"mt-1.5 h-0.5 w-3 shrink-0 " + it.swatch} aria-hidden />
          <span className="min-w-0">
            <span className="block text-sm text-ink">{it.label}</span>
            <span className="block text-2xs text-ink-3">{it.hint}</span>
          </span>
        </label>
      ))}
    </fieldset>
  );
  return (
    <div ref={box} className="relative">
      <button type="button" className="btn h-7 text-xs" aria-expanded={open} aria-haspopup="true" onClick={() => setOpen((o) => !o)}>
        Chỉ báo{value.length ? ` (${value.length})` : ""}
        <ChevronDown size={14} aria-hidden />
      </button>
      {open && (
        <div className="absolute right-0 top-8 z-30 w-[330px] border border-line bg-surface shadow-[0_6px_20px_rgb(0_0_0/0.12)]">
          {group("Vẽ trên biểu đồ giá", INDICATORS.filter((x) => !x.pane))}
          <div className="border-t border-line-soft" />
          {group("Khung riêng bên dưới", INDICATORS.filter((x) => x.pane))}
          {value.length > 0 && (
            <div className="border-t border-line-soft px-3 py-2 text-right">
              <button type="button" className="text-xs text-ink-2 hover:text-brand" onClick={() => onChange([])}>
                Bỏ chọn tất cả
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
