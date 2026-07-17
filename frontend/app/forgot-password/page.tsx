"use client";

import Link from "next/link";
import { useState } from "react";

import { ApiError, forgotPassword } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res = await forgotPassword(email);
      setSent(true);
      setDevToken(res.reset_token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "提交失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="text-2xl font-bold text-slate-900">找回密码</h1>
      <p className="mt-2 text-sm text-slate-600">
        输入注册邮箱，我们会发送重置链接（若该邮箱已注册）。
      </p>

      {sent ? (
        <div className="mt-6 space-y-3">
          <p className="rounded-lg bg-green-50 p-3 text-sm text-green-700">
            若邮箱已注册，重置链接已发送，请查收邮件。
          </p>
          {devToken && (
            <p className="rounded-lg bg-amber-50 p-3 text-xs text-amber-700">
              开发模式（未配置真实邮件）：
              <Link
                href={`/reset-password?token=${devToken}`}
                className="ml-1 font-medium text-brand-600 hover:underline"
              >
                点此直接重置
              </Link>
            </p>
          )}
          <Link href="/login" className="inline-block text-sm text-brand-600 hover:underline">
            返回登录
          </Link>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm font-medium text-slate-700">邮箱</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="you@example.com"
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
          </label>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-lg bg-brand-600 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting ? "提交中…" : "发送重置链接"}
          </button>
        </form>
      )}
    </div>
  );
}
