"use client";

import { useEffect, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import { useAuth } from "@/lib/auth";
import { getAccessToken, getMyPoints, type PointsOverview } from "@/lib/api";

export default function MePage() {
  return (
    <RequireAuth>
      <MeInner />
    </RequireAuth>
  );
}

function MeInner() {
  const { user } = useAuth();
  const [points, setPoints] = useState<PointsOverview | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    getMyPoints(token)
      .then(setPoints)
      .catch(() => setPoints(null));
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
    </div>
  );
}
