"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Empty, ErrorText, Loading, PageHeader } from "@/components/content";
import {
  getCategories,
  getKnowledgeList,
  type CategoryNode,
  type KnowledgeListItem,
} from "@/lib/api";

const PAGE_SIZE = 20;

export default function KnowledgePage() {
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [items, setItems] = useState<KnowledgeListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [selected, setSelected] = useState<number | null>(null);
  const [sort, setSort] = useState<"hot" | "new">("hot");
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCategories("knowledge")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  // 输入防抖：停止输入 300ms 后再触发搜索
  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(query), 300);
    return () => clearTimeout(t);
  }, [query]);

  useEffect(() => {
    setPage(1);
  }, [selected, sort, debouncedQuery]);

  useEffect(() => {
    setLoading(true);
    getKnowledgeList({ categoryId: selected, q: debouncedQuery, sort, page, pageSize: PAGE_SIZE })
      .then((res) => {
        setItems(res.items);
        setTotal(res.total);
      })
      .catch(() => setError("无法加载内容，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, [selected, sort, page, debouncedQuery]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <PageHeader title="八股总结" desc="按技术域分区整理的高频知识点，按热度优先展示" />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[220px_1fr]">
        <aside className="text-sm md:sticky md:top-20 md:self-start">
          <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
            分类
          </p>
          <div className="space-y-0.5">
            <button
              onClick={() => setSelected(null)}
              className={`block w-full rounded px-2 py-1.5 text-left ${
                selected === null
                  ? "bg-brand-50 font-medium text-brand-700"
                  : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              全部知识点
            </button>
            <CategoryTree nodes={categories} selected={selected} onSelect={setSelected} />
          </div>
        </aside>

        <section>
          <div className="mb-4">
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
                🔍
              </span>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索关键词（标题 / 正文）…"
                className="w-full rounded-lg border border-slate-300 py-2 pl-9 pr-9 text-sm focus:border-brand-500 focus:outline-none"
              />
              {query && (
                <button
                  onClick={() => setQuery("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  aria-label="清空搜索"
                >
                  ✕
                </button>
              )}
            </div>
          </div>
          <div className="mb-4 flex items-center justify-between">
            <div className="flex gap-2">
              {(["hot", "new"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setSort(s)}
                  className={`rounded-full px-3 py-1 text-sm transition ${
                    sort === s
                      ? "bg-brand-600 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                  }`}
                >
                  {s === "hot" ? "🔥 热门" : "🆕 最新"}
                </button>
              ))}
            </div>
            {total > 0 && (
              <span className="text-xs text-slate-400">
                {debouncedQuery ? `搜索到 ${total} 条` : `共 ${total} 条`}
              </span>
            )}
          </div>

          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorText message={error} />
          ) : items.length === 0 ? (
            <Empty message={debouncedQuery ? `未找到与「${debouncedQuery}」相关的内容` : "暂无内容"} />
          ) : (
            <>
              <ol className="divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200 bg-white">
                {items.map((it, i) => (
                  <li key={it.id}>
                    <Link
                      href={`/knowledge/${it.id}`}
                      className="flex items-center gap-3 px-4 py-3 transition hover:bg-slate-50"
                    >
                      <span className="w-6 shrink-0 text-center text-sm font-semibold text-slate-300">
                        {(page - 1) * PAGE_SIZE + i + 1}
                      </span>
                      <span className="flex-1 truncate font-medium text-slate-900">
                        {it.title}
                      </span>
                      {it.is_paid && (
                        <span className="shrink-0 rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                          付费
                        </span>
                      )}
                      <span className="hidden shrink-0 items-center gap-3 text-xs text-slate-400 sm:flex">
                        <span title="热度">🔥 {it.hotness}</span>
                        <span title="浏览">👁 {it.views}</span>
                        <span title="点赞">❤️ {it.likes}</span>
                        <span title="收藏">⭐ {it.favorites}</span>
                      </span>
                    </Link>
                  </li>
                ))}
              </ol>

              {totalPages > 1 && (
                <div className="mt-4 flex items-center justify-center gap-3 text-sm">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="rounded border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  >
                    上一页
                  </button>
                  <span className="text-slate-500">
                    {page} / {totalPages}
                  </span>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="rounded border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
                  >
                    下一页
                  </button>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

function CategoryTree({
  nodes,
  selected,
  onSelect,
  depth = 0,
}: {
  nodes: CategoryNode[];
  selected: number | null;
  onSelect: (id: number) => void;
  depth?: number;
}) {
  return (
    <>
      {nodes.map((n) => (
        <div key={n.id}>
          <div className="flex items-center">
            <button
              onClick={() => onSelect(n.id)}
              style={{ paddingLeft: `${8 + depth * 12}px` }}
              className={`block flex-1 rounded px-2 py-1.5 text-left ${
                selected === n.id
                  ? "bg-brand-50 font-medium text-brand-700"
                  : depth === 0
                    ? "font-medium text-slate-700 hover:bg-slate-100"
                    : "text-slate-600 hover:bg-slate-100"
              }`}
            >
              {n.name}
            </button>
          </div>
          {n.children.length > 0 && (
            <CategoryTree
              nodes={n.children}
              selected={selected}
              onSelect={onSelect}
              depth={depth + 1}
            />
          )}
        </div>
      ))}
    </>
  );
}
