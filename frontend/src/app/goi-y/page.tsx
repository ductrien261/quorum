"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { ChangePct, Empty, ErrorBox, RankDelta, Skeleton, StarButton, TickerLink } from "@/components/ui/bits";
import { QuorumStrip } from "@/components/ui/quorum-strip";
import { fetcher, type RankRow, type Rankings } from "@/lib/api";
import { day, pct, price } from "@/lib/format";
import { usePageContext } from "@/lib/session";

type View = "all" | "movers" | "new" | "news";

export default function PicksPage() {
  const router = useRouter();
  const { data: dates } = useSWR<{ as_of: string; kind: string }[]>("/api/ai/dates", fetcher);
  const [date, setDate] = useState<string | null>(null);
  const [view, setView] = useState<View>("all");
  const [sector, setSector] = useState("");
  const key = date ? `/api/ai/rankings?date=${date}` : "/api/ai/rankings";
  const { data, error } = useSWR<Rankings>(key, fetcher);
  usePageContext("Gợi ý AI", undefined, data?.as_of);

  const sectors = useMemo(() => [...new Set(data?.rows.map((r) => r.sector) ?? [])].sort(), [data]);
  const rows = useMemo(() => {
    if (!data) return [];
    let r: RankRow[] = data.rows;
    if (sector) r = r.filter((x) => x.sector === sector);
    if (view === "movers") r = r.filter((x) => (x.rank_change ?? 0) >= 10).sort((a, b) => (b.rank_change ?? 0) - (a.rank_change ?? 0));
    if (view === "new") r = r.filter((x) => x.rank <= 10 && x.rank_change != null && x.rank + x.rank_change > 10);
    if (view === "news") r = r.filter((x) => x.has_news);
    return r;
  }, [data, view, sector]);
  const hasOutcome = data?.rows.some((r) => r.realized_return != null);
  const recent = useMemo(() => (dates ?? []).slice().reverse().slice(0, 60), [dates]);

  if (error) return <ErrorBox error={error} />;

  return (
    <div className="mx-auto max-w-[1400px]">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold">Gợi ý AI{data ? ` cho phiên ${day(data.target_session, true)}` : ""}</h1>
          <p className="text-sm text-ink-2">
            Thứ hạng là trung bình của {data?.seeds ?? 10} mô hình. Cột đồng thuận đếm số mô hình xếp mã vào top 5.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-2">
          Dữ liệu đến phiên
          <select className="input w-44" value={date ?? ""} onChange={(e) => setDate(e.target.value || null)}>
            <option value="">Mới nhất</option>
            {recent.map((d) => (
              <option key={d.as_of} value={d.as_of}>
                {day(d.as_of)}
                {d.kind === "history" ? " (kiểm định 2025)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="panel">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b border-line px-3">
          <div className="flex h-10 items-end gap-5">
            {(
              [
                ["all", "Toàn bộ 78 mã"],
                ["movers", "Tăng hạng mạnh"],
                ["new", "Mới vào top 10"],
                ["news", "Có tin mới"],
              ] as const
            ).map(([k, label]) => (
              <button key={k} className="tab" data-active={view === k} onClick={() => setView(k)}>
                {label}
              </button>
            ))}
          </div>
          <select className="input mb-1 w-48" value={sector} onChange={(e) => setSector(e.target.value)} aria-label="Lọc theo ngành">
            <option value="">Mọi ngành</option>
            {sectors.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="overflow-x-auto thin-scroll">
          {!data ? (
            <Skeleton className="h-[600px]" />
          ) : rows.length === 0 ? (
            <Empty title="Không có mã nào khớp">Thử chọn tab khác hoặc bỏ lọc ngành.</Empty>
          ) : (
            <table className="tbl min-w-[960px]">
              <thead>
                <tr>
                  <th className="w-14 text-right">Hạng</th>
                  <th className="w-16">Thay đổi</th>
                  <th>Mã</th>
                  <th>Ngành</th>
                  <th className="text-right">Giá</th>
                  <th className="text-right">%</th>
                  <th>Đồng thuận</th>
                  <th>Yếu tố đẩy hạng nhiều nhất</th>
                  {hasOutcome && <th className="text-right">Kết quả phiên sau</th>}
                  <th className="w-8" />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.symbol} className="cursor-pointer" onClick={() => router.push(`/co-phieu/${r.symbol}`)}>
                    <td className="num text-right font-semibold">{r.rank}</td>
                    <td>
                      <RankDelta value={r.rank_change} />
                    </td>
                    <td>
                      <TickerLink symbol={r.symbol} />
                      <span className="ml-2 text-xs text-ink-3">{r.short_name}</span>
                    </td>
                    <td className="text-ink-2">{r.sector}</td>
                    <td className="num text-right">{price(r.close)}</td>
                    <td className="text-right">
                      <ChangePct value={r.change_pct} />
                    </td>
                    <td>
                      <QuorumStrip votes={r.votes} seeds={data.seeds} size="sm" />
                    </td>
                    <td className="text-ink-2">
                      {r.driver_label ?? "–"}
                      {r.has_news && <span className="ml-2 border border-line px-1 text-2xs text-ink-2">có tin</span>}
                    </td>
                    {hasOutcome && (
                      <td className="text-right">
                        {r.realized_return != null ? <ChangePct value={r.realized_return} /> : <span className="text-ink-3">chờ</span>}
                      </td>
                    )}
                    <td onClick={(e) => e.stopPropagation()}>
                      <StarButton symbol={r.symbol} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
      {data && (
        <p className="mt-2 text-xs text-ink-3">
          {data.n_news} mã có tin trong 5 ngày gần nhất được đưa vào mô hình. {data.kind === "history" && "Đây là phiên thuộc giai đoạn kiểm định 2025. "}
          Cột kết quả phiên sau hiện khi đã có giá đóng cửa của phiên đó.
        </p>
      )}
    </div>
  );
}
