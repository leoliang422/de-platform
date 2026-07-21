"use client";

import { useEffect, useMemo, useState } from "react";

import { Empty, ErrorText, ListCard, Loading, PageHeader } from "@/components/content";
import { getCategories, getSqlList, type CategoryNode, type SqlListItem } from "@/lib/api";

const DIFF_COLOR: Record<string, string> = {
  easy: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  hard: "bg-red-100 text-red-700",
};

export default function SqlPage() {
  const [items, setItems] = useState<SqlListItem[]>([]);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [activeCat, setActiveCat] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCategories("sql")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    getSqlList(activeCat ?? undefined)
      .then(setItems)
      .catch(() => setError("无法加载题目，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, [activeCat]);

  // 只取一级题型作为筛选项。
  const tabs = useMemo(
    () => [...categories].sort((a, b) => a.order - b.order),
    [categories],
  );

  return (
    <div>
      <PageHeader title="SQL 题库" desc="数据开发高频 SQL 题目：问题 · 求解思路 · Hive SQL" />

      {tabs.length > 0 && (
        <div className="mb-5 flex flex-wrap gap-2">
          <FilterChip active={activeCat === null} onClick={() => setActiveCat(null)}>
            全部
          </FilterChip>
          {tabs.map((c) => (
            <FilterChip
              key={c.id}
              active={activeCat === c.id}
              onClick={() => setActiveCat(c.id)}
            >
              {c.name}
            </FilterChip>
          ))}
        </div>
      )}

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : items.length === 0 ? (
        <Empty message="该题型下暂无题目" />
      ) : (
        <div className="space-y-3">
          {items.map((q) => (
            <ListCard key={q.id} href={`/sql/${q.id}`}>
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-900">{q.title}</span>
                <span
                  className={`rounded px-2 py-0.5 text-xs ${
                    DIFF_COLOR[q.difficulty] ?? "bg-slate-100 text-slate-600"
                  }`}
                >
                  {q.difficulty}
                </span>
              </div>
              {q.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {q.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              )}
            </ListCard>
          ))}
        </div>
      )}
    </div>
  );
}

function FilterChip({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
        active
          ? "bg-brand-600 text-white"
          : "bg-slate-100 text-slate-600 hover:bg-slate-200"
      }`}
    >
      {children}
    </button>
  );
}
