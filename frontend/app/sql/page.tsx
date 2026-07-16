"use client";

import { useEffect, useState } from "react";

import { Empty, ErrorText, ListCard, Loading, PageHeader } from "@/components/content";
import { getSqlList, type SqlListItem } from "@/lib/api";

const DIFF_COLOR: Record<string, string> = {
  easy: "bg-green-100 text-green-700",
  medium: "bg-amber-100 text-amber-700",
  hard: "bg-red-100 text-red-700",
};

export default function SqlPage() {
  const [items, setItems] = useState<SqlListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getSqlList()
      .then(setItems)
      .catch(() => setError("无法加载题目，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="SQL 题库" desc="数据开发高频 SQL 题目与参考答案" />
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : items.length === 0 ? (
        <Empty message="暂无题目" />
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
