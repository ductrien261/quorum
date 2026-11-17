"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { ChangePct, Empty, ErrorBox, Segmented, Skeleton, StarButton, TickerLink } from "@/components/ui/bits";
import { QuorumStrip } from "@/components/ui/quorum-strip";
import { fetcher, type ScreenRow } from "@/lib/api";
import { money, num, price } from "@/lib/format";
import { usePageContext } from "@/lib/session";

interface F {
  sectors: string[];
  max_rank: number | null;
  min_votes: number;
  rsi_min: string;
  rsi_max: string;
  change_min: string;
  change_max: string;
  min_value_bn: string;
  macd_positive: boolean;
  sort: string;
}

const EMPTY: F = {
  sectors: [],
  max_rank: null,
  min_votes: 0,
  rsi_min: "",
  rsi_max: "",
  change_min: "",
  change_max: "",
  min_value_bn: "",
  macd_positive: false,
  sort: "ai_rank",
};

const PRESETS: { label: string; f: Partial<F> }[] = [
  { label: "Top 10 AI, chưa quá mua", f: { max_rank: 10, rsi_max: "70" } },
  { label: "Được ít nhất 5/10 mô hình chọn", f: { min_votes: 5 } },
  { label: "Quá bán nhưng hạng AI cao", f: { rsi_max: "35", max_rank: 30 } },
  { label: "Thanh khoản trên 100 tỷ", f: { min_value_bn: "100", sort: "value" } },
];

function toQuery(f: F) {
  const p = new URLSearchParams();
  f.sectors.forEach((s) => p.append("sectors", s));
  if (f.max_rank) p.set("max_rank", String(f.max_rank));
  if (f.min_votes) p.set("min_votes", String(f.min_votes));
  if (f.rsi_min) p.set("rsi_min", f.rsi_min);
  if (f.rsi_max) p.set("rsi_max", f.rsi_max);
  if (f.change_min) p.set("change_min", String(Number(f.change_min) / 100));
  if (f.change_max) p.set("change_max", String(Number(f.change_max) / 100));
  if (f.min_value_bn) p.set("min_value_bn", f.min_value_bn);
  if (f.macd_positive) p.set("macd_positive", "true");
  p.set("sort", f.sort);
  return p.toString();
}

