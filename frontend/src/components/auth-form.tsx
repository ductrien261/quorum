"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { Logo, LogoMark } from "@/components/ui/logo";
import { useSession } from "@/lib/session";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const { login, register } = useSession();
  const router = useRouter();
  const params = useSearchParams();
  const next = params.get("next") || "/";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const isLogin = mode === "login";

  return (
    <div className="grid min-h-screen bg-canvas lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
      <aside className="relative hidden overflow-hidden bg-[#083E48] text-white lg:flex lg:flex-col lg:items-center lg:justify-center">
        <LogoMark size={720} className="pointer-events-none absolute -bottom-40 -right-48 text-white/[0.025]" />
        <Link href="/" className="relative flex flex-col items-center gap-5 text-white" aria-label="Quorum, về trang chủ">
          <LogoMark size={96} />
          <span className="text-[44px] font-bold leading-none tracking-[-0.02em]">Quorum</span>
        </Link>
        <p className="relative mt-4 text-sm text-white/70">Gợi ý cổ phiếu Việt Nam bằng mô hình AI</p>
      </aside>

      <main className="flex flex-col px-5 py-6 sm:px-10">
        <div className="flex items-center justify-between">
          <Link href="/" className="lg:invisible" aria-label="Về trang chủ">
            <Logo />
          </Link>
          <Link href="/" className="text-sm text-ink-2 hover:text-brand">
            Về trang chủ
          </Link>
        </div>
        <div className="mx-auto my-auto w-full max-w-[380px] py-10">
          <LogoMark size={36} className="mb-5 hidden text-brand lg:block" />
          <h1 className="text-xl font-bold tracking-[-0.01em]">{isLogin ? "Đăng nhập" : "Tạo tài khoản"}</h1>
          <p className="mt-2 text-sm text-ink-2">
            {isLogin ? "Để xem danh sách theo dõi và lưu lịch sử trò chuyện với trợ lý." : "Miễn phí. Chỉ cần email để lưu danh sách theo dõi."}
          </p>
          <form
            className="mt-5 grid gap-3"
            onSubmit={async (e) => {
              e.preventDefault();
              setError(null);
              setBusy(true);
              try {
                if (isLogin) await login(email, password);
                else await register(name, email, password);
                router.push(next);
              } catch (err) {
                setError(err instanceof Error ? err.message : String(err));
              } finally {
                setBusy(false);
              }
            }}
          >
            {!isLogin && (
              <label className="grid gap-1 text-sm">
                Tên hiển thị
                <input className="input" required value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" />
              </label>
            )}
            <label className="grid gap-1 text-sm">
              Email
              <input className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
            </label>
            <label className="grid gap-1 text-sm">
              Mật khẩu
              <input
                className="input"
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={isLogin ? "current-password" : "new-password"}
              />
              {!isLogin && <span className="text-xs text-ink-3">Tối thiểu 6 ký tự.</span>}
            </label>
            {error && <p className="border-l-2 border-down pl-2 text-sm text-down">{error}</p>}
            <button className="btn-primary mt-1 h-9" disabled={busy}>
              {busy ? "Đang xử lý" : isLogin ? "Đăng nhập" : "Tạo tài khoản"}
            </button>
          </form>
          <p className="mt-6 border-t border-line pt-4 text-sm text-ink-2">
            {isLogin ? "Chưa có tài khoản? " : "Đã có tài khoản? "}
            <Link href={`${isLogin ? "/dang-ky" : "/dang-nhap"}?next=${encodeURIComponent(next)}`} className="font-medium text-brand hover:underline">
              {isLogin ? "Tạo tài khoản" : "Đăng nhập"}
            </Link>
          </p>
        </div>
      </main>
    </div>
  );
}
