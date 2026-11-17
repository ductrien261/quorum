"use client";

import clsx from "clsx";
import { Star } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { changeTone, pct, price, priceTone, signed, toneClass } from "@/lib/format";
import { useSession } from "@/lib/session";

export function PriceText({
  value,
  refPrice,
  ceil,
  floor,
  className,
}: {
  value: number | null | undefined;
  refPrice: number | null | undefined;
  ceil?: number | null;
  floor?: number | null;
  className?: string;
}) {
  return <span className={clsx("num", toneClass[priceTone(value, refPrice, ceil, floor)], className)}>{price(value)}</span>;
}

export function ChangePct({ value, className, digits = 2 }: { value: number | null | undefined; className?: string; digits?: number }) {
  return <span className={clsx("num", toneClass[changeTone(value)], className)}>{pct(value, digits)}</span>;
}

export function ChangeAbs({ value, className }: { value: number | null | undefined; className?: string }) {
  return <span className={clsx("num", toneClass[changeTone(value)], className)}>{signed(value)}</span>;
}

/** Rank movement versus the previous run: positive = moved up. */
export function RankDelta({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-ink-3">–</span>;
  if (value === 0) return <span className="num text-ink-3">0</span>;
  return (
    <span className={clsx("num text-xs font-medium", value > 0 ? "text-up" : "text-down")}>
      {value > 0 ? "▲" : "▼"} {Math.abs(value)}
    </span>
  );
}

export function TickerLink({ symbol, className }: { symbol: string; className?: string }) {
  return (
    <Link href={`/co-phieu/${symbol}`} className={clsx("font-semibold text-ink hover:text-brand hover:underline", className)}>
      {symbol}
    </Link>
  );
}

export function StarButton({ symbol, className }: { symbol: string; className?: string }) {
  const { watchlist, toggleWatch } = useSession();
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const on = watchlist.includes(symbol);
  return (
    <button
      type="button"
      disabled={busy}
      onClick={async (e) => {
        e.stopPropagation();
        setBusy(true);
        const r = await toggleWatch(symbol).finally(() => setBusy(false));
        if (r === "login") router.push(`/dang-nhap?next=/co-phieu/${symbol}`);
      }}
      className={clsx("inline-flex h-6 w-6 items-center justify-center text-ink-3 hover:text-ref", className)}
      aria-label={on ? `Bỏ ${symbol} khỏi danh sách theo dõi` : `Theo dõi ${symbol}`}
      title={on ? "Bỏ theo dõi" : "Theo dõi"}
    >
      <Star size={15} strokeWidth={1.8} className={on ? "fill-ref text-ref" : ""} />
    </button>
  );
}

export function ErrorBox({ error }: { error: unknown }) {
  const msg = error instanceof Error ? error.message : String(error);
  return (
    <div className="border border-down/40 bg-down/5 px-3 py-2.5 text-sm text-ink">
      <span className="font-medium text-down">Không tải được dữ liệu.</span> {msg}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse bg-line-soft", className)} />;
}

export function Empty({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div className="px-4 py-10 text-center">
      <p className="text-base font-medium text-ink">{title}</p>
      {children && <div className="mt-1.5 text-sm text-ink-2">{children}</div>}
    </div>
  );
}

export function Segmented<T extends string | number>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex border border-line">
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          onClick={() => onChange(o.value)}
          className={clsx(
            "h-7 border-r border-line px-2.5 text-xs font-medium last:border-r-0",
            o.value === value ? "bg-ink text-surface" : "bg-surface text-ink-2 hover:text-ink",
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function AskButton({ question, label = "Hỏi trợ lý" }: { question: string; label?: string }) {
  const { ask } = useSession();
  return (
    <button type="button" className="text-xs font-medium text-brand hover:underline" onClick={() => ask(question)}>
      {label}
    </button>
  );
}
