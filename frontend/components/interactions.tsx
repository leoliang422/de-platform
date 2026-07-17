"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  addView,
  createComment,
  deleteComment,
  getComments,
  getInteractionStats,
  getAccessToken,
  toggleFavorite,
  toggleLike,
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
