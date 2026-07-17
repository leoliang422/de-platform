"use client";

import Link from "next/link";

import { useAuth } from "@/lib/auth";

/** 首页注册/登录 CTA：仅未登录时展示，与 Navbar 鉴权表现一致。 */
export function HomeAuthCtas() {
  const { user, loading } = useAuth();

  if (loading || user) {
    return null;
  }

  return (
    <div className="mt-6 flex justify-center gap-3">
      <Link
        href="/register"
        className="rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white hover:bg-brand-700"
      >
        免费注册
      </Link>
      <Link
        href="/login"
        className="rounded-lg border border-slate-300 px-5 py-2.5 font-medium text-slate-700 hover:bg-slate-100"
      >
        登录
      </Link>
    </div>
  );
}
