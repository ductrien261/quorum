export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

const TOKEN_KEY = "quorum.token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable */
  }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers: { ...headers, ...(init?.headers as object) } });
  } catch {
    throw new ApiError(0, "Không kết nối được máy chủ Quorum. Kiểm tra backend đã chạy ở " + API_URL);
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* not json */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const fetcher = <T,>(path: string) => api<T>(path);

/* ----------------------------------------------------------------- types */

export interface BoardRow {
  symbol: string;
  short_name: string;
  sector: string;
  exchange: string;
  ref: number | null;
  ceiling: number | null;
  floor: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
  change: number | null;
  change_pct: number | null;
  value: number | null;
  ai_rank?: number;
  ai_votes?: number;
  ai_score?: number;
  ai_rank_change?: number | null;
  spark?: number[];
}

export interface Board {
  date: string;
  ref_date: string | null;
  ai_as_of: string | null;
  rows: BoardRow[];
}

export interface Bar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  rsi?: number | null;
  macd?: number | null;
}

export interface MiniRow {
  symbol: string;
  short_name: string;
  close: number | null;
  change_pct: number | null;
  value: number | null;
  ai_rank?: number | null;
}

export interface SectorStat {
  sector: string;
  n: number;
  avg_change_pct: number | null;
  value: number;
  avg_ai_rank: number | null;
  symbols: { symbol: string; change_pct: number | null; value: number | null; ai_rank?: number | null }[];
}

export interface Overview {
  date: string;
  index: { code: string; series: Bar[]; close: number | null; change: number | null; change_pct: number | null };
  breadth: { up: number; down: number; flat: number; ceiling: number; floor: number };
  total_value: number;
  sectors: SectorStat[];
  gainers: MiniRow[];
  losers: MiniRow[];
  most_active: MiniRow[];
}

export interface RankRow {
  symbol: string;
  short_name: string;
  name: string;
  sector: string;
  rank: number;
  avg_rank: number;
  score: number;
  score_std: number;
  votes: number;
  rank_change: number | null;
  close: number | null;
  change_pct: number | null;
  summary: string | null;
  top_driver: string | null;
  driver_label: string | null;
  has_news: boolean;
  realized_return: number | null;
}

export interface Rankings {
  as_of: string;
  target_session: string;
  target_confirmed: boolean;
  kind: string | null;
  n_news: number;
  seeds: number;
  previous_as_of: string | null;
  rows: RankRow[];
  movers?: RankRow[];
  new_in_top10?: RankRow[];
}

export interface StockDetail {
  symbol: string;
  short_name: string;
  name: string;
  sector: string;
  exchange: string;
  price: {
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
    ref: number | null;
    change: number | null;
    change_pct: number | null;
    high_52w: number;
    low_52w: number;
    avg_volume_20: number;
    ret_1m: number | null;
  } | null;
  ai: {
    as_of: string;
    rank: number;
    votes: number;
    score: number;
    score_std: number;
    seeds: number;
    rank_change: number | null;
    summary: string | null;
  } | null;
}

export interface SourceEffect {
  label: string;
  delta_score: number;
  rank_without: number;
  rank_shift: number;
}

export interface Explanation {
  as_of: string;
  symbol: string;
  rank: number;
  n: number;
  votes: number;
  seeds: number;
  summary: string;
  top_driver: string;
  sources: Record<string, SourceEffect>;
  features: Record<string, { label: string; value: number | null; percentile: number | null; note: string | null }>;
  sector: { name: string; rank_in_sector: number; n_in_sector: number; leaders: string[] };
  news: { date: string; title: string; url: string } | null;
}

export interface NewsItem {
  date: string;
  title: string;
  url: string;
  source: string;
}

export interface RankPoint {
  as_of: string;
  rank: number;
  votes: number;
  score: number;
  realized_return: number | null;
}

export interface Peer {
  symbol: string;
  short_name: string;
  close: number | null;
  change_pct: number | null;
  ai_rank: number | null;
  ai_votes: number | null;
}

export interface Stats {
  total_return?: number;
  avg_daily?: number;
  sharpe_daily?: number | null;
  sharpe_annual?: number | null;
  max_drawdown?: number;
  positive_days?: number;
}

export interface TrackDay {
  as_of: string;
  kind: string | null;
  top: number;
  basket: number;
  index: number | null;
  ndcg: number;
  picks: { symbol: string; ret: number }[];
  equity_top: number;
  equity_basket: number;
  equity_index: number | null;
}

export interface TrackRecord {
  k: number;
  n_days: number;
  from: string | null;
  to: string | null;
  top: Stats;
  basket: Stats;
  index: Stats | null;
  beat_basket_days: number | null;
  ndcg: number | null;
  periods: string[];
  daily: TrackDay[];
}

export interface Health {
  latest_price_date: string | null;
  latest_as_of: string | null;
  n_runs: number;
  n_news: number;
  demo_data: boolean;
  last_job: { status: string; message: string | null; started_at: string | null; finished_at: string | null } | null;
}

export interface SearchHit {
  symbol: string;
  short_name: string;
  sector: string;
  ai_rank: number | null;
}

export interface ScreenRow extends BoardRow {
  rsi: number | null;
  macd: number | null;
  ret_5d: number | null;
}
