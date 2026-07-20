"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/lib/auth";
import {
  ApiError,
  getAccessToken,
  unlockContent,
  unlockModule,
  type AccessModule,
  type PayableType,
} from "@/lib/api";

const MODULE_LABEL: Record<AccessModule, string> = {
  sql: "SQL 题库",
  interview: "面经",
};

// SQL / 面经 的模块级解锁卡片：免费额度用尽后，一次性用积分解锁整个模块。
export function ModuleUnlockPanel({
  module,
  freeUsed,
  freeLimit,
  unlockPoints,
  onUnlocked,
}: {
  module: AccessModule;
  freeUsed: number;
  freeLimit: number;
  unlockPoints: number;
  onUnlocked: () => void;
}) {
  const { user, refreshUser } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function unlock() {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await unlockModule(token, module);
      await refreshUser();
      onUnlocked();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "解锁失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-5 text-center">
      <p className="font-medium text-amber-800">
        本模块免费额度已用完（{freeUsed}/{freeLimit} 条）
      </p>
      <p className="mt-1 text-sm text-amber-700">
        用 {unlockPoints} 积分一次性解锁「{MODULE_LABEL[module]}」全部内容，永久有效。
      </p>
      {!user ? (
        <p className="mt-4 text-sm text-amber-800">
          请先
          <Link href="/login" className="mx-1 font-medium text-brand-600 hover:underline">
            登录
          </Link>
        </p>
      ) : (
        <div className="mt-4 flex flex-col items-center gap-2">
          <button
            disabled={busy}
            onClick={unlock}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            用 {unlockPoints} 积分解锁整个模块
          </button>
          <span className="text-xs text-amber-700">当前积分：{user.points_balance}</span>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}

export function UnlockPanel({
  contentType,
  contentId,
  pricePoints,
  onUnlocked,
}: {
  contentType: PayableType;
  contentId: number;
  priceCash?: string | null;
  pricePoints: number | null;
  onUnlocked: () => void;
}) {
  const { user, refreshUser } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function unlock() {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await unlockContent(token, {
        content_type: contentType,
        content_id: contentId,
        method: "points",
      });
      await refreshUser();
      onUnlocked();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "解锁失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5 text-center">
      <p className="font-medium text-amber-800">该内容需要积分解锁</p>
      <p className="mt-1 text-sm text-amber-700">
        {pricePoints != null ? `${pricePoints} 积分` : "暂未设置积分价"}
      </p>

      {!user ? (
        <p className="mt-4 text-sm text-amber-800">
          请先
          <Link href="/login" className="mx-1 font-medium text-brand-600 hover:underline">
            登录
          </Link>
          后解锁
        </p>
      ) : (
        <div className="mt-4 flex flex-col items-center gap-2">
          <button
            disabled={busy || pricePoints == null}
            onClick={unlock}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            {pricePoints != null ? `用 ${pricePoints} 积分解锁` : "暂不可解锁"}
          </button>
          <span className="text-xs text-amber-700">当前积分：{user.points_balance}</span>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
