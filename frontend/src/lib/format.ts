const nf = (min: number, max = min) =>
  new Intl.NumberFormat("vi-VN", { minimumFractionDigits: min, maximumFractionDigits: max });

const f0 = nf(0);
const f1 = nf(1);
const f2 = nf(2);

export function price(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "–";
  return f2.format(v);
}

export function num(v: number | null | undefined, digits = 0): string {
  if (v == null || Number.isNaN(v)) return "–";
  return nf(digits).format(v);
}

export function pct(v: number | null | undefined, digits = 2, signed = true): string {
  if (v == null || Number.isNaN(v)) return "–";
  const s = nf(digits).format(Math.abs(v * 100));
  if (!signed) return `${v < 0 ? "-" : ""}${s}%`;
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${s}%`;
}

export function signed(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return "–";
  return `${v > 0 ? "+" : v < 0 ? "−" : ""}${nf(digits).format(Math.abs(v))}`;
}

export function volume(v: number | null | undefined): string {
  if (v == null) return "–";
  if (v >= 1e6) return `${f2.format(v / 1e6)} tr`;
  if (v >= 1e3) return `${f1.format(v / 1e3)} k`;
  return f0.format(v);
}

/** VND -> "12,5 tỷ" */
export function money(v: number | null | undefined): string {
  if (v == null) return "–";
  if (v >= 1e12) return `${f2.format(v / 1e12)} nghìn tỷ`;
  if (v >= 1e9) return `${f1.format(v / 1e9)} tỷ`;
  if (v >= 1e6) return `${f0.format(v / 1e6)} tr`;
  return f0.format(v);
}

const WEEKDAY = ["CN", "T2", "T3", "T4", "T5", "T6", "T7"];

export function day(iso: string | null | undefined, withWeekday = false): string {
  if (!iso) return "–";
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  const s = `${String(d).padStart(2, "0")}/${String(m).padStart(2, "0")}/${y}`;
  if (!withWeekday) return s;
  const wd = new Date(Date.UTC(y, m - 1, d)).getUTCDay();
  return `${WEEKDAY[wd]}, ${s}`;
}

export function shortDay(iso: string | null | undefined): string {
  if (!iso) return "–";
  const [, m, d] = iso.slice(0, 10).split("-");
  return `${d}/${m}`;
}

export type Tone = "up" | "down" | "ref" | "ceil" | "floor" | "none";

/** Colour of a price against the reference (previous close), price-board convention. */
export function priceTone(p: number | null | undefined, ref: number | null | undefined, ceil?: number | null, floor?: number | null): Tone {
  if (p == null || ref == null) return "none";
  if (ceil != null && p >= ceil - 0.005) return "ceil";
  if (floor != null && p <= floor + 0.005) return "floor";
  if (Math.abs(p - ref) < 0.005) return "ref";
  return p > ref ? "up" : "down";
}

export function changeTone(v: number | null | undefined): Tone {
  if (v == null) return "none";
  if (Math.abs(v) < 0.00005) return "ref";
  return v > 0 ? "up" : "down";
}

export const toneClass: Record<Tone, string> = {
  up: "text-up",
  down: "text-down",
  ref: "text-ref",
  ceil: "text-ceil",
  floor: "text-floor",
  none: "text-ink-2",
};
