"use client";

import { hierarchy, treemap, treemapSquarify } from "d3-hierarchy";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import type { SectorStat } from "@/lib/api";
import { pct } from "@/lib/format";

/** Diverging fill for a daily % change, capped at ±4%. */
function fill(chg: number | null | undefined): string {
  if (chg == null) return "rgb(var(--line-soft))";
  const t = Math.max(-1, Math.min(1, chg / 0.04));
  if (Math.abs(t) < 0.03) return "rgb(var(--ref) / 0.30)";
  return t > 0 ? `rgb(var(--up) / ${0.18 + 0.72 * t})` : `rgb(var(--down) / ${0.18 + 0.72 * -t})`;
}

interface Leaf {
  name: string;
  value: number;
  chg: number | null;
  sector: string;
  rank?: number | null;
}

/** Market map: one tile per stock, sized by traded value, grouped by sector, coloured by today's change. */
export function SectorTreemap({ sectors, height = 340 }: { sectors: SectorStat[]; height?: number }) {
  const box = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);

  useEffect(() => {
    if (!box.current) return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(320, Math.floor(e.contentRect.width))));
    ro.observe(box.current);
    return () => ro.disconnect();
  }, []);

  const layout = useMemo(() => {
    type Node = { name: string; children?: Node[]; leaf?: Leaf; value?: number };
    const data: Node = {
      name: "root",
      children: sectors.map((s) => ({
        name: s.sector,
        children: s.symbols.map((x) => ({
          name: x.symbol,
          value: Math.max(x.value ?? 0, 1e8),
          leaf: { name: x.symbol, value: x.value ?? 0, chg: x.change_pct, sector: s.sector, rank: x.ai_rank },
        })),
      })),
    };
    const root = hierarchy<Node>(data)
      .sum((d) => d.value ?? 0)
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    treemap<Node>().tile(treemapSquarify).size([width, height]).paddingInner(1).paddingTop((d) => (d.depth === 1 ? 16 : 0))(root);
    return root;
  }, [sectors, width, height]);

  return (
    <div ref={box} className="relative w-full select-none" style={{ height }}>
      {layout.children?.map((sec) => {
        const s = sec as unknown as { x0: number; y0: number; x1: number; y1: number; data: { name: string } };
        return (
          <div
            key={s.data.name}
            className="absolute overflow-hidden truncate px-1 text-2xs font-medium text-ink-2"
            style={{ left: s.x0, top: s.y0, width: s.x1 - s.x0, height: 16 }}
          >
            {s.data.name}
          </div>
        );
      })}
      {layout.leaves().map((l) => {
        const n = l as unknown as { x0: number; y0: number; x1: number; y1: number; data: { leaf?: Leaf } };
        const leaf = n.data.leaf!;
        const w = n.x1 - n.x0;
        const h = n.y1 - n.y0;
        const big = w > 46 && h > 30;
        return (
          <Link
            key={leaf.name}
            href={`/co-phieu/${leaf.name}`}
            className="absolute flex flex-col items-center justify-center overflow-hidden text-ink outline-none hover:ring-2 hover:ring-inset hover:ring-ink focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand"
            style={{ left: n.x0, top: n.y0, width: w, height: h, background: fill(leaf.chg) }}
            title={`${leaf.name}, ${leaf.sector}: ${pct(leaf.chg)}${leaf.rank ? `, hạng AI ${leaf.rank}` : ""}`}
          >
            {w > 26 && h > 14 && <span className={big ? "text-xs font-semibold" : "text-2xs font-semibold"}>{leaf.name}</span>}
            {big && <span className="num text-2xs">{pct(leaf.chg, 1)}</span>}
          </Link>
        );
      })}
    </div>
  );
}
