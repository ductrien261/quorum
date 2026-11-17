"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import useSWR from "swr";

import { api, getToken, setToken } from "./api";

export interface User {
  id: number;
  email: string;
  name: string;
}

interface PageContext {
  page: string;
  symbol?: string;
  date?: string;
}

interface SessionValue {
  user: User | null;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  watchlist: string[];
  toggleWatch: (symbol: string) => Promise<"added" | "removed" | "login">;
  pageContext: PageContext;
  setPageContext: (c: PageContext) => void;
  chatOpen: boolean;
  setChatOpen: (open: boolean) => void;
  ask: (question: string) => void;
  pendingQuestion: string | null;
  clearPending: () => void;
  dark: boolean;
  toggleDark: () => void;
}

const Ctx = createContext<SessionValue | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);
  const [pageContext, setPageContext] = useState<PageContext>({ page: "Tổng quan" });
  const [chatOpen, setChatOpen] = useState(true);
  const [pendingQuestion, setPending] = useState<string | null>(null);
  const [dark, setDark] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setReady(true);
    } else {
      api<User>("/api/auth/me")
        .then(setUser)
        .catch(() => setToken(null))
        .finally(() => setReady(true));
    }
    try {
      const d = window.localStorage.getItem("quorum.dark") === "1";
      setDark(d);
      document.documentElement.classList.toggle("dark", d);
      const c = window.localStorage.getItem("quorum.chat");
      if (c === "0" || window.innerWidth < 1100) setChatOpen(false);
    } catch {
      /* ignore */
    }
  }, []);

  const { data: wl, mutate: mutateWl } = useSWR<{ symbols: string[] }>(user ? "/api/watchlist" : null, (p: string) => api<{ symbols: string[] }>(p));

  const login = useCallback(async (email: string, password: string) => {
    const r = await api<{ user: User; token: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
    setToken(r.token);
    setUser(r.user);
  }, []);

  const register = useCallback(async (name: string, email: string, password: string) => {
    const r = await api<{ user: User; token: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    });
    setToken(r.token);
    setUser(r.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  const watchlist = useMemo(() => wl?.symbols ?? [], [wl]);

  const toggleWatch = useCallback(
    async (symbol: string) => {
      if (!user) return "login" as const;
      const has = watchlist.includes(symbol);
      await api(`/api/watchlist/${symbol}`, { method: has ? "DELETE" : "PUT" });
      await mutateWl();
      return has ? ("removed" as const) : ("added" as const);
    },
    [user, watchlist, mutateWl],
  );

  const setChat = useCallback((open: boolean) => {
    setChatOpen(open);
    try {
      window.localStorage.setItem("quorum.chat", open ? "1" : "0");
    } catch {
      /* ignore */
    }
  }, []);

  const ask = useCallback(
    (q: string) => {
      setPending(q);
      setChat(true);
    },
    [setChat],
  );

  const toggleDark = useCallback(() => {
    setDark((d) => {
      const n = !d;
      document.documentElement.classList.toggle("dark", n);
      try {
        window.localStorage.setItem("quorum.dark", n ? "1" : "0");
      } catch {
        /* ignore */
      }
      return n;
    });
  }, []);

  const value: SessionValue = {
    user,
    ready,
    login,
    register,
    logout,
    watchlist,
    toggleWatch,
    pageContext,
    setPageContext,
    chatOpen,
    setChatOpen: setChat,
    ask,
    pendingQuestion,
    clearPending: () => setPending(null),
    dark,
    toggleDark,
  };
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSession() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useSession outside SessionProvider");
  return v;
}

/** Tell the assistant which page/stock the user is looking at. */
export function usePageContext(page: string, symbol?: string, date?: string) {
  const { setPageContext } = useSession();
  useEffect(() => {
    setPageContext({ page, symbol, date });
  }, [page, symbol, date, setPageContext]);
}
