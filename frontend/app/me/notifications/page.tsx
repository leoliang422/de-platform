"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  getAccessToken,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
  type Notification,
} from "@/lib/api";

export default function NotificationsPage() {
  return (
    <RequireAuth>
      <NotificationsInner />
    </RequireAuth>
  );
}

const TYPE_ICON: Record<string, string> = {
  submission_approved: "✅",
  submission_rejected: "❌",
  comment: "💬",
  like: "👍",
  message: "✉️",
  system: "🔔",
};

function NotificationsInner() {
  const router = useRouter();
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    getNotifications(token)
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleClick(n: Notification) {
    const token = getAccessToken();
    if (!token) return;
    if (!n.read_at) {
      try {
        await markNotificationRead(token, n.id);
        setItems((prev) =>
          prev.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)),
        );
      } catch {
        // ignore
      }
    }
    if (n.link) router.push(n.link);
  }

  async function handleReadAll() {
    const token = getAccessToken();
    if (!token) return;
    await markAllNotificationsRead(token);
    setItems((prev) => prev.map((x) => ({ ...x, read_at: x.read_at ?? new Date().toISOString() })));
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <PageHeader title="通知" desc="审核结果、互动与系统消息" />
        {items.some((n) => !n.read_at) && (
          <button
            onClick={handleReadAll}
            className="text-sm text-brand-600 hover:underline"
          >
            全部标为已读
          </button>
        )}
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">加载中…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-400">暂无通知。</p>
      ) : (
        <div className="space-y-2">
          {items.map((n) => (
            <button
              key={n.id}
              onClick={() => handleClick(n)}
              className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition ${
                n.read_at
                  ? "border-slate-200 bg-white"
                  : "border-brand-200 bg-brand-50"
              } hover:border-brand-400`}
            >
              <span className="text-lg">{TYPE_ICON[n.type] ?? "🔔"}</span>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-slate-900">{n.title}</span>
                  {!n.read_at && <span className="h-2 w-2 rounded-full bg-brand-500" />}
                </div>
                {n.body && <p className="mt-0.5 text-sm text-slate-600">{n.body}</p>}
                <p className="mt-1 text-xs text-slate-400">
                  {new Date(n.created_at).toLocaleString("zh-CN")}
                </p>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
