"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

export function Navbar() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="sticky top-0 z-10 border-b border-slate-200 bg-white/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link href="/" className="text-lg font-semibold text-slate-900">
          DE<span className="text-brand-600">Platform</span>
        </Link>
        <nav className="flex items-center gap-3 text-sm">
          {loading ? (
            <span className="text-slate-400">…</span>
          ) : user ? (
            <>
              <span className="text-slate-600">
                {user.nickname} · {user.points_balance} 积分
              </span>
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
