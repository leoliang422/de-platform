"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { BackLink, PageHeader } from "@/components/content";
import { RequireAuth } from "@/components/guard";
import {
  addApplicationRecord,
  APPLICATION_STATUS_LABEL,
  COMPANY_NATURE_LABEL,
  createApplicationList,
  deleteApplicationList,
  deleteApplicationRecord,
  getAccessToken,
  getApplicationLists,
  getInterviewCompanies,
  renameApplicationList,
  updateApplicationRecord,
  type ApplicationList,
  type ApplicationRecord,
  type ApplicationStatus,
  type CompanyNature,
  type InterviewCompany,
} from "@/lib/api";

import { CalendarPanel } from "./calendar";

export default function ApplicationsPage() {
  return (
    <RequireAuth>
      <ApplicationsInner />
    </RequireAuth>
  );
}

// 状态徽标配色：进行中=琥珀，挂/拒=红，Offer=绿，已投递=蓝。
const STATUS_STYLE: Record<string, string> = {
  applied: "bg-sky-100 text-sky-700",
  written: "bg-amber-100 text-amber-800",
  round1: "bg-amber-100 text-amber-800",
  round2: "bg-amber-100 text-amber-800",
  round3: "bg-amber-100 text-amber-800",
  hr: "bg-amber-100 text-amber-800",
  resume_fail: "bg-red-100 text-red-700",
  written_fail: "bg-red-100 text-red-700",
  round1_fail: "bg-red-100 text-red-700",
  round2_fail: "bg-red-100 text-red-700",
  round3_fail: "bg-red-100 text-red-700",
  hr_fail: "bg-red-100 text-red-700",
  rejected: "bg-red-100 text-red-700",
  offer: "bg-green-100 text-green-700",
};

const STATUS_OPTIONS = Object.keys(APPLICATION_STATUS_LABEL) as ApplicationStatus[];
const NATURE_OPTIONS = Object.keys(COMPANY_NATURE_LABEL) as CompanyNature[];

