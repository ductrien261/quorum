"use client";

import clsx from "clsx";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import useSWR from "swr";

import { DayRange, Sparkline } from "@/components/charts/mini";
import { SectorTreemap } from "@/components/charts/sector-treemap";
import { ChangeAbs, ChangePct, ErrorBox, PriceText, Segmented, Skeleton, StarButton } from "@/components/ui/bits";
import { QuorumStrip } from "@/components/ui/quorum-strip";
import { type Board, type BoardRow, fetcher, type SectorStat } from "@/lib/api";
import { day, money, pct, price, volume } from "@/lib/format";
import { usePageContext } from "@/lib/session";

type SortKey = "sector" | "symbol" | "change_pct" | "value" | "ai_rank";

export default function PriceBoardPage() {
  usePageContext("Bảng giá");
  const router = useRouter();
  const { data, error } = useSWR<Board>("/api/market/board", fetcher, { refreshInterval: 60_000 });
  const [sort, setSort] = useState<SortKey>("sector");
  const [q, setQ] = useState("");
  const [onlyTop, setOnlyTop] = useState(false);
  const [view, setView] = useState<"table" | "map">("table");

  const groups = useMemo(() => {
    if (!data) return [];
    let rows = data.rows.filter(
      (r) => (!q || r.symbol.includes(q.toUpperCase()) || r.short_name.toLowerCase().includes(q.toLowerCase())) && (!onlyTop || (r.ai_rank ?? 99) <= 20),
    );
    if (sort === "sector") {
      const m = new Map<string, BoardRow[]>();
      rows.forEach((r) => m.set(r.sector, [...(m.get(r.sector) ?? []), r]));
      return [...m.entries()].map(([name, rs]) => ({ name, rows: rs }));
    }
    const key: Record<Exclude<SortKey, "sector">, (r: BoardRow) => number | string> = {
      symbol: (r) => r.symbol,
      change_pct: (r) => -(r.change_pct ?? -9),
      value: (r) => -(r.value ?? 0),
      ai_rank: (r) => r.ai_rank ?? 999,
    };
    rows = [...rows].sort((a, b) => {
      const ka = key[sort](a);
      const kb = key[sort](b);
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });
    return [{ name: "", rows }];
  }, [data, sort, q, onlyTop]);

  if (error) return <ErrorBox error={error} />;

  return (
    <div className="mx-auto max-w-[1500px]">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-bold">Bảng giá</h1>
          <p className="text-sm text-ink-2">
            78 mã Quorum theo dõi, giá nghìn đồng, phiên {data ? day(data.date) : "…"}. Cột hạng AI là gợi ý cho phiên kế tiếp.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input className="input w-44" placeholder="Lọc mã" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Lọc theo mã" />
          <label className="flex h-8 items-center gap-2 border border-line bg-surface px-2.5 text-sm">
            <input type="checkbox" checked={onlyTop} onChange={(e) => setOnlyTop(e.target.checked)} className="accent-[rgb(var(--brand))]" />
            Chỉ top 20 AI
          </label>
          <Segmented
            label="Sắp xếp"
            value={sort}
            onChange={setSort}
            options={[
              { value: "sector", label: "Theo ngành" },
              { value: "ai_rank", label: "Hạng AI" },
              { value: "change_pct", label: "% thay đổi" },
              { value: "value", label: "Giá trị GD" },
              { value: "symbol", label: "A-Z" },
            ]}
          />
        </div>
      </div>

      {data ? <Pulse rows={data.rows} onOpen={(s) => router.push(`/co-phieu/${s}`)} /> : <Skeleton className="mb-3 h-[150px]" />}

      <div className="mb-2 flex items-center justify-between gap-2">
        <Segmented
          label="Kiểu xem"
          value={view}
          onChange={setView}
          options={[
            { value: "table", label: "Bảng giá" },
            { value: "map", label: "Bản đồ nhiệt" },
          ]}
        />
        <span className="hidden text-xs text-ink-3 md:inline">
          {view === "table" ? "Bấm vào một dòng để xem biểu đồ chi tiết của mã." : "Mỗi ô là một mã: diện tích theo giá trị giao dịch, màu theo % thay đổi."}
        </span>
      </div>

      {view === "map" ? (
        <div className="panel p-2">{data ? <SectorTreemap sectors={toSectors(data.rows)} height={560} /> : <Skeleton className="h-[560px]" />}</div>
      ) : (
      <div className="panel overflow-x-auto thin-scroll">
        {!data ? (
          <Skeleton className="h-[600px]" />
        ) : (
          <table className="tbl min-w-[1280px]">
            <thead className="sticky top-0 z-10">
              <tr>
                <th className="w-8" aria-label="Theo dõi" />
                <th>Mã</th>
                <th className="text-right">Tham chiếu</th>
                <th className="text-right">Trần</th>
                <th className="text-right">Sàn</th>
                <th className="text-right">Mở</th>
                <th className="text-right">Cao</th>
                <th className="text-right">Thấp</th>
                <th className="border-x border-line text-right">Đóng cửa</th>
                <th className="text-right">+/−</th>
                <th className="text-right">%</th>
                <th>Biên độ ngày</th>
                <th>30 phiên</th>
                <th className="text-right">Khối lượng</th>
                <th className="text-right">Giá trị</th>
                <th className="text-right">Hạng AI</th>
                <th>Đồng thuận</th>
              </tr>
            </thead>
            <tbody>
              {groups.map((g) => (
                <GroupRows key={g.name || "all"} name={g.name} rows={g.rows} onOpen={(s) => router.push(`/co-phieu/${s}`)} />
              ))}
            </tbody>
          </table>
        )}
      </div>
      )}
      <p className="mt-2 text-xs text-ink-3">
        Màu giá: xanh lá tăng, đỏ giảm, vàng bằng tham chiếu, tím chạm trần, xanh lam chạm sàn. Biên độ HOSE ±7%, HNX ±10%. Cột biên
        độ ngày: thanh mờ là khoảng thấp đến cao trong phiên, ô vuông là giá đóng cửa, vạch vàng là tham chiếu, hai đầu là sàn và trần.
      </p>
    </div>
  );
}

