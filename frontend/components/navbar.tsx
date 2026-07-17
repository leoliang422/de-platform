"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { getAccessToken, getUnreadCount } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const MODULES: { href: string; label: string }[] = [
  { href: "/knowledge", label: "八股" },
  { href: "/sql", label: "SQL 题库" },
  { href: "/interview", label: "面经" },
  { href: "/projects", label: "项目" },
];

export function Navbar() {
  const { user, loading, logout } = useAuth();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    if (!user) {
      setUnread(0);
      return;
    }
    const poll = () => {
      const token = getAccessToken();
      if (!token) return;
      getUnreadCount(token)
        .then((r) => setUnread(r.unread))
        .catch(() => {});
    };
    poll();
    const timer = setInterval(poll, 30000);
    return () => clearInterval(timer);
  }, [user]);

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <div className="flex items-center gap-2 sm:gap-5">
          <Link href="/" className="text-lg font-semibold text-slate-900">
            DE<span className="text-brand-600">Platform</span>
          </Link>
          <nav className="flex items-center gap-1 text-sm">
            {MODULES.map((m) => {
              const active = pathname === m.href || pathname.startsWith(`${m.href}/`);
              return (
                <Link
                  key={m.href}
                  href={m.href}
                  className={`rounded-md px-2.5 py-1.5 transition sm:px-3 ${
                    active
                      ? "bg-brand-50 font-medium text-brand-700"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                >
                  {m.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <nav className="flex items-center gap-3 text-sm">
          {loading ? (
            <span className="text-slate-400">…</span>
          ) : user ? (
            <>
              <Link
                href="/submit"
                className="rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-100"
              >
                投稿
              </Link>
              {user.role === "admin" && (
                <Link
                  href="/admin"
                  className="rounded-md px-3 py-1.5 text-brand-600 hover:bg-slate-100"
                >
                  管理
                </Link>
              )}
              <Link
                href="/me/notifications"
                className="relative rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-100"
              >
                通知
                {unread > 0 && (
                  <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-medium text-white">
                    {unread > 99 ? "99+" : unread}
                  </span>
                )}
              </Link>
              <Link
                href="/me"
                className="text-slate-600 hover:text-slate-900"
              >
                {user.nickname} · {user.points_balance} 积分
              </Link>
              <button
                onClick={logout}
                className="rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-100"
              >
                退出
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="rounded-md px-3 py-1.5 text-slate-600 hover:bg-slate-100"
              >
                登录
              </Link>
              <Link
                href="/register"
                className="rounded-md bg-brand-600 px-3 py-1.5 font-medium text-white hover:bg-brand-700"
              >
                注册
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
