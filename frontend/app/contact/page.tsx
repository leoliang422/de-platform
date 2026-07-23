"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  type ContactMessage,
  getAccessToken,
  getMyMessages,
  sendMessageToAdmin,
} from "@/lib/api";

export default function ContactPage() {
  return (
    <RequireAuth>
      <ContactInner />
    </RequireAuth>
  );
}

function ContactInner() {
  const [messages, setMessages] = useState<ContactMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const load = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    getMyMessages(token)
      .then(setMessages)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const body = draft.trim();
    if (!body || sending) return;
    const token = getAccessToken();
    if (!token) return;
    setSending(true);
    setError(null);
    try {
      const msg = await sendMessageToAdmin(token, body);
      setMessages((prev) => [...prev, msg]);
      setDraft("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "发送失败");
    } finally {
      setSending(false);
    }
  }

  return (
    <div>
      <PageHeader title="联系管理员" desc="有任何问题、建议或反馈，都可以在这里私信管理员" />

      <div className="mx-auto flex h-[60vh] max-w-2xl flex-col overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex-1 space-y-3 overflow-y-auto p-4">
          {loading ? (
            <p className="text-center text-sm text-slate-400">加载中…</p>
          ) : messages.length === 0 ? (
            <p className="mt-8 text-center text-sm text-slate-400">
              还没有消息，发一条试试吧～管理员会尽快回复你。
            </p>
          ) : (
            messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${m.from_admin ? "justify-start" : "justify-end"}`}
              >
                <div className="max-w-[75%]">
                  <div
                    className={`whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
                      m.from_admin
                        ? "rounded-tl-sm bg-slate-100 text-slate-800"
                        : "rounded-tr-sm bg-brand-600 text-white"
                    }`}
                  >
                    {m.body}
                  </div>
                  <div
                    className={`mt-1 text-[11px] text-slate-400 ${
                      m.from_admin ? "text-left" : "text-right"
                    }`}
                  >
                    {m.from_admin ? "管理员 · " : ""}
                    {new Date(m.created_at).toLocaleString("zh-CN")}
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-slate-200 p-3">
          {error && <p className="mb-2 text-xs text-red-600">{error}</p>}
          <div className="flex items-end gap-2">
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              rows={2}
              placeholder="输入消息…（⌘/Ctrl + Enter 发送）"
              className="flex-1 resize-none rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
            />
            <button
              onClick={handleSend}
              disabled={sending || !draft.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