function GroupRows({ name, rows, onOpen }: { name: string; rows: BoardRow[]; onOpen: (s: string) => void }) {
  return (
    <>
      {name && (
        <tr>
          <td colSpan={17} className="h-7 bg-sunken text-xs font-semibold text-ink-2">
            {name} <span className="font-normal text-ink-3">({rows.length})</span>
          </td>
        </tr>
      )}
      {rows.map((r) => (
        <tr key={r.symbol} className="cursor-pointer" onClick={() => onOpen(r.symbol)}>
          <td className="px-1">
            <StarButton symbol={r.symbol} />
          </td>
          <td>
            <span className={clsx("font-semibold", toneOf(r))}>{r.symbol}</span>
            <span className="ml-2 hidden text-xs text-ink-3 2xl:inline">{r.short_name}</span>
          </td>
          <td className="num text-right text-ref">{price(r.ref)}</td>
          <td className="num text-right text-ceil">{price(r.ceiling)}</td>
          <td className="num text-right text-floor">{price(r.floor)}</td>
          <td className="text-right">
            <PriceText value={r.open} refPrice={r.ref} ceil={r.ceiling} floor={r.floor} />
          </td>
          <td className="text-right">
            <PriceText value={r.high} refPrice={r.ref} ceil={r.ceiling} floor={r.floor} />
          </td>
          <td className="text-right">
            <PriceText value={r.low} refPrice={r.ref} ceil={r.ceiling} floor={r.floor} />
          </td>
          <td className="border-x border-line-soft bg-sunken/60 text-right font-semibold">
            <PriceText value={r.close} refPrice={r.ref} ceil={r.ceiling} floor={r.floor} />
          </td>
          <td className="text-right">
            <ChangeAbs value={r.change} />
          </td>
          <td className="text-right">
            <ChangePct value={r.change_pct} />
          </td>
          <td>
            <DayRange low={r.low} high={r.high} close={r.close} refPrice={r.ref} floor={r.floor} ceil={r.ceiling} />
          </td>
          <td>
            <Sparkline values={r.spark ?? []} refPrice={r.ref} />
          </td>
          <td className="num text-right text-ink-2">{volume(r.volume)}</td>
          <td className="num text-right text-ink-2">{money(r.value)}</td>
          <td className="num text-right font-medium">{r.ai_rank ?? "–"}</td>
          <td>{r.ai_votes != null ? <QuorumStrip votes={r.ai_votes} size="sm" showLabel={false} /> : null}</td>
        </tr>
      ))}
    </>
  );
}

function toneOf(r: BoardRow) {
  if (r.close == null || r.ref == null) return "text-ink";
  if (r.ceiling && r.close >= r.ceiling - 0.005) return "text-ceil";
  if (r.floor && r.close <= r.floor + 0.005) return "text-floor";
  if (Math.abs(r.close - r.ref) < 0.005) return "text-ref";
  return r.close > r.ref ? "text-up" : "text-down";
}

function toSectors(rows: BoardRow[]): SectorStat[] {
  const m = new Map<string, BoardRow[]>();
  rows.forEach((r) => m.set(r.sector, [...(m.get(r.sector) ?? []), r]));
  return [...m.entries()].map(([sector, rs]) => ({
    sector,
    n: rs.length,
    avg_change_pct: null,
    value: rs.reduce((a, r) => a + (r.value ?? 0), 0),
    avg_ai_rank: null,
    symbols: rs.map((r) => ({ symbol: r.symbol, change_pct: r.change_pct, value: r.value, ai_rank: r.ai_rank })),
  }));
}

