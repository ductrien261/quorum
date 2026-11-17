/** Read a token from :root as an rgb()/rgba() string usable by canvas libraries. */
export function cssColor(name: string, alpha = 1): string {
  if (typeof window === "undefined") return "#888";
  const raw = getComputedStyle(document.documentElement).getPropertyValue(`--${name}`).trim();
  const parts = raw.split(/\s+/).map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) return "#888";
  return alpha === 1 ? `rgb(${parts[0]},${parts[1]},${parts[2]})` : `rgba(${parts[0]},${parts[1]},${parts[2]},${alpha})`;
}

export const vnPrice = (p: number) =>
  new Intl.NumberFormat("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(p);
