"use client";

import { useEffect, useState } from "react";

import {
  Empty,
  ErrorText,
  ListCard,
  Loading,
  PageHeader,
} from "@/components/content";
import {
  getCategories,
  getKnowledgeList,
  type CategoryNode,
  type KnowledgeListItem,
} from "@/lib/api";

export default function KnowledgePage() {
  const [categories, setCategories] = useState<CategoryNode[]>([]);
  const [items, setItems] = useState<KnowledgeListItem[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCategories("knowledge")
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    getKnowledgeList(selected ?? undefined)
      .then(setItems)
      .catch(() => setError("无法加载内容，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, [selected]);

  return (
    <div>
      <PageHeader title="八股总结" desc="按技术域分区整理的高频知识点" />
      <div className="grid grid-cols-1 gap-6 md:grid-cols-[220px_1fr]">
        <aside className="space-y-1 text-sm">
          <button
            onClick={() => setSelected(null)}
            className={`block w-full rounded px-2 py-1 text-left ${
              selected === null ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            全部
          </button>
          <CategoryTree
            nodes={categories}
            selected={selected}
            onSelect={setSelected}
          />
        </aside>

        <section className="space-y-3">
          {loading ? (
            <Loading />
          ) : error ? (
            <ErrorText message={error} />
          ) : items.length === 0 ? (
            <Empty message="暂无内容" />
          ) : (
            items.map((it) => (
              <ListCard key={it.id} href={`/knowledge/${it.id}`}>
                <div className="flex items-center justify-between">
                  <span className="font-medium text-slate-900">{it.title}</span>
                  {it.is_paid && (
                    <span className="rounded bg-amber-100 px-2 py-0.5 text-xs text-amber-700">
                      付费
                    </span>
                  )}
                </div>
              </ListCard>
            ))
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
          <button
            onClick={() => onSelect(n.id)}
            style={{ paddingLeft: `${8 + depth * 12}px` }}
            className={`block w-full rounded px-2 py-1 text-left ${
              selected === n.id
                ? "bg-brand-50 text-brand-700"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {n.name}
          </button>
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
