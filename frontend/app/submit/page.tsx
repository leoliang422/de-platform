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
  retrySubmission,
  type InterviewQAInput,
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
  failed: "bg-red-100 text-red-700",
};

const STATUS_LABEL: Record<string, string> = {
  draft: "草稿",
  processing: "加工中",
  pending_review: "待审核",
  published: "已发布",
  rejected: "已驳回",
  failed: "加工失败",
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
  const [positionLevel, setPositionLevel] = useState("");
  const [interviewDate, setInterviewDate] = useState("");
  const [interviewRounds, setInterviewRounds] = useState("");
  const [interviewResult, setInterviewResult] = useState<
    "pass" | "fail" | "pending" | "unknown"
  >("unknown");
  const [interviewCity, setInterviewCity] = useState("");
  const [interviewChannel, setInterviewChannel] = useState("");
  const [qaItems, setQaItems] = useState<InterviewQAInput[]>([
    { section: "technical", question: "", answer: "" },
  ]);
  const [level, setLevel] = useState("basic");
  const [accessType, setAccessType] = useState<"free" | "paid">("free");
  const [implementation, setImplementation] = useState("");
  const [priceCash, setPriceCash] = useState("");
  const [pricePoints, setPricePoints] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mine, setMine] = useState<Submission[]>([]);

  const [retryingId, setRetryingId] = useState<number | null>(null);

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

  // 异步加工时投稿会停留在「加工中」，轮询刷新直到状态流转。
  useEffect(() => {
    if (!mine.some((s) => s.status === "processing")) return;
    const timer = setInterval(loadMine, 3000);
    return () => clearInterval(timer);
  }, [mine, loadMine]);

  async function handleRetry(id: number) {
    const token = getAccessToken();
    if (!token) return;
    setRetryingId(id);
    try {
      await retrySubmission(token, id);
      loadMine();
    } catch {
      // 忽略：状态会在下次刷新体现
    } finally {
      setRetryingId(null);
    }
  }

  function updateQa(index: number, patch: Partial<InterviewQAInput>) {
    setQaItems((prev) => prev.map((q, i) => (i === index ? { ...q, ...patch } : q)));
  }

  function addQa(section: "technical" | "hr") {
    setQaItems((prev) => [...prev, { section, question: "", answer: "" }]);
  }

  function removeQa(index: number) {
    setQaItems((prev) => prev.filter((_, i) => i !== index));
  }

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
      position_level: targetType === "interview" ? positionLevel || null : undefined,
      interview_date: targetType === "interview" ? interviewDate || null : undefined,
      interview_rounds:
        targetType === "interview" && interviewRounds ? Number(interviewRounds) : undefined,
      interview_result: targetType === "interview" ? interviewResult : undefined,
      interview_city: targetType === "interview" ? interviewCity || null : undefined,
      interview_channel: targetType === "interview" ? interviewChannel || null : undefined,
      qa_items:
        targetType === "interview"
          ? qaItems.filter((q) => q.question.trim() || q.answer.trim())
          : undefined,
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
      const created = await createSubmission(token, payload);
      setMessage(
        created.status === "processing"
          ? "投稿已提交，正在后台加工，稍后在下方「我的投稿」查看进度。"
          : "投稿已提交，大模型加工完成后进入审核队列。",
      );
      setTitle("");
      setRaw("");
      setPromptMd("");
      setImplementation("");
      setQaItems([{ section: "technical", question: "", answer: "" }]);
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
          <div className="space-y-3">
            <div className="flex gap-3">
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-slate-700">企业名称</label>
                <input value={companyName} onChange={(e) => setCompanyName(e.target.value)} required className={inputCls} />
              </div>
              <div className="flex-1">
                <label className="mb-1 block text-sm font-medium text-slate-700">岗位（相同岗位会自动合并）</label>
                <input value={position} onChange={(e) => setPosition(e.target.value)} required className={inputCls} />
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="flex-1 min-w-[140px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">岗位级别</label>
                <input value={positionLevel} onChange={(e) => setPositionLevel(e.target.value)} placeholder="如 校招/社招 P5" className={inputCls} />
              </div>
              <div className="flex-1 min-w-[140px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">面试时间</label>
                <input value={interviewDate} onChange={(e) => setInterviewDate(e.target.value)} placeholder="如 2026-03" className={inputCls} />
              </div>
              <div className="flex-1 min-w-[100px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">轮次</label>
                <input value={interviewRounds} onChange={(e) => setInterviewRounds(e.target.value)} inputMode="numeric" placeholder="如 3" className={inputCls} />
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              <div className="flex-1 min-w-[120px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">结果</label>
                <select value={interviewResult} onChange={(e) => setInterviewResult(e.target.value as typeof interviewResult)} className={inputCls}>
                  <option value="pass">已通过</option>
                  <option value="fail">未通过</option>
                  <option value="pending">流程中</option>
                  <option value="unknown">未知</option>
                </select>
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">城市</label>
                <input value={interviewCity} onChange={(e) => setInterviewCity(e.target.value)} className={inputCls} />
              </div>
              <div className="flex-1 min-w-[120px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">投递渠道</label>
                <input value={interviewChannel} onChange={(e) => setInterviewChannel(e.target.value)} placeholder="如 官网/内推" className={inputCls} />
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 p-3">
              <p className="mb-2 text-sm font-medium text-slate-700">面试问答（上传时区分技术面 / HR 面、问题与答案）</p>
              <div className="space-y-3">
                {qaItems.map((qa, i) => (
                  <div key={i} className="rounded-md bg-slate-50 p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <select
                        value={qa.section}
                        onChange={(e) => updateQa(i, { section: e.target.value as "technical" | "hr" })}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      >
                        <option value="technical">技术面</option>
                        <option value="hr">HR 面</option>
                      </select>
                      <span className="text-xs text-slate-400">第 {i + 1} 条</span>
                      {qaItems.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeQa(i)}
                          className="ml-auto text-xs text-red-500 hover:underline"
                        >
                          删除
                        </button>
                      )}
                    </div>
                    <input
                      value={qa.question}
                      onChange={(e) => updateQa(i, { question: e.target.value })}
                      placeholder="问题"
                      className={`${inputCls} mb-2`}
                    />
                    <textarea
                      value={qa.answer}
                      onChange={(e) => updateQa(i, { answer: e.target.value })}
                      placeholder="答案 / 参考回答（可选）"
                      rows={2}
                      className={inputCls}
                    />
                  </div>
                ))}
              </div>
              <div className="mt-2 flex gap-3">
                <button type="button" onClick={() => addQa("technical")} className="text-sm text-brand-600 hover:underline">
                  + 技术面问答
                </button>
                <button type="button" onClick={() => addQa("hr")} className="text-sm text-brand-600 hover:underline">
                  + HR 面问答
                </button>
              </div>
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
            {targetType === "sql"
              ? "解答 / 思路（原始内容）"
              : targetType === "interview"
                ? "整体感受 / 概述（原始内容）"
                : "正文（原始内容）"}
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

      <div className="mb-3 mt-8 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">我的投稿</h2>
        <button
          type="button"
          onClick={loadMine}
          className="text-xs text-brand-600 hover:underline"
        >
          刷新
        </button>
      </div>
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
                <div className="flex items-center gap-2">
                  {s.status === "failed" && (
                    <button
                      type="button"
                      disabled={retryingId === s.id}
                      onClick={() => handleRetry(s.id)}
                      className="rounded border border-brand-500 px-2 py-0.5 text-xs text-brand-600 hover:bg-brand-50 disabled:opacity-50"
                    >
                      {retryingId === s.id ? "重试中…" : "重试"}
                    </button>
                  )}
                  <span className={`rounded px-2 py-0.5 text-xs ${STATUS_BADGE[s.status] ?? ""}`}>
                    {STATUS_LABEL[s.status] ?? s.status}
                  </span>
                </div>
              </div>
              {s.status === "rejected" && s.reject_reason && (
                <p className="mt-1 text-xs text-red-600">驳回原因：{s.reject_reason}</p>
              )}
              {s.status === "failed" && s.reject_reason && (
                <p className="mt-1 text-xs text-red-600">{s.reject_reason}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