export default function ScreenerPage() {
  usePageContext("Bộ lọc");
  const router = useRouter();
  const [f, setF] = useState<F>(EMPTY);
  const { data: tickers } = useSWR<{ sector: string }[]>("/api/tickers", fetcher);
  const sectors = useMemo(() => [...new Set(tickers?.map((t) => t.sector) ?? [])].sort(), [tickers]);
  const { data, error, isLoading } = useSWR<{ count: number; rows: ScreenRow[] }>(`/api/screener?${toQuery(f)}`, fetcher, { keepPreviousData: true });
  const set = (patch: Partial<F>) => setF((x) => ({ ...x, ...patch }));

  return (
    <div className="mx-auto grid max-w-[1400px] gap-4 lg:grid-cols-[270px_minmax(0,1fr)]">
      <aside className="panel h-fit">
        <div className="panel-head">
          <h1 className="panel-title">Bộ lọc cổ phiếu</h1>
          <button className="text-xs text-brand hover:underline" onClick={() => setF(EMPTY)}>
            Xoá lọc
          </button>
        </div>
        <div className="grid gap-4 p-3">
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">Bộ lọc có sẵn</legend>
            <div className="grid">
              {PRESETS.map((p) => (
                <button key={p.label} className="border-b border-line-soft py-1.5 text-left text-sm text-brand hover:text-brand-deep" onClick={() => setF({ ...EMPTY, ...p.f })}>
                  {p.label}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">Hạng AI tối đa</legend>
            <Segmented
              label="Hạng AI tối đa"
              value={f.max_rank ?? 0}
              onChange={(v) => set({ max_rank: v || null })}
              options={[
                { value: 0, label: "Tất cả" },
                { value: 5, label: "5" },
                { value: 10, label: "10" },
                { value: 20, label: "20" },
              ]}
            />
          </fieldset>
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">Số mô hình đồng thuận tối thiểu: {f.min_votes}/10</legend>
            <input
              type="range"
              min={0}
              max={10}
              value={f.min_votes}
              onChange={(e) => set({ min_votes: Number(e.target.value) })}
              className="w-full accent-[rgb(var(--brand))]"
              aria-label="Số mô hình đồng thuận tối thiểu"
            />
          </fieldset>
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">RSI (14)</legend>
            <div className="flex items-center gap-2">
              <input className="input" placeholder="từ" inputMode="numeric" value={f.rsi_min} onChange={(e) => set({ rsi_min: e.target.value })} aria-label="RSI từ" />
              <span className="text-ink-3">–</span>
              <input className="input" placeholder="đến" inputMode="numeric" value={f.rsi_max} onChange={(e) => set({ rsi_max: e.target.value })} aria-label="RSI đến" />
            </div>
          </fieldset>
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">% thay đổi trong phiên</legend>
            <div className="flex items-center gap-2">
              <input className="input" placeholder="từ %" value={f.change_min} onChange={(e) => set({ change_min: e.target.value })} aria-label="Thay đổi từ %" />
              <span className="text-ink-3">–</span>
              <input className="input" placeholder="đến %" value={f.change_max} onChange={(e) => set({ change_max: e.target.value })} aria-label="Thay đổi đến %" />
            </div>
          </fieldset>
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">Giá trị giao dịch tối thiểu (tỷ đồng)</legend>
            <input className="input" inputMode="numeric" value={f.min_value_bn} onChange={(e) => set({ min_value_bn: e.target.value })} aria-label="Giá trị giao dịch tối thiểu" />
          </fieldset>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={f.macd_positive} onChange={(e) => set({ macd_positive: e.target.checked })} className="accent-[rgb(var(--brand))]" />
            MACD dương (xu hướng tăng)
          </label>
          <fieldset>
            <legend className="mb-1.5 text-xs font-medium text-ink-2">Ngành</legend>
            <div className="grid max-h-60 gap-1 overflow-y-auto thin-scroll">
              {sectors.map((s) => (
                <label key={s} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={f.sectors.includes(s)}
                    onChange={(e) => set({ sectors: e.target.checked ? [...f.sectors, s] : f.sectors.filter((x) => x !== s) })}
                    className="accent-[rgb(var(--brand))]"
                  />
                  {s}
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </aside>

      <section className="panel">
        <div className="panel-head">
          <h2 className="panel-title">{data ? `${data.count} mã khớp điều kiện` : "Kết quả"}</h2>
          <label className="flex items-center gap-2 text-xs text-ink-2">
            Sắp xếp
            <select className="input h-7 w-36 text-xs" value={f.sort} onChange={(e) => set({ sort: e.target.value })}>
              <option value="ai_rank">Hạng AI</option>
              <option value="change_pct">% thay đổi</option>
              <option value="value">Giá trị GD</option>
              <option value="rsi">RSI cao trước</option>
            </select>
          </label>
        </div>
        {error ? (
          <div className="p-3">
            <ErrorBox error={error} />
          </div>
        ) : !data && isLoading ? (
          <Skeleton className="h-96" />
        ) : data && data.rows.length === 0 ? (
          <Empty title="Không có mã nào khớp">Nới bớt điều kiện, ví dụ bỏ giới hạn RSI hoặc hạng AI.</Empty>
        ) : (
          <div className="overflow-x-auto thin-scroll">
            <table className="tbl min-w-[860px]">
              <thead>
                <tr>
                  <th>Mã</th>
                  <th>Ngành</th>
                  <th className="text-right">Giá</th>
                  <th className="text-right">%</th>
                  <th className="text-right">Lợi suất 5 phiên</th>
                  <th className="text-right">RSI</th>
                  <th className="text-right">Giá trị GD</th>
                  <th className="text-right">Hạng AI</th>
                  <th>Đồng thuận</th>
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {data?.rows.map((r) => (
                  <tr key={r.symbol} className="cursor-pointer" onClick={() => router.push(`/co-phieu/${r.symbol}`)}>
                    <td>
                      <TickerLink symbol={r.symbol} />
                      <span className="ml-2 text-xs text-ink-3">{r.short_name}</span>
                    </td>
                    <td className="text-ink-2">{r.sector}</td>
                    <td className="num text-right">{price(r.close)}</td>
                    <td className="text-right">
                      <ChangePct value={r.change_pct} />
                    </td>
                    <td className="text-right">
                      <ChangePct value={r.ret_5d} />
                    </td>
                    <td className={`num text-right ${r.rsi != null && r.rsi >= 70 ? "text-down" : r.rsi != null && r.rsi <= 30 ? "text-up" : ""}`}>{num(r.rsi, 1)}</td>
                    <td className="num text-right text-ink-2">{money(r.value)}</td>
                    <td className="num text-right font-medium">{r.ai_rank ?? "–"}</td>
                    <td>{r.ai_votes != null && <QuorumStrip votes={r.ai_votes} size="sm" />}</td>
                    <td onClick={(e) => e.stopPropagation()}>
                      <StarButton symbol={r.symbol} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="border-t border-line-soft px-3 py-2 text-xs text-ink-3">
          RSI trên 70 thường gọi là quá mua (tô đỏ), dưới 30 là quá bán (tô xanh). Hạng AI là gợi ý cho phiên kế tiếp, không phải tín hiệu mua bán.
        </p>
      </section>
    </div>
  );
}
