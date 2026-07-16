"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import {
  adminCreateContent,
  adminDeleteContent,
  adminGetContentDetail,
  adminListContent,
  adminUpdateContent,
  getAccessToken,
  type ContentSummary,
  type ContentType,
} from "@/lib/api";

type FieldType = "text" | "textarea" | "number" | "checkbox" | "select";

interface FieldDef {
  name: string;
  label: string;
  type: FieldType;
  required?: boolean;
  nullable?: boolean;
  options?: { value: string; label: string }[];
  placeholder?: string;
}

const TABS: { value: ContentType; label: string }[] = [
  { value: "knowledge", label: "八股" },
  { value: "sql", label: "SQL" },
  { value: "interview", label: "面经" },
  { value: "project", label: "项目" },
];

const FIELDS: Record<ContentType, FieldDef[]> = {
  knowledge: [
    { name: "title", label: "标题", type: "text", required: true },
    { name: "content_md", label: "正文（直接粘贴 Markdown）", type: "textarea", required: true },
    { name: "category_id", label: "分类 ID（可选）", type: "number" },
    { name: "is_paid", label: "付费内容", type: "checkbox" },
    { name: "price_cash", label: "现金价（元，可选）", type: "text", nullable: true },
    { name: "price_points", label: "积分价（可选）", type: "number" },
  ],
  sql: [
    { name: "title", label: "题目标题", type: "text", required: true },
    { name: "prompt_md", label: "题干（Markdown）", type: "textarea", required: true },
    { name: "answer_md", label: "参考答案（Markdown）", type: "textarea", required: true },
    {
      name: "difficulty",
      label: "难度",
      type: "select",
      options: [
        { value: "easy", label: "简单" },
        { value: "medium", label: "中等" },
        { value: "hard", label: "困难" },
      ],
    },
    { name: "tags", label: "标签（逗号分隔）", type: "text" },
    { name: "category_id", label: "分类 ID（可选）", type: "number" },
  ],
  interview: [
    { name: "company_name", label: "企业名称", type: "text", required: true },
    { name: "position", label: "岗位", type: "text", required: true },
    { name: "content_md", label: "面经正文（Markdown）", type: "textarea", required: true },
  ],
  project: [
    { name: "title", label: "项目标题", type: "text", required: true },
    { name: "description_md", label: "项目描述（Markdown）", type: "textarea", required: true },
    { name: "implementation_md", label: "实现说明（Markdown）", type: "textarea" },
    {
      name: "level",
      label: "层级",
      type: "select",
      options: [
        { value: "basic", label: "基础" },
        { value: "advanced", label: "进阶" },
      ],
    },
    {
      name: "access_type",
      label: "访问类型",
      type: "select",
      options: [
        { value: "free", label: "免费" },
        { value: "paid", label: "付费" },
      ],
    },
    { name: "price_cash", label: "现金价（元，可选）", type: "text", nullable: true },
    { name: "price_points", label: "积分价（可选）", type: "number" },
  ],
};

type FormValues = Record<string, string | boolean>;

function emptyValues(type: ContentType): FormValues {
  const v: FormValues = {};
  for (const f of FIELDS[type]) {
    v[f.name] = f.type === "checkbox" ? false : f.type === "select" ? f.options![0].value : "";
  }
  return v;
}

const inputCls =
  "w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none";

