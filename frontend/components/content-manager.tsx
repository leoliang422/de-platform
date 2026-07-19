"use client";

import { useEffect, useState, type FormEvent } from "react";

import { MarkdownTextarea } from "@/components/markdown-textarea";
import {
  adminCreateContent,
  adminGetContentDetail,
  adminListCategories,
  adminUpdateContent,
  completeAnswer,
  getAccessToken,
  parseSubmission,
  type CategoryFlat,
  type ContentType,
  type InterviewQAInput,
} from "@/lib/api";

type FieldType = "text" | "textarea" | "number" | "checkbox" | "select" | "category";

const ROUND_OPTIONS: { value: InterviewQAInput["section"]; label: string }[] = [
  { value: "round1", label: "一面" },
  { value: "round2", label: "二面" },
  { value: "round3", label: "三面" },
  { value: "hr", label: "HR面" },
];

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}

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
    { name: "category_id", label: "分类（可选）", type: "category" },
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
    { name: "category_id", label: "分类（可选）", type: "category" },
  ],
  interview: [
    { name: "company_name", label: "企业名称", type: "text", required: true },
    {
      name: "interview_type",
      label: "类型",
      type: "select",
      options: [
        { value: "campus", label: "校招" },
        { value: "social", label: "社招" },
        { value: "daily", label: "日常实习" },
        { value: "summer", label: "暑期实习" },
      ],
    },
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

function emptyQa(): InterviewQAInput {
  return { section: "round1", question: "", answer: "" };
}

// 面经问答编辑器：管理员可按轮次编辑问题/答案，并可 AI 生成答案。
function InterviewQaEditor({
  items,
  onChange,
}: {
  items: InterviewQAInput[];
  onChange: (next: InterviewQAInput[]) => void;
}) {
  const [genIndex, setGenIndex] = useState<number | null>(null);

  function update(i: number, patch: Partial<InterviewQAInput>) {
    onChange(items.map((q, idx) => (idx === i ? { ...q, ...patch } : q)));
  }

  async function generate(i: number) {
    const token = getAccessToken();
    if (!token || !items[i].question.trim()) return;
    setGenIndex(i);
    try {
      const { answer } = await completeAnswer(token, {
        target_type: "interview",
        question: items[i].question,
      });
      update(i, { answer });
    } catch {
      // 忽略：保留原答案
    } finally {
      setGenIndex(null);
    }
  }

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3">
      <p className="mb-2 text-xs font-medium text-slate-600">面试问答（按轮次分别填写问题与答案）</p>
      <div className="space-y-3">
        {items.map((qa, i) => (
          <div key={i} className="rounded-md bg-slate-50 p-3">
            <div className="mb-2 flex items-center gap-2">
              <select
                value={qa.section}
                onChange={(e) =>
                  update(i, { section: e.target.value as InterviewQAInput["section"] })
                }
                className="rounded border border-slate-300 px-2 py-1 text-xs"
              >
                {ROUND_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              <span className="text-xs text-slate-400">第 {i + 1} 条</span>
              {items.length > 1 && (
                <button
                  type="button"
                  onClick={() => onChange(items.filter((_, idx) => idx !== i))}
                  className="ml-auto text-xs text-red-500 hover:underline"
                >
                  删除
                </button>
              )}
            </div>
            <input
              value={qa.question}
              onChange={(e) => update(i, { question: e.target.value })}
              placeholder="问题"
              className={`${inputCls} mb-2`}
            />
            <MarkdownTextarea
              value={qa.answer}
              onChange={(v) => update(i, { answer: v })}
              placeholder="答案 / 参考回答"
              rows={2}
              className={inputCls}
              hint={false}
            />
            <button
              type="button"
              onClick={() => generate(i)}
              disabled={genIndex === i}
              className="mt-1 text-xs text-brand-600 hover:underline disabled:opacity-50"
            >
              {genIndex === i ? "生成中…" : "AI 生成答案"}
            </button>
          </div>
        ))}
      </div>
      <button
        type="button"
        onClick={() => onChange([...items, emptyQa()])}
        className="mt-2 text-sm text-brand-600 hover:underline"
      >
        + 添加一条问答
      </button>
    </div>
  );
}

interface AiDraft {
  title: string;
  content_md: string;
  prompt_md: string;
  answer_md: string;
  difficulty: string;
  description_md: string;
  implementation_md: string;
  company_name: string;
  interview_type: string;
  qa_items: InterviewQAInput[];
  completing: boolean;
}

function emptyAiDraft(): AiDraft {
  return {
    title: "",
    content_md: "",
    prompt_md: "",
    answer_md: "",
    difficulty: "medium",
    description_md: "",
    implementation_md: "",
    company_name: "",
    interview_type: "campus",
    qa_items: [emptyQa()],
    completing: false,
  };
}

// 管理员 AI 解析：上传文件 / 粘贴文本 → 拆分为多条草稿 → 编辑后一键直接发布。
export function AiImportPanel({
  type,
  onDone,
  presetCategoryId,
}: {
  type: ContentType;
  onDone: () => void;
  presetCategoryId?: number | null;
}) {
  const [text, setText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [drafts, setDrafts] = useState<AiDraft[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  function update(i: number, patch: Partial<AiDraft>) {
    setDrafts((prev) => prev.map((d, idx) => (idx === i ? { ...d, ...patch } : d)));
  }

  async function handleParse(file: File | null) {
    const token = getAccessToken();
    if (!token) return;
    if (!file && !text.trim()) {
      setErr("请上传文件或粘贴文本");
      return;
    }
    setParsing(true);
    setErr(null);
    setMsg(null);
    try {
      const res = await parseSubmission(token, {
        targetType: type,
        text: text.trim() || undefined,
        file,
      });
      const items = res.items ?? [];
      const ds: AiDraft[] = items.map((it) => {
        const qa = Array.isArray(it.qa_items) ? (it.qa_items as Record<string, unknown>[]) : [];
        return {
          ...emptyAiDraft(),
          title: str(it.title),
          content_md: str(it.content_md),
          prompt_md: str(it.prompt_md),
          answer_md: str(it.answer_md),
          difficulty: str(it.difficulty) || "medium",
          description_md: str(it.description_md),
          implementation_md: str(it.implementation_md),
          company_name: str(it.company_name),
          interview_type: ["social", "campus", "daily", "summer"].includes(str(it.interview_type))
            ? str(it.interview_type)
            : "campus",
          qa_items:
            qa.length > 0
              ? qa.map((q) => ({
                  section: (["round1", "round2", "round3", "hr"].includes(str(q.section))
                    ? str(q.section)
                    : "round1") as InterviewQAInput["section"],
                  question: str(q.question),
                  answer: str(q.answer),
                }))
              : [emptyQa()],
        };
      });
      setDrafts(ds);
      setMsg(`已解析出 ${ds.length} 条，请检查 / 补全后一键发布。`);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "解析失败");
    } finally {
      setParsing(false);
    }
  }

  async function generateAnswer(i: number) {
    const token = getAccessToken();
    if (!token) return;
    const d = drafts[i];
    const question = type === "sql" ? d.prompt_md : d.content_md;
    if (!question.trim()) {
      setErr("请先填写题目 / 问题再生成答案");
      return;
    }
    update(i, { completing: true });
    try {
      const { answer } = await completeAnswer(token, {
        target_type: type,
        question,
        context: d.title,
      });
      if (type === "sql") update(i, { answer_md: answer });
      else update(i, { content_md: `${d.content_md}\n\n${answer}`.trim() });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "生成失败");
    } finally {
      update(i, { completing: false });
    }
  }

  function draftToBody(d: AiDraft): Record<string, unknown> {
    const cat = presetCategoryId != null ? { category_id: presetCategoryId } : {};
    if (type === "knowledge") {
      return { title: d.title || "未命名", content_md: d.content_md, status: "published", ...cat };
    }
    if (type === "sql") {
      return {
        title: d.title || "未命名",
        prompt_md: d.prompt_md,
        answer_md: d.answer_md,
        difficulty: d.difficulty,
        status: "published",
        ...cat,
      };
    }
    if (type === "interview") {
      return {
        company_name: d.company_name || "未知企业",
        interview_type: d.interview_type,
        qa_items: d.qa_items.filter((q) => q.question.trim() || q.answer.trim()),
        status: "published",
      };
    }
    return {
      title: d.title || "未命名",
      description_md: d.description_md,
      implementation_md: d.implementation_md,
      level: "basic",
      access_type: "free",
      status: "published",
    };
  }

  async function uploadAll() {
    const token = getAccessToken();
    if (!token || drafts.length === 0) return;
    setUploading(true);
    setErr(null);
    setMsg(null);
    let ok = 0;
    let fail = 0;
    for (const d of drafts) {
      try {
        await adminCreateContent(token, type, draftToBody(d));
        ok += 1;
      } catch {
        fail += 1;
      }
    }
    setUploading(false);
    setDrafts([]);
    setText("");
    setMsg(`发布完成：成功 ${ok} 条${fail ? `，失败 ${fail} 条` : ""}。`);
    onDone();
  }

  return (
    <div className="mb-6 rounded-xl border border-brand-200 bg-brand-50/40 p-4">
      <p className="text-sm font-semibold text-slate-800">AI 解析一键上传（直接发布）</p>
      <p className="mt-1 text-xs text-slate-500">
        上传 Word / PDF / 文本或粘贴内容，自动拆分为多条
        {TABS.find((t) => t.value === type)?.label}
        草稿，检查后可一键发布（无需再走投稿审核）。
      </p>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="可直接粘贴原始文本（如整篇八股 / 多道题 / 一份面经）…"
        rows={3}
        className={`${inputCls} mt-3`}
      />
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <label className="cursor-pointer rounded-lg bg-white px-3 py-1.5 text-sm text-brand-600 ring-1 ring-slate-300 hover:bg-brand-50">
          选择文件解析
          <input
            type="file"
            accept=".txt,.md,.csv,.json,.doc,.docx,.pdf"
            className="hidden"
            disabled={parsing}
            onChange={(e) => {
              const f = e.target.files?.[0] ?? null;
              e.target.value = "";
              handleParse(f);
            }}
          />
        </label>
        <button
          type="button"
          onClick={() => handleParse(null)}
          disabled={parsing}
          className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {parsing ? "解析中…" : "解析文本"}
        </button>
        {drafts.length > 0 && (
          <button
            type="button"
            onClick={uploadAll}
            disabled={uploading}
            className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            {uploading ? "发布中…" : `一键发布 ${drafts.length} 条`}
          </button>
        )}
      </div>
      {msg && <p className="mt-2 text-xs text-green-600">{msg}</p>}
      {err && <p className="mt-2 text-xs text-red-600">{err}</p>}

      {drafts.length > 0 && (
        <div className="mt-3 space-y-3">
          {drafts.map((d, i) => (
            <div key={i} className="space-y-2 rounded-md bg-white p-3 ring-1 ring-slate-200">
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400">#{i + 1}</span>
                <button
                  type="button"
                  onClick={() => setDrafts((prev) => prev.filter((_, idx) => idx !== i))}
                  className="ml-auto text-xs text-red-500 hover:underline"
                >
                  删除
                </button>
              </div>
              {type === "interview" ? (
                <>
                  <input
                    value={d.company_name}
                    onChange={(e) => update(i, { company_name: e.target.value })}
                    placeholder="企业名称"
                    className={inputCls}
                  />
                  <select
                    value={d.interview_type}
                    onChange={(e) => update(i, { interview_type: e.target.value })}
                    className={inputCls}
                  >
                    <option value="campus">校招</option>
                    <option value="social">社招</option>
                    <option value="daily">日常实习</option>
                    <option value="summer">暑期实习</option>
                  </select>
                  <InterviewQaEditor
                    items={d.qa_items}
                    onChange={(next) => update(i, { qa_items: next })}
                  />
                </>
              ) : (
                <>
                  <input
                    value={d.title}
                    onChange={(e) => update(i, { title: e.target.value })}
                    placeholder="标题"
                    className={inputCls}
                  />
                  {type === "knowledge" && (
                    <MarkdownTextarea
                      value={d.content_md}
                      onChange={(v) => update(i, { content_md: v })}
                      placeholder="正文（Markdown）"
                      rows={4}
                      className={inputCls}
                      hint={false}
                    />
                  )}
                  {type === "sql" && (
                    <>
                      <textarea
                        value={d.prompt_md}
                        onChange={(e) => update(i, { prompt_md: e.target.value })}
                        placeholder="题干"
                        rows={2}
                        className={inputCls}
                      />
                      <div className="flex items-start gap-2">
                        <textarea
                          value={d.answer_md}
                          onChange={(e) => update(i, { answer_md: e.target.value })}
                          placeholder="参考答案（可点右侧 AI 生成）"
                          rows={2}
                          className={`${inputCls} flex-1`}
                        />
                        <button
                          type="button"
                          onClick={() => generateAnswer(i)}
                          disabled={d.completing}
                          className="shrink-0 rounded-lg border border-brand-500 px-2 py-1.5 text-xs text-brand-600 hover:bg-brand-50 disabled:opacity-50"
                        >
                          {d.completing ? "生成中…" : "AI 生成答案"}
                        </button>
                      </div>
                      <select
                        value={d.difficulty}
                        onChange={(e) => update(i, { difficulty: e.target.value })}
                        className="rounded border border-slate-300 px-2 py-1 text-xs"
                      >
                        <option value="easy">easy</option>
                        <option value="medium">medium</option>
                        <option value="hard">hard</option>
                      </select>
                    </>
                  )}
                  {type === "project" && (
                    <>
                      <MarkdownTextarea
                        value={d.description_md}
                        onChange={(v) => update(i, { description_md: v })}
                        placeholder="项目描述（Markdown）"
                        rows={3}
                        className={inputCls}
                        hint={false}
                      />
                      <MarkdownTextarea
                        value={d.implementation_md}
                        onChange={(v) => update(i, { implementation_md: v })}
                        placeholder="实现说明（可选）"
                        rows={2}
                        className={inputCls}
                        hint={false}
                      />
                    </>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// 单条内容的新建 / 编辑表单，供目录管理的弹窗复用。
export function ContentForm({
  type,
  editingId,
  presetCategoryId,
  onSaved,
  onCancel,
}: {
  type: ContentType;
  editingId: number | null;
  presetCategoryId?: number | null;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const [values, setValues] = useState<FormValues>(emptyValues(type));
  const [qaItems, setQaItems] = useState<InterviewQAInput[]>([emptyQa()]);
  const [status, setStatus] = useState("published");
  const [cats, setCats] = useState<CategoryFlat[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(editingId != null);

  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      adminListCategories(token, type)
        .then(setCats)
        .catch(() => setCats([]));
    }
  }, [type]);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    if (editingId == null) {
      const v = emptyValues(type);
      if (presetCategoryId != null && (type === "knowledge" || type === "sql")) {
        v.category_id = String(presetCategoryId);
      }
      setValues(v);
      setQaItems([emptyQa()]);
      setStatus("published");
      setLoading(false);
      return;
    }
    setLoading(true);
    adminGetContentDetail(token, type, editingId)
      .then((detail) => {
        const v = emptyValues(type);
        for (const f of FIELDS[type]) {
          const raw = detail[f.name];
          if (raw == null) continue;
          v[f.name] = f.type === "checkbox" ? Boolean(raw) : String(raw);
        }
        setValues(v);
        if (type === "interview") {
          const qa = Array.isArray(detail.qa_items)
            ? (detail.qa_items as Record<string, unknown>[])
            : [];
          setQaItems(
            qa.length > 0
              ? qa.map((q) => ({
                  section: (["round1", "round2", "round3", "hr"].includes(str(q.section))
                    ? str(q.section)
                    : "round1") as InterviewQAInput["section"],
                  question: str(q.question),
                  answer: str(q.answer),
                }))
              : [emptyQa()],
          );
        }
        setStatus(String(detail.status ?? "published"));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, [type, editingId, presetCategoryId]);

  function buildBody(): Record<string, unknown> {
    const body: Record<string, unknown> = { status };
    for (const f of FIELDS[type]) {
      const val = values[f.name];
      if (f.type === "checkbox") {
        body[f.name] = Boolean(val);
      } else if (f.type === "number" || f.type === "category") {
        body[f.name] = val === "" ? null : Number(val);
      } else if (f.nullable) {
        body[f.name] = val === "" ? null : val;
      } else {
        body[f.name] = val;
      }
    }
    if (type === "interview") {
      body.qa_items = qaItems.filter((q) => q.question.trim() || q.answer.trim());
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
      if (editingId == null) {
        await adminCreateContent(token, type, body);
      } else {
        await adminUpdateContent(token, type, editingId, body);
      }
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <p className="text-sm text-slate-400">加载中…</p>;

  return (
    <form onSubmit={submit} className="space-y-3">
      {FIELDS[type].map((f) => (
        <label key={f.name} className="block">
          <span className="mb-1 block text-xs font-medium text-slate-600">{f.label}</span>
          {f.type === "textarea" ? (
            <MarkdownTextarea
              value={values[f.name] as string}
              onChange={(v) => setValues((s) => ({ ...s, [f.name]: v }))}
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
          ) : f.type === "category" ? (
            <select
              value={values[f.name] as string}
              onChange={(e) => setValues((s) => ({ ...s, [f.name]: e.target.value }))}
              className={inputCls}
            >
              <option value="">（不分类）</option>
              {cats.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.parent_id ? "　└ " : ""}
                  {c.name}
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
      {type === "interview" && <InterviewQaEditor items={qaItems} onChange={setQaItems} />}
      <label className="block">
        <span className="mb-1 block text-xs font-medium text-slate-600">状态</span>
        <select value={status} onChange={(e) => setStatus(e.target.value)} className={inputCls}>
          <option value="published">已发布（上架）</option>
          <option value="draft">草稿（下架）</option>
        </select>
      </label>
      {error && <p className="text-sm text-red-600">{error}</p>}
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
          onClick={onCancel}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm text-slate-600 hover:bg-slate-100"
        >
          取消
        </button>
      </div>
    </form>
  );
}
