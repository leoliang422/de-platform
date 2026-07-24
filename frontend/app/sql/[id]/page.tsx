"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";

import { ErrorText, Loading, Prose } from "@/components/content";
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
  setSqlProgress,
  type SqlDetail,
  type SqlListItem,
  type SqlProgressStatus,
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

  const accessible = !!item && !item.locked;
  const quotaExhausted =
    !!item && item.locked && !item.module_unlocked && item.free_used >= item.free_limit;

  // 「查看本题」：题目级门控——消耗一次免费额度，解锁整题（题干+解答）。
  async function handleReveal() {
    if (!item) return;
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setRevealError(null);
    try {
      const next = await revealSqlAnswer(token, item.id);
      setItem(next);
      await refreshUser();
    } catch (err) {
      setRevealError(err instanceof ApiError ? err.message : "解锁失败");
    } finally {
      setBusy(false);
    }
  }

  const isAdmin = user?.role === "admin";

  async function markProgress(target: "done" | "mastered") {
    if (!item) return;
    const token = getAccessToken();
    if (!token) return;
    const next: SqlProgressStatus = item.my_status === target ? "none" : target;
    try {
      const res = await setSqlProgress(token, item.id, next);
      setItem((prev) => (prev ? { ...prev, my_status: res.my_status ?? null } : prev));
    } catch {
      // 忽略
    }
  }

  return (
    <div>
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link href="/sql" className="text-sm text-brand-600 hover:underline">
          ← 返回 SQL 题库
        </Link>
        {(nav.prev || nav.next) && (
          <div className="flex items-center gap-4 text-sm">
            {nav.prev && (
              <Link
                href={`/sql/${nav.prev.id}`}
                title={nav.prev.title}
                className="text-brand-600 hover:underline"
              >
                ← 上一题
              </Link>
            )}
            {nav.next && (
              <Link
                href={`/sql/${nav.next.id}`}
                title={nav.next.title}
                className="flex items-center gap-1 text-brand-600 hover:underline"
              >
                下一题：
                <span className="max-w-[9rem] truncate">{nav.next.title}</span>
                <span aria-hidden>→</span>
              </Link>
            )}
          </div>
        )}
      </div>
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
              {item.my_status === "done" && (
                <span className="rounded bg-sky-100 px-2 py-0.5 text-xs text-sky-700">已做</span>
              )}
              {item.my_status === "mastered" && (
                <span className="rounded bg-green-100 px-2 py-0.5 text-xs text-green-700">
                  已掌握
                </span>
              )}
              {isAdmin && (
                <span className="rounded bg-brand-50 px-2 py-0.5 text-xs text-brand-700">
                  管理员 · 无限查看
                </span>
              )}
            </div>
            {user && (
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => markProgress("done")}
                  className={`rounded-lg border px-3 py-1 text-xs font-medium transition ${
                    item.my_status === "done"
                      ? "border-sky-400 bg-sky-50 text-sky-700"
                      : "border-slate-300 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {item.my_status === "done" ? "✓ 已做" : "标记已做"}
                </button>
                <button
                  onClick={() => markProgress("mastered")}
                  className={`rounded-lg border px-3 py-1 text-xs font-medium transition ${
                    item.my_status === "mastered"
                      ? "border-green-400 bg-green-50 text-green-700"
                      : "border-slate-300 text-slate-600 hover:bg-slate-50"
                  }`}
                >
                  {item.my_status === "mastered" ? "✓ 已掌握" : "标记已掌握"}
                </button>
              </div>
            )}
          </header>

          {accessible ? (
            /* 已授权：左 题目+解答 ｜ 右 我的笔记（sticky 随手记） */
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div className="min-w-0">
                <div className="overflow-hidden rounded-lg">
                  <Prose bare>{item.prompt_md}</Prose>
                </div>

                <div className="mt-3 mb-3">
                  <button
                    onClick={() => setShowAnswer((v) => !v)}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700"
                  >
                    {showAnswer ? "收起解答" : "查看求解思路与 SQL"}
                  </button>
                </div>

                {showAnswer && item.answer_md && <AnswerTabs md={item.answer_md} />}

                {PLAYGROUND_FIXTURES[item.title] && (
                  <SqlPlayground fixture={PLAYGROUND_FIXTURES[item.title]} />
                )}
              </div>

              <div className="lg:sticky lg:top-20 lg:self-start">
                <PersonalNotes contentType="sql" contentId={item.id} />
              </div>
            </div>
          ) : (
            /* 未授权：居中限宽的门控卡片（登录 / 解锁模块 / 查看本题） */
            <div className="mx-auto max-w-lg py-4">
              {!user ? (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center text-sm text-slate-600">
                  🔒 本题内容已锁定。
                  <Link href="/login" className="mx-1 font-medium text-brand-600 hover:underline">
                    登录
                  </Link>
                  后可查看（每个模块免费查看 {item.free_limit} 条题目）。
                </div>
              ) : quotaExhausted ? (
                <ModuleUnlockPanel
                  module="sql"
                  freeUsed={item.free_used}
                  freeLimit={item.free_limit}
                  unlockPoints={item.unlock_points}
                  onUnlocked={load}
                />
              ) : (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-8 text-center">
                  <p className="mb-4 text-sm text-slate-500">
                    🔒 本题内容已锁定，查看后可见题目与解答。
                  </p>
                  <button
                    onClick={handleReveal}
                    disabled={busy}
                    className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-brand-700 disabled:opacity-50"
                  >
                    {item.module_unlocked
                      ? "查看本题"
                      : `查看本题（免费剩 ${Math.max(0, item.free_limit - item.free_used)} 条）`}
                  </button>
                  {revealError && <p className="mt-2 text-sm text-red-600">{revealError}</p>}
                </div>
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

  if (!sql) return <Prose bare>{md}</Prose>;

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
      {tab === "idea" ? <Prose bare>{idea}</Prose> : <Prose bare>{sql}</Prose>}
    </div>
  );
}