export function ContentManager() {
  const [type, setType] = useState<ContentType>("knowledge");
  const [items, setItems] = useState<ContentSummary[]>([]);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [values, setValues] = useState<FormValues>(emptyValues("knowledge"));
  const [status, setStatus] = useState("published");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback((t: ContentType) => {
    const token = getAccessToken();
    if (!token) return;
    adminListContent(token, t)
      .then(setItems)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    load(type);
  }, [type, load]);

  function switchType(t: ContentType) {
    setType(t);
    setEditing(null);
    setError(null);
  }

  function openNew() {
    setValues(emptyValues(type));
    setStatus("published");
    setEditing("new");
    setError(null);
  }

  async function openEdit(id: number) {
    const token = getAccessToken();
    if (!token) return;
    setError(null);
    try {
      const detail = await adminGetContentDetail(token, type, id);
      const v = emptyValues(type);
      for (const f of FIELDS[type]) {
        const raw = detail[f.name];
        if (raw == null) continue;
        v[f.name] = f.type === "checkbox" ? Boolean(raw) : String(raw);
      }
      setValues(v);
      setStatus(String(detail.status ?? "published"));
      setEditing(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "加载失败");
    }
  }

  function buildBody(): Record<string, unknown> {
    const body: Record<string, unknown> = { status };
    for (const f of FIELDS[type]) {
      const val = values[f.name];
      if (f.type === "checkbox") {
        body[f.name] = Boolean(val);
      } else if (f.type === "number") {
        body[f.name] = val === "" ? null : Number(val);
      } else if (f.nullable) {
        body[f.name] = val === "" ? null : val;
      } else {
        body[f.name] = val;
      }
    }
    return body;
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      const body = buildBody();
      if (editing === "new") {
        await adminCreateContent(token, type, body);
      } else if (typeof editing === "number") {
        await adminUpdateContent(token, type, editing, body);
      }
      setEditing(null);
      load(type);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  async function toggleStatus(item: ContentSummary) {
    const token = getAccessToken();
    if (!token) return;
    const next = item.status === "published" ? "draft" : "published";
    await adminUpdateContent(token, type, item.id, { status: next });
    load(type);
  }

  async function remove(id: number) {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("确认删除该内容？此操作不可恢复。")) return;
    await adminDeleteContent(token, type, id);
    load(type);
  }

  return (
    <div className="mt-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">内容管理</h2>
        <button
          onClick={openNew}
          className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
        >
          + 新建{TABS.find((t) => t.value === type)?.label}
        </button>
      </div>

      <div className="mb-4 flex gap-2">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => switchType(t.value)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              type === t.value ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      {editing !== null && (
        <form onSubmit={submit} className="mb-6 space-y-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="text-sm font-medium text-slate-700">
            {editing === "new" ? "新建内容" : `编辑内容 #${editing}`}
          </p>
          {FIELDS[type].map((f) => (
            <label key={f.name} className="block">
              <span className="mb-1 block text-xs font-medium text-slate-600">{f.label}</span>
              {f.type === "textarea" ? (
                <textarea
                  value={values[f.name] as string}
                  onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.target.value }))}
                  required={f.required}
                  rows={5}
                  className={inputCls}
                />
              ) : f.type === "checkbox" ? (
                <input
                  type="checkbox"
                  checked={values[f.name] as boolean}
                  onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.target.checked }))}
                  className="h-4 w-4"
                />
              ) : f.type === "select" ? (
                <select
                  value={values[f.name] as string}
                  onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.target.value }))}
                  className={inputCls}
                >
                  {f.options!.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type={f.type === "number" ? "number" : "text"}
                  value={values[f.name] as string}
                  onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.target.value }))}
                  required={f.required}
                  className={inputCls}
                />
              )}
            </label>
          ))}
          <label className="block">
            <span className="mb-1 block text-xs font-medium text-slate-600">状态</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className={inputCls}
            >
              <option value="published">已发布（上架）</option>
              <option value="draft">草稿（下架）</option>
            </select>
          </label>
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              {busy ? "保存中…" : "保存"}
            </button>
            <button
              type="button"
              onClick={() => setEditing(null)}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
            >
              取消
            </button>
          </div>
        </form>
      )}

      <div className="space-y-1">
        {items.length === 0 ? (
          <p className="text-sm text-slate-400">该板块暂无内容。</p>
        ) : (
          items.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between rounded border border-slate-200 bg-white px-3 py-2 text-sm"
            >
              <span className="flex items-center gap-2 truncate">
                <span className="text-slate-800">{item.title}</span>
                {item.subtitle && <span className="text-xs text-slate-400">{item.subtitle}</span>}
                <span
                  className={`rounded px-1.5 py-0.5 text-xs ${
                    item.status === "published"
                      ? "bg-green-100 text-green-700"
                      : "bg-slate-200 text-slate-600"
                  }`}
                >
                  {item.status === "published" ? "已发布" : "草稿"}
                </span>
              </span>
              <span className="flex shrink-0 gap-3">
                <button onClick={() => openEdit(item.id)} className="text-xs text-brand-600 hover:underline">
                  编辑
                </button>
                <button onClick={() => toggleStatus(item)} className="text-xs text-slate-500 hover:underline">
                  {item.status === "published" ? "下架" : "上架"}
                </button>
                <button onClick={() => remove(item.id)} className="text-xs text-red-500 hover:underline">
                  删除
                </button>
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