function ApplicationsInner() {
  const [lists, setLists] = useState<ApplicationList[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 有面经的公司（供「选择关联」下拉 + 按公司名自动匹配）。
  const [companies, setCompanies] = useState<InterviewCompany[]>([]);

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;
    try {
      const data = await getApplicationLists(token);
      setLists(data);
      setActiveId((prev) => (prev && data.some((l) => l.id === prev) ? prev : (data[0]?.id ?? null)));
    } catch {
      setError("无法加载投递记录");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const token = getAccessToken();
    if (token) getInterviewCompanies(token).then(setCompanies).catch(() => {});
  }, [load]);

  // 公司名（归一化）→ 公司 id，用于未手动关联时自动匹配面经。
  const nameToId = useMemo(() => {
    const m = new Map<string, number>();
    for (const c of companies) m.set(c.name.trim().toLowerCase(), c.id);
    return m;
  }, [companies]);

  const active = lists.find((l) => l.id === activeId) ?? null;

  async function handleCreateList() {
    const token = getAccessToken();
    if (!token) return;
    const name = window.prompt("新建投递列表，请输入名称（如：2026 秋招）");
    if (!name || !name.trim()) return;
    const created = await createApplicationList(token, name.trim());
    setLists((prev) => [...prev, created]);
    setActiveId(created.id);
  }

  async function handleRenameList() {
    const token = getAccessToken();
    if (!token || !active) return;
    const name = window.prompt("重命名列表", active.name);
    if (!name || !name.trim()) return;
    const updated = await renameApplicationList(token, active.id, name.trim());
    setLists((prev) => prev.map((l) => (l.id === updated.id ? { ...l, name: updated.name } : l)));
  }

  async function handleDeleteList() {
    const token = getAccessToken();
    if (!token || !active) return;
    if (!window.confirm(`确定删除列表「${active.name}」及其中所有记录吗？`)) return;
    await deleteApplicationList(token, active.id);
    setLists((prev) => prev.filter((l) => l.id !== active.id));
    setActiveId((prev) => {
      const rest = lists.filter((l) => l.id !== prev);
      return rest[0]?.id ?? null;
    });
  }

  // 记录增删改：均在本地乐观更新对应列表的 records。
  function patchLocal(listId: number, fn: (recs: ApplicationRecord[]) => ApplicationRecord[]) {
    setLists((prev) => prev.map((l) => (l.id === listId ? { ...l, records: fn(l.records) } : l)));
  }

  async function handleAddRecord() {
    const token = getAccessToken();
    if (!token || !active) return;
    const created = await addApplicationRecord(token, active.id, { status: "applied" });
    patchLocal(active.id, (recs) => [...recs, created]);
  }

  async function handleUpdateRecord(
    rec: ApplicationRecord,
    patch: Partial<ApplicationRecord>,
  ) {
    const token = getAccessToken();
    if (!token) return;
    // 先本地更新，避免输入抖动。
    patchLocal(rec.list_id, (recs) => recs.map((r) => (r.id === rec.id ? { ...r, ...patch } : r)));
    try {
      await updateApplicationRecord(token, rec.id, patch);
    } catch {
      load();
    }
  }

  async function handleDeleteRecord(rec: ApplicationRecord) {
    const token = getAccessToken();
    if (!token) return;
    patchLocal(rec.list_id, (recs) => recs.filter((r) => r.id !== rec.id));
    try {
      await deleteApplicationRecord(token, rec.id);
    } catch {
      load();
    }
  }

  return (
    <div>
      <BackLink href="/me" label="返回个人中心" />
      <PageHeader title="投递记录管理" desc="按列表追踪求职进度，并用下方日历记录面试安排" />

      {loading ? (
        <p className="text-sm text-slate-400">加载中…</p>
      ) : error ? (
        <p className="text-sm text-red-600">{error}</p>
      ) : (
        <>
          {/* 列表标签页 */}
          <div className="mb-4 flex flex-wrap items-center gap-2">
            {lists.map((l) => (
              <button
                key={l.id}
                onClick={() => setActiveId(l.id)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  activeId === l.id
                    ? "bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {l.name}
                <span className="ml-1 opacity-70">({l.records.length})</span>
              </button>
            ))}
            <button
              onClick={handleCreateList}
              className="rounded-full border border-dashed border-brand-400 px-4 py-1.5 text-sm font-medium text-brand-600 hover:bg-brand-50"
            >
              + 新建列表
            </button>
          </div>

          {!active ? (
            <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-sm text-slate-500">
              还没有投递列表，点击「+ 新建列表」开始记录你的求职进度。
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white p-4">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-base font-semibold text-slate-900">{active.name}</h2>
                <div className="flex gap-2 text-xs">
                  <button onClick={handleRenameList} className="text-slate-500 hover:text-brand-600">
                    重命名
                  </button>
                  <button onClick={handleDeleteList} className="text-slate-500 hover:text-red-600">
                    删除列表
                  </button>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[840px] border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-200 text-left text-xs font-semibold text-slate-500">
                      <th className="w-10 px-2 py-2">#</th>
                      <th className="px-2 py-2">公司名称</th>
                      <th className="w-28 px-2 py-2">性质</th>
                      <th className="px-2 py-2">岗位名称</th>
                      <th className="w-36 px-2 py-2">投递时间</th>
                      <th className="w-32 px-2 py-2">投递状态</th>
                      <th className="w-44 px-2 py-2">关联面经</th>
                      <th className="w-12 px-2 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {active.records.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="px-2 py-6 text-center text-xs text-slate-400">
                          暂无记录，点击下方「+ 添加一行」新增。
                        </td>
                      </tr>
                    ) : (
                      active.records.map((rec, i) => (
                        <RecordRow
                          key={rec.id}
                          index={i + 1}
                          rec={rec}
                          companies={companies}
                          nameToId={nameToId}
                          onUpdate={(patch) => handleUpdateRecord(rec, patch)}
                          onDelete={() => handleDeleteRecord(rec)}
                        />
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <button
                onClick={handleAddRecord}
                className="mt-3 rounded-lg border border-dashed border-slate-300 px-4 py-1.5 text-sm text-brand-600 hover:bg-brand-50"
              >
                + 添加一行
              </button>
            </div>
          )}

          {/* 面试日历 */}
          <CalendarPanel />
        </>
      )}
    </div>
  );
}

function RecordRow({
  index,
  rec,
  companies,
  nameToId,
  onUpdate,
  onDelete,
}: {
  index: number;
  rec: ApplicationRecord;
  companies: InterviewCompany[];
  nameToId: Map<string, number>;
  onUpdate: (patch: Partial<ApplicationRecord>) => void;
  onDelete: () => void;
}) {
  const [company, setCompany] = useState(rec.company_name);
  const [position, setPosition] = useState(rec.position);

  // 生效的面经公司：优先手动关联，否则按公司名自动匹配。
  const suggestedId = nameToId.get((company || rec.company_name).trim().toLowerCase()) ?? null;
  const effectiveId = rec.interview_company_id ?? suggestedId;

  // 服务端/其它来源变更时同步本地输入。
  useEffect(() => setCompany(rec.company_name), [rec.company_name]);
  useEffect(() => setPosition(rec.position), [rec.position]);

  const cellInput =
    "w-full rounded border border-transparent bg-transparent px-2 py-1 text-sm hover:border-slate-200 focus:border-brand-500 focus:bg-white focus:outline-none";

  return (
    <tr className="border-b border-slate-100 last:border-0">
      <td className="px-2 py-1 text-xs text-slate-400">{index}</td>
      <td className="px-2 py-1">
        <input
          value={company}
          onChange={(e) => setCompany(e.target.value)}
          onBlur={() => company !== rec.company_name && onUpdate({ company_name: company })}
          placeholder="公司名称"
          className={cellInput}
        />
      </td>
      <td className="px-2 py-1">
        <select
          value={rec.nature ?? ""}
          onChange={(e) => onUpdate({ nature: (e.target.value || null) as CompanyNature | null })}
          className={`${cellInput} cursor-pointer`}
        >
          <option value="">未选择</option>
          {NATURE_OPTIONS.map((n) => (
            <option key={n} value={n}>
              {COMPANY_NATURE_LABEL[n]}
            </option>
          ))}
        </select>
      </td>
      <td className="px-2 py-1">
        <input
          value={position}
          onChange={(e) => setPosition(e.target.value)}
          onBlur={() => position !== rec.position && onUpdate({ position })}
          placeholder="岗位名称"
          className={cellInput}
        />
      </td>
      <td className="px-2 py-1">
        <input
          type="date"
          value={rec.applied_date ?? ""}
          onChange={(e) => onUpdate({ applied_date: e.target.value || null })}
          className={`${cellInput} cursor-pointer`}
        />
      </td>
      <td className="px-2 py-1">
        <select
          value={rec.status}
          onChange={(e) => onUpdate({ status: e.target.value as ApplicationStatus })}
          className={`w-full cursor-pointer rounded px-2 py-1 text-xs font-medium focus:outline-none ${
            STATUS_STYLE[rec.status] ?? "bg-slate-100 text-slate-700"
          }`}
        >
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {APPLICATION_STATUS_LABEL[s]}
            </option>
          ))}
        </select>
      </td>
      <td className="px-2 py-1">
        <div className="flex flex-col gap-1">
          <select
            value={String(effectiveId ?? "")}
            onChange={(e) =>
              onUpdate({ interview_company_id: e.target.value ? Number(e.target.value) : null })
            }
            className={`${cellInput} cursor-pointer`}
            title="选择要关联的面经公司"
          >
            <option value="">未关联</option>
            {companies.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}（{c.post_count}）
              </option>
            ))}
          </select>
          {effectiveId ? (
            <Link
              href={`/interview/${effectiveId}`}
              className="text-xs font-medium text-brand-600 hover:underline"
              title="跳转到关联的面经"
            >
              查看面经 →
            </Link>
          ) : (company || rec.company_name).trim() ? (
            <Link
              href={`/submit?type=interview&company=${encodeURIComponent(
                (company || rec.company_name).trim(),
              )}`}
              className="text-xs text-slate-400 hover:text-brand-600 hover:underline"
              title="还没这家公司的面经，去上传一份（可获得积分）"
            >
              + 上传面经
            </Link>
          ) : null}
        </div>
      </td>
      <td className="px-2 py-1 text-center">
        <button
          onClick={onDelete}
          className="text-xs text-slate-400 hover:text-red-600"
          title="删除该记录"
        >
          删除
        </button>
      </td>
    </tr>
  );
}
