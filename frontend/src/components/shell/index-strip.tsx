"use client";

import Link from "next/link";
import useSWR from "swr";

import { fetcher, type Health, type Overview } from "@/lib/api";
import { day, num, pct } from "@/lib/format";

const tone = (v: number | null | undefined) => (v == null ? "text-white/60" : v > 0 ? "text-[#4ADE80]" : v < 0 ? "text-[#F87171]" : "text-[#FACC15]");

/** Dark market strip under the top bar: VN-Index, breadth, movers. */
export function IndexStrip() {
  const { data } = useSWR<Overview>("/api/market/overview", fetcher, { refreshInterval: 60_000 });
  const { data: health } = useSWR<Health>("/api/health", fetcher, { refreshInterval: 120_000 });
  const idx = data?.index;
  return (
    <div className="flex h-8 items-center gap-5 overflow-x-auto whitespace-nowrap bg-strip px-3 text-xs text-white/85 thin-scroll lg:px-4">
      {health?.demo_data && (
        <span className="bg-[#FACC15] px-1.5 py-0.5 font-semibold text-[#13233A]" title="Giá đang là dữ liệu giả lập để phát triển giao diện">
          Giá giả lập
        </span>
      )}
      <span className="flex items-center gap-2">
        <span className="font-semibold text-white">VN-Index</span>
        <span className={`num ${tone(idx?.change)}`}>{num(idx?.close, 2)}</span>
        <span className={`num ${tone(idx?.change)}`}>
          {idx?.change != null ? `${idx.change > 0 ? "+" : ""}${num(idx.change, 2)}` : ""} ({pct(idx?.change_pct)})
        </span>
      </span>
      {data && (
        <span className="num flex items-center gap-2" title="Số mã tăng / đứng giá / giảm trong rổ 78 mã">
          <span className="text-[#4ADE80]">▲ {data.breadth.up}</span>
          <span className="text-[#FACC15]">■ {data.breadth.flat}</span>
          <span className="text-[#F87171]">▼ {data.breadth.down}</span>
        </span>
      )}
      <span className="h-3 w-px bg-white/20" />
      {data?.gainers.slice(0, 4).map((g) => (
        <Link key={g.symbol} href={`/co-phieu/${g.symbol}`} className="flex gap-1.5 hover:text-white">
          <span className="font-medium">{g.symbol}</span>
          <span className={`num ${tone(g.change_pct)}`}>{pct(g.change_pct)}</span>
        </Link>
      ))}
      {data?.losers.slice(0, 3).map((g) => (
        <Link key={g.symbol} href={`/co-phieu/${g.symbol}`} className="flex gap-1.5 hover:text-white">
          <span className="font-medium">{g.symbol}</span>
          <span className={`num ${tone(g.change_pct)}`}>{pct(g.change_pct)}</span>
        </Link>
      ))}
      <span className="ml-auto pl-4 text-white/55">
        {data ? <>Dữ liệu phiên {day(data.date)}</> : null}
      </span>
    </div>
  );
}
