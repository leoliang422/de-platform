"use client";

import { use, useCallback, useEffect, useState } from "react";

import { BackLink, ErrorText, Loading, Prose } from "@/components/content";
import { AnnotatedReader, ContentInteractions } from "@/components/interactions";
import { getAccessToken, getKnowledgeDetail, type KnowledgeDetail } from "@/lib/api";

export default function KnowledgeDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [item, setItem] = useState<KnowledgeDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    getKnowledgeDetail(Number(id), getAccessToken())
      .then(setItem)
      .catch(() => setError("内容不存在或加载失败"));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div>
      <BackLink href="/knowledge" label="返回八股列表" />
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