/** Market pulse above the board: breadth, biggest movers, where the money went. */
function Pulse({ rows, onOpen }: { rows: BoardRow[]; onOpen: (s: string) => void }) {
  const live = rows.filter((r) => r.change_pct != null);
  const isCeil = (r: BoardRow) => r.close != null && r.ceiling != null && r.close >= r.ceiling - 0.005;
  const isFloor = (r: BoardRow) => r.close != null && r.floor != null && r.close <= r.floor + 0.005;
  const ceil = live.filter(isCeil).length;
  const floor = live.filter(isFloor).length;
  const up = live.filter((r) => (r.change_pct ?? 0) > 0.0005 && !isCeil(r)).length;
  const down = live.filter((r) => (r.change_pct ?? 0) < -0.0005 && !isFloor(r)).length;
  const flat = live.length - up - down - ceil - floor;
  const total = live.reduce((a, r) => a + (r.value ?? 0), 0);
  const sorted = [...live].sort((a, b) => (b.change_pct ?? 0) - (a.change_pct ?? 0));
  const gainers = sorted.slice(0, 5);
  const losers = sorted.slice(-5).reverse();
  const maxAbs = Math.max(0.001, ...[...gainers, ...losers].map((r) => Math.abs(r.change_pct ?? 0)));
  const sectors = toSectors(rows)
    .map((s) => ({ name: s.sector, value: s.value, chg: avg(s.symbols.map((x) => x.change_pct)) }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 6);
  const maxSec = Math.max(1, ...sectors.map((s) => s.value));
  const seg: [number, string, string][] = [
    [ceil, "bg-ceil", "Trần"],
    [up, "bg-up", "Tăng"],
    [flat, "bg-ref", "Đứng"],
    [down, "bg-down", "Giảm"],
    [floor, "bg-floor", "Sàn"],
  ];

  return (
    <div className="mb-3 grid gap-3 md:grid-cols-2 xl:grid-cols-[1fr_1.2fr_1.2fr]">
      <section className="panel p-3">
        <h2 className="text-sm font-semibold">Độ rộng thị trường</h2>
        <p className="mt-0.5 text-xs text-ink-3">78 mã, tổng giá trị {money(total)}</p>
        <div className="mt-3 flex h-3 w-full overflow-hidden" role="img" aria-label={`${up + ceil} mã tăng, ${flat} đứng, ${down + floor} giảm`}>
          {seg.map(([n, cls, label]) => (n > 0 ? <span key={label} className={cls} style={{ width: `${(n / Math.max(1, live.length)) * 100}%` }} /> : null))}
        </div>
        <dl className="mt-3 grid grid-cols-5 gap-1 text-center">
          {seg.map(([n, cls, label]) => (
            <div key={label}>
              <dt className="flex items-center justify-center gap-1 text-2xs text-ink-3">
                <span className={"inline-block h-2 w-2 " + cls} />
                {label}
              </dt>
              <dd className="num text-md font-semibold">{n}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="panel p-3">
        <h2 className="text-sm font-semibold">Biến động mạnh nhất</h2>
        <div className="mt-2 grid grid-cols-2 gap-x-4">
          {[gainers, losers].map((list, k) => (
            <ul key={k} className="grid gap-1">
              {list.map((r) => (
                <li key={r.symbol}>
                  <button type="button" onClick={() => onOpen(r.symbol)} className="grid w-full grid-cols-[38px_1fr_52px] items-center gap-2 text-left text-xs hover:bg-sunken">
                    <span className="font-semibold">{r.symbol}</span>
                    <span className="h-2 bg-line-soft">
                      <span className={"block h-2 " + (k === 0 ? "bg-up" : "bg-down")} style={{ width: `${(Math.abs(r.change_pct ?? 0) / maxAbs) * 100}%` }} />
                    </span>
                    <span className={"num text-right " + ((r.change_pct ?? 0) >= 0 ? "text-up" : "text-down")}>{pct(r.change_pct)}</span>
                  </button>
                </li>
              ))}
            </ul>
          ))}
        </div>
      </section>

      <section className="panel p-3 md:col-span-2 xl:col-span-1">
        <h2 className="text-sm font-semibold">Dòng tiền theo ngành</h2>
        <ul className="mt-2 grid gap-1">
          {sectors.map((s) => (
            <li key={s.name} className="grid grid-cols-[minmax(0,130px)_1fr_64px_48px] items-center gap-2 text-xs">
              <span className="truncate text-ink-2" title={s.name}>
                {s.name}
              </span>
              <span className="h-2 bg-line-soft">
                <span className="block h-2 bg-brand" style={{ width: `${(s.value / maxSec) * 100}%` }} />
              </span>
              <span className="num text-right text-ink-2">{money(s.value)}</span>
              <span className={"num text-right " + ((s.chg ?? 0) >= 0 ? "text-up" : "text-down")}>{pct(s.chg, 1)}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}

function avg(xs: (number | null)[]): number | null {
  const v = xs.filter((x): x is number => x != null);
  return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null;
}
