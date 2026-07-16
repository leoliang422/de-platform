"use client";

import { use, useEffect, useState } from "react";

import { BackLink, Empty, ErrorText, Loading, Prose } from "@/components/content";
import {
  getCompanyInterviews,
  getInterviewDetail,
  type InterviewDetail,
  type InterviewListItem,
} from "@/lib/api";

export default function CompanyInterviewsPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = use(params);
  const [posts, setPosts] = useState<InterviewListItem[]>([]);
  const [openId, setOpenId] = useState<number | null>(null);
  const [detail, setDetail] = useState<InterviewDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCompanyInterviews(Number(companyId))
      .then(setPosts)
      .catch(() => setError("无法加载面经"))
      .finally(() => setLoading(false));
  }, [companyId]);

  function toggle(id: number) {
    if (openId === id) {
      setOpenId(null);
      return;
    }
    setOpenId(id);
    setDetail(null);
    getInterviewDetail(id)
      .then(setDetail)
      .catch(() => setDetail(null));
  }

  return (
    <div>
      <BackLink href="/interview" label="返回企业列表" />
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : posts.length === 0 ? (
        <Empty message="该企业暂无面经" />
      ) : (
        <div className="space-y-3">
          {posts.map((p) => (
            <div
              key={p.id}
              className="rounded-lg border border-slate-200 bg-white p-4"
            >
              <button
                onClick={() => toggle(p.id)}
                className="flex w-full items-center justify-between text-left"
              >
                <span className="font-medium text-slate-900">{p.position}</span>
                <span className="text-sm text-brand-600">
                  {openId === p.id ? "收起" : "展开"}
                </span>
              </button>
              {openId === p.id && (
                <div className="mt-3">
                  {detail && detail.id === p.id ? (
                    <Prose>{detail.content_md}</Prose>
                  ) : (
                    <Loading />
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
