"use client";

import { useRef, useState } from "react";

import {
  getAccessToken,
  uploadAttachment,
  type ContactMessage,
  type SendMessagePayload,
} from "@/lib/api";

const EMOJIS = [
  "😀", "😄", "😊", "😉", "😍", "😎", "🤔", "😅", "😂", "🥰",
  "😢", "😭", "😡", "😴", "👍", "👎", "🙏", "👏", "💪", "🤝",
  "🎉", "❤️", "🔥", "✅", "❌", "💯", "🚀", "👀", "💡", "⭐",
];

/** 消息气泡列表。`selfIsAdmin` 决定哪一侧算「我方」（靠右）。 */
export function MessageBubbles({
  messages,
  selfIsAdmin,
}: {
  messages: ContactMessage[];
  selfIsAdmin: boolean;
}) {
  return (
    <>
      {messages.map((m) => {
        const mine = m.from_admin === selfIsAdmin;
        return (
          <div key={m.id} className={`flex ${mine ? "justify-end" : "justify-start"}`}>
            <div className="max-w-[78%]">
              <div
                className={`overflow-hidden rounded-2xl text-sm ${
                  mine
                    ? "rounded-tr-sm bg-brand-600 text-white"
                    : "rounded-tl-sm bg-slate-100 text-slate-800"
                }`}
              >
                {m.attachment_url && m.attachment_kind === "image" ? (
                  <a href={m.attachment_url} target="_blank" rel="noreferrer">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={m.attachment_url}
                      alt={m.attachment_name ?? "图片"}
                      className="max-h-56 w-auto"
                    />
                  </a>
                ) : m.attachment_url ? (
                  <a
                    href={m.attachment_url}
                    target="_blank"
                    rel="noreferrer"
                    className={`flex items-center gap-2 px-3.5 py-2 underline ${
                      mine ? "text-white" : "text-brand-700"
                    }`}
                  >
                    📎 {m.attachment_name ?? "文件"}
                  </a>
                ) : null}
                {m.body && <div className="whitespace-pre-wrap px-3.5 py-2">{m.body}</div>}
              </div>
              <div
                className={`mt-1 text-[11px] text-slate-400 ${mine ? "text-right" : "text-left"}`}
              >
                {!mine && !selfIsAdmin ? "管理员 · " : ""}
                {new Date(m.created_at).toLocaleString("zh-CN")}
              </div>
            </div>
          </div>
        );
      })}
    </>
  );
}

/** 输入区：文字 + 表情 + 图片/文件上传，统一通过 onSend 提交。 */
export function ChatComposer({
  onSend,
  placeholder = "输入消息…（⌘/Ctrl + Enter 发送）",
}: {
  onSend: (payload: SendMessagePayload) => Promise<void>;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showEmoji, setShowEmoji] = useState(false);
  const imgRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);

  async function sendText() {
    const body = draft.trim();
    if (!body || sending) return;
    setSending(true);
    setError(null);
    try {
      await onSend({ body });
      setDraft("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setSending(false);
    }
  }

  async function handleFile(file: File | undefined) {
    if (!file) return;
    const token = getAccessToken();
    if (!token) return;
    setUploading(true);
    setError(null);
    try {
      const up = await uploadAttachment(token, file);
      await onSend({
        attachment_url: up.url,
        attachment_name: up.filename,
        attachment_kind: up.kind,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "上传失败");
    } finally {
      setUploading(false);
      if (imgRef.current) imgRef.current.value = "";
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="border-t border-slate-200 p-3">
      {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
      <div className="relative flex items-end gap-2">
        {/* 表情 */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowEmoji((v) => !v)}
            className="rounded-lg px-2 py-2 text-lg hover:bg-slate-100"
            title="表情"
          >
            😊
          </button>
          {showEmoji && (
            <div className="absolute bottom-11 left-0 z-10 grid w-64 grid-cols-8 gap-1 rounded-lg border border-slate-200 bg-white p-2 shadow-lg">
              {EMOJIS.map((em) => (
                <button
                  key={em}
                  type="button"
                  onClick={() => {
                    setDraft((d) => d + em);
                    setShowEmoji(false);
                    taRef.current?.focus();
                  }}
                  className="rounded p-1 text-lg hover:bg-slate-100"
                >
                  {em}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* 图片 */}
        <button
          type="button"
          onClick={() => imgRef.current?.click()}
          disabled={uploading}
          className="rounded-lg px-2 py-2 text-lg hover:bg-slate-100 disabled:opacity-50"
          title="发送图片"
        >
          🖼
        </button>
        <input
          ref={imgRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        {/* 文件 */}
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="rounded-lg px-2 py-2 text-lg hover:bg-slate-100 disabled:opacity-50"
          title="发送文件"
        >
          📎
        </button>
        <input
          ref={fileRef}
          type="file"
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        <textarea
          ref={taRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              sendText();
            }
          }}
          rows={2}
          placeholder={uploading ? "上传中…" : placeholder}
          className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
        />
        <button
          onClick={sendText}
          disabled={sending || uploading || !draft.trim()}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          发送
        </button>
      </div>
    </div>
  );
}
