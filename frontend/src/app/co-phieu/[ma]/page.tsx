"use client";

import clsx from "clsx";
import Link from "next/link";
import { use, useEffect, useState } from "react";
import useSWR from "swr";

import { CandleChart, IndicatorMenu, type IndicatorId } from "@/components/charts/candle-chart";
import { AskButton, ChangeAbs, ChangePct, Empty, ErrorBox, PriceText, RankDelta, Segmented, Skeleton, StarButton, TickerLink } from "@/components/ui/bits";
import { QuorumStrip } from "@/components/ui/quorum-strip";
import {
  type Bar,
  type Explanation,
  fetcher,
  type NewsItem,
  type Peer,
  type RankPoint,
  type StockDetail,
} from "@/lib/api";
import { day, num, pct, price, volume } from "@/lib/format";
import { usePageContext } from "@/lib/session";

const RANGES = [
  { value: 66, label: "3T" },
  { value: 130, label: "6T" },
  { value: 250, label: "1N" },
  { value: 500, label: "2N" },
];

const IND_KEY = "quorum.indicators";

export default function StockPage({ params }: { params: Promise<{ ma: string }> }) {
  const { ma } = use(params);
  const symbol = decodeURIComponent(ma).toUpperCase();
  usePageContext("Chi tiết mã", symbol);
  const [range, setRange] = useState(130);
  const [ind, setInd] = useState<IndicatorId[]>(["ma20", "rank"]);
  useEffect(() => {
    try {
      const saved = localStorage.getItem(IND_KEY);
      if (saved) setInd(JSON.parse(saved));
    } catch {}
  }, []);
  const changeInd = (v: IndicatorId[]) => {
    setInd(v);
    try {
      localStorage.setItem(IND_KEY, JSON.stringify(v));
    } catch {}
  };
  const detail = useSWR<StockDetail>(`/api/stocks/${symbol}`, fetcher);
  const bars = useSWR<Bar[]>(`/api/stocks/${symbol}/prices?days=700`, fetcher);
  const ranks = useSWR<RankPoint[]>(`/api/stocks/${symbol}/rank-history?days=500`, fetcher);
  const expl = useSWR<Explanation>(`/api/stocks/${symbol}/explanation`, fetcher);
  const news = useSWR<NewsItem[]>(`/api/stocks/${symbol}/news?days=60`, fetcher);
  const peers = useSWR<Peer[]>(`/api/stocks/${symbol}/peers`, fetcher);

  if (detail.error) return <ErrorBox error={detail.error} />;
  const d = detail.data;
  const p = d?.price;

  return (
    <div className="mx-auto grid max-w-[1400px] gap-4">
      {/* header */}
      <section className="panel">
        {!d ? (
          <Skeleton className="h-28" />
        ) : (
          <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,1fr)_auto]">
            <div className="flex flex-wrap items-start gap-x-8 gap-y-3">
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold">{d.symbol}</h1>
                  <span className="border border-line px-1.5 text-2xs text-ink-2">{d.exchange}</span>
                  <StarButton symbol={d.symbol} />
                </div>
                <p className="mt-0.5 text-sm text-ink-2">{d.name}</p>
                <p className="text-xs text-ink-3">{d.sector}</p>
              </div>
              {p && (
                <div>
                  <div className="flex items-baseline gap-3">
                    <PriceText value={p.close} refPrice={p.ref} className="text-2xl font-bold" />
                    <ChangeAbs value={p.change} className="text-md font-medium" />
                    <ChangePct value={p.change_pct} className="text-md font-medium" />
                  </div>
                  <p className="text-xs text-ink-3">Đóng cửa phiên {day(p.date)}, nghìn đồng</p>
                </div>
              )}
              {p && (
                <dl className="grid grid-cols-3 gap-x-4 gap-y-1 text-sm sm:grid-cols-6 sm:gap-x-6">
                  {[
                    ["Tham chiếu", price(p.ref)],
                    ["Mở", price(p.open)],
                    ["Cao", price(p.high)],
                    ["Thấp", price(p.low)],
                    ["Khối lượng", volume(p.volume)],
                    ["KL TB 20 phiên", volume(p.avg_volume_20)],
                    ["Cao 52 tuần", price(p.high_52w)],
                    ["Thấp 52 tuần", price(p.low_52w)],
                    ["1 tháng", pct(p.ret_1m)],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="text-xs text-ink-3">{k}</dt>
                      <dd className="num">{v}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
            {d.ai ? (
              <div className="border-l-4 border-brand bg-brand-tint/60 px-4 py-3 lg:min-w-[290px]">
                <p className="text-xs text-ink-2">Hạng AI cho phiên kế tiếp</p>
                <div className="mt-1 flex items-baseline gap-2">
                  <span className="num text-2xl font-bold text-brand">{d.ai.rank}</span>
                  <span className="text-sm text-ink-2">/ 78</span>
                  <RankDelta value={d.ai.rank_change} />
                </div>
                <div className="mt-2">
                  <QuorumStrip votes={d.ai.votes} seeds={d.ai.seeds} size="lg" />
                </div>
                <p className="mt-2 text-xs text-ink-2">Dữ liệu đến phiên {day(d.ai.as_of)}</p>
              </div>
            ) : (
              <div className="text-sm text-ink-2">Chưa có điểm AI cho mã này.</div>
            )}
          </div>
        )}
      </section>

      {/* chart */}
      <section className="panel">
        <div className="panel-head">
          <h2 className="panel-title">Diễn biến giá và hạng AI</h2>
          <div className="flex items-center gap-2">
            <IndicatorMenu value={ind} onChange={changeInd} />
            <Segmented label="Khoảng thời gian" value={range} onChange={setRange} options={RANGES} />
          </div>
        </div>
        {bars.error ? (
          <div className="p-3">
            <ErrorBox error={bars.error} />
          </div>
        ) : bars.data && bars.data.length ? (
          <CandleChart bars={bars.data} ranks={ranks.data} visible={range} indicators={ind} height={420} />
        ) : bars.data ? (
          <Empty title="Chưa có dữ liệu giá">Chạy lệnh cập nhật giá ở backend để có biểu đồ.</Empty>
        ) : (
          <Skeleton className="h-[440px]" />
        )}
      </section>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
        <div className="grid content-start gap-4">
          <WhyPanel e={expl.data} loading={!expl.data && !expl.error} symbol={symbol} />
          <IndicatorPanel e={expl.data} />
        </div>
        <div className="grid content-start gap-4">
          <NewsPanel items={news.data} />
          <PeersPanel peers={peers.data} current={symbol} sector={d?.sector} />
          <HistoryPanel points={ranks.data} />
        </div>
      </div>
    </div>
  );
}

function WhyPanel({ e, loading, symbol }: { e?: Explanation; loading: boolean; symbol: string }) {
  const sources = e ? Object.entries(e.sources).sort((a, b) => b[1].rank_shift - a[1].rank_shift) : [];
  const maxShift = Math.max(5, ...sources.map(([, s]) => Math.abs(s.rank_shift)));
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Vì sao Quorum xếp hạng này</h2>
        <AskButton question={`Giải thích chi tiết vì sao ${symbol} được xếp hạng như vậy`} label="Hỏi trợ lý giải thích" />
      </div>
      {loading ? (
        <Skeleton className="m-3 h-40" />
      ) : !e ? (
        <Empty title="Chưa có giải thích" />
      ) : (
        <div className="p-4">
          <p className="text-sm">{e.summary}</p>
          <h3 className="mt-4 text-sm font-semibold">Nếu bỏ từng nguồn thông tin, mã này đứng hạng mấy?</h3>
          <p className="text-xs text-ink-3">Thanh xanh: nguồn đó đang kéo mã lên. Thanh đỏ: đang kéo xuống.</p>
          <div className="mt-3 grid gap-2">
            {sources.map(([k, s]) => {
              const w = (Math.abs(s.rank_shift) / maxShift) * 50;
              return (
                <div key={k} className="grid grid-cols-[minmax(0,1fr)_minmax(60px,1fr)_auto] items-center gap-2 text-sm sm:grid-cols-[170px_1fr_130px] sm:gap-3">
                  <span className="text-ink-2">{s.label}</span>
                  <div className="relative h-4 bg-sunken">
                    <span className="absolute inset-y-0 left-1/2 w-px bg-line" />
                    <span
                      className={clsx("absolute inset-y-0.5", s.rank_shift >= 0 ? "bg-up/80" : "bg-down/80")}
                      style={s.rank_shift >= 0 ? { left: "50%", width: `${w}%` } : { right: "50%", width: `${w}%` }}
                    />
                  </div>
                  <span className="num text-xs text-ink-2">
                    {s.rank_shift === 0 ? "không đổi" : `hạng ${s.rank_without} (${s.rank_shift > 0 ? "tụt" : "lên"} ${Math.abs(s.rank_shift)})`}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-4 grid gap-1 border-t border-line-soft pt-3 text-sm sm:grid-cols-2">
            <p>
              Trong ngành <span className="font-medium">{e.sector.name.toLowerCase()}</span>: hạng {e.sector.rank_in_sector}/{e.sector.n_in_sector}
            </p>
            <p className="text-ink-2">
              Dẫn đầu ngành:{" "}
              {e.sector.leaders.map((s, i) => (
                <span key={s}>
                  {i > 0 && ", "}
                  <TickerLink symbol={s} />
                </span>
              ))}
            </p>
            {e.news && (
              <p className="sm:col-span-2">
                Tin được đưa vào mô hình ({day(e.news.date)}):{" "}
                <a href={e.news.url} target="_blank" rel="noreferrer" className="text-brand hover:underline">
                  {e.news.title}
                </a>
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

const FMT: Record<string, (v: number) => string> = {
  ret_1d: (v) => pct(v),
  ret_5d: (v) => pct(v),
  ret_10d: (v) => pct(v),
  rsi: (v) => num(v, 1),
  macd: (v) => num(v, 2),
  close_open_ratio: (v) => pct(v),
  high_low_ratio: (v) => pct(v, 2, false),
};

function IndicatorPanel({ e }: { e?: Explanation }) {
  if (!e) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">7 chỉ báo mô hình đọc</h2>
        <span className="text-xs text-ink-3">Vị trí so với 78 mã trong rổ</span>
      </div>
      <table className="tbl">
        <tbody>
          {Object.entries(e.features).map(([k, f]) => (
            <tr key={k}>
              <td className="whitespace-normal text-ink-2 sm:w-44">{f.label}{f.note && <span className="block text-2xs text-ink-3 sm:hidden">{f.note}</span>}</td>
              <td className="num w-24 text-right font-medium">{f.value == null ? "–" : (FMT[k] ?? ((v: number) => num(v, 2)))(f.value)}</td>
              <td className="w-[38%] min-w-[80px]">
                {f.percentile != null && (
                  <div className="relative h-1.5 w-full max-w-[220px] bg-line-soft" title={`Cao hơn ${Math.round(f.percentile * 100)}% số mã`}>
                    <span className="absolute -top-1 h-3.5 w-1 bg-ink" style={{ left: `calc(${f.percentile * 100}% - 2px)` }} />
                  </div>
                )}
              </td>
              <td className="hidden text-xs text-ink-2 sm:table-cell">{f.note ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function NewsPanel({ items }: { items?: NewsItem[] }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Tin tức</h2>
        <span className="text-xs text-ink-3">CafeF</span>
      </div>
      {!items ? (
        <Skeleton className="m-3 h-24" />
      ) : items.length === 0 ? (
        <Empty title="Chưa có tin">Tin được cập nhật mỗi tối cùng pipeline.</Empty>
      ) : (
        <ul>
          {items.slice(0, 8).map((n) => (
            <li key={n.url} className="border-b border-line-soft px-3 py-2 last:border-b-0">
              <a href={n.url} target="_blank" rel="noreferrer" className="text-sm hover:text-brand">
                {n.title}
              </a>
              <p className="text-2xs text-ink-3">{day(n.date)}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function PeersPanel({ peers, current, sector }: { peers?: Peer[]; current: string; sector?: string }) {
  if (!peers || peers.length <= 1) return null;
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Cùng ngành {sector?.toLowerCase()}</h2>
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>Mã</th>
            <th className="text-right">Giá</th>
            <th className="text-right">%</th>
            <th className="text-right">Hạng AI</th>
          </tr>
        </thead>
        <tbody>
          {peers.map((p) => (
            <tr key={p.symbol} className={p.symbol === current ? "bg-brand-tint/50" : ""}>
              <td>
                {p.symbol === current ? <span className="font-semibold">{p.symbol}</span> : <TickerLink symbol={p.symbol} />}
              </td>
              <td className="num text-right">{price(p.close)}</td>
              <td className="text-right">
                <ChangePct value={p.change_pct} />
              </td>
              <td className="num text-right">{p.ai_rank ?? "–"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function HistoryPanel({ points }: { points?: RankPoint[] }) {
  if (!points || points.length === 0) return null;
  const last = points.slice(-12).reverse();
  return (
    <section className="panel">
      <div className="panel-head">
        <h2 className="panel-title">Lịch sử gợi ý gần đây</h2>
      </div>
      <table className="tbl">
        <thead>
          <tr>
            <th>Dữ liệu đến</th>
            <th className="text-right">Hạng</th>
            <th>Đồng thuận</th>
            <th className="text-right">Phiên sau</th>
          </tr>
        </thead>
        <tbody>
          {last.map((r) => (
            <tr key={r.as_of}>
              <td className="num text-ink-2">{day(r.as_of)}</td>
              <td className="num text-right font-medium">{r.rank}</td>
              <td>
                <QuorumStrip votes={r.votes} size="sm" />
              </td>
              <td className="text-right">{r.realized_return != null ? <ChangePct value={r.realized_return} /> : <span className="text-ink-3">chờ</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="px-3 py-2 text-xs text-ink-3">
        <Link href="/hieu-qua" className="text-brand hover:underline">
          Xem hiệu quả chung của gợi ý
        </Link>
      </p>
    </section>
  );
}
