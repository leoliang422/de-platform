"use client";

import { useCallback, useEffect, useState, type ChangeEvent, type FormEvent } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import { MarkdownTextarea } from "@/components/markdown-textarea";
import { useAuth } from "@/lib/auth";
import {
  ApiError,
  completeAnswer,
  createSubmission,
  deleteSubmission,
  extractFile,
  getAccessToken,
  getCategories,
  getCompanies,
  getMySubmissions,
  parseSubmission,
  retrySubmission,
  type CategoryNode,
  type InterviewQAInput,
  type Submission,
  type SubmissionCreateInput,
  type TargetType,
} from "@/lib/api";

interface FolderOption {
  id: number;
  depth: number;
  name: string;
  path: string;
}

function flattenCategories(
  nodes: CategoryNode[],
  depth = 0,
  parentPath = "",
): FolderOption[] {
  const out: FolderOption[] = [];
  for (const n of nodes) {
    const path = parentPath ? `${parentPath} / ${n.name}` : n.name;
    out.push({ id: n.id, depth, name: n.name, path });
    out.push(...flattenCategories(n.children, depth + 1, path));
  }
  return out;
}

// 批量解析后的可编辑草稿（字段按模块使用其中一部分）
interface Draft {
  title: string;
  content_md: string;
  prompt_md: string;
  answer_md: string;
  difficulty: string;
  description_md: string;
  implementation_md: string;
  completing: boolean;
}

function emptyDraft(): Draft {
  return {
    title: "",
    content_md: "",
    prompt_md: "",
    answer_md: "",
    difficulty: "medium",
    description_md: "",
    implementation_md: "",
    completing: false,
  };
}

function str(v: unknown): string {
  return typeof v === "string" ? v : v == null ? "" : String(v);
}

type RoundSection = InterviewQAInput["section"];

// 面经问答按轮次分组：一个轮次选一次，下面挂多条问答。
interface QaGroup {
  section: RoundSection;
  items: { question: string; answer: string; completing?: boolean }[];
}

const ROUND_OPTIONS: { value: RoundSection; label: string }[] = [
  { value: "round1", label: "一面" },
  { value: "round2", label: "二面" },
  { value: "round3", label: "三面" },
  { value: "hr", label: "HR面" },
];

const ROUND_LABEL: Record<string, string> = Object.fromEntries(
  ROUND_OPTIONS.map((r) => [r.value, r.label]),
);

function defaultQaGroups(): QaGroup[] {
  return [{ section: "round1", items: [{ question: "", answer: "" }] }];
}

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

// 本地文件导入：Word/PDF/图片/文本 → 大模型解析（占位）→ 插入正文
function FileImportField({ onInsert }: { onInsert: (text: string) => void }) {
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // 允许重复选择同一文件
    if (!file) return;
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    setErr(null);
    setNote(null);
    try {
      const r = await extractFile(token, file);
      onInsert(r.text);
      setNote(
        r.kind === "image"
          ? `已插入图片：${r.filename}`
          : r.placeholder
            ? `已上传「${r.filename}」，文档解析 / 大模型识别尚未接入（占位）——已插入下载链接与提示，请手动补充正文。`
            : `已从「${r.filename}」导入内容。`,
      );
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : "解析失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mb-2 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-3">
      <div className="flex flex-wrap items-center gap-3">
        <label className="cursor-pointer rounded-lg bg-white px-3 py-1.5 text-sm text-brand-600 ring-1 ring-slate-300 hover:bg-brand-50">
          {busy ? "解析中…" : "从文件导入"}
          <input
            type="file"
            accept=".txt,.md,.csv,.json,.doc,.docx,.pdf,image/*"
            onChange={onChange}
            disabled={busy}
            className="hidden"
          />
        </label>
        <span className="text-xs text-slate-500">
          支持 Word / PDF / 图片 / 文本；内容将插入下方正文（扫描件/旧版 .doc 无法抽取文字）
        </span>
      </div>
      {note && <p className="mt-2 text-xs text-green-600">{note}</p>}
      {err && <p className="mt-2 text-xs text-red-600">{err}</p>}
    </div>
  );
}

