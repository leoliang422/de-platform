"use client";

import { use, useEffect, useState } from "react";

import { BackLink, ErrorText, Loading, Prose } from "@/components/content";
import { getSqlDetail, type SqlDetail } from "@/lib/api";

export default function SqlDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [item, setItem] = useState<SqlDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);

  useEffect(() => {
    getSqlDetail(Number(id))
      .then(setItem)
      .catch(() => setError("题目不存在或加载失败"));
  }, [id]);

  return (
    <div>
      <BackLink href="/sql" label="返回 SQL 题库" />
      {error ? (
        <ErrorText message={error} />
      ) : !item ? (
        <Loading />
      ) : (
        <>
          <h1 className="mb-4 text-2xl font-bold text-slate-900">{item.title}</h1>
          <h2 className="mb-2 text-sm font-semibold text-slate-500">题目</h2>
          <Prose>{item.prompt_md}</Prose>
          <button
            onClick={() => setShowAnswer((v) => !v)}
            className="my-4 rounded-lg border border-slate-300 px-4 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
          >
            {showAnswer ? "隐藏答案" : "显示答案"}
          </button>
          {showAnswer && (
            <>
              <h2 className="mb-2 text-sm font-semibold text-slate-500">参考答案</h2>
              <Prose>{item.answer_md}</Prose>
            </>
          )}
        </>
      )}
    </div>
  );
}
