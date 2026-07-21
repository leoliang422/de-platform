"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";

import { ErrorText, Loading, Prose } from "@/components/content";
import { AnnotatedReader, ContentInteractions } from "@/components/interactions";
import {
  getAccessToken,
  getKnowledgeDetail,
  getKnowledgeList,
  type KnowledgeDetail,
  type KnowledgeListItem,
} from "@/lib/api";

export default function KnowledgeDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [item, setItem] = useState<KnowledgeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [siblings, setSiblings] = useState<KnowledgeListItem[]>([]);

  const load = useCallback(() => {
    getKnowledgeDetail(Number(id), getAccessToken())
      .then(setItem)
      .catch(() => setError("内容不存在或加载失败"));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // 拉取同文件夹（分类）下的所有知识点，用于「上一个 / 下一个」顺序浏览
  const categoryId = item?.category_id ?? null;
  useEffect(() => {
    if (categoryId == null) {
      setSiblings([]);
      return;
    }
    getKnowledgeList({ categoryId, sort: "hot", pageSize: 500 })
      .then((res) => setSiblings(res.items))
      .catch(() => setSiblings([]));
  }, [categoryId]);

  const currentIndex = item ? siblings.findIndex((s) => s.id === item.id) : -1;
  const prev = currentIndex > 0 ? siblings[currentIndex - 1] : null;
  const next =
    currentIndex >= 0 && currentIndex < siblings.length - 1 ? siblings[currentIndex + 1] : null;

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link href="/knowledge" className="text-sm text-brand-600 hover:underline">
          ← 返回八股列表
        </Link>
        {(prev || next) && (
          <div className="flex items-center gap-2 text-sm">
            {currentIndex >= 0 && siblings.length > 0 && (
              <span className="hidden text-xs text-slate-400 sm:inline">
                {currentIndex + 1} / {siblings.length}
              </span>
            )}
            {prev && (
              <Link
                href={`/knowledge/${prev.id}`}
                title={prev.title}
                className="rounded-lg border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50"
              >
                ← 上一个
              </Link>
            )}
            {next && (
              <Link
                href={`/knowledge/${next.id}`}
                title={next.title}
                className="flex items-center gap-1 rounded-lg border border-brand-200 bg-brand-50 px-3 py-1 text-brand-700 hover:bg-brand-100"
              >
                下一个：
                <span className="max-w-[9rem] truncate">{next.title}</span>
                <span aria-hidden>→</span>
              </Link>
            )}
          </div>
        )}
      </div>
      {error ? (
        <ErrorText message={error} />
      ) : !item ? (
        <Loading />
      ) : (
        <AnnotatedReader contentType="knowledge" contentId={item.id}>
          <h1 className="mb-4 text-2xl font-bold text-slate-900">{item.title}</h1>
          <Prose>{item.content_md ?? ""}</Prose>
          <ContentInteractions contentType="knowledge" contentId={item.id} />
        </AnnotatedReader>
      )}
    </div>
  );
}
