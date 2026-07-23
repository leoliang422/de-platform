"use client";

import { useCallback, useEffect, useState } from "react";

import { PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  createRechargeOrder,
  getAccessToken,
  getMyRechargeOrders,
  getRechargeConfig,
  type RechargeConfig,
  type RechargeOrder,
} from "@/lib/api";

const STATUS_LABEL: Record<string, { text: string; cls: string }> = {
  pending: { text: "待确认", cls: "bg-amber-100 text-amber-700" },
  paid: { text: "已到账", cls: "bg-green-100 text-green-700" },
  failed: { text: "已驳回", cls: "bg-red-100 text-red-700" },
};

export default function RechargePage() {
  return (
    <RequireAuth>
      <RechargeInner />
    </RequireAuth>
  );
}

function RechargeInner() {
  const [config, setConfig] = useState<RechargeConfig | null>(null);
  const [orders, setOrders] = useState<RechargeOrder[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadOrders = useCallback(() => {
    const token = getAccessToken();
    if (!token) return;
    getMyRechargeOrders(token)
      .then(setOrders)
      .catch(() => setOrders([]));
  }, []);

  useEffect(() => {
    getRechargeConfig()
      .then((c) => {
        setConfig(c);
        if (c.packages.length > 0) setSelected(c.packages[0].id);
      })
      .catch(() => setError("无法加载充值配置"));
    loadOrders();
  }, [loadOrders]);

  const selectedPkg = config?.packages.find((p) => p.id === selected) ?? null;

  async function submit() {
    const token = getAccessToken();
    if (!token || selected === null) return;
    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      await createRechargeOrder(token, selected, note);
      setNotice("已提交充值申请，请扫码支付对应金额；管理员核对到账后积分将自动到账。");
      setNote("");
      loadOrders();
    } catch (e) {
      setError(e instanceof Error ? e.message : "提交失败，请重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <PageHeader title="充值积分" desc="选择套餐 → 扫码支付 → 管理员确认到账后积分自动到账" />

      {error && <p className="mb-4 text-sm text-red-600">{error}</p>}
      {notice && (
        <p className="mb-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          {notice}
        </p>
      )}

      {/* 套餐选择 */}
      <h2 className="mb-3 text-lg font-semibold text-slate-900">选择充值套餐</h2>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(config?.packages ?? []).map((p) => (
          <button
            key={p.id}
            onClick={() => setSelected(p.id)}
            className={`rounded-xl border p-4 text-center transition ${
              selected === p.id
                ? "border-brand-500 bg-brand-50 ring-1 ring-brand-500"
                : "border-slate-200 bg-white hover:border-brand-300"
            }`}
          >
            <div className="text-2xl font-bold text-brand-600">{p.points}</div>
            <div className="text-xs text-slate-400">积分</div>
            <div className="mt-1 text-sm font-medium text-slate-700">¥{p.amount}</div>
          </button>
        ))}
      </div>

      {/* 收款码 + 提交 */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-5">
        {config && !config.qr_url ? (
          <p className="text-sm text-amber-700">
            管理员尚未配置收款码，请稍后再试或联系管理员。
          </p>
        ) : (
          <div className="flex flex-col items-center gap-4 sm:flex-row sm:items-start">
            {config?.qr_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={config.qr_url}
                alt="收款码"
                className="h-52 w-52 rounded-lg border border-slate-200 object-contain"
              />
            )}
            <div className="flex-1 text-sm text-slate-600">
              <p className="font-medium text-slate-900">
                请用微信 / 支付宝扫码，支付
                {selectedPkg ? ` ¥${selectedPkg.amount}（到账 ${selectedPkg.points} 积分）` : "对应金额"}
              </p>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-slate-500">
                <li>选择上方套餐</li>
                <li>扫码支付「对应金额」（金额需与套餐一致，便于核对）</li>
                <li>点击下方「我已支付」提交申请</li>
                <li>管理员核对到账后确认，积分自动到账</li>
              </ol>
              <div className="mt-3">
                <label className="mb-1 block text-xs font-medium text-slate-500">
                  转账备注（选填，方便管理员核对，如付款账号/昵称）
                </label>
                <input
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={255}
                  placeholder="如：微信付款尾号 1234 / 昵称 xxx"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none"
                />
              </div>
              <button
                onClick={submit}
                disabled={submitting || selected === null || !config?.qr_url}
                className="mt-4 rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                {submitting ? "提交中…" : "我已支付，提交确认"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* 我的充值记录 */}
      <h2 className="mb-3 mt-8 text-lg font-semibold text-slate-900">我的充值记录</h2>
      {orders.length === 0 ? (
        <p className="text-sm text-slate-400">暂无充值记录。</p>
      ) : (
        <div className="space-y-2">
          {orders.map((o) => {
            const s = STATUS_LABEL[o.status] ?? { text: o.status, cls: "bg-slate-100 text-slate-600" };
            return (
              <div
                key={o.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <span className="text-slate-700">
                  ¥{o.amount_cash} · {o.points_delta ?? 0} 积分
                  {o.note && <span className="ml-2 text-xs text-slate-400">备注：{o.note}</span>}
                </span>
                <span className={`rounded px-2 py-0.5 text-xs ${s.cls}`}>{s.text}</span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
