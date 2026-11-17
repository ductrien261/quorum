/** Small inline charts for tables: no axes, no interaction. */

export function Sparkline({ values, refPrice, width = 84, height = 24 }: { values: number[]; refPrice?: number | null; width?: number; height?: number }) {
  if (values.length < 2) return <span className="inline-block" style={{ width, height }} />;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (i: number) => (i / (values.length - 1)) * (width - 2) + 1;
  const y = (v: number) => height - 2 - ((v - min) / span) * (height - 4);
  const d = values.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
  const up = values[values.length - 1] >= values[0];
  const color = up ? "rgb(var(--up))" : "rgb(var(--down))";
  const area = `${d}L${x(values.length - 1).toFixed(1)},${height}L${x(0).toFixed(1)},${height}Z`;
  const last = values.length - 1;
  return (
    <svg width={width} height={height} className="block" aria-hidden>
      <path d={area} fill={color} opacity={0.12} />
      {refPrice != null && refPrice >= min && refPrice <= max && (
        <line x1={0} x2={width} y1={y(refPrice)} y2={y(refPrice)} stroke="rgb(var(--ref))" strokeWidth={1} strokeDasharray="2 2" />
      )}
      <path d={d} fill="none" stroke={color} strokeWidth={1.25} />
      <rect x={x(last) - 1.5} y={y(values[last]) - 1.5} width={3} height={3} fill={color} />
    </svg>
  );
}

/**
 * Where today's trading sat inside the floor..ceiling band:
 * grey track = allowed band, bar = low..high, tick = reference, square = close.
 */
export function DayRange({
  low,
  high,
  close,
  refPrice,
  floor,
  ceil,
  width = 96,
}: {
  low: number | null;
  high: number | null;
  close: number | null;
  refPrice: number | null;
  floor: number | null;
  ceil: number | null;
  width?: number;
}) {
  if (low == null || high == null || close == null) return null;
  const lo = floor ?? low;
  const hi = ceil ?? high;
  const span = hi - lo || 1;
  const pos = (v: number) => Math.max(0, Math.min(1, (v - lo) / span)) * width;
  const color =
    refPrice == null || Math.abs(close - refPrice) < 0.005 ? "rgb(var(--ref))" : close > refPrice ? "rgb(var(--up))" : "rgb(var(--down))";
  return (
    <svg width={width} height={14} className="block" aria-hidden>
      <rect x={0} y={6} width={width} height={2} fill="rgb(var(--line))" />
      <rect x={pos(low)} y={4} width={Math.max(2, pos(high) - pos(low))} height={6} fill={color} opacity={0.45} />
      {refPrice != null && <rect x={pos(refPrice) - 0.5} y={1} width={1} height={12} fill="rgb(var(--ref))" />}
      <rect x={pos(close) - 2.5} y={4.5} width={5} height={5} fill={color} />
    </svg>
  );
}
