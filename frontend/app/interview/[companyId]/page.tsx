"use client";

import { use, useEffect, useState } from "react";

import { BackLink, Empty, ErrorText, Loading, Prose } from "@/components/content";
import {
  getCompanyPositions,
  getInterviewDetail,
  INTERVIEW_RESULT_LABEL,
  type InterviewDetail,
  type InterviewListItem,
  type PositionGroup,
} from "@/lib/api";

const RESULT_BADGE: Record<string, string> = {
  pass: "bg-green-100 text-green-700",
  fail: "bg-red-100 text-red-700",
  pending: "bg-amber-100 text-amber-700",
  unknown: "bg-slate-100 text-slate-600",
};

export default function CompanyInterviewsPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = use(params);
  const [groups, setGroups] = useState<PositionGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompanyPositions(Number(companyId))
      .then(setGroups)
      .catch(() => setError("无法加载面经"))
      .finally(() => setLoading(false));
  }, [companyId]);

  return (
    <div>
      <BackLink href="/interview" label="返回企业列表" />
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : groups.length === 0 ? (
        <Empty message="该企业暂无面经" />
      ) : (
        <div className="space-y-6">
          {groups.map((g) => (
            <section key={g.position}>
              <h2 className="mb-2 flex items-center gap-2 text-lg font-semibold text-slate-900">
                {g.position}
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-normal text-slate-500">
                  {g.count} 篇面经
                </span>
              </h2>
              <div className="space-y-3">
                {g.posts.map((p) => (
                  <InterviewCard key={p.id} post={p} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

function InterviewCard({ post }: { post: InterviewListItem }) {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<InterviewDetail | null>(null);

  function toggle() {
    if (open) {
      setOpen(false);
      return;
    }
    setOpen(true);
    if (!detail) {
      getInterviewDetail(post.id)
        .then(setDetail)
        .catch(() => setDetail(null));
    }
  }

  const meta = [
    post.interview_date,
    post.city,
    post.position_level,
    post.rounds != null ? `${post.rounds} 轮` : null,
    post.channel,
  ].filter(Boolean);

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <button onClick={toggle} className="flex w-full items-center justify-between text-left">
        <div className="flex flex-wrap items-center gap-2">
          {post.result && (
            <span
              className={`rounded px-2 py-0.5 text-xs ${
                RESULT_BADGE[post.result] ?? RESULT_BADGE.unknown
              }`}
            >
              {INTERVIEW_RESULT_LABEL[post.result] ?? post.result}
            </span>
          )}
          <span className="text-sm text-slate-500">
            {meta.length > 0 ? meta.join(" · ") : "面试详情"}
          </span>
        </div>
        <span className="shrink-0 text-sm text-brand-600">{open ? "收起" : "展开"}</span>
      </button>

      {open && (
        <div className="mt-3">
          {detail ? (
            <div className="space-y-4">
              {detail.content_md && (
                <div>
                  <h4 className="mb-1 text-sm font-semibold text-slate-700">整体感受</h4>
                  <Prose>{detail.content_md}</Prose>
                </div>
              )}
              <QASection title="技术面" items={detail.technical_qa} />
              <QASection title="HR 面" items={detail.hr_qa} />
            </div>
          ) : (
            <Loading />
          )}
        </div>
      )}
    </div>
  );
}

function QASection({ title, items }: { title: string; items: InterviewDetail["technical_qa"] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h4 className="mb-2 text-sm font-semibold text-brand-700">{title}</h4>
      <div className="space-y-3">
        {items.map((qa) => (
          <div key={qa.id} className="rounded-md bg-slate-50 p-3">
            <p className="text-sm font-medium text-slate-900">Q：{qa.question}</p>
            {qa.answer && (
              <div className="mt-1 border-l-2 border-brand-200 pl-3 text-sm text-slate-600">
                <Prose>{qa.answer}</Prose>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
