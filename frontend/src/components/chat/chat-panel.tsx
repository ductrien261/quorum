"use client";

import clsx from "clsx";
import { ArrowUp, RotateCcw, X } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import useSWR from "swr";

import { API_URL, fetcher, getToken, type Board } from "@/lib/api";
import { pct, price } from "@/lib/format";
import { useSession } from "@/lib/session";

interface Msg {
  role: "user" | "assistant";
  text: string;
  status?: string;
  tickers?: string[];
  error?: string;
}

function suggestions(page: string, symbol?: string): string[] {
  if (symbol)
    return [
      `Vì sao ${symbol} được xếp hạng như vậy?`,
      `Tin tức gần đây của ${symbol} có gì đáng chú ý?`,
      `So sánh ${symbol} với các mã cùng ngành`,
    ];
  if (page === "Hiệu quả gợi ý")
    return ["Gợi ý của Quorum đáng tin đến mức nào?", "Top 5 năm 2025 so với VN-Index thế nào?"];
  if (page === "Bộ lọc") return ["Lọc mã ngân hàng có RSI dưới 40", "Mã nào trong top 10 chưa quá mua?"];
  return ["Top 5 mã cho phiên tới là gì?", "Hôm nay thị trường thế nào?", "Mã nào tăng hạng mạnh nhất?"];
}

function TickerCard({ symbol, row }: { symbol: string; row?: Board["rows"][number] }) {
  const ch = row?.change_pct;
  return (
    <Link
      href={`/co-phieu/${symbol}`}
      className="flex min-w-[118px] flex-col border border-line bg-surface px-2.5 py-1.5 hover:border-brand"
    >
      <span className="flex items-baseline justify-between gap-2">
        <span className="font-semibold">{symbol}</span>
        {row?.ai_rank && <span className="num text-2xs text-ink-3">hạng {row.ai_rank}</span>}
      </span>
      <span className="num text-xs">
        {price(row?.close)}{" "}
        <span className={ch == null ? "text-ink-3" : ch > 0 ? "text-up" : ch < 0 ? "text-down" : "text-ref"}>{pct(ch)}</span>
      </span>
    </Link>
  );
}

