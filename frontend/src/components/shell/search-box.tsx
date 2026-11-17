"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, type SearchHit } from "@/lib/api";

export function SearchBox() {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.key === "k" && (e.metaKey || e.ctrlKey)) || (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA")) {
        e.preventDefault();
        ref.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    if (!q.trim()) {
      setHits([]);
      return;
    }
    const t = setTimeout(() => {
      api<SearchHit[]>(`/api/search?q=${encodeURIComponent(q.trim())}`)
        .then((h) => {
          setHits(h);
          setActive(0);
        })
        .catch(() => setHits([]));
    }, 120);
    return () => clearTimeout(t);
  }, [q]);

  const go = (symbol: string) => {
    setQ("");
    setOpen(false);
    ref.current?.blur();
    router.push(`/co-phieu/${symbol}`);
  };

  return (
    <div className="relative w-full max-w-[300px]">
      <Search size={14} className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-3" />
      <input
        ref={ref}
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={(e) => {
          if (e.key === "ArrowDown") setActive((a) => Math.min(a + 1, hits.length - 1));
          else if (e.key === "ArrowUp") setActive((a) => Math.max(a - 1, 0));
          else if (e.key === "Enter" && hits[active]) go(hits[active].symbol);
          else if (e.key === "Escape") ref.current?.blur();
        }}
        placeholder="Tìm mã hoặc tên công ty"
        className="input pl-8 pr-10"
        aria-label="Tìm mã chứng khoán"
      />
      <kbd className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 border border-line px-1 text-2xs text-ink-3">/</kbd>
      {open && hits.length > 0 && (
        <ul className="absolute left-0 right-0 top-9 z-50 border border-line bg-surface shadow-[0_8px_24px_rgb(15_26_43/0.12)]">
          {hits.map((h, i) => (
            <li key={h.symbol}>
              <button
                type="button"
                onMouseDown={() => go(h.symbol)}
                onMouseEnter={() => setActive(i)}
                className={`flex w-full items-center gap-3 px-3 py-2 text-left ${i === active ? "bg-brand-tint" : ""}`}
              >
                <span className="w-10 font-semibold">{h.symbol}</span>
                <span className="min-w-0 flex-1 truncate text-sm text-ink-2">{h.short_name}</span>
                {h.ai_rank != null && <span className="num text-xs text-ink-3">hạng {h.ai_rank}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
