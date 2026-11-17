"use client";

import clsx from "clsx";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { LineChart, type Series } from "@/components/charts/line-chart";
import { ChangePct, Empty, ErrorBox, Segmented, Skeleton, TickerLink } from "@/components/ui/bits";
import { fetcher, type Stats, type TrackRecord } from "@/lib/api";
import { day, num, pct } from "@/lib/format";
import { usePageContext } from "@/lib/session";

type Period = "all" | "history" | "live";

const PERIOD_NOTE: Record<Period, string> = {
  all: "Toàn bộ các phiên đã có kết quả.",
  history: "Năm 2025: mô hình chưa từng thấy dữ liệu này khi huấn luyện, nên đây là phép kiểm định trung thực nhất.",
  live: "Các phiên chạy thật hằng ngày kể từ khi đưa Quorum vào sử dụng.",
};

export default function PerformancePage() {
  usePageContext("Hiệu quả gợi ý");
  const [period, setPeriod] = useState<Period>("history");
  const [k, setK] = useState(5);
  const qs = `k=${k}${period === "all" ? "" : `&kind=${period}`}`;
  const { data, error } = useSWR<TrackRecord>(`/api/ai/track-record?${qs}`, fetcher);

  const series = useMemo<Series[]>(() => {
    if (!data) return [];
    const s: Series[] = [
      { name: `Top ${k}`, color: "brand", points: data.daily.map((d) => ({ date: d.as_of, value: (d.equity_top - 1) * 100 })) },
      { name: "Cả rổ 78 mã", color: "ink-3", dashed: true, points: data.daily.map((d) => ({ date: d.as_of, value: (d.equity_basket - 1) * 100 })) },
    ];
    if (data.index)
      s.push({ name: "VN-Index", color: "ref", points: data.daily.map((d) => ({ date: d.as_of, value: ((d.equity_index ?? 1) - 1) * 100 })) });
    return s;
  }, [data, k]);

  if (error) return <ErrorBox error={error} />;

  return (
    <div className="mx-auto grid max-w-[1300px] gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold">Hiệu quả gợi ý</h1>
          <p className="max-w-[70ch] text-sm text-ink-2">
            Nếu mỗi phiên mua đều {k} mã được xếp hạng cao nhất và bán ở phiên sau, kết quả sẽ ra sao. Chưa tính phí giao dịch, thuế và
            trượt giá.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Segmented
            label="Giai đoạn"
            value={period}
            onChange={setPeriod}
            options={[
              { value: "history", label: "Kiểm định 2025" },
              { value: "live", label: "Chạy thật" },
              { value: "all", label: "Tất cả" },
            ]}
          />
          <Segmented
            label="Số mã"
            value={k}
            onChange={setK}
            options={[
              { value: 3, label: "Top 3" },
              { value: 5, label: "Top 5" },
              { value: 10, label: "Top 10" },
            ]}
          />
        </div>
      </div>
      <p className="-mt-2 text-xs text-ink-3">{PERIOD_NOTE[period]}</p>

      {!data ? (
        <Skeleton className="h-96" />
      ) : data.n_days === 0 ? (
        <div className="panel">
          <Empty title="Chưa có phiên nào đủ dữ liệu cho giai đoạn này">
            Kết quả của một gợi ý chỉ có sau khi phiên kế tiếp đóng cửa.
          </Empty>
        </div>
      ) : (
        <>
          <section className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Lợi nhuận cộng dồn, %</h2>
              <div className="flex gap-4 text-xs">
                {series.map((s) => (
                  <span key={s.name} className="flex items-center gap-1.5 text-ink-2">
                    <span className={clsx("inline-block h-0.5 w-4", s.dashed && "border-t-2 border-dashed bg-transparent")} style={s.dashed ? { borderColor: `rgb(var(--${s.color}))` } : { background: `rgb(var(--${s.color}))` }} />
                    {s.name}
                  </span>
                ))}
              </div>
            </div>
            <LineChart series={series} height={320} format={(v) => `${num(v, 1)}%`} />
          </section>

          <section className="panel overflow-x-auto">
            <table className="tbl min-w-[640px]">
              <thead>
                <tr>
                  <th>{`${day(data.from)} đến ${day(data.to)}, ${data.n_days} phiên`}</th>
                  <th className="text-right">Top {k}</th>
                  <th className="text-right">Cả rổ 78 mã</th>
                  {data.index && <th className="text-right">VN-Index</th>}
                </tr>
              </thead>
              <tbody>
                <StatRow label="Tổng lợi nhuận" k="total_return" d={data} fmt={(v) => pct(v)} tone />
                <StatRow label="Lợi nhuận trung bình mỗi phiên" k="avg_daily" d={data} fmt={(v) => pct(v, 3)} tone />
                <StatRow label="Sharpe theo phiên" k="sharpe_daily" d={data} fmt={(v) => num(v, 3)} />
                <StatRow label="Sharpe quy đổi năm" k="sharpe_annual" d={data} fmt={(v) => num(v, 2)} />
                <StatRow label="Sụt giảm tối đa" k="max_drawdown" d={data} fmt={(v) => pct(v, 1, false)} />
                <StatRow label="Tỷ lệ phiên có lãi" k="positive_days" d={data} fmt={(v) => pct(v, 0, false)} />
                <tr>
                  <td className="text-ink-2">Số phiên top {k} thắng cả rổ</td>
                  <td className="num text-right font-medium">{pct(data.beat_basket_days, 0, false)}</td>
                  <td />
                  {data.index && <td />}
                </tr>
                <tr>
                  <td className="text-ink-2">nDCG@5 trung bình (độ đúng của thứ tự)</td>
                  <td className="num text-right font-medium">{num(data.ndcg, 3)}</td>
                  <td className="num text-right text-ink-3">~0,49 nếu chọn ngẫu nhiên</td>
                  {data.index && <td />}
                </tr>
              </tbody>
            </table>
          </section>

          <section className="panel">
            <div className="panel-head">
              <h2 className="panel-title">Nhật ký từng phiên</h2>
              <span className="text-xs text-ink-3">Mới nhất ở trên</span>
            </div>
            <div className="max-h-[520px] overflow-auto thin-scroll">
              <table className="tbl min-w-[760px]">
                <thead className="sticky top-0">
                  <tr>
                    <th>Dữ liệu đến</th>
                    <th>Các mã được chọn và kết quả phiên sau</th>
                    <th className="text-right">Top {k}</th>
                    <th className="text-right">Cả rổ</th>
                    {data.index && <th className="text-right">VN-Index</th>}
                  </tr>
                </thead>
                <tbody>
                  {data.daily
                    .slice()
                    .reverse()
                    .map((d) => (
                      <tr key={d.as_of}>
                        <td className="num text-ink-2">{day(d.as_of)}</td>
                        <td className="whitespace-normal">
                          <span className="flex flex-wrap gap-x-3 gap-y-0.5">
                            {d.picks.map((p) => (
                              <span key={p.symbol} className="text-xs">
                                <TickerLink symbol={p.symbol} /> <ChangePct value={p.ret} digits={1} />
                              </span>
                            ))}
                          </span>
                        </td>
                        <td className="text-right font-medium">
                          <ChangePct value={d.top} />
                        </td>
                        <td className="text-right">
                          <ChangePct value={d.basket} />
                        </td>
                        {data.index && (
                          <td className="text-right">
                            <ChangePct value={d.index} />
                          </td>
                        )}
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </section>
          <p className="text-xs text-ink-3">
            Lưu ý: trên dữ liệu kiểm định 2025, chênh lệch giữa gợi ý và chọn ngẫu nhiên chưa có ý nghĩa thống kê. Hãy xem điểm AI như một
            nguồn tham khảo bên cạnh phân tích của riêng bạn.
          </p>
        </>
      )}
    </div>
  );
}

function StatRow({ label, k, d, fmt, tone }: { label: string; k: keyof Stats; d: TrackRecord; fmt: (v: number) => string; tone?: boolean }) {
  const cell = (s: Stats | null) => {
    const v = s?.[k];
    if (v == null) return <span className="text-ink-3">–</span>;
    return <span className={clsx("num", tone && (v > 0 ? "text-up" : v < 0 ? "text-down" : ""))}>{fmt(v)}</span>;
  };
  return (
    <tr>
      <td className="text-ink-2">{label}</td>
      <td className="text-right font-semibold">{cell(d.top)}</td>
      <td className="text-right">{cell(d.basket)}</td>
      {d.index && <td className="text-right">{cell(d.index)}</td>}
    </tr>
  );
}
