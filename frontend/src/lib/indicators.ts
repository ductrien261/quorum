/** Technical indicators computed in the browser from daily closes. `null` where there is not enough history. */

export type Series = (number | null)[];

export function sma(v: number[], n: number): Series {
  const out: Series = new Array(v.length).fill(null);
  let sum = 0;
  for (let i = 0; i < v.length; i++) {
    sum += v[i];
    if (i >= n) sum -= v[i - n];
    if (i >= n - 1) out[i] = sum / n;
  }
  return out;
}

/** EMA seeded with the SMA of the first n values (same convention as most charting platforms). */
export function ema(v: number[], n: number): Series {
  const out: Series = new Array(v.length).fill(null);
  if (v.length < n) return out;
  const k = 2 / (n + 1);
  let prev = v.slice(0, n).reduce((a, b) => a + b, 0) / n;
  out[n - 1] = prev;
  for (let i = n; i < v.length; i++) {
    prev = v[i] * k + prev * (1 - k);
    out[i] = prev;
  }
  return out;
}

export function bollinger(v: number[], n = 20, k = 2): { mid: Series; upper: Series; lower: Series } {
  const mid = sma(v, n);
  const upper: Series = new Array(v.length).fill(null);
  const lower: Series = new Array(v.length).fill(null);
  for (let i = n - 1; i < v.length; i++) {
    const m = mid[i] as number;
    let ss = 0;
    for (let j = i - n + 1; j <= i; j++) ss += (v[j] - m) ** 2;
    const sd = Math.sqrt(ss / n);
    upper[i] = m + k * sd;
    lower[i] = m - k * sd;
  }
  return { mid, upper, lower };
}

/** RSI with Wilder smoothing. */
export function rsi(v: number[], n = 14): Series {
  const out: Series = new Array(v.length).fill(null);
  if (v.length <= n) return out;
  let gain = 0;
  let loss = 0;
  for (let i = 1; i <= n; i++) {
    const d = v[i] - v[i - 1];
    gain += Math.max(d, 0);
    loss += Math.max(-d, 0);
  }
  gain /= n;
  loss /= n;
  out[n] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
  for (let i = n + 1; i < v.length; i++) {
    const d = v[i] - v[i - 1];
    gain = (gain * (n - 1) + Math.max(d, 0)) / n;
    loss = (loss * (n - 1) + Math.max(-d, 0)) / n;
    out[i] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
  }
  return out;
}

export function macd(v: number[], fast = 12, slow = 26, signal = 9): { line: Series; signal: Series; hist: Series } {
  const f = ema(v, fast);
  const s = ema(v, slow);
  const line: Series = v.map((_, i) => (f[i] != null && s[i] != null ? (f[i] as number) - (s[i] as number) : null));
  const start = line.findIndex((x) => x != null);
  const sig: Series = new Array(v.length).fill(null);
  if (start >= 0) {
    const e = ema(line.slice(start) as number[], signal);
    e.forEach((x, i) => (sig[start + i] = x));
  }
  const hist: Series = line.map((x, i) => (x != null && sig[i] != null ? x - (sig[i] as number) : null));
  return { line, signal: sig, hist };
}

/**
 * Least-squares line through the last `n` closes, with a ±k·σ channel of the residuals.
 * `slope` is the fitted change per session as a fraction of the fitted last value.
 */
export function linearRegression(v: number[], n: number, k = 2) {
  const m = Math.min(n, v.length);
  const off = v.length - m;
  const ys = v.slice(off);
  const xm = (m - 1) / 2;
  const ym = ys.reduce((a, b) => a + b, 0) / m;
  let sxy = 0;
  let sxx = 0;
  ys.forEach((y, i) => {
    sxy += (i - xm) * (y - ym);
    sxx += (i - xm) ** 2;
  });
  const b = sxx ? sxy / sxx : 0;
  const a = ym - b * xm;
  const fit = ys.map((_, i) => a + b * i);
  const sd = Math.sqrt(ys.reduce((acc, y, i) => acc + (y - fit[i]) ** 2, 0) / Math.max(1, m - 2));
  const ssTot = ys.reduce((acc, y) => acc + (y - ym) ** 2, 0);
  const r2 = ssTot ? 1 - ys.reduce((acc, y, i) => acc + (y - fit[i]) ** 2, 0) / ssTot : 0;
  const last = fit[m - 1];
  return { offset: off, fit, upper: fit.map((y) => y + k * sd), lower: fit.map((y) => y - k * sd), slope: last ? b / last : 0, r2 };
}
