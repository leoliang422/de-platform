"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import { useAuth } from "@/lib/auth";
import {
  ApiError,
  createSubmission,
  getAccessToken,
  getMySubmissions,
  type Submission,
  type SubmissionCreateInput,
  type TargetType,
} from "@/lib/api";

const TYPE_LABELS: Record<TargetType, string> = {
  knowledge: "八股知识",
  sql: "SQL 题目",
  interview: "面经",
  project: "项目",
};

const STATUS_BADGE: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  processing: "bg-blue-100 text-blue-700",
  pending_review: "bg-amber-100 text-amber-700",
  published: "bg-green-100 text-green-700",
  rejected: "bg-red-100 text-red-700",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  processing: "加工中",
  pending_review: "待审核",
  published: "已发布",
  rejected: "已驳回",
};

export default function SubmitPage() {
  return (
    <RequireAuth>
      <SubmitInner />
    </RequireAuth>
  );
}

function SubmitInner() {
  const { refreshUser } = useAuth();
  const [targetType, setTargetType] = useState<TargetType>("knowledge");
  const [title, setTitle] = useState("");
  const [raw, setRaw] = useState("");
  const [promptMd, setPromptMd] = useState("");
  const [difficulty, setDifficulty] = useState("medium");
  const [tags, setTags] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [position, setPosition] = useState("");
  const [level, setLevel] = useState("basic");
  const [accessType, setAccessType] = useState<"free" | "paid">("free");
  const [implementation, setImplementation] = useState("");
  const [priceCash, setPriceCash] = useState("");
  const [pricePoints, setPricePoints] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mine, setMine] = useState<Submission[]>([]);

  const loadMine = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    getMySubmissions(token)
      .then(setMine)
      .catch(() => setMine([]));
  }, []);

  useEffect(() => {
    loadMine();
  }, [loadMine]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    const token = getAccessToken();
    if (!token) return;

    const paid = accessType === "paid";
    const payload: SubmissionCreateInput = {
      target_type: targetType,
      title,
      raw_content: raw,
      prompt_md: targetType === "sql" ? promptMd : undefined,
      difficulty: targetType === "sql" ? difficulty : undefined,
      tags: targetType === "sql" ? tags : undefined,
      company_name: targetType === "interview" ? companyName : undefined,
      position: targetType === "interview" ? position : undefined,
      level: targetType === "project" ? level : undefined,
      access_type: targetType === "project" ? accessType : undefined,
      implementation_md: targetType === "project" ? implementation : undefined,
      is_paid: targetType === "project" ? paid : undefined,
      price_cash: targetType === "project" && paid ? priceCash || null : undefined,
      price_points:
        targetType === "project" && paid && pricePoints ? Number(pricePoints) : undefined,
    };

    setSubmitting(true);
    try {
      await createSubmission(token, payload);
      setMessage("投稿已提交，大模型加工完成后进入审核队列。");
      setTitle("");
      setRaw("");
      setPromptMd("");
      setImplementation("");
      loadMine();
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  const inputCls =
    "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

  return (
    <div>
      <PageHeader title="投稿" desc="内容经大模型整理为统一格式，管理员审核通过后发布并发放积分" />

      <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-5">
        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">类型</label>
          <select
            value={targetType}
            onChange={(e) => setTargetType(e.target.value as TargetType)}
            className={inputCls}
          >
            {Object.entries(TYPE_LABELS).map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">标题</label>
          <input value={title} onChange={(e) => setTitle(e.target.value)} required className={inputCls} />
        </div>

        {targetType === "sql" && (
          <>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">题目</label>
              <textarea
                value={promptMd}
                onChange={(e) => setPromptMd(e.target.value)}
                rows={3}
                required
                className={inputCls}
              />
            </div>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-slate-700">难度</label>
                <select value={difficulty} onChange={(e) => setDifficulty(e.target.value)} className={inputCls}>
                  <option value="easy">easy</option>
                  <option value="medium">medium</option>
                  <option value="hard">hard</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-slate-700">标签（逗号分隔）</label>
                <input value={tags} onChange={(e) => setTags(e.target.value)} className={inputCls} />
              </div>
            </div>
          </>
        )}

        {targetType === "interview" && (
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-slate-700">企业名称</label>
              <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} required className={inputCls} />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-slate-700">岗位</label>
              <input value={position} onChange={(e) => setPosition(e.target.value)} required className={inputCls} />
            </div>
          </div>
        )}

        {targetType === "project" && (
          <>
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-slate-700">难度</label>
                <select value={level} onChange={(e) => setLevel(e.target.value)} className={inputCls}>
                  <option value="basic">basic</option>
                  <option value="intermediate">intermediate</option>
                  <option value="advanced">advanced</option>
                </select>
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-slate-700">访问级别</label>
                <select
                  value={accessType}
                  onChange={(e) => setAccessType(e.target.value as "free" | "paid")}
                  className={inputCls}
                >
                  <option value="free">免费</option>
                  <option value="paid">付费</option>
                </select>
              </div>
            </div>
            {accessType === "paid" && (
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="mb-1 block text-sm font-medium text-slate-700">现金价（元）</label>
                  <input value={priceCash} onChange={(e) => setPriceCash(e.target.value)} className={inputCls} />
                </div>
                <div className="flex-1">
                  <label className="mb-1 block text-sm font-medium text-slate-700">积分价</label>
                  <input
                    value={pricePoints}
                    onChange={(e) => setPricePoints(e.target.value)}
                    inputMode="numeric"
                    className={inputCls}
                  />
                </div>
              </div>
            )}
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-700">项目实现</label>
              <textarea
                value={implementation}
                onChange={(e) => setImplementation(e.target.value)}
                rows={4}
                className={inputCls}
              />
            </div>
          </>
        )}

        <div>
          <label className="mb-1 block text-sm font-medium text-slate-700">
            {targetType === "sql" ? "解答 / 思路（原始内容）" : "正文（原始内容）"}
          </label>
          <textarea value={raw} onChange={(e) => setRaw(e.target.value)} rows={6} required className={inputCls} />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}
        {message && <p className="text-sm text-green-600">{message}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {submitting ? "提交中…" : "提交投稿"}
        </button>
      </form>

      <h2 className="mb-3 mt-8 text-lg font-semibold text-slate-900">我的投稿</h2>
      {mine.length === 0 ? (
        <p className="text-sm text-slate-400">还没有投稿。</p>
      ) : (
        <div className="space-y-2">
          {mine.map((s) => (
            <div key={s.id} className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-900">
                  [{TYPE_LABELS[s.target_type as TargetType] ?? s.target_type}] {s.title}
                </span>
                <span className={`rounded px-2 py-0.5 text-xs ${STATUS_BADGE[s.status] ?? ""}`}>
                  {STATUS_LABEL[s.status] ?? s.status}
                </span>
              </div>
              {s.reject_reason && (
                <p className="mt-1 text-xs text-red-600">驳回原因：{s.reject_reason}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
