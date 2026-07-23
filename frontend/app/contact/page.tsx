"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ChatComposer, MessageBubbles } from "@/components/chat";
import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  type ContactMessage,
  type SendMessagePayload,
  deleteMyMessage,
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

  async function handleSend(payload: SendMessagePayload) {
    const token = getAccessToken();
    if (!token) return;
    const msg = await sendMessageToAdmin(token, payload);
    setMessages((prev) => [...prev, msg]);
  }

  async function handleDelete(m: ContactMessage) {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("撤回这条消息？")) return;
    setMessages((prev) => prev.filter((x) => x.id !== m.id));
    try {
      await deleteMyMessage(token, m.id);
    } catch {
      load();
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
            <MessageBubbles messages={messages} selfIsAdmin={false} onDelete={handleDelete} />
          )}
          <div ref={bottomRef} />
        </div>

        <ChatComposer onSend={handleSend} />
      </div>
    </div>
  );
}
