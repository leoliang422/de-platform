"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import { useAuth } from "@/lib/auth";
import {
  getAccessToken,
  getMyEntitlements,
  getMyPoints,
  type Entitlement,
  type PointsOverview,
} from "@/lib/api";

export default function MePage() {
  return (
    <RequireAuth>
      <MeInner />
    </RequireAuth>
  );
}

const CONTENT_LABEL: Record<string, string> = {
  project: "项目",
  knowledge: "八股",
};

const SOURCE_LABEL: Record<string, string> = {
  purchase: "现金购买",
  points: "积分兑换",
};

function MeInner() {
  const { user } = useAuth();
  const [points, setPoints] = useState<PointsOverview | null>(null);
  const [entitlements, setEntitlements] = useState<Entitlement[]>([]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    getMyPoints(token)
      .then(setPoints)
      .catch(() => setPoints(null));
    getMyEntitlements(token)
      .then(setEntitlements)
      .catch(() => setEntitlements([]));
  }, []);

  return (
    <div>
      <PageHeader title="个人中心" desc={user ? `${user.nickname} · ${user.email}` : undefined} />

      <div className="mb-6 rounded-xl border border-slate-200 bg-white p-5">
        <div className="text-sm text-slate-500">积分余额</div>
        <div className="mt-1 text-3xl font-bold text-brand-600">
          {points?.balance ?? user?.points_balance ?? 0}
        </div>
      </div>

      <h2 className="mb-3 text-lg font-semibold text-slate-900">积分明细</h2>
      {!points ? (
        <p className="text-sm text-slate-400">加载中…</p>
      ) : points.ledger.length === 0 ? (
        <p className="text-sm text-slate-400">暂无积分记录。投稿被审核通过即可获得积分。</p>
      ) : (
        <div className="space-y-2">
          {points.ledger.map((e) => (
            <div
              key={e.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 text-sm"
            >
              <span className="text-slate-700">{e.reason}</span>
              <span className={e.delta >= 0 ? "font-medium text-green-600" : "font-medium text-red-600"}>
                {e.delta >= 0 ? `+${e.delta}` : e.delta}
              </span>
            </div>
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-8 text-lg font-semibold text-slate-900">已解锁内容</h2>
      {entitlements.length === 0 ? (
        <p className="text-sm text-slate-400">还没有解锁任何付费内容。</p>
      ) : (
        <div className="space-y-2">
          {entitlements.map((e) => {
            const href = e.content_type === "project" ? `/projects/${e.content_id}` : `/knowledge/${e.content_id}`;
            return (
              <Link
                key={e.id}
                href={href}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 text-sm hover:border-brand-500"
              >
                <span className="text-slate-700">
                  {CONTENT_LABEL[e.content_type] ?? e.content_type} #{e.content_id}
                </span>
                <span className="text-xs text-slate-400">{SOURCE_LABEL[e.source] ?? e.source}</span>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
