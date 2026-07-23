"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  clearNotifications,
  deleteNotification,
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

  async function handleDelete(id: number) {
    const token = getAccessToken();
    if (!token) return;
    setItems((prev) => prev.filter((x) => x.id !== id));
    try {
      await deleteNotification(token, id);
    } catch {
      load();
    }
  }

  async function handleClearAll() {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("确定清空全部通知？此操作不可恢复。")) return;
    setItems([]);
    try {
      await clearNotifications(token);
    } catch {
      load();
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <PageHeader title="通知" desc="审核结果、互动与系统消息" />
        <div className="flex items-center gap-4">
          {items.some((n) => !n.read_at) && (
            <button
              onClick={handleReadAll}
              className="text-sm text-brand-600 hover:underline"
            >
              全部标为已读
            </button>
          )}
          {items.length > 0 && (
            <button
              onClick={handleClearAll}
              className="text-sm text-red-500 hover:underline"
            >
              清空
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-slate-400">加载中…</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-slate-400">暂无通知。</p>
      ) : (
        <div className="space-y-2">
          {items.map((n) => (
            <div
              key={n.id}
              className={`group flex items-start gap-3 rounded-lg border p-3 transition ${
                n.read_at
                  ? "border-slate-200 bg-white"
                  : "border-brand-200 bg-brand-50"
              } hover:border-brand-400`}
            >
              <button
                onClick={() => handleClick(n)}
                className="flex flex-1 items-start gap-3 text-left"
              >
                <span className="text-lg">{TYPE_ICON[n.type] ?? "🔔"}</span>
                <span className="flex-1">
                  <span className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-900">{n.title}</span>
                    {!n.read_at && <span className="h-2 w-2 rounded-full bg-brand-500" />}
                  </span>
                  {n.body && <span className="mt-0.5 block text-sm text-slate-600">{n.body}</span>}
                  <span className="mt-1 block text-xs text-slate-400">
                    {new Date(n.created_at).toLocaleString("zh-CN")}
                  </span>
                </span>
              </button>
              <button
                onClick={() => handleDelete(n.id)}
                title="删除"
                className="shrink-0 rounded px-1.5 text-slate-300 hover:bg-red-50 hover:text-red-500"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
