"use client";

import { useRouter } from "next/navigation";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { ApiError, register as apiRegister, sendEmailCode } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [nickname, setNickname] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 验证码发送状态与倒计时。
  const [sending, setSending] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [codeHint, setCodeHint] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  function startCooldown() {
    setCooldown(60);
    timerRef.current = setInterval(() => {
      setCooldown((c) => {
        if (c <= 1 && timerRef.current) {
          clearInterval(timerRef.current);
          timerRef.current = null;
          return 0;
        }
        return c - 1;
      });
    }, 1000);
  }

  const emailValid = /.+@.+\..+/.test(email);

  async function onSendCode() {
    setError(null);
    setCodeHint(null);
    if (!emailValid) {
      setError("请先填写正确的邮箱");
      return;
    }
    setSending(true);
    try {
      const res = await sendEmailCode(email);
      startCooldown();
      if (res.dev_code) {
        // 未接真实邮件（mock）：直接把验证码填入并提示。
        setCode(res.dev_code);
        setCodeHint(`开发模式（未配置真实邮件）：验证码 ${res.dev_code} 已自动填入`);
      } else {
        setCodeHint("验证码已发送至邮箱，请查收（10 分钟内有效）");
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "验证码发送失败，请重试");
    } finally {
      setSending(false);
    }
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password.length < 6) {
      setError("密码至少 6 位");
      return;
    }
    if (password !== confirm) {
      setError("两次输入的密码不一致");
      return;
    }
    if (!code.trim()) {
      setError("请先获取并填写邮箱验证码");
      return;
    }
    setSubmitting(true);
    try {
      await apiRegister({ email, password, nickname, code: code.trim() });
      await login(email, password);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "注册失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-sm">
      <h1 className="text-2xl font-bold text-slate-900">注册</h1>
      <form onSubmit={onSubmit} className="mt-6 space-y-4">
        <Field
          label="邮箱"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="you@example.com"
        />

        <label className="block">
          <span className="mb-1 block text-sm font-medium text-slate-700">邮箱验证码</span>
          <div className="flex gap-2">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="6 位验证码"
              required
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
            />
            <button
              type="button"
              onClick={onSendCode}
              disabled={sending || cooldown > 0 || !emailValid}
              className="shrink-0 whitespace-nowrap rounded-lg border border-brand-500 px-3 text-sm font-medium text-brand-600 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {sending ? "发送中…" : cooldown > 0 ? `${cooldown}s` : "获取验证码"}
            </button>
          </div>
          {codeHint && (
            <p className="mt-1 rounded-lg bg-amber-50 p-2 text-xs text-amber-700">{codeHint}</p>
          )}
        </label>

        <Field
          label="昵称"
          type="text"
          value={nickname}
          onChange={setNickname}
          placeholder="你的昵称"
        />
        <Field
          label="密码"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="至少 6 位"
        />
        <Field
          label="确认密码"
          type="password"
          value={confirm}
          onChange={setConfirm}
          placeholder="再次输入密码"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-lg bg-brand-600 py-2.5 font-medium text-white hover:bg-brand-700 disabled:opacity-60"
        >
          {submitting ? "注册中…" : "注册"}
        </button>
      </form>
      <p className="mt-4 text-sm text-slate-600">
        已有账号？{" "}
        <Link href="/login" className="font-medium text-brand-600">
          去登录
        </Link>
      </p>
    </div>
  );
}

function Field({
  label,
  type,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-medium text-slate-700">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required
        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
      />
    </label>
  );
}
