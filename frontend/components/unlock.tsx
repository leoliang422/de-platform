"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/lib/auth";
import {
  ApiError,
  getAccessToken,
  unlockContent,
  type PayableType,
  type UnlockMethod,
} from "@/lib/api";

export function UnlockPanel({
  contentType,
  contentId,
  priceCash,
  pricePoints,
  onUnlocked,
}: {
  contentType: PayableType;
  contentId: number;
  priceCash: string | null;
  pricePoints: number | null;
  onUnlocked: () => void;
}) {
  const { user, refreshUser } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [payUrl, setPayUrl] = useState<string | null>(null);

  async function unlock(method: UnlockMethod) {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    setPayUrl(null);
    try {
      const res = await unlockContent(token, {
        content_type: contentType,
        content_id: contentId,
        method,
      });
      if (res.status === "pending") {
        // 异步支付（微信/支付宝）：引导用户去付款，回调结算后再刷新解锁态。
        setPayUrl(res.pay_url ?? null);
        return;
      }
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
      <p className="font-medium text-amber-800">该内容为付费内容</p>
      <p className="mt-1 text-sm text-amber-700">
        {priceCash != null && `¥${priceCash}`}
        {priceCash != null && pricePoints != null && " 或 "}
        {pricePoints != null && `${pricePoints} 积分`}
        解锁
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
        <div className="mt-4 flex justify-center gap-3">
          {priceCash != null && (
            <button
              disabled={busy}
              onClick={() => unlock("cash")}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              现金购买（模拟）
            </button>
          )}
          {pricePoints != null && (
            <button
              disabled={busy}
              onClick={() => unlock("points")}
              className="rounded-lg border border-brand-500 px-4 py-2 text-sm font-medium text-brand-600 hover:bg-brand-50 disabled:opacity-50"
            >
              用 {pricePoints} 积分兑换
            </button>
          )}
        </div>
      )}
      {payUrl && (
        <p className="mt-3 text-sm text-amber-800">
          请前往
          <a
            href={payUrl}
            target="_blank"
            rel="noreferrer"
            className="mx-1 font-medium text-brand-600 hover:underline"
          >
            支付页面
          </a>
          完成付款，支付成功后刷新本页即可查看。
        </p>
      )}
      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
    </div>
  );
}
