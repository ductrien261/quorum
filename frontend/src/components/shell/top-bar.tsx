"use client";

import clsx from "clsx";
import { Menu, MessageSquareText, Moon, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { Logo } from "@/components/ui/logo";
import { useSession } from "@/lib/session";

import { SearchBox } from "./search-box";

export const NAV = [
  { href: "/", label: "Tổng quan" },
  { href: "/bang-gia", label: "Bảng giá" },
  { href: "/goi-y", label: "Gợi ý AI" },
  { href: "/bo-loc", label: "Bộ lọc" },
  { href: "/theo-doi", label: "Theo dõi" },
  { href: "/hieu-qua", label: "Hiệu quả gợi ý" },
];

export function TopBar() {
  const path = usePathname();
  const { user, logout, chatOpen, setChatOpen, dark, toggleDark } = useSession();
  const [menu, setMenu] = useState(false);
  const isActive = (href: string) => (href === "/" ? path === "/" : path.startsWith(href));

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-surface">
      <div className="flex h-12 items-center gap-4 px-3 lg:px-4">
        <button className="lg:hidden" onClick={() => setMenu((m) => !m)} aria-label="Mở menu">
          {menu ? <X size={18} /> : <Menu size={18} />}
        </button>
        <Link href="/" aria-label="Quorum, về trang tổng quan">
          <Logo />
        </Link>
        <nav className="ml-2 hidden h-12 items-stretch gap-5 lg:flex" aria-label="Điều hướng chính">
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              className={clsx(
                "flex items-center border-b-2 text-sm font-medium",
                isActive(n.href) ? "border-brand text-ink" : "border-transparent text-ink-2 hover:text-ink",
              )}
            >
              {n.label}
            </Link>
          ))}
        </nav>
        <div className="ml-auto flex flex-1 items-center justify-end gap-2">
          <div className="hidden w-full max-w-[300px] sm:block">
            <SearchBox />
          </div>
          <button className="btn w-8 px-0" onClick={toggleDark} aria-label={dark ? "Chuyển giao diện sáng" : "Chuyển giao diện tối"}>
            {dark ? <Sun size={15} /> : <Moon size={15} />}
          </button>
          <button
            className={clsx("btn", chatOpen && "border-brand text-brand")}
            onClick={() => setChatOpen(!chatOpen)}
            aria-pressed={chatOpen}
          >
            <MessageSquareText size={15} />
            <span className="hidden md:inline">Trợ lý</span>
          </button>
          {user ? (
            <div className="hidden items-center gap-2 md:flex">
              <span className="max-w-[120px] truncate text-sm text-ink-2">{user.name}</span>
              <button className="text-sm text-ink-2 hover:text-ink" onClick={logout}>
                Đăng xuất
              </button>
            </div>
          ) : (
            <Link href="/dang-nhap" className="btn-primary">
              Đăng nhập
            </Link>
          )}
        </div>
      </div>
      {menu && (
        <nav className="border-t border-line px-3 py-2 lg:hidden" aria-label="Điều hướng">
          <div className="mb-2 sm:hidden">
            <SearchBox />
          </div>
          {NAV.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              onClick={() => setMenu(false)}
              className={clsx("block py-2 text-sm", isActive(n.href) ? "font-semibold text-brand" : "text-ink")}
            >
              {n.label}
            </Link>
          ))}
        </nav>
      )}
    </header>
  );
}
