"use client";

import { useState } from "react";

import { MarkdownTextarea } from "@/components/markdown-textarea";
import { completeAnswer, getAccessToken, type InterviewQAInput } from "@/lib/api";

export type RoundSection = InterviewQAInput["section"];

export const ROUND_OPTIONS: { value: RoundSection; label: string }[] = [
  { value: "round1", label: "一面" },
  { value: "round2", label: "二面" },
  { value: "round3", label: "三面" },
  { value: "hr", label: "HR面" },
];

export const ROUND_LABEL: Record<string, string> = Object.fromEntries(
  ROUND_OPTIONS.map((r) => [r.value, r.label]),
);

export function emptyQa(section: RoundSection = "round1"): InterviewQAInput {
  return { section, question: "", answer: "" };
}

const inputCls =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

/**
 * 面经问答编辑器（投稿页 & 管理后台共用）。
 *
 * - 对外始终以扁平的 `InterviewQAInput[]` 传入/传出，内部按 `section` 归组展示；
 * - 每个轮次（一面/二面/三面/HR面）只需选择一次，其下可加多条「问题 + 答案」；
 * - 每条答案可一键「AI 生成答案」（以问题为输入）。
 */
export function InterviewQaEditor({
  items,
  onChange,
  onError,
}: {
  items: InterviewQAInput[];
  onChange: (next: InterviewQAInput[]) => void;
  onError?: (msg: string) => void;
}) {
  const [genIndex, setGenIndex] = useState<number | null>(null);

  // 按 ROUND_OPTIONS 顺序把扁平项归为若干轮次组（保留每项在扁平数组中的下标以便编辑）。
  const groups = ROUND_OPTIONS.map((r) => ({
    section: r.value,
    label: r.label,
    entries: items
      .map((it, idx) => ({ it, idx }))
      .filter(({ it }) => it.section === r.value),
  })).filter((g) => g.entries.length > 0);

  function update(idx: number, patch: Partial<InterviewQAInput>) {
    onChange(items.map((q, i) => (i === idx ? { ...q, ...patch } : q)));
  }

  function removeItem(idx: number) {
    const next = items.filter((_, i) => i !== idx);
    onChange(next.length > 0 ? next : [emptyQa()]);
  }

  function changeGroupSection(from: RoundSection, to: RoundSection) {
    onChange(items.map((q) => (q.section === from ? { ...q, section: to } : q)));
  }

  function addItem(section: RoundSection) {
    onChange([...items, emptyQa(section)]);
  }

  function removeRound(section: RoundSection) {
    const next = items.filter((q) => q.section !== section);
    onChange(next.length > 0 ? next : [emptyQa()]);
  }

  function addRound() {
    const used = new Set(items.map((q) => q.section));
    const next = ROUND_OPTIONS.find((r) => !used.has(r.value))?.value ?? "hr";
    onChange([...items, emptyQa(next)]);
  }

  async function generate(idx: number) {
    const token = getAccessToken();
    if (!token) return;
    if (!items[idx].question.trim()) {
      onError?.("请先填写问题再生成答案");
      return;
    }
    setGenIndex(idx);
    try {
      const { answer } = await completeAnswer(token, {
        target_type: "interview",
        question: items[idx].question,
      });
      update(idx, { answer });
    } catch (e) {
      onError?.(e instanceof Error ? e.message : "生成失败");
    } finally {
      setGenIndex(null);
    }
  }

  return (
    <div>
      <p className="mb-2 text-sm font-medium text-slate-700">
        面试问答（每个轮次只需选择一次，其下可加多条问答）
      </p>
      <div className="space-y-4">
        {groups.map((g) => (
          <div
            key={g.section}
            className="border-t border-slate-100 pt-3 first:border-t-0 first:pt-0"
          >
            <div className="mb-2 flex items-center gap-2">
              <select
                value={g.section}
                onChange={(e) =>
                  changeGroupSection(g.section, e.target.value as RoundSection)
                }
                className="rounded border border-slate-300 px-2 py-1 text-xs font-medium"
              >
                {ROUND_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <span className="text-xs text-slate-400">共 {g.entries.length} 问</span>
              <button
                type="button"
                onClick={() => removeRound(g.section)}
                className="ml-auto text-xs text-red-500 hover:underline"
              >
                删除该轮次
              </button>
            </div>
            <div className="space-y-2">
              {g.entries.map(({ it, idx }) => (
                <div key={idx} className="rounded-md border border-slate-200 p-2">
                  <input
                    value={it.question}
                    onChange={(e) => update(idx, { question: e.target.value })}
                    placeholder="问题"
                    className={`${inputCls} mb-2`}
                  />
                  <MarkdownTextarea
                    value={it.answer}
                    onChange={(v) => update(idx, { answer: v })}
                    placeholder="答案 / 参考回答（可选，可点下方 AI 生成后人工确认）"
                    rows={2}
                    className={inputCls}
                    hint={false}
                  />
                  <div className="mt-1 flex items-center justify-between">
                    <button
                      type="button"
                      onClick={() => generate(idx)}
                      disabled={genIndex === idx}
                      className="text-xs text-brand-600 hover:underline disabled:opacity-50"
                    >
                      {genIndex === idx ? "生成中…" : "AI 生成答案"}
                    </button>
                    {items.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeItem(idx)}
                        className="text-xs text-red-500 hover:underline"
                      >
                        删除
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
            <button
              type="button"
              onClick={() => addItem(g.section)}
              className="mt-2 text-xs text-brand-600 hover:underline"
            >
              + 添加一问一答
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={addRound}
        className="mt-3 rounded-lg border border-brand-500 px-3 py-1 text-xs font-medium text-brand-600 hover:bg-brand-50"
      >
        + 添加一个轮次
      </button>
    </div>
  );
}
