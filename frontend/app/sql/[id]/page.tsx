"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";

import { BackLink, ErrorText, Loading, Prose } from "@/components/content";
import { ContentInteractions, PersonalNotes } from "@/components/interactions";
import { SqlPlayground } from "@/components/sql-playground";
import { ModuleUnlockPanel } from "@/components/unlock";
import { PLAYGROUND_FIXTURES } from "@/lib/sql-playground";
import {
  ApiError,
  getAccessToken,
  getSqlDetail,
  revealSqlAnswer,
  type SqlDetail,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function SqlDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const { user, refreshUser } = useAuth();
  const [item, setItem] = useState<SqlDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showAnswer, setShowAnswer] = useState(false);
  const [busy, setBusy] = useState(false);
  const [revealError, setRevealError] = useState<string | null>(null);

  const load = useCallback(() => {
    getSqlDetail(Number(id), getAccessToken())
      .then(setItem)
      .catch(() => setError("题目不存在或加载失败"));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  const answerReady = !!item && item.answer_md != null && !item.answer_locked;
  const quotaExhausted =
    !!item && item.answer_locked && !item.module_unlocked && item.free_used >= item.free_limit;

  async function handleShowAnswer() {
    if (!item) return;
    if (answerReady) {
      setShowAnswer((v) => !v);
      return;
    }
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setRevealError(null);
    try {
      const next = await revealSqlAnswer(token, item.id);
      setItem(next);
      await refreshUser();
      if (!next.answer_locked) setShowAnswer(true);
    } catch (err) {
      setRevealError(err instanceof ApiError ? err.message : "解锁失败");
    } finally {
      setBusy(false);
    }
  }

  const isAdmin = user?.role === "admin";

  return (
    <div>
      <BackLink href="/sql" label="返回 SQL 题库" />
      {error ? (
        <ErrorText message={error} />
      ) : !item ? (
        <Loading />
      ) : (
        <>
          {/* 标题区 */}
          <header className="mb-6 border-b border-slate-200 pb-4">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900">{item.title}</h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <span
                className={`rounded px-2 py-0.5 text-xs font-medium ${
                  DIFFICULTY[item.difficulty]?.cls ?? "bg-slate-100 text-slate-600"
                }`}
              >
                {DIFFICULTY[item.difficulty]?.label ?? item.difficulty}
              </span>
              {item.tags.map((t) => (
                <span
                  key={t}
                  className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-500"
                >
                  #{t}
                </span>
              ))}
              {isAdmin && (
                <span className="rounded bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                  管理员 · 无限查看
                </span>
              )}
            </div>
          </header>

          {/* 左：题目描述 + 求解思路/SQL ｜ 右：我的笔记（随手记，sticky 跟随滚动） */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
            <div className="min-w-0">
              {/* 一、题目描述（含示例表与数据）——正文已含「## 一、题目描述」标题 */}
              <Prose>{item.prompt_md}</Prose>

              {/* 二、三：求解思路 / 求解 SQL —— 门控展示 */}
              <div className="my-5">
                {!user && item.answer_locked ? (
                  <p className="text-sm text-slate-500">
                    <Link href="/login" className="text-brand-600 hover:underline">
                      登录
                    </Link>
                    后可查看解答（每个模块免费查看 {item.free_limit} 条）。
                  </p>
                ) : quotaExhausted ? null : (
                  <button
                    onClick={handleShowAnswer}
                    disabled={busy}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
                  >
                    {answerReady
                      ? showAnswer
                        ? "收起解答"
                        : "查看求解思路与 SQL"
                      : item.module_unlocked
                        ? "查看求解思路与 SQL"
                        : `查看解答（免费剩 ${Math.max(0, item.free_limit - item.free_used)} 条）`}
                  </button>
                )}
                {revealError && <p className="mt-2 text-sm text-red-600">{revealError}</p>}
              </div>

              {quotaExhausted && (
                <ModuleUnlockPanel
                  module="sql"
                  freeUsed={item.free_used}
                  freeLimit={item.free_limit}
                  unlockPoints={item.unlock_points}
                  onUnlocked={load}
                />
              )}

              {answerReady && showAnswer && <Prose>{item.answer_md ?? ""}</Prose>}

              {PLAYGROUND_FIXTURES[item.title] && (
                <SqlPlayground fixture={PLAYGROUND_FIXTURES[item.title]} />
              )}
            </div>

            <div className="lg:sticky lg:top-20 lg:self-start">
              <PersonalNotes contentType="sql" contentId={item.id} />
            </div>
          </div>

          <ContentInteractions contentType="sql" contentId={item.id} />
        </>
      )}
    </div>
  );
}

const DIFFICULTY: Record<string, { label: string; cls: string }> = {
  easy: { label: "简单", cls: "bg-green-100 text-green-700" },
  medium: { label: "中等", cls: "bg-amber-100 text-amber-700" },
  hard: { label: "困难", cls: "bg-red-100 text-red-700" },
};
