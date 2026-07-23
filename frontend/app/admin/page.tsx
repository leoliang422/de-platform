"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ChatComposer, MessageBubbles } from "@/components/chat";
import { PageHeader, Prose } from "@/components/content";
import { FolderManager } from "@/components/folder-manager";
import { RequireAuth } from "@/components/guard";
import {
  type AdminConversation,
  adminApprove,
  adminGetUserAccess,
  adminListSubmissions,
  adminListUsers,
  adminReject,
  adminSetModuleAccess,
  adminSetProjectAccess,
  adminUpdateUser,
  type AdminSubmission,
  type AdminUser,
  type AdminUserAccess,
  type ContactMessage,
  getAccessToken,
  getAdminConversation,
  getAdminConversations,
  replyToUser,
} from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  knowledge: "八股",
  sql: "SQL",
  interview: "面经",
  project: "项目",
};

export default function AdminPage() {
  return (
    <RequireAuth adminOnly>
      <AdminInner />
    </RequireAuth>
  );
}

function AdminInner() {
  const [subs, setSubs] = useState<AdminSubmission[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    adminListSubmissions(token, "pending_review")
      .then(setSubs)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function approve(id: number, content?: string) {
    const token = getAccessToken();
    if (!token) return;
    await adminApprove(token, id, content);
    load();
  }

  async function reject(id: number) {
    const token = getAccessToken();
    if (!token) return;
    const reason = window.prompt("请输入驳回原因：");
    if (!reason) return;
    await adminReject(token, id, reason);
    load();
  }

  return (
    <div>
      <PageHeader title="管理后台" desc="审核投稿、管理内容、维护分类" />

      <h2 className="mb-3 text-lg font-semibold text-slate-900">审核队列</h2>
      {error && <p className="text-sm text-red-600">{error}</p>}
      {subs.length === 0 ? (
        <p className="text-sm text-slate-400">当前没有待审核的投稿。</p>
      ) : (
        <div className="space-y-4">
          {subs.map((s) => (
            <SubmissionReview key={s.id} sub={s} onApprove={approve} onReject={reject} />
          ))}
        </div>
      )}

      <FolderManager />

      <UserManager />

      <AdminMessages />
    </div>
  );
}

function AdminMessages() {
  const [convs, setConvs] = useState<AdminConversation[]>([]);
  const [activeUser, setActiveUser] = useState<number | null>(null);
  const [msgs, setMsgs] = useState<ContactMessage[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  const loadConvs = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    getAdminConversations(token)
      .then(setConvs)
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadConvs();
    const timer = setInterval(loadConvs, 20000);
    return () => clearInterval(timer);
  }, [loadConvs]);

  const openConv = useCallback((userId: number) => {
    const token = getAccessToken();
    if (!token) return;
    setActiveUser(userId);
    getAdminConversation(token, userId)
      .then(setMsgs)
      .catch(() => setMsgs([]));
    // 拉取后未读会清零，刷新列表徽标
    setConvs((prev) => prev.map((c) => (c.user_id === userId ? { ...c, unread: 0 } : c)));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs]);

  async function handleReply(payload: Parameters<typeof replyToUser>[2]) {
    if (activeUser == null) return;
    const token = getAccessToken();
    if (!token) return;
    const msg = await replyToUser(token, activeUser, payload);
    setMsgs((prev) => [...prev, msg]);
    loadConvs();
  }

  const activeConv = convs.find((c) => c.user_id === activeUser);

  return (
    <div className="mt-10">
      <h2 className="mb-3 text-lg font-semibold text-slate-900">用户私信</h2>
      <div className="flex h-[26rem] overflow-hidden rounded-xl border border-slate-200 bg-white">
        {/* 会话列表 */}
        <div className="w-64 shrink-0 overflow-y-auto border-r border-slate-200">
          {convs.length === 0 ? (
            <p className="p-4 text-sm text-slate-400">暂无用户私信。</p>
          ) : (
            convs.map((c) => (
              <button
                key={c.user_id}
                onClick={() => openConv(c.user_id)}
                className={`flex w-full items-center gap-2 border-b border-slate-100 px-3 py-2.5 text-left transition hover:bg-slate-50 ${
                  activeUser === c.user_id ? "bg-brand-50" : ""
                }`}
              >
                <div className="flex-1 overflow-hidden">
                  <div className="flex items-center justify-between">
                    <span className="truncate text-sm font-medium text-slate-800">
                      {c.nickname}
                    </span>
                    {c.unread > 0 && (
                      <span className="ml-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-500 px-1 text-[10px] font-medium text-white">
                        {c.unread}
                      </span>
                    )}
                  </div>
                  <p className="truncate text-xs text-slate-400">{c.last_body}</p>
                </div>
              </button>
            ))
          )}
        </div>

        {/* 对话窗口 */}
        <div className="flex flex-1 flex-col">
          {activeUser == null ? (
            <div className="flex flex-1 items-center justify-center text-sm text-slate-400">
              选择左侧用户开始对话
            </div>
          ) : (
            <>
              <div className="border-b border-slate-200 px-4 py-2 text-sm font-medium text-slate-700">
                {activeConv?.nickname ?? `用户 #${activeUser}`}
              </div>
              <div className="flex-1 space-y-3 overflow-y-auto p-4">
                <MessageBubbles messages={msgs} selfIsAdmin />
                <div ref={bottomRef} />
              </div>
              <ChatComposer onSend={handleReply} placeholder="回复用户…（⌘/Ctrl + Enter 发送）" />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function SubmissionReview({
  sub,
  onApprove,
  onReject,
}: {
  sub: AdminSubmission;
  onApprove: (id: number, content?: string) => Promise<void>;
  onReject: (id: number) => Promise<void>;
}) {
  // 编辑器默认取 AI 整理稿；管理员可一键切换原文，或手动二次编辑后发布。
  const [editor, setEditor] = useState(sub.processed_md ?? sub.raw_content);
  const [busy, setBusy] = useState(false);
  const isInterview = sub.target_type === "interview";

  async function publish() {
    setBusy(true);
    try {
      await onApprove(sub.id, editor);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-medium text-slate-900">
          [{TYPE_LABELS[sub.target_type] ?? sub.target_type}] {sub.title}
        </span>
        <span className="text-xs text-slate-400">用户 #{sub.user_id}</span>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">用户原文</span>
            <button
              type="button"
              onClick={() => setEditor(sub.raw_content)}
              className="text-xs text-brand-600 hover:underline"
            >
              用此版本 →
            </button>
          </div>
          <Prose>{sub.raw_content}</Prose>
        </div>
        <div>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-slate-500">AI 整理稿</span>
            <button
              type="button"
              onClick={() => setEditor(sub.processed_md ?? sub.raw_content)}
              className="text-xs text-brand-600 hover:underline"
            >
              用此版本 →
            </button>
          </div>
          <Prose>{sub.processed_md ?? "（暂无 AI 稿）"}</Prose>
        </div>
      </div>

      <div className="mt-4">
        <label className="mb-1 block text-xs font-medium text-slate-500">
          最终发布内容（可二次编辑，Markdown）
        </label>
        <textarea
          value={editor}
          onChange={(e) => setEditor(e.target.value)}
          rows={10}
          className="w-full rounded-lg border border-slate-300 p-3 font-mono text-xs leading-relaxed focus:border-brand-500 focus:outline-none"
        />
        {isInterview && (
          <p className="mt-1 text-xs text-amber-600">
            面经按「企业 / 问答」结构化发布，此正文仅供参考，不影响最终展示。
          </p>
        )}
      </div>

      <div className="mt-3 flex gap-2">
        <button
          disabled={busy}
          onClick={publish}
          className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
        >
          通过发布
        </button>
        <button
          disabled={busy}
          onClick={() => onReject(sub.id)}
          className="rounded-lg border border-red-300 px-4 py-1.5 text-sm text-red-600 hover:bg-red-50 disabled:opacity-50"
        >
          驳回
        </button>
      </div>
    </div>
  );
}

function UserManager() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [q, setQ] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [accessUser, setAccessUser] = useState<AdminUser | null>(null);

  const load = useCallback((query: string) => {
    const token = getAccessToken();
    if (!token) return;
    adminListUsers(token, query || undefined)
      .then(setUsers)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load("");
  }, [load]);

  async function patch(id: number, input: Parameters<typeof adminUpdateUser>[2]) {
    const token = getAccessToken();
    if (!token) return;
    setBusyId(id);
    setError(null);
    try {
      const updated = await adminUpdateUser(token, id, input);
      setUsers((us) => us.map((u) => (u.id === id ? updated : u)));
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusyId(null);
    }
  }

  function adjustPoints(u: AdminUser) {
    const raw = window.prompt(
      `为「${u.nickname}」设置积分（当前 ${u.points_balance}）：\n输入绝对值，或用 +N / -N 增减`,
    );
    if (raw == null) return;
    const t = raw.trim();
    if (!t) return;
    const reason = window.prompt("调整原因（可选）：") ?? undefined;
    if (t.startsWith("+") || t.startsWith("-")) {
      const delta = Number(t);
      if (Number.isNaN(delta)) return;
      patch(u.id, { delta_points: delta, reason });
    } else {
      const abs = Number(t);
      if (Number.isNaN(abs)) return;
      patch(u.id, { set_points: abs, reason });
    }
  }

  return (
    <div className="mt-10">
      <h2 className="mb-3 text-lg font-semibold text-slate-900">用户管理</h2>
      <div className="mb-3 flex gap-2">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && load(q)}
          placeholder="搜索邮箱 / 昵称"
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        <button
          onClick={() => load(q)}
          className="rounded-lg bg-slate-100 px-3 py-2 text-sm text-slate-600 hover:bg-slate-200"
        >
          搜索
        </button>
      </div>
      {error && <p className="mb-2 text-sm text-red-600">{error}</p>}

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2">ID</th>
              <th className="px-3 py-2">邮箱</th>
              <th className="px-3 py-2">昵称</th>
              <th className="px-3 py-2">角色</th>
              <th className="px-3 py-2">积分</th>
              <th className="px-3 py-2">操作</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {users.map((u) => (
              <tr key={u.id} className="hover:bg-slate-50">
                <td className="px-3 py-2 text-slate-400">{u.id}</td>
                <td className="px-3 py-2 text-slate-700">{u.email}</td>
                <td className="px-3 py-2 text-slate-700">{u.nickname}</td>
                <td className="px-3 py-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs ${
                      u.role === "admin"
                        ? "bg-brand-100 text-brand-700"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {u.role}
                  </span>
                </td>
                <td className="px-3 py-2 font-medium text-slate-800">{u.points_balance}</td>
                <td className="px-3 py-2">
                  <div className="flex gap-3">
                    <button
                      disabled={busyId === u.id}
                      onClick={() => adjustPoints(u)}
                      className="text-xs text-brand-600 hover:underline disabled:opacity-50"
                    >
                      调整积分
                    </button>
                    <button
                      disabled={busyId === u.id}
                      onClick={() =>
                        patch(u.id, { role: u.role === "admin" ? "user" : "admin" })
                      }
                      className="text-xs text-slate-500 hover:underline disabled:opacity-50"
                    >
                      {u.role === "admin" ? "降为用户" : "设为管理员"}
                    </button>
                    <button
                      onClick={() => setAccessUser(u)}
                      className="text-xs text-brand-600 hover:underline"
                    >
                      权限
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {accessUser && (
        <AccessPanel user={accessUser} onClose={() => setAccessUser(null)} />
      )}
    </div>
  );
}

function AccessPanel({ user, onClose }: { user: AdminUser; onClose: () => void }) {
  const [access, setAccess] = useState<AdminUserAccess | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    adminGetUserAccess(token, user.id)
      .then(setAccess)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [user.id]);

  const isAdmin = user.role === "admin";

  async function toggleModule(module: string, grant: boolean) {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      setAccess(await adminSetModuleAccess(token, user.id, module, grant));
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  async function toggleProject(projectId: number, grant: boolean) {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      setAccess(await adminSetProjectAccess(token, user.id, projectId, grant));
    } catch (e) {
      setError(e instanceof Error ? e.message : "操作失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">
              权限范围 · {user.nickname}
            </h3>
            <p className="text-xs text-slate-500">{user.email}</p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            ✕
          </button>
        </div>

        {isAdmin && (
          <p className="mb-3 rounded-md bg-brand-50 px-3 py-2 text-xs text-brand-700">
            该用户是管理员，默认拥有全部权限（无限查看，不受额度限制）。
          </p>
        )}
        {error && <p className="mb-2 text-sm text-red-600">{error}</p>}
        {!access ? (
          <p className="text-sm text-slate-400">加载中…</p>
        ) : (
          <div className="space-y-5">
            <div>
              <h4 className="mb-2 text-sm font-semibold text-slate-700">模块解锁</h4>
              <div className="space-y-2">
                {access.modules.map((m) => (
                  <div
                    key={m.module}
                    className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"
                  >
                    <span className="text-sm text-slate-700">
                      {m.label}
                      <span
                        className={`ml-2 rounded px-1.5 py-0.5 text-xs ${
                          m.unlocked
                            ? "bg-green-100 text-green-700"
                            : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        {m.unlocked ? "已解锁" : "未解锁"}
                      </span>
                    </span>
                    <button
                      disabled={busy || isAdmin}
                      onClick={() => toggleModule(m.module, !m.unlocked)}
                      className="text-xs text-brand-600 hover:underline disabled:opacity-40"
                    >
                      {m.unlocked ? "收回" : "赋予"}
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <h4 className="mb-2 text-sm font-semibold text-slate-700">项目解锁</h4>
              {access.projects.length === 0 ? (
                <p className="text-xs text-slate-400">暂无需要积分解锁的项目。</p>
              ) : (
                <div className="space-y-2">
                  {access.projects.map((p) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2"
                    >
                      <span className="text-sm text-slate-700">
                        {p.title}
                        <span
                          className={`ml-2 rounded px-1.5 py-0.5 text-xs ${
                            p.unlocked
                              ? "bg-green-100 text-green-700"
                              : "bg-slate-100 text-slate-500"
                          }`}
                        >
                          {p.unlocked ? "已解锁" : "未解锁"}
                        </span>
                      </span>
                      <button
                        disabled={busy || isAdmin}
                        onClick={() => toggleProject(p.id, !p.unlocked)}
                        className="text-xs text-brand-600 hover:underline disabled:opacity-40"
                      >
                        {p.unlocked ? "收回" : "赋予"}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

