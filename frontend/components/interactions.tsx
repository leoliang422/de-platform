"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import {
  addView,
  createAnnotation,
  createComment,
  deleteAnnotation,
  deleteComment,
  getAnnotations,
  getComments,
  getInteractionStats,
  getAccessToken,
  toggleFavorite,
  toggleLike,
  type AnnotationItem,
  type CommentItem,
  type InteractionContentType,
  type InteractionStats,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function ContentInteractions({
  contentType,
  contentId,
}: {
  contentType: InteractionContentType;
  contentId: number;
}) {
  return (
    <div className="mt-8 border-t border-slate-200 pt-6">
      <InteractionBar contentType={contentType} contentId={contentId} />
      <CommentSection contentType={contentType} contentId={contentId} />
    </div>
  );
}

function InteractionBar({
  contentType,
  contentId,
}: {
  contentType: InteractionContentType;
  contentId: number;
}) {
  const { user } = useAuth();
  const [stats, setStats] = useState<InteractionStats | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getInteractionStats(contentType, contentId, getAccessToken())
      .then(setStats)
      .catch(() => {});
    // 浏览量 +1（每次进入详情计一次）
    addView(contentType, contentId).catch(() => {});
  }, [contentType, contentId]);

  async function act(kind: "like" | "favorite") {
    const token = getAccessToken();
    if (!token) return;
    setBusy(true);
    try {
      const next =
        kind === "like"
          ? await toggleLike(token, contentType, contentId)
          : await toggleFavorite(token, contentType, contentId);
      setStats(next);
    } catch {
      // ignore
    } finally {
      setBusy(false);
    }
  }

  if (!stats) return null;

  return (
    <div className="flex items-center gap-4 text-sm">
      <span className="text-slate-400">👁 {stats.views} 浏览</span>
      {user ? (
        <>
          <button
            onClick={() => act("like")}
            disabled={busy}
            className={`flex items-center gap-1 rounded-full border px-3 py-1 transition ${
              stats.liked
                ? "border-red-300 bg-red-50 text-red-600"
                : "border-slate-300 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {stats.liked ? "❤️" : "🤍"} {stats.likes}
          </button>
          <button
            onClick={() => act("favorite")}
            disabled={busy}
            className={`flex items-center gap-1 rounded-full border px-3 py-1 transition ${
              stats.favorited
                ? "border-amber-300 bg-amber-50 text-amber-600"
                : "border-slate-300 text-slate-600 hover:bg-slate-50"
            }`}
          >
            {stats.favorited ? "⭐" : "☆"} {stats.favorites}
          </button>
        </>
      ) : (
        <span className="text-slate-400">
          🤍 {stats.likes} · ⭐ {stats.favorites} ·{" "}
          <Link href="/login" className="text-brand-600 hover:underline">
            登录后互动
          </Link>
        </span>
      )}
      <span className="text-slate-400">💬 {stats.comments} 评论</span>
    </div>
  );
}

function CommentSection({
  contentType,
  contentId,
}: {
  contentType: InteractionContentType;
  contentId: number;
}) {
  const { user } = useAuth();
  const [comments, setComments] = useState<CommentItem[]>([]);
  const [body, setBody] = useState("");
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    getComments(contentType, contentId)
      .then(setComments)
      .catch(() => setComments([]));
  }, [contentType, contentId]);

  useEffect(() => {
    load();
  }, [load]);

  async function submitTop() {
    const token = getAccessToken();
    if (!token || !body.trim()) return;
    setBusy(true);
    try {
      await createComment(token, contentType, contentId, body.trim());
      setBody("");
      load();
    } finally {
      setBusy(false);
    }
  }

  async function submitReply(parentId: number) {
    const token = getAccessToken();
    if (!token || !replyBody.trim()) return;
    setBusy(true);
    try {
      await createComment(token, contentType, contentId, replyBody.trim(), parentId);
      setReplyBody("");
      setReplyTo(null);
      load();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("确认删除该评论？")) return;
    await deleteComment(token, id);
    load();
  }

  const tops = comments.filter((c) => c.parent_id == null);
  const repliesOf = (id: number) => comments.filter((c) => c.parent_id === id);

  return (
    <div className="mt-6">
      <h3 className="mb-3 text-base font-semibold text-slate-900">评论 ({comments.length})</h3>

      {user ? (
        <div className="mb-5">
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            placeholder="友善发言，理性讨论…"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
          />
          <button
            onClick={submitTop}
            disabled={busy || !body.trim()}
            className="mt-2 rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
          >
            发表评论
          </button>
        </div>
      ) : (
        <p className="mb-5 text-sm text-slate-400">
          <Link href="/login" className="text-brand-600 hover:underline">
            登录
          </Link>
          后参与评论。
        </p>
      )}

      {tops.length === 0 ? (
        <p className="text-sm text-slate-400">还没有评论，来做第一个。</p>
      ) : (
        <div className="space-y-4">
          {tops.map((c) => (
            <div key={c.id} className="rounded-lg border border-slate-200 bg-white p-3">
              <CommentRow comment={c} canDelete={user?.id === c.user_id || user?.role === "admin"} onDelete={remove} />
              {user && (
                <button
                  onClick={() => {
                    setReplyTo(replyTo === c.id ? null : c.id);
                    setReplyBody("");
                  }}
                  className="mt-1 text-xs text-brand-600 hover:underline"
                >
                  {replyTo === c.id ? "取消" : "回复"}
                </button>
              )}

              {replyTo === c.id && (
                <div className="mt-2">
                  <textarea
                    value={replyBody}
                    onChange={(e) => setReplyBody(e.target.value)}
                    rows={2}
                    placeholder={`回复 ${c.author_nickname}…`}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                  />
                  <button
                    onClick={() => submitReply(c.id)}
                    disabled={busy || !replyBody.trim()}
                    className="mt-1 rounded-lg bg-brand-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                  >
                    发送
                  </button>
                </div>
              )}

              {repliesOf(c.id).length > 0 && (
                <div className="mt-3 space-y-2 border-l-2 border-slate-100 pl-3">
                  {repliesOf(c.id).map((r) => (
                    <CommentRow
                      key={r.id}
                      comment={r}
                      canDelete={user?.id === r.user_id || user?.role === "admin"}
                      onDelete={remove}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================ 划词批注 ============================

// CSS Custom Highlight API 类型（TS 标准库尚未内置），做最小声明避免使用 any。
interface HighlightCtor {
  new (...ranges: Range[]): object;
}
interface HighlightRegistry {
  set(name: string, highlight: object): void;
  delete(name: string): void;
}

function highlightRegistry(): HighlightRegistry | null {
  const css = (globalThis as unknown as { CSS?: { highlights?: HighlightRegistry } }).CSS;
  return css?.highlights ?? null;
}
function highlightCtor(): HighlightCtor | null {
  return (globalThis as unknown as { Highlight?: HighlightCtor }).Highlight ?? null;
}

// 在容器内，把 [offset, offset+length) 的纯文本位置映射为一个 DOM Range。
function buildRange(container: HTMLElement, offset: number, length: number): Range | null {
  if (length <= 0) return null;
  const end = offset + length;
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let idx = 0;
  let startNode: Text | null = null;
  let startOff = 0;
  let node = walker.nextNode() as Text | null;
  while (node) {
    const len = node.data.length;
    const nodeStart = idx;
    const nodeEnd = idx + len;
    if (startNode === null && offset < nodeEnd) {
      startNode = node;
      startOff = offset - nodeStart;
    }
    if (end <= nodeEnd) {
      const range = document.createRange();
      if (!startNode) return null;
      range.setStart(startNode, startOff);
      range.setEnd(node, end - nodeStart);
      return range;
    }
    idx = nodeEnd;
    node = walker.nextNode() as Text | null;
  }
  return null;
}

interface PendingSelection {
  quote: string;
  offset: number;
  x: number;
  y: number;
}

// 阅读页两栏容器：左侧正文可划词加注，右侧批注栏（全员可见、免审核、可回复/删除）。
export function AnnotatedReader({
  contentType,
  contentId,
  disabled = false,
  privateNote = false,
  children,
}: {
  contentType: InteractionContentType;
  contentId: number;
  disabled?: boolean;
  /** 私有笔记模式：仅本人可见（后端按登录用户过滤），文案改为「我的笔记」。 */
  privateNote?: boolean;
  children: React.ReactNode;
}) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [notes, setNotes] = useState<AnnotationItem[]>([]);
  const [pending, setPending] = useState<PendingSelection | null>(null);
  const [activeId, setActiveId] = useState<number | null>(null);

  const load = useCallback(() => {
    // 私有笔记需带 token，后端据此只返回本人的笔记。
    getAnnotations(contentType, contentId, getAccessToken())
      .then(setNotes)
      .catch(() => setNotes([]));
  }, [contentType, contentId]);

  useEffect(() => {
    if (!disabled) load();
  }, [load, disabled]);

  // 应用高亮（CSS Highlight API：不改 DOM，避免与 React 冲突）。
  useEffect(() => {
    if (disabled) return;
    const container = contentRef.current;
    const reg = highlightRegistry();
    const HC = highlightCtor();
    if (!container || !reg || !HC) return;

    const raf = requestAnimationFrame(() => {
      const base: Range[] = [];
      const active: Range[] = [];
      for (const a of notes) {
        if (a.parent_id != null || !a.quote) continue;
        const r = buildRange(container, a.anchor_offset, a.quote.length);
        if (!r) continue;
        if (a.id === activeId) active.push(r);
        else base.push(r);
      }
      if (base.length) reg.set("de-annotation", new HC(...base));
      else reg.delete("de-annotation");
      if (active.length) reg.set("de-annotation-active", new HC(...active));
      else reg.delete("de-annotation-active");
    });
    return () => {
      cancelAnimationFrame(raf);
    };
  }, [notes, activeId, disabled]);

  useEffect(() => {
    const reg = highlightRegistry();
    return () => {
      if (reg) {
        reg.delete("de-annotation");
        reg.delete("de-annotation-active");
      }
    };
  }, []);

  // 划词：鼠标松开时若容器内有选区，弹出加注按钮。
  useEffect(() => {
    if (disabled) return;
    function onMouseUp() {
      const container = contentRef.current;
      const sel = window.getSelection();
      if (!container || !sel || sel.isCollapsed || sel.rangeCount === 0) {
        return;
      }
      const range = sel.getRangeAt(0);
      if (!container.contains(range.commonAncestorContainer)) return;
      const quote = sel.toString().trim();
      if (!quote) return;

      const pre = document.createRange();
      pre.selectNodeContents(container);
      try {
        pre.setEnd(range.startContainer, range.startOffset);
      } catch {
        return;
      }
      const offset = pre.toString().length;
      const rect = range.getBoundingClientRect();
      setPending({
        quote: quote.slice(0, 2000),
        offset,
        x: rect.left + rect.width / 2,
        y: rect.top - 8,
      });
    }
    document.addEventListener("mouseup", onMouseUp);
    return () => document.removeEventListener("mouseup", onMouseUp);
  }, [disabled]);

  if (disabled) {
    return <div className="min-w-0">{children}</div>;
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div ref={contentRef} className="min-w-0">
        {children}
      </div>
      <AnnotationSidebar
        contentType={contentType}
        contentId={contentId}
        notes={notes}
        pending={pending}
        onClearPending={() => setPending(null)}
        onChanged={load}
        activeId={activeId}
        onActivate={setActiveId}
        privateNote={privateNote}
      />
      {pending && (
        <button
          type="button"
          onMouseDown={(e) => e.preventDefault()}
          onClick={() => {
            document.getElementById("annotation-composer")?.scrollIntoView({ block: "center" });
            document.getElementById("annotation-body")?.focus();
          }}
          style={{ left: pending.x, top: pending.y }}
          className="fixed z-50 -translate-x-1/2 -translate-y-full rounded-full bg-brand-600 px-3 py-1 text-xs font-medium text-white shadow-lg hover:bg-brand-700"
        >
          ✎ {privateNote ? "记笔记" : "添加批注"}
        </button>
      )}
    </div>
  );
}

function AnnotationSidebar({
  contentType,
  contentId,
  notes,
  pending,
  onClearPending,
  onChanged,
  activeId,
  onActivate,
  privateNote = false,
}: {
  contentType: InteractionContentType;
  contentId: number;
  notes: AnnotationItem[];
  pending: PendingSelection | null;
  onClearPending: () => void;
  onChanged: () => void;
  activeId: number | null;
  onActivate: (id: number | null) => void;
  privateNote?: boolean;
}) {
  const { user } = useAuth();
  const [body, setBody] = useState("");
  const [replyTo, setReplyTo] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitTop() {
    const token = getAccessToken();
    if (!token || !body.trim()) return;
    setBusy(true);
    try {
      await createAnnotation(token, contentType, contentId, body.trim(), {
        quote: pending?.quote ?? "",
        anchorOffset: pending?.offset ?? 0,
      });
      setBody("");
      onClearPending();
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function submitReply(parentId: number) {
    const token = getAccessToken();
    if (!token || !replyBody.trim()) return;
    setBusy(true);
    try {
      await createAnnotation(token, contentType, contentId, replyBody.trim(), {
        parentId,
      });
      setReplyBody("");
      setReplyTo(null);
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("确认删除该批注？")) return;
    await deleteAnnotation(token, id);
    onChanged();
  }

  const tops = notes.filter((n) => n.parent_id == null);
  const repliesOf = (id: number) => notes.filter((n) => n.parent_id === id);

  return (
    <aside className="lg:sticky lg:top-4 lg:h-fit">
      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <h3 className="text-base font-semibold text-slate-900">
          {privateNote ? "我的笔记" : "批注"} ({tops.length})
        </h3>
        <p className="mb-3 mt-0.5 text-xs text-slate-400">
          {privateNote
            ? "选中正文文字即可记笔记，仅自己可见、即时生效。"
            : "选中正文文字即可加注，全员可见、即时生效。"}
        </p>

        {user ? (
          <div id="annotation-composer" className="mb-4">
            {pending?.quote && (
              <div className="mb-2 rounded-md border-l-2 border-brand-300 bg-brand-50 px-2 py-1 text-xs text-slate-600">
                <span className="line-clamp-3">“{pending.quote}”</span>
                <button
                  onClick={onClearPending}
                  className="mt-1 text-[11px] text-slate-400 hover:underline"
                >
                  取消选区
                </button>
              </div>
            )}
            <textarea
              id="annotation-body"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={3}
              placeholder={
                pending?.quote
                  ? "对选中文字的补充说明…"
                  : privateNote
                    ? "写一条笔记（可先在正文中选词）…"
                    : "写一条批注（可先在正文中选词）…"
              }
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
            <button
              onClick={submitTop}
              disabled={busy || !body.trim()}
              className="mt-2 w-full rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
            >
              {privateNote ? "保存笔记" : "提交批注"}
            </button>
          </div>
        ) : (
          <p className="mb-4 text-sm text-slate-400">
            <Link href="/login" className="text-brand-600 hover:underline">
              登录
            </Link>
            后可{privateNote ? "记笔记" : "添加批注"}。
          </p>
        )}

        {tops.length === 0 ? (
          <p className="text-sm text-slate-400">
            还没有{privateNote ? "笔记" : "批注"}。选中正文试试。
          </p>
        ) : (
          <div className="space-y-3">
            {tops.map((n) => (
              <div
                key={n.id}
                onMouseEnter={() => onActivate(n.id)}
                onMouseLeave={() => onActivate(null)}
                className={`rounded-lg border p-3 transition ${
                  activeId === n.id ? "border-brand-300 bg-brand-50/50" : "border-slate-200 bg-white"
                }`}
              >
                {n.quote && (
                  <p className="mb-1 border-l-2 border-amber-300 pl-2 text-xs italic text-slate-500 line-clamp-2">
                    “{n.quote}”
                  </p>
                )}
                <AnnotationRow
                  note={n}
                  canDelete={user?.id === n.user_id || user?.role === "admin"}
                  onDelete={remove}
                />
                {user && (
                  <button
                    onClick={() => {
                      setReplyTo(replyTo === n.id ? null : n.id);
                      setReplyBody("");
                    }}
                    className="mt-1 text-xs text-brand-600 hover:underline"
                  >
                    {replyTo === n.id ? "取消" : "回复"}
                  </button>
                )}
                {replyTo === n.id && (
                  <div className="mt-2">
                    <textarea
                      value={replyBody}
                      onChange={(e) => setReplyBody(e.target.value)}
                      rows={2}
                      placeholder={`回复 ${n.author_nickname}…`}
                      className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                    />
                    <button
                      onClick={() => submitReply(n.id)}
                      disabled={busy || !replyBody.trim()}
                      className="mt-1 rounded-lg bg-brand-600 px-3 py-1 text-xs font-medium text-white hover:bg-brand-700 disabled:opacity-50"
                    >
                      发送
                    </button>
                  </div>
                )}
                {repliesOf(n.id).length > 0 && (
                  <div className="mt-2 space-y-2 border-l-2 border-slate-100 pl-3">
                    {repliesOf(n.id).map((r) => (
                      <AnnotationRow
                        key={r.id}
                        note={r}
                        canDelete={user?.id === r.user_id || user?.role === "admin"}
                        onDelete={remove}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function AnnotationRow({
  note,
  canDelete,
  onDelete,
}: {
  note: AnnotationItem;
  canDelete: boolean;
  onDelete: (id: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-slate-800">{note.author_nickname}</span>
        <span className="text-xs text-slate-400">
          {new Date(note.created_at).toLocaleDateString("zh-CN")}
        </span>
        {canDelete && (
          <button
            onClick={() => onDelete(note.id)}
            className="ml-auto text-xs text-red-400 hover:underline"
          >
            删除
          </button>
        )}
      </div>
      <p className="mt-0.5 whitespace-pre-wrap text-sm text-slate-700">{note.body}</p>
    </div>
  );
}

function CommentRow({
  comment,
  canDelete,
  onDelete,
}: {
  comment: CommentItem;
  canDelete: boolean;
  onDelete: (id: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="text-sm font-medium text-slate-800">{comment.author_nickname}</span>
        <span className="text-xs text-slate-400">
          {new Date(comment.created_at).toLocaleString("zh-CN")}
        </span>
        {canDelete && (
          <button
            onClick={() => onDelete(comment.id)}
            className="ml-auto text-xs text-red-400 hover:underline"
          >
            删除
          </button>
        )}
      </div>
      <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{comment.body}</p>
    </div>
  );
}
