"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import { ContentManager } from "@/components/content-manager";
import { PageHeader, Prose } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  adminApprove,
  adminApproveNode,
  adminCreateCategory,
  adminDeleteCategory,
  adminListCategories,
  adminListPendingNodes,
  adminListSubmissions,
  adminListUsers,
  adminReject,
  adminRejectNode,
  adminUpdateUser,
  getAccessToken,
  type AdminSubmission,
  type AdminUser,
  type CategoryFlat,
  type PendingNode,
  type TargetType,
} from "@/lib/api";

const TYPE_LABELS: Record<string, string> = {
  knowledge: "八股",
  sql: "SQL",
  interview: "面经",
  project: "项目",
};

const SECTIONS: { value: TargetType; label: string }[] = [
  { value: "knowledge", label: "八股" },
  { value: "sql", label: "SQL" },
  { value: "interview", label: "面经" },
  { value: "project", label: "项目" },
];

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

  async function approve(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await adminApprove(token, id);
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
            <div key={s.id} className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-medium text-slate-900">
                  [{TYPE_LABELS[s.target_type] ?? s.target_type}] {s.title}
                </span>
                <span className="text-xs text-slate-400">用户 #{s.user_id}</span>
              </div>
              {s.processed_md && <Prose>{s.processed_md}</Prose>}
              <div className="mt-3 flex gap-2">
                <button
                  onClick={() => approve(s.id)}
                  className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700"
                >
                  通过发布
                </button>
                <button
                  onClick={() => reject(s.id)}
                  className="rounded-lg border border-red-300 px-4 py-1.5 text-sm text-red-600 hover:bg-red-50"
                >
                  驳回
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <KnowledgeTreeReview />

      <ContentManager />

      <UserManager />

      <CategoryManager />
    </div>
  );
}

function UserManager() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [q, setQ] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

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
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function KnowledgeTreeReview() {
  const [pending, setPending] = useState<PendingNode[]>([]);

  const load = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    adminListPendingNodes(token)
      .then(setPending)
      .catch(() => setPending([]));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function approve(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await adminApproveNode(token, id);
    load();
  }

  async function reject(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await adminRejectNode(token, id);
    load();
  }

  return (
    <div className="mt-10">
      <h2 className="mb-3 text-lg font-semibold text-slate-900">
        知识树待审 {pending.length > 0 && `(${pending.length})`}
      </h2>
      {pending.length === 0 ? (
        <p className="text-sm text-slate-400">当前没有待审核的知识树节点。</p>
      ) : (
        <div className="space-y-2">
          {pending.map((n) => (
            <div
              key={n.id}
              className="flex items-center justify-between rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <span className="truncate text-slate-800">
                {n.parent_title ? `${n.parent_title} → ` : "（顶层）"}
                <span className="font-medium">{n.title}</span>
                <span className="ml-2 text-xs text-slate-400">
                  分类 #{n.category_id} · 用户 #{n.proposer_id ?? "-"}
                </span>
              </span>
              <span className="flex shrink-0 gap-3">
                <button onClick={() => approve(n.id)} className="text-xs text-green-600 hover:underline">
                  通过
                </button>
                <button onClick={() => reject(n.id)} className="text-xs text-red-500 hover:underline">
                  驳回
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function CategoryManager() {
  const [section, setSection] = useState<TargetType>("knowledge");
  const [cats, setCats] = useState<CategoryFlat[]>([]);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [parentId, setParentId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    adminListCategories(token, section)
      .then(setCats)
      .catch(() => setCats([]));
  }, [section]);

  useEffect(() => {
    load();
  }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const token = getAccessToken();
    if (!token) return;
    try {
      await adminCreateCategory(token, {
        section,
        name,
        slug,
        parent_id: parentId ? Number(parentId) : null,
      });
      setName("");
      setSlug("");
      setParentId("");
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建失败");
    }
  }

  async function remove(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await adminDeleteCategory(token, id);
    load();
  }

  const inputCls =
    "rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

  return (
    <div className="mt-10">
      <h2 className="mb-3 text-lg font-semibold text-slate-900">分类维护</h2>
      <div className="mb-3 flex gap-2">
        {SECTIONS.map((s) => (
          <button
            key={s.value}
            onClick={() => setSection(s.value)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              section === s.value ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="mb-4 space-y-1">
        {cats.length === 0 ? (
          <p className="text-sm text-slate-400">该板块暂无分类。</p>
        ) : (
          cats.map((c) => (
            <div
              key={c.id}
              className="flex items-center justify-between rounded border border-slate-200 bg-white px-3 py-1.5 text-sm"
            >
              <span className="text-slate-700">
                {c.parent_id ? "└ " : ""}
                {c.name} <span className="text-slate-400">/{c.slug}</span>
              </span>
              <button onClick={() => remove(c.id)} className="text-xs text-red-500 hover:underline">
                删除
              </button>
            </div>
          ))
        )}
      </div>

      <form onSubmit={add} className="flex flex-wrap items-end gap-2">
        <input placeholder="名称" value={name} onChange={(e) => setName(e.target.value)} required className={inputCls} />
        <input placeholder="slug" value={slug} onChange={(e) => setSlug(e.target.value)} required className={inputCls} />
        <input
          placeholder="父分类ID（可选）"
          value={parentId}
          onChange={(e) => setParentId(e.target.value)}
          inputMode="numeric"
          className={inputCls}
        />
        <button
          type="submit"
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
        >
          添加分类
        </button>
      </form>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </div>
  );
}
