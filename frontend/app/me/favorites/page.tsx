"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import { getAccessToken, getMyFavorites, type FavoriteItem } from "@/lib/api";

const TYPE_LABEL: Record<string, string> = {
  knowledge: "八股",
  sql: "SQL",
  interview: "面经",
  project: "项目",
};

const TYPE_PATH: Record<string, string> = {
  knowledge: "/knowledge",
  sql: "/sql",
  project: "/projects",
};

export default function FavoritesPage() {
  return (
    <RequireAuth>
      <FavoritesInner />
    </RequireAuth>
  );
}

function FavoritesInner() {
  const [items, setItems] = useState<FavoriteItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    getMyFavorites(token)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="我的收藏" desc="你收藏的内容" />
      {loading ? (
        <p className="text-sm text-slate-400">加载中…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-400">还没有收藏任何内容。</p>
      ) : (
        <div className="space-y-2">
          {items.map((f) => {
            const path = TYPE_PATH[f.content_type];
            const inner = (
              <div className="flex items-center gap-2">
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
                  {TYPE_LABEL[f.content_type] ?? f.content_type}
                </span>
                <span className="text-sm font-medium text-slate-900">{f.title}</span>
              </div>
            );
            return (
              <div
                key={`${f.content_type}-${f.content_id}`}
                className="rounded-lg border border-slate-200 bg-white p-3 hover:border-brand-400"
              >
                {path ? (
                  <Link href={`${path}/${f.content_id}`}>{inner}</Link>
                ) : (
                  <Link href="/interview">{inner}</Link>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
