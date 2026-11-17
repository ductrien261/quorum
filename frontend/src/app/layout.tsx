import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/shell/app-shell";
import { SessionProvider } from "@/lib/session";

import "./globals.css";

export const metadata: Metadata = {
  title: { default: "Quorum — Gợi ý cổ phiếu bằng hội đồng AI", template: "%s · Quorum" },
  description:
    "Quorum chấm điểm 78 cổ phiếu Việt Nam mỗi tối bằng mô hình học sâu MIDMoE: 10 mô hình cùng bỏ phiếu, kèm lý do và trợ lý AI giải thích.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#0B5563",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="vi" suppressHydrationWarning>
      <body>
        <SessionProvider>
          <AppShell>{children}</AppShell>
        </SessionProvider>
      </body>
    </html>
  );
}
