"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";

import { BackLink, ErrorText, Loading, Prose } from "@/components/content";
import { ContentInteractions, PersonalNotes } from "@/components/interactions";
import { SqlPlayground } from "@/components/sql-playground";
import { ModuleUnlockPanel } from "@/components/unlock";
import { PLAYGROUND_FIXTURES } from "@/lib/sql-playground";
import {
  ApiError,
  getAccessToken,
  getSqlDetail,
  getSqlList,
  revealSqlAnswer,
  type SqlDetail,
  type SqlListItem,
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
  const [nav, setNav] = useState<{ prev: SqlListItem | null; next: SqlListItem | null }>({
    prev: null,
    next: null,
  });

  const load = useCallback(() => {
    getSqlDetail(Number(id), getAccessToken())
      .then(setItem)
      .catch(() => setError("题目不存在或加载失败"));
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  // 同题型内的上一题/下一题（列表按 id 倒序）。
  useEffect(() => {
    if (!item) return;
    getSqlList(item.category_id ?? undefined)
      .then((list) => {
        const idx = list.findIndex((x) => x.id === item.id);
        if (idx === -1) {
          setNav({ prev: null, next: null });
          return;
        }
        setNav({ prev: list[idx - 1] ?? null, next: list[idx + 1] ?? null });
      })
      .catch(() => setNav({ prev: null, next: null }));
  }, [item?.id, item?.category_id]); // eslint-disable-line react-hooks/exhaustive-deps

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
          <header className="mb-4 border-b border-slate-200 pb-3">
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
              {/* 题目描述：难度色条 + 卡片 */}
              <div
                className={`overflow-hidden rounded-lg border-l-4 ${
                  DIFF_BAR[item.difficulty] ?? "border-slate-300"
                }`}
              >
                <Prose>{item.prompt_md}</Prose>
              </div>

              {/* 求解思路 / 求解 SQL —— 门控展示 */}
              <div className="mt-3 mb-3">
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

              {answerReady && showAnswer && <AnswerTabs md={item.answer_md ?? ""} />}

              {PLAYGROUND_FIXTURES[item.title] && (
                <SqlPlayground fixture={PLAYGROUND_FIXTURES[item.title]} />
              )}
            </div>

            <div className="lg:sticky lg:top-20 lg:self-start">
              <PersonalNotes contentType="sql" contentId={item.id} />
            </div>
          </div>

          {(nav.prev || nav.next) && (
            <div className="mt-6 grid grid-cols-2 gap-3 border-t border-slate-200 pt-4">
              {nav.prev ? (
                <Link
                  href={`/sql/${nav.prev.id}`}
                  className="group rounded-lg border border-slate-200 p-3 transition hover:border-brand-400 hover:bg-slate-50"
                >
                  <div className="text-xs text-slate-400">← 上一题</div>
                  <div className="mt-0.5 truncate text-sm font-medium text-slate-700 group-hover:text-brand-700">
                    {nav.prev.title}
                  </div>
                </Link>
              ) : (
                <span />
              )}
              {nav.next ? (
                <Link
                  href={`/sql/${nav.next.id}`}
                  className="group rounded-lg border border-slate-200 p-3 text-right transition hover:border-brand-400 hover:bg-slate-50"
                >
                  <div className="text-xs text-slate-400">下一题 →</div>
                  <div className="mt-0.5 truncate text-sm font-medium text-slate-700 group-hover:text-brand-700">
                    {nav.next.title}
                  </div>
                </Link>
              ) : (
                <span />
              )}
            </div>
          )}

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

const DIFF_BAR: Record<string, string> = {
  easy: "border-green-400",
  medium: "border-amber-400",
  hard: "border-red-400",
};

// 把答案 Markdown 拆成「求解思路」与「求解 SQL」两段（去掉各自的 ## 标题行）。
function splitAnswer(md: string): { idea: string; sql: string } {
  const marker = md.indexOf("## 求解 SQL");
  if (marker === -1) return { idea: md.replace(/^##\s*求解思路\s*\n?/, "").trim(), sql: "" };
  const idea = md
    .slice(0, marker)
    .replace(/^##\s*求解思路\s*\n?/, "")
    .trim();
  const sql = md
    .slice(marker)
    .replace(/^##[^\n]*\n?/, "")
    .trim();
  return { idea, sql };
}

// 解答区：求解思路 / 求解 SQL 分标签页切换。
function AnswerTabs({ md }: { md: string }) {
  const { idea, sql } = useMemo(() => splitAnswer(md), [md]);
  const [tab, setTab] = useState<"idea" | "sql">("idea");

  if (!sql) return <Prose>{md}</Prose>;

  const tabCls = (active: boolean) =>
    `-mb-px border-b-2 px-3 py-1.5 text-sm font-medium transition ${
      active
        ? "border-brand-600 text-brand-700"
        : "border-transparent text-slate-500 hover:text-slate-700"
    }`;

  return (
    <div className="mt-3">
      <div className="mb-2 flex gap-1 border-b border-slate-200">
        <button onClick={() => setTab("idea")} className={tabCls(tab === "idea")}>
          求解思路
        </button>
        <button onClick={() => setTab("sql")} className={tabCls(tab === "sql")}>
          求解 SQL
        </button>
      </div>
      {tab === "idea" ? <Prose>{idea}</Prose> : <Prose>{sql}</Prose>}
    </div>
  );
}
