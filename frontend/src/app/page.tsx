"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { LineChart } from "@/components/charts/line-chart";
import { SectorTreemap } from "@/components/charts/sector-treemap";
import { AskButton, ChangePct, ErrorBox, PriceText, RankDelta, Skeleton, StarButton, TickerLink } from "@/components/ui/bits";
import { QuorumStrip } from "@/components/ui/quorum-strip";
import { fetcher, type MiniRow, type Overview, type Rankings, type TrackRecord } from "@/lib/api";
import { day, money, num, pct, price } from "@/lib/format";
import { usePageContext } from "@/lib/session";

function PicksPanel({ data }: { data: Rankings }) {
  return (
    <section className="panel" aria-labelledby="picks-title">
      <div className="flex flex-wrap items-end justify-between gap-2 border-b border-line px-4 pb-3 pt-4">
        <div>
          <h1 id="picks-title" className="text-lg font-bold">
            Gợi ý cho phiên {day(data.target_session, true)}
          </h1>
          <p className="mt-0.5 text-sm text-ink-2">
            {data.seeds} mô hình chấm điểm 78 mã dựa trên dữ liệu đến hết phiên {day(data.as_of)}.
            {!data.target_confirmed && " Ngày phiên tới là dự kiến."}
          </p>
        </div>
        <Link href="/goi-y" className="text-sm font-medium text-brand hover:underline">
          Xem đủ 78 mã
        </Link>
      </div>
      <ol>
        {data.rows.map((r) => (
          <li key={r.symbol} className="grid grid-cols-[32px_1fr_auto] items-center gap-x-4 border-b border-line-soft px-4 py-3 last:border-b-0 md:grid-cols-[32px_minmax(150px,1.3fr)_92px_minmax(180px,1.2fr)_auto]">
            <span className="num text-xl font-bold text-ink-3">{r.rank}</span>
            <div className="min-w-0">
              <div className="flex items-baseline gap-2">
                <TickerLink symbol={r.symbol} className="text-md" />
                <RankDelta value={r.rank_change} />
              </div>
              <div className="truncate text-xs text-ink-2">
                {r.short_name}, {r.sector.toLowerCase()}
              </div>
              <div className="mt-0.5 flex gap-2 text-xs md:hidden">
                <span className="num">{price(r.close)}</span>
                <ChangePct value={r.change_pct} />
              </div>
            </div>
            <div className="hidden text-right md:block">
              <div className="num font-medium">{price(r.close)}</div>
              <ChangePct value={r.change_pct} className="text-xs" />
            </div>
            <div className="col-span-2 col-start-2 mt-2 min-w-0 md:col-span-1 md:col-start-auto md:mt-0">
              <QuorumStrip votes={r.votes} seeds={data.seeds} />
              {r.driver_label && (
                <p className="mt-1 truncate text-xs text-ink-2" title={r.summary ?? undefined}>
                  Nhờ nhiều nhất: <span className="text-ink">{r.driver_label.toLowerCase()}</span>
                  {r.has_news && ", có tin mới"}
                </p>
              )}
            </div>
            <div className="col-start-3 row-start-1 flex items-center gap-3 md:col-start-auto md:row-start-auto">
              <span className="hidden md:inline">
                <AskButton question={`Vì sao ${r.symbol} được xếp hạng ${r.rank}?`} label="Hỏi lý do" />
              </span>
              <StarButton symbol={r.symbol} />
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function IndexPanel({ o }: { o: Overview }) {
  const series = useMemo(
    () => [{ name: "VN-Index", color: "brand", area: true, points: o.index.series.slice(-130).map((b) => ({ date: b.date, value: b.close })) }],
    [o],
  );
  const b = o.breadth;
  const total = b.up + b.flat + b.down || 1;
  return (
    <section className="panel flex flex-col">
      <div className="panel-head">
        <h2 className="panel-title">VN-Index</h2>
        <span className="text-xs text-ink-3">6 tháng</span>
      </div>
      <div className="px-3 pt-3">
        <div className="flex items-baseline gap-3">
          <span className="num text-xl font-bold">{num(o.index.close, 2)}</span>
          <ChangePct value={o.index.change_pct} className="text-base font-medium" />
        </div>
      </div>
      <LineChart series={series} height={190} format={(v) => num(v, 0)} />
      <div className="mt-auto border-t border-line-soft px-3 py-3">
        <div className="mb-1.5 flex justify-between text-xs text-ink-2">
          <span>Độ rộng rổ 78 mã</span>
          <span>Giá trị GD {money(o.total_value)}</span>
        </div>
        <div className="flex h-2.5 w-full" role="img" aria-label={`${b.up} mã tăng, ${b.flat} đứng giá, ${b.down} mã giảm`}>
          <span className="bg-up" style={{ width: `${(b.up / total) * 100}%` }} />
          <span className="bg-ref" style={{ width: `${(b.flat / total) * 100}%` }} />
          <span className="bg-down" style={{ width: `${(b.down / total) * 100}%` }} />
        </div>
        <div className="num mt-1.5 flex justify-between text-xs">
          <span className="text-up">{b.up} tăng</span>
          <span className="text-ref">{b.flat} đứng</span>
          <span className="text-down">{b.down} giảm</span>
        </div>
      </div>
    </section>
  );
}

function MoversTable({ rows, valueCol }: { rows: MiniRow[]; valueCol?: boolean }) {
  return (
    <table className="tbl">
      <tbody>
        {rows.map((r) => (
          <tr key={r.symbol}>
            <td className="w-14">
              <TickerLink symbol={r.symbol} />
            </td>
            <td className="max-w-[120px] truncate text-xs text-ink-2">{r.short_name}</td>
            <td className="num text-right">{price(r.close)}</td>
            <td className="w-20 text-right">{valueCol ? <span className="num text-ink-2">{money(r.value)}</span> : <ChangePct value={r.change_pct} />}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function TrackTeaser() {
  const { data } = useSWR<TrackRecord>("/api/ai/track-record?k=5", fetcher);
  if (!data || data.n_days === 0) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Gợi ý top 5 đã làm được gì</h2>
        <Link href="/hieu-qua" className="text-sm font-medium text-brand hover:underline">
          Chi tiết
        </Link>
      </div>
      <dl className="grid grid-cols-2 gap-px bg-line-soft text-sm sm:grid-cols-4">
        {[
          ["Lợi nhuận top 5", pct(data.top.total_return), (data.top.total_return ?? 0) >= 0 ? "text-up" : "text-down"],
          ["Cả rổ 78 mã", pct(data.basket.total_return), (data.basket.total_return ?? 0) >= 0 ? "text-up" : "text-down"],
          ["Phiên top 5 thắng cả rổ", pct(data.beat_basket_days, 0, false), "text-ink"],
          ["Số phiên đã đối chiếu", num(data.n_days), "text-ink"],
        ].map(([k, v, c]) => (
          <div key={k} className="bg-surface px-3 py-3">
            <dt className="text-xs text-ink-2">{k}</dt>
            <dd className={`num mt-1 text-lg font-semibold ${c}`}>{v}</dd>
          </div>
        ))}
      </dl>
      <p className="px-3 py-2 text-xs text-ink-3">
        Từ {day(data.from)} đến {day(data.to)}, mua đều 5 mã mỗi phiên, chưa tính phí giao dịch.
      </p>
    </section>
  );
}

export default function HomePage() {
  usePageContext("Tổng quan");
  const picks = useSWR<Rankings>("/api/ai/picks?k=5", fetcher);
  const overview = useSWR<Overview>("/api/market/overview", fetcher);
  const [tab, setTab] = useState<"gainers" | "losers" | "most_active">("gainers");

  if (picks.error) return <ErrorBox error={picks.error} />;

  return (
    <div className="mx-auto grid max-w-[1400px] gap-4">
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.9fr)_minmax(300px,1fr)]">
        {picks.data ? <PicksPanel data={picks.data} /> : <Skeleton className="h-[420px]" />}
        {overview.data ? <IndexPanel o={overview.data} /> : <Skeleton className="h-[420px]" />}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.9fr)_minmax(300px,1fr)]">
        <section className="panel">
          <div className="panel-head">
            <h2 className="panel-title">Bản đồ thị trường</h2>
            <span className="text-xs text-ink-3">Diện tích theo giá trị giao dịch, màu theo % thay đổi</span>
          </div>
          <div className="p-2">{overview.data ? <SectorTreemap sectors={overview.data.sectors} /> : <Skeleton className="h-[340px]" />}</div>
        </section>
        <section className="panel">
          <div className="flex h-10 items-end gap-5 border-b border-line px-3">
            {(
              [
                ["gainers", "Tăng mạnh"],
                ["losers", "Giảm mạnh"],
                ["most_active", "Giao dịch nhiều"],
              ] as const
            ).map(([k, label]) => (
              <button key={k} className="tab" data-active={tab === k} onClick={() => setTab(k)}>
                {label}
              </button>
            ))}
          </div>
          {overview.data ? <MoversTable rows={overview.data[tab]} valueCol={tab === "most_active"} /> : <Skeleton className="h-60" />}
        </section>
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.9fr)_minmax(300px,1fr)]">
        <TrackTeaser />
        {picks.data?.movers && picks.data.movers.length > 0 && (
          <section className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Tăng hạng mạnh</h2>
              <span className="text-xs text-ink-3">so với phiên {day(picks.data.previous_as_of)}</span>
            </div>
            <table className="tbl">
              <tbody>
                {picks.data.movers.map((r) => (
                  <tr key={r.symbol}>
                    <td className="w-14">
                      <TickerLink symbol={r.symbol} />
                    </td>
                    <td className="num text-ink-2">hạng {r.rank}</td>
                    <td>
                      <RankDelta value={r.rank_change} />
                    </td>
                    <td className="text-right">
                      <PriceText value={r.close} refPrice={r.close && r.change_pct != null ? r.close / (1 + r.change_pct) : null} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </div>
    </div>
  );
}