export function ChatPanel() {
  const { chatOpen, setChatOpen, pageContext, pendingQuestion, clearPending } = useSession();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const sessionRef = useRef<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const { data: board } = useSWR<Board>(chatOpen ? "/api/market/board" : null, fetcher);
  const rowOf = (s: string) => board?.rows.find((r) => r.symbol === s);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [msgs]);

  const send = useCallback(
    async (text: string) => {
      const q = text.trim();
      if (!q || busy) return;
      setInput("");
      setBusy(true);
      setMsgs((m) => [...m, { role: "user", text: q }, { role: "assistant", text: "", status: "Đang suy nghĩ" }]);
      const patch = (fn: (m: Msg) => Msg) =>
        setMsgs((all) => {
          const copy = all.slice();
          copy[copy.length - 1] = fn(copy[copy.length - 1]);
          return copy;
        });
      try {
        const headers: Record<string, string> = { "Content-Type": "application/json" };
        const token = getToken();
        if (token) headers.Authorization = `Bearer ${token}`;
        const res = await fetch(`${API_URL}/api/chat`, {
          method: "POST",
          headers,
          body: JSON.stringify({ message: q, session_id: sessionRef.current, context: pageContext }),
        });
        if (!res.ok || !res.body) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || `Lỗi ${res.status}`);
        }
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buf = "";
        for (;;) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          const events = buf.split("\n\n");
          buf = events.pop() ?? "";
          for (const raw of events) {
            const line = raw.trim();
            if (!line.startsWith("data:")) continue;
            const ev = JSON.parse(line.slice(5));
            if (ev.type === "session") sessionRef.current = ev.session_id;
            else if (ev.type === "status") patch((m) => ({ ...m, status: ev.text }));
            else if (ev.type === "delta") patch((m) => ({ ...m, status: undefined, text: m.text + ev.text }));
            else if (ev.type === "tickers") patch((m) => ({ ...m, tickers: ev.symbols }));
            else if (ev.type === "error") patch((m) => ({ ...m, status: undefined, error: ev.message }));
          }
        }
        patch((m) => ({ ...m, status: undefined }));
      } catch (e) {
        patch((m) => ({ ...m, status: undefined, error: e instanceof Error ? e.message : String(e) }));
      } finally {
        setBusy(false);
      }
    },
    [busy, pageContext],
  );

  useEffect(() => {
    if (pendingQuestion && chatOpen) {
      send(pendingQuestion);
      clearPending();
    }
  }, [pendingQuestion, chatOpen, send, clearPending]);

  if (!chatOpen) return null;

  return (
    <aside
      className="fixed inset-0 z-50 flex flex-col border-l border-line bg-surface xl:sticky xl:top-12 xl:z-auto xl:h-[calc(100vh-48px-28px)] xl:w-[360px] xl:shrink-0"
      aria-label="Trợ lý Quorum"
    >
      <div className="flex h-10 items-center justify-between border-b border-line px-3">
        <span className="text-base font-semibold">Trợ lý Quorum</span>
        <div className="flex items-center gap-1">
          <button
            className="inline-flex h-7 w-7 items-center justify-center text-ink-2 hover:text-ink disabled:opacity-40"
            onClick={() => {
              setMsgs([]);
              sessionRef.current = null;
            }}
            disabled={busy || msgs.length === 0}
            aria-label="Cuộc trò chuyện mới"
            title="Cuộc trò chuyện mới"
          >
            <RotateCcw size={14} />
          </button>
          <button className="inline-flex h-7 w-7 items-center justify-center text-ink-2 hover:text-ink" onClick={() => setChatOpen(false)} aria-label="Đóng trợ lý">
            <X size={16} />
          </button>
        </div>
      </div>
      <div className="border-b border-line-soft bg-sunken px-3 py-1.5 text-xs text-ink-2">
        Đang xem: <span className="font-medium text-ink">{pageContext.symbol ?? pageContext.page}</span>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3 thin-scroll">
        {msgs.length === 0 && (
          <div>
            <p className="text-sm text-ink-2">
              Hỏi về gợi ý của mô hình, lý do một mã được xếp hạng, chỉ báo kỹ thuật hay tin tức. Trợ lý trả lời bằng dữ liệu của
              Quorum.
            </p>
            <div className="mt-3 flex flex-col">
              {suggestions(pageContext.page, pageContext.symbol).map((s) => (
                <button key={s} onClick={() => send(s)} className="border-b border-line-soft py-2 text-left text-sm text-brand hover:text-brand-deep">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex flex-col gap-4">
          {msgs.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="ml-8 self-end border-l-2 border-brand bg-brand-tint px-3 py-2 text-sm">
                {m.text}
              </div>
            ) : (
              <div key={i} className="text-sm leading-relaxed">
                {m.status && (
                  <p className="flex items-center gap-2 text-xs text-ink-3">
                    <span className="inline-block h-2 w-2 animate-pulse bg-brand" />
                    {m.status}…
                  </p>
                )}
                {m.text && (
                  <div className="chat-md">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        a: ({ href, children }) => (
                          <a href={href} target="_blank" rel="noreferrer" className="text-brand underline">
                            {children}
                          </a>
                        ),
                      }}
                    >
                      {m.text}
                    </ReactMarkdown>
                  </div>
                )}
                {m.error && <p className="mt-1 border-l-2 border-down pl-2 text-sm text-down">{m.error}</p>}
                {m.tickers && m.tickers.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {m.tickers.map((s) => (
                      <TickerCard key={s} symbol={s} row={rowOf(s)} />
                    ))}
                  </div>
                )}
              </div>
            ),
          )}
        </div>
        <div ref={endRef} />
      </div>

      <form
        className="border-t border-line p-2"
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
      >
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            rows={2}
            placeholder="Nhập câu hỏi, Enter để gửi"
            className="input h-auto min-h-[52px] resize-none py-2"
            aria-label="Câu hỏi cho trợ lý"
          />
          <button type="submit" disabled={busy || !input.trim()} className={clsx("btn-primary h-[52px] w-10 px-0")} aria-label="Gửi">
            <ArrowUp size={16} />
          </button>
        </div>
        <p className="mt-1.5 text-2xs text-ink-3">Câu trả lời là thông tin tham khảo, không phải khuyến nghị mua bán.</p>
      </form>
    </aside>
  );
}
