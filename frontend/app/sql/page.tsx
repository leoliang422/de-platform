"use client";

import { useEffect, useMemo, useState } from "react";

import { Empty, ErrorText, ListCard, Loading, PageHeader } from "@/components/content";
import { getCategories, getSqlList, type CategoryNode, type SqlListItem } from "@/lib/api";

const DIFF_COLOR: Record<string, string> = {
  easy: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  hard: "bg-red-100 text-red-700",
};

const PAGE_SIZE = 20;

export default function SqlPage() {
  const [items, setItems] = useState<SqlListItem[]>([]);
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [activeCat, setActiveCat] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCategories("sql")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    setPage(1); // 切换题型时回到第一页
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

  // 按标题搜索（客户端，忽略大小写与首尾空格）。
  const filtered = useMemo(() => {
    const kw = query.trim().toLowerCase();
    if (!kw) return items;
    return items.filter((q) => q.title.toLowerCase().includes(kw));
  }, [items, query]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = useMemo(
    () => filtered.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE),
    [filtered, currentPage],
  );

  return (
    <div>
      <PageHeader title="SQL 题库" desc="数据开发高频 SQL 题目：问题 · 求解思路 · Hive SQL" />

      <div className="grid grid-cols-1 gap-6 md:grid-cols-[220px_1fr]">
        <aside className="text-sm md:sticky md:top-20 md:self-start">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            题型
          </p>
          <div className="space-y-0.5">
            <button
              onClick={() => setActiveCat(null)}
              className={`block w-full rounded px-2 py-1.5 text-left ${
                activeCat === null
                  ? "bg-brand-50 font-medium text-brand-700"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              全部题目
            </button>
            {tabs.map((c) => (
              <button
                key={c.id}
                onClick={() => setActiveCat(c.id)}
                className={`block w-full rounded px-2 py-1.5 text-left ${
                  activeCat === c.id
                    ? "bg-brand-50 font-medium text-brand-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`}
              >
                {c.name}
              </button>
            ))}
          </div>
        </aside>

        <section>
          <div className="mb-4">
            <input
              type="search"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1); // 搜索时回到第一页
              }}
              placeholder="搜索题目标题…"
              className="w-full rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </div>

          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorText message={error} />
          ) : items.length === 0 ? (
            <Empty message="该题型下暂无题目" />
          ) : filtered.length === 0 ? (
            <Empty message={`没有匹配「${query.trim()}」的题目`} />
          ) : (
            <>
              <div className="space-y-3">
                {pageItems.map((q) => (
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

              <Pagination
                page={currentPage}
                totalPages={totalPages}
                total={items.length}
                onPrev={() => setPage((p) => Math.max(1, p - 1))}
                onNext={() => setPage((p) => Math.min(totalPages, p + 1))}
              />
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  total,
  onPrev,
  onNext,
}: {
  page: number;
  totalPages: number;
  total: number;
  onPrev: () => void;
  onNext: () => void;
}) {
  if (totalPages <= 1) return null;
  return (
    <div className="mt-6 flex items-center justify-center gap-4 text-sm">
      <button
        onClick={onPrev}
        disabled={page <= 1}
        className="rounded-lg border border-slate-300 px-4 py-1.5 font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        上一页
      </button>
      <span className="text-slate-500">
        第 {page} / {totalPages} 页 · 共 {total} 题
      </span>
      <button
        onClick={onNext}
        disabled={page >= totalPages}
        className="rounded-lg border border-slate-300 px-4 py-1.5 font-medium text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-40"
      >
        下一页
      </button>
    </div>
  );
}