function SubmitInner() {
  const { refreshUser } = useAuth();
  const [targetType, setTargetType] = useState<TargetType>("knowledge");
  const [title, setTitle] = useState("");
  const [raw, setRaw] = useState("");
  const [completingMain, setCompletingMain] = useState(false);
  const [difficulty, setDifficulty] = useState("medium");
  const [tags, setTags] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [position, setPosition] = useState("");
  const [interviewType, setInterviewType] = useState<
    "social" | "campus" | "daily" | "summer"
  >("campus");
  const [qaGroups, setQaGroups] = useState<QaGroup[]>(defaultQaGroups());
  const [level, setLevel] = useState("basic");
  const [categoryId, setCategoryId] = useState("");
  const [folders, setFolders] = useState<FolderOption[]>([]);
  const [companyNames, setCompanyNames] = useState<string[]>([]);
  const [accessType, setAccessType] = useState<"free" | "paid">("free");
  const [implementation, setImplementation] = useState("");
  const [pricePoints, setPricePoints] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [mine, setMine] = useState<Submission[]>([]);

  const [retryingId, setRetryingId] = useState<number | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);

  // 批量解析
  const [parseText, setParseText] = useState("");
  const [parsing, setParsing] = useState(false);
  const [parseMsg, setParseMsg] = useState<string | null>(null);
  const [parseErr, setParseErr] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [batchSubmitting, setBatchSubmitting] = useState(false);

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

  useEffect(() => {
    getCategories("knowledge")
      .then((tree) => setFolders(flattenCategories(tree)))
      .catch(() => setFolders([]));
    getCompanies()
      .then((cs) => setCompanyNames(cs.map((c) => c.name)))
      .catch(() => setCompanyNames([]));
  }, []);

  // 支持从「投递记录」等入口带参预填：?type=interview&company=字节跳动
  useEffect(() => {
    if (typeof window === "undefined") return;
    const sp = new URLSearchParams(window.location.search);
    const t = sp.get("type");
    if (t && ["knowledge", "sql", "interview", "project"].includes(t)) {
      setTargetType(t as TargetType);
    }
    const company = sp.get("company");
    if (company) setCompanyName(company);
  }, []);

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

  async function handleDelete(id: number) {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("确定删除这条投稿记录吗？该操作仅清理列表，不影响已发布内容。")) return;
    setDeletingId(id);
    // 乐观更新：先从列表移除，失败再回滚。
    setMine((prev) => prev.filter((s) => s.id !== id));
    try {
      await deleteSubmission(token, id);
    } catch {
      loadMine();
    } finally {
      setDeletingId(null);
    }
  }

  function setGroupSection(gi: number, section: RoundSection) {
    setQaGroups((prev) => prev.map((g, i) => (i === gi ? { ...g, section } : g)));
  }

  function updateItem(gi: number, ii: number, patch: Partial<QaGroup["items"][number]>) {
    setQaGroups((prev) =>
      prev.map((g, i) =>
        i === gi
          ? { ...g, items: g.items.map((it, j) => (j === ii ? { ...it, ...patch } : it)) }
          : g,
      ),
    );
  }

  function addItem(gi: number) {
    setQaGroups((prev) =>
      prev.map((g, i) =>
        i === gi ? { ...g, items: [...g.items, { question: "", answer: "" }] } : g,
      ),
    );
  }

  function removeItem(gi: number, ii: number) {
    setQaGroups((prev) =>
      prev.map((g, i) => (i === gi ? { ...g, items: g.items.filter((_, j) => j !== ii) } : g)),
    );
  }

  function addRound() {
    setQaGroups((prev) => {
      const used = new Set(prev.map((g) => g.section));
      const next = ROUND_OPTIONS.find((r) => !used.has(r.value))?.value ?? "hr";
      return [...prev, { section: next, items: [{ question: "", answer: "" }] }];
    });
  }

  function removeRound(gi: number) {
    setQaGroups((prev) => prev.filter((_, i) => i !== gi));
  }

  async function handleParse(file: File | null) {
    const token = getAccessToken();
    if (!token) return;
    if (!file && !parseText.trim()) {
      setParseErr("请上传文件或粘贴文本");
      return;
    }
    setParsing(true);
    setParseErr(null);
    setParseMsg(null);
    try {
      const res = await parseSubmission(token, {
        targetType,
        text: parseText.trim() || undefined,
        file,
      });
      const items = res.items ?? [];
      if (targetType === "interview") {
        // 面经：一场面试，填入现有表单
        const post = items[0] ?? {};
        if (str(post.company_name)) setCompanyName(str(post.company_name));
        if (str(post.position)) setPosition(str(post.position));
        const t = str(post.interview_type);
        if (["social", "campus", "daily", "summer"].includes(t)) {
          setInterviewType(t as typeof interviewType);
        }
        const qa = Array.isArray(post.qa_items) ? (post.qa_items as Record<string, unknown>[]) : [];
        if (qa.length > 0) {
          // 按轮次分组（轮次只出现一次），保持一/二/三/HR 顺序。
          const grouped = new Map<RoundSection, QaGroup["items"]>();
          for (const q of qa) {
            const section = (["round1", "round2", "round3", "hr"].includes(str(q.section))
              ? str(q.section)
              : "round1") as RoundSection;
            if (!grouped.has(section)) grouped.set(section, []);
            grouped.get(section)!.push({ question: str(q.question), answer: str(q.answer) });
          }
          setQaGroups(
            ROUND_OPTIONS.filter((r) => grouped.has(r.value)).map((r) => ({
              section: r.value,
              items: grouped.get(r.value)!,
            })),
          );
        }
        setParseMsg(`已解析出 ${qa.length} 条问答并填入下方表单，请检查后提交。`);
      } else {
        const ds: Draft[] = items.map((it) => ({
          ...emptyDraft(),
          title: str(it.title),
          content_md: str(it.content_md),
          prompt_md: str(it.prompt_md),
          answer_md: str(it.answer_md),
          difficulty: str(it.difficulty) || "medium",
          description_md: str(it.description_md),
          implementation_md: str(it.implementation_md),
        }));
        setDrafts(ds);
        setParseMsg(`已解析出 ${ds.length} 条，请在下方检查/补全后批量提交。`);
      }
    } catch (e) {
      setParseErr(e instanceof ApiError ? e.message : "解析失败");
    } finally {
      setParsing(false);
    }
  }

  function updateDraft(i: number, patch: Partial<Draft>) {
    setDrafts((prev) => prev.map((d, idx) => (idx === i ? { ...d, ...patch } : d)));
  }

  function removeDraft(i: number) {
    setDrafts((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function completeDraftAnswer(i: number) {
    const token = getAccessToken();
    if (!token) return;
    const d = drafts[i];
    const question = targetType === "sql" ? d.prompt_md : d.content_md;
    if (!question.trim()) {
      setParseErr("请先填写题目/问题再生成答案");
      return;
    }
    updateDraft(i, { completing: true });
    try {
      const { answer } = await completeAnswer(token, {
        target_type: targetType,
        question,
        context: d.title,
      });
      if (targetType === "sql") updateDraft(i, { answer_md: answer });
      else updateDraft(i, { content_md: `${d.content_md}\n\n${answer}`.trim() });
    } catch (e) {
      setParseErr(e instanceof ApiError ? e.message : "生成失败");
    } finally {
      updateDraft(i, { completing: false });
    }
  }

  async function completeQaAnswer(gi: number, ii: number) {
    const token = getAccessToken();
    if (!token) return;
    const qa = qaGroups[gi]?.items[ii];
    if (!qa || !qa.question.trim()) {
      setError("请先填写问题再生成答案");
      return;
    }
    updateItem(gi, ii, { completing: true });
    try {
      const { answer } = await completeAnswer(token, {
        target_type: "interview",
        question: qa.question,
      });
      updateItem(gi, ii, { answer, completing: false });
    } catch (e) {
      updateItem(gi, ii, { completing: false });
      setError(e instanceof ApiError ? e.message : "生成失败");
    }
  }

  // 八股 / SQL 人工单独上传：用标题作为问题，让大模型生成正文/解答。
  async function completeMainAnswer() {
    const token = getAccessToken();
    if (!token) return;
    const question = title.trim();
    if (!question) {
      setError("请先填写标题，再用它作为问题生成答案");
      return;
    }
    setCompletingMain(true);
    setError(null);
    try {
      const { answer } = await completeAnswer(token, { target_type: targetType, question });
      setRaw((p) => (p.trim() ? `${p}\n\n${answer}` : answer));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "生成失败");
    } finally {
      setCompletingMain(false);
    }
  }

  async function handleBatchSubmit() {
    const token = getAccessToken();
    if (!token || drafts.length === 0) return;
    if (targetType === "knowledge" && !categoryId) {
      setParseErr("请先在上方选择「所属文件夹」再批量提交。");
      return;
    }
    setBatchSubmitting(true);
    setParseErr(null);
    setParseMsg(null);
    let ok = 0;
    let fail = 0;
    for (const d of drafts) {
      const payload: SubmissionCreateInput = {
        target_type: targetType,
        title: d.title || "未命名",
        raw_content:
          targetType === "sql"
            ? d.answer_md.trim() || "（待补充）"
            : targetType === "project"
              ? d.description_md
              : d.content_md,
        prompt_md: targetType === "sql" ? d.prompt_md : undefined,
        difficulty: targetType === "sql" ? d.difficulty : undefined,
        implementation_md: targetType === "project" ? d.implementation_md : undefined,
        category_id: targetType === "knowledge" && categoryId ? Number(categoryId) : undefined,
      };
      try {
        await createSubmission(token, payload);
        ok += 1;
      } catch {
        fail += 1;
      }
    }
    setBatchSubmitting(false);
    setDrafts([]);
    setParseMsg(`批量提交完成：成功 ${ok} 条${fail ? `，失败 ${fail} 条` : ""}。`);
    loadMine();
    await refreshUser();
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
      // 面经无标题/无整体感受：标题回落为企业名，正文置空
      title: targetType === "interview" ? companyName : title,
      raw_content: targetType === "interview" ? "" : raw,
      // SQL 已合并「题目」到「标题」：标题即题干。
      prompt_md: targetType === "sql" ? title : undefined,
      difficulty: targetType === "sql" ? difficulty : undefined,
      tags: targetType === "sql" ? tags : undefined,
      company_name: targetType === "interview" ? companyName : undefined,
      position: targetType === "interview" ? position || undefined : undefined,
      interview_type: targetType === "interview" ? interviewType : undefined,
      qa_items:
        targetType === "interview"
          ? qaGroups.flatMap((g) =>
              g.items
                .filter((it) => it.question.trim() || it.answer.trim())
                .map((it) => ({
                  section: g.section,
                  question: it.question,
                  answer: it.answer,
                })),
            )
          : undefined,
      level: targetType === "project" ? level : undefined,
      access_type: targetType === "project" ? accessType : undefined,
      implementation_md: targetType === "project" ? implementation : undefined,
      is_paid: targetType === "project" ? paid : undefined,
      price_points:
        targetType === "project" && paid && pricePoints ? Number(pricePoints) : undefined,
      category_id: targetType === "knowledge" && categoryId ? Number(categoryId) : undefined,
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
      setImplementation("");
      setPosition("");
      setQaGroups(defaultQaGroups());
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

        {targetType === "knowledge" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              所属文件夹 <span className="text-red-500">*</span>
            </label>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              required
              className={inputCls}
            >
              <option value="">— 请选择投稿到哪个文件夹 —</option>
              {folders.map((f) => (
                <option key={f.id} value={f.id}>
                  {"\u3000".repeat(f.depth)}
                  {f.depth > 0 ? "└ " : ""}
                  {f.name}
                </option>
              ))}
            </select>
            {categoryId && (
              <p className="mt-1 text-xs text-slate-500">
                投稿位置：{folders.find((f) => String(f.id) === categoryId)?.path}
              </p>
            )}
            {folders.length === 0 && (
              <p className="mt-1 text-xs text-amber-600">
                暂无文件夹，请联系管理员在后台「目录管理」中创建。
              </p>
            )}
          </div>
        )}

        <div className="rounded-lg border border-brand-200 bg-brand-50/40 p-4">
          <p className="text-sm font-semibold text-slate-800">
            AI 批量解析（上传文件 / 粘贴文本，自动拆分为多条）
          </p>
          <p className="mt-1 text-xs text-slate-500">
            支持 图片 / Word / PDF / 文本（图片会自动识别文字）。
            {targetType === "interview"
              ? "面经将解析为一场面试的多条问答，填入下方表单。"
              : "解析为多条草稿，可逐条检查 / 补全后一次性提交。"}
          </p>
          <textarea
            value={parseText}
            onChange={(e) => setParseText(e.target.value)}
            placeholder="可直接粘贴原始文本（如整篇八股/多道题/一份面经）…"
            rows={3}
            className={`${inputCls} mt-3`}
          />
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <label className="cursor-pointer rounded-lg bg-white px-3 py-1.5 text-sm text-brand-600 ring-1 ring-slate-300 hover:bg-brand-50">
              选择文件解析
              <input
                type="file"
                accept=".txt,.md,.csv,.json,.doc,.docx,.pdf,image/*"
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
          </div>
          {parseMsg && <p className="mt-2 text-xs text-green-600">{parseMsg}</p>}
          {parseErr && <p className="mt-2 text-xs text-red-600">{parseErr}</p>}
        </div>

        {targetType !== "interview" && drafts.length > 0 && (
          <div className="space-y-3 rounded-lg border border-slate-300 p-4">
            <div className="flex items-center justify-between">
              <p className="text-sm font-semibold text-slate-800">解析结果（{drafts.length} 条）</p>
              <button
                type="button"
                onClick={handleBatchSubmit}
                disabled={batchSubmitting}
                className="rounded-lg bg-green-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {batchSubmitting ? "提交中…" : `批量提交 ${drafts.length} 条`}
              </button>
            </div>
            {drafts.map((d, i) => (
              <div key={i} className="space-y-2 rounded-md bg-slate-50 p-3">
                <div className="flex items-center gap-2">
                  <input
                    value={d.title}
                    onChange={(e) => updateDraft(i, { title: e.target.value })}
                    placeholder="标题"
                    className={`${inputCls} flex-1`}
                  />
                  <button
                    type="button"
                    onClick={() => removeDraft(i)}
                    className="shrink-0 text-xs text-red-500 hover:underline"
                  >
                    删除
                  </button>
                </div>
                {targetType === "knowledge" && (
                  <MarkdownTextarea
                    value={d.content_md}
                    onChange={(v) => updateDraft(i, { content_md: v })}
                    placeholder="正文（Markdown）"
                    rows={4}
                    className={inputCls}
                    hint={false}
                  />
                )}
                {targetType === "sql" && (
                  <>
                    <textarea
                      value={d.prompt_md}
                      onChange={(e) => updateDraft(i, { prompt_md: e.target.value })}
                      placeholder="题干"
                      rows={2}
                      className={inputCls}
                    />
                    <div className="flex items-start gap-2">
                      <textarea
                        value={d.answer_md}
                        onChange={(e) => updateDraft(i, { answer_md: e.target.value })}
                        placeholder="参考答案（可点右侧 AI 生成，人工确认后提交）"
                        rows={2}
                        className={`${inputCls} flex-1`}
                      />
                      <button
                        type="button"
                        onClick={() => completeDraftAnswer(i)}
                        disabled={d.completing}
                        className="shrink-0 rounded-lg border border-brand-500 px-2 py-1.5 text-xs text-brand-600 hover:bg-brand-50 disabled:opacity-50"
                      >
                        {d.completing ? "生成中…" : "AI 生成答案"}
                      </button>
                    </div>
                    <select
                      value={d.difficulty}
                      onChange={(e) => updateDraft(i, { difficulty: e.target.value })}
                      className="rounded border border-slate-300 px-2 py-1 text-xs"
                    >
                      <option value="easy">easy</option>
                      <option value="medium">medium</option>
                      <option value="hard">hard</option>
                    </select>
                  </>
                )}
                {targetType === "project" && (
                  <>
                    <MarkdownTextarea
                      value={d.description_md}
                      onChange={(v) => updateDraft(i, { description_md: v })}
                      placeholder="项目描述（Markdown）"
                      rows={3}
                      className={inputCls}
                      hint={false}
                    />
                    <MarkdownTextarea
                      value={d.implementation_md}
                      onChange={(v) => updateDraft(i, { implementation_md: v })}
                      placeholder="实现说明（可选）"
                      rows={2}
                      className={inputCls}
                      hint={false}
                    />
                  </>
                )}
              </div>
            ))}
          </div>
        )}

        {targetType !== "interview" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">
              {targetType === "sql" ? "标题 / 题目" : "标题"}
            </label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              placeholder={
                targetType === "sql"
                  ? "简明描述题目，如：连续登录 N 天的用户"
                  : targetType === "knowledge"
                    ? "知识点，如：Hive 内部表与外部表的区别"
                    : undefined
              }
              className={inputCls}
            />
            {targetType === "sql" && (
              <p className="mt-1 text-xs text-slate-400">标题即题目描述，无需再单独填写题干。</p>
            )}
          </div>
        )}

        {targetType === "sql" && (
          <>
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
            <div className="flex flex-wrap gap-3">
              <div className="flex-1 min-w-[160px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">企业名称</label>
                <input
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  required
                  list="company-options"
                  placeholder="从已有公司选择，或直接输入新公司"
                  className={inputCls}
                />
                <datalist id="company-options">
                  {companyNames.map((n) => (
                    <option key={n} value={n} />
                  ))}
                </datalist>
                <p className="mt-1 text-xs text-slate-400">
                  优先从下拉里选择已有公司，避免同一公司出现多个名称。
                </p>
              </div>
              <div className="flex-1 min-w-[160px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">岗位名称</label>
                <input
                  value={position}
                  onChange={(e) => setPosition(e.target.value)}
                  placeholder="如：数据开发工程师（可选）"
                  className={inputCls}
                />
                <p className="mt-1 text-xs text-slate-400">
                  填写本次面试对应的岗位，方便读者判断面经方向。
                </p>
              </div>
              <div className="flex-1 min-w-[160px]">
                <label className="mb-1 block text-sm font-medium text-slate-700">类型</label>
                <select
                  value={interviewType}
                  onChange={(e) => setInterviewType(e.target.value as typeof interviewType)}
                  className={inputCls}
                >
                  <option value="campus">校招</option>
                  <option value="social">社招</option>
                  <option value="daily">日常实习</option>
                  <option value="summer">暑期实习</option>
                </select>
              </div>
            </div>

            <div className="rounded-lg border border-slate-200 p-3">
              <p className="mb-3 text-sm font-medium text-slate-700">
                面试问答（每个轮次只需选择一次，下面依次填写该轮的问题与答案）
              </p>
              <div className="space-y-4">
                {qaGroups.map((g, gi) => (
                  <div key={gi} className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="text-xs text-slate-500">轮次</span>
                      <select
                        value={g.section}
                        onChange={(e) => setGroupSection(gi, e.target.value as RoundSection)}
                        className="rounded border border-slate-300 bg-white px-2 py-1 text-xs font-medium"
                      >
                        {ROUND_OPTIONS.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>
                      {qaGroups.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeRound(gi)}
                          className="ml-auto text-xs text-red-500 hover:underline"
                        >
                          删除该轮次
                        </button>
                      )}
                    </div>
                    <div className="space-y-3">
                      {g.items.map((it, ii) => (
                        <div key={ii} className="rounded-md bg-white p-3 ring-1 ring-slate-200">
                          <div className="mb-2 flex items-center gap-2">
                            <span className="text-xs text-slate-400">
                              {ROUND_LABEL[g.section]} · 第 {ii + 1} 题
                            </span>
                            {g.items.length > 1 && (
                              <button
                                type="button"
                                onClick={() => removeItem(gi, ii)}
                                className="ml-auto text-xs text-red-500 hover:underline"
                              >
                                删除
                              </button>
                            )}
                          </div>
                          <input
                            value={it.question}
                            onChange={(e) => updateItem(gi, ii, { question: e.target.value })}
                            placeholder="问题"
                            className={`${inputCls} mb-2`}
                          />
                          <MarkdownTextarea
                            value={it.answer}
                            onChange={(v) => updateItem(gi, ii, { answer: v })}
                            placeholder="答案 / 参考回答（可选，可点下方 AI 生成后人工确认）"
                            rows={2}
                            className={inputCls}
                            hint={false}
                          />
                          <button
                            type="button"
                            onClick={() => completeQaAnswer(gi, ii)}
                            disabled={it.completing}
                            className="mt-1 text-xs text-brand-600 hover:underline disabled:opacity-50"
                          >
                            {it.completing ? "生成中…" : "AI 生成答案"}
                          </button>
                        </div>
                      ))}
                    </div>
                    <button
                      type="button"
                      onClick={() => addItem(gi)}
                      className="mt-2 text-sm text-brand-600 hover:underline"
                    >
                      + 添加一道问答
                    </button>
                  </div>
                ))}
              </div>
              <div className="mt-3">
                <button
                  type="button"
                  onClick={addRound}
                  className="rounded-lg border border-brand-500 px-3 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50"
                >
                  + 添加一个轮次
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
                  <option value="paid">积分解锁</option>
                </select>
              </div>
            </div>
            {accessType === "paid" && (
              <div className="flex gap-3">
                <div className="flex-1">
                  <label className="mb-1 block text-sm font-medium text-slate-700">解锁所需积分</label>
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
              <MarkdownTextarea
                value={implementation}
                onChange={setImplementation}
                rows={4}
                className={inputCls}
              />
            </div>
          </>
        )}

        {(targetType === "knowledge" || targetType === "sql") && (
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="block text-sm font-medium text-slate-700">
                {targetType === "sql" ? "解答 / 思路" : "正文"}
              </label>
              <button
                type="button"
                onClick={completeMainAnswer}
                disabled={completingMain}
                className="rounded-lg border border-brand-500 px-2 py-1 text-xs text-brand-600 hover:bg-brand-50 disabled:opacity-50"
              >
                {completingMain ? "生成中…" : "AI 生成答案"}
              </button>
            </div>
            <MarkdownTextarea value={raw} onChange={setRaw} rows={6} required className={inputCls} />
            <p className="mt-1 text-xs text-slate-400">
              {targetType === "sql"
                ? "可先填标题，点「AI 生成答案」由大模型生成解题思路与 SQL，再人工确认。"
                : "可先填标题，点「AI 生成答案」由大模型生成讲解，再人工确认。"}
            </p>
          </div>
        )}

        {targetType === "project" && (
          <div>
            <label className="mb-1 block text-sm font-medium text-slate-700">正文（原始内容）</label>
            <FileImportField onInsert={(t) => setRaw((p) => (p ? `${p}\n\n${t}` : t))} />
            <MarkdownTextarea value={raw} onChange={setRaw} rows={6} required className={inputCls} />
          </div>
        )}

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
                  <button
                    type="button"
                    disabled={deletingId === s.id}
                    onClick={() => handleDelete(s.id)}
                    className="rounded border border-slate-300 px-2 py-0.5 text-xs text-slate-500 hover:border-red-400 hover:text-red-600 disabled:opacity-50"
                  >
                    {deletingId === s.id ? "删除中…" : "删除"}
                  </button>
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
