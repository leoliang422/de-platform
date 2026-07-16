"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/lib/auth";

export function RequireAuth({
  adminOnly = false,
  children,
}: {
  adminOnly?: boolean;
  children: ReactNode;
}) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading) return <p className="text-sm text-slate-400">加载中…</p>;
  if (!user) return null;
  if (adminOnly && user.role !== "admin") {
    return <p className="text-sm text-red-600">需要管理员权限。</p>;
  }
  return <>{children}</>;
}
