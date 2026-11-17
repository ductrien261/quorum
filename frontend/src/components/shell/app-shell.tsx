"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { ChatPanel } from "@/components/chat/chat-panel";
import { IndexStrip } from "@/components/shell/index-strip";
import { TopBar } from "@/components/shell/top-bar";

/** Pages that get a bare, focused screen: no navigation, index strip, assistant or footer. */
const BARE = ["/dang-nhap", "/dang-ky"];

export function AppShell({ children }: { children: React.ReactNode }) {
  const path = usePathname();
  if (BARE.some((p) => path.startsWith(p))) return <>{children}</>;

  return (
    <>
      <TopBar />
      <div className="flex min-h-[calc(100vh-48px-28px)] pb-7">
        <div className="min-w-0 flex-1">
          <IndexStrip />
          <main className="px-3 py-4 lg:px-4">{children}</main>
        </div>
        <ChatPanel />
      </div>
      <footer className="fixed inset-x-0 bottom-0 z-30 flex h-7 items-center justify-between gap-3 border-t border-line bg-surface px-3 text-2xs text-ink-3 lg:px-4">
        <span className="truncate">Điểm AI là công cụ tham khảo, không phải khuyến nghị đầu tư. Giá từ KBS, tin tức từ CafeF.</span>
        <Link href="/gioi-thieu" className="shrink-0 text-ink-2 hover:text-brand">
          Cách Quorum hoạt động
        </Link>
      </footer>
    </>
  );
}
