"use client";

import { use, useEffect, useState } from "react";

import { BackLink, ErrorText, Loading, Prose } from "@/components/content";
import { getProjectDetail, type ProjectDetail } from "@/lib/api";

export default function ProjectDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [item, setItem] = useState<ProjectDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getProjectDetail(Number(id))
      .then(setItem)
      .catch(() => setError("项目不存在或加载失败"));
  }, [id]);

  return (
    <div>
      <BackLink href="/projects" label="返回项目列表" />
      {error ? (
        <ErrorText message={error} />
      ) : !item ? (
        <Loading />
      ) : (
        <>
          <div className="mb-4 flex items-center gap-3">
            <h1 className="text-2xl font-bold text-slate-900">{item.title}</h1>
            <span
              className={`rounded px-2 py-0.5 text-xs ${
                item.access_type === "free"
                  ? "bg-green-100 text-green-700"
                  : "bg-amber-100 text-amber-700"
              }`}
            >
              {item.access_type === "free" ? "免费" : "付费"}
            </span>
          </div>

          <h2 className="mb-2 text-sm font-semibold text-slate-500">项目描述</h2>
          <Prose>{item.description_md}</Prose>

          {item.locked ? (
            <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-5 text-center">
              <p className="font-medium text-amber-800">该项目为付费内容</p>
              <p className="mt-1 text-sm text-amber-700">
                {item.price_cash != null && `¥${item.price_cash}`}
                {item.price_cash != null && item.price_points != null && " 或 "}
                {item.price_points != null && `${item.price_points} 积分`}
                解锁（购买 / 兑换功能将在后续里程碑上线）
              </p>
            </div>
          ) : (
            <>
              <h2 className="mb-2 mt-6 text-sm font-semibold text-slate-500">项目实现</h2>
              <Prose>{item.implementation_md ?? ""}</Prose>

              {item.qa.length > 0 && (
                <>
                  <h2 className="mb-2 mt-6 text-sm font-semibold text-slate-500">
                    问题讲解
                  </h2>
                  <div className="space-y-4">
                    {item.qa.map((qa) => (
                      <div key={qa.id}>
                        <p className="font-medium text-slate-900">Q: {qa.question_md}</p>
                        <div className="mt-1">
                          <Prose>{qa.answer_md}</Prose>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
