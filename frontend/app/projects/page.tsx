"use client";

import { useEffect, useState } from "react";

import { Empty, ErrorText, ListCard, Loading, PageHeader } from "@/components/content";
import { getProjectList, type ProjectListItem } from "@/lib/api";

export default function ProjectsPage() {
  const [items, setItems] = useState<ProjectListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProjectList()
      .then(setItems)
      .catch(() => setError("无法加载项目，请确认后端已启动"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <PageHeader title="项目整理" desc="实战项目的描述、实现与问答讲解" />
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : items.length === 0 ? (
        <Empty message="暂无项目" />
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {items.map((p) => (
            <ListCard key={p.id} href={`/projects/${p.id}`}>
              <div className="flex items-center justify-between">
                <span className="font-medium text-slate-900">{p.title}</span>
                <span
                  className={`rounded px-2 py-0.5 text-xs ${
                    p.access_type === "free"
                      ? "bg-green-100 text-green-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {p.access_type === "free" ? "免费" : "付费"}
                </span>
              </div>
              <div className="mt-1 text-xs text-slate-500">难度：{p.level}</div>
            </ListCard>
          ))}
        </div>
      )}
    </div>
  );
}
