"use client";

import { useState } from "react";

import {
  runAndJudge,
  type JudgeResult,
  type PlaygroundFixture,
  type QueryResult,
} from "@/lib/sql-playground";

function ResultTable({ data }: { data: QueryResult }) {
  if (data.columns.length === 0) {
    return <p className="text-xs text-slate-400">（无结果列）</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr>
            {data.columns.map((c) => (
              <th
                key={c}
                className="border-b border-slate-200 bg-slate-50 px-3 py-1.5 text-left font-semibold text-slate-600"
              >
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.rows.length === 0 ? (
            <tr>
              <td
                colSpan={data.columns.length}
                className="px-3 py-2 text-center text-xs text-slate-400"
              >
                （0 行）
              </td>
            </tr>
          ) : (
            data.rows.map((r, ri) => (
              <tr key={ri} className="odd:bg-white even:bg-slate-50/50">
                {r.map((cell, ci) => (
                  <td key={ci} className="border-b border-slate-100 px-3 py-1.5 text-slate-700">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}

export function SqlPlayground({ fixture }: { fixture: PlaygroundFixture }) {
  const [sql, setSql] = useState(fixture.starterSql);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<JudgeResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showExpected, setShowExpected] = useState(false);

  async function run() {
    setRunning(true);
    setError(null);
    setResult(null);
    setShowExpected(false);
    try {
      const r = await runAndJudge(fixture.setupSql, fixture.solutionSql, sql, fixture.ordered);
      setResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "执行失败");
    } finally {
      setRunning(false);
    }
  }

  return (
    <section className="mt-8 rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-base font-bold text-slate-900">在线练习</h2>
        <span className="rounded bg-brand-50 px-1.5 py-0.5 text-xs font-medium text-brand-700">
          Beta
        </span>
        <span className="text-xs text-slate-400">在浏览器内运行（DuckDB），提交后自动判分</span>
      </div>

      <textarea
        value={sql}
        onChange={(e) => setSql(e.target.value)}
        spellCheck={false}
        rows={12}
        className="w-full resize-y rounded-lg border border-slate-300 bg-slate-900 p-3 font-mono text-xs leading-relaxed text-slate-100 focus:border-brand-500 focus:outline-none"
      />

      <div className="mt-3 flex items-center gap-3">
        <button
          onClick={run}
          disabled={running}
          className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          {running ? "运行中…" : "运行并判题"}
        </button>
        <button
          onClick={() => {
            setSql(fixture.starterSql);
            setResult(null);
            setError(null);
          }}
          className="text-sm text-slate-500 hover:underline"
        >
          重置
        </button>
      </div>

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          <p className="font-medium">执行出错</p>
          <pre className="mt-1 whitespace-pre-wrap break-words font-mono text-xs">{error}</pre>
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div
            className={`rounded-lg px-4 py-2 text-sm font-medium ${
              result.pass
                ? "bg-green-50 text-green-700"
                : "bg-amber-50 text-amber-800"
            }`}
          >
            {result.pass
              ? "✅ 通过！结果与期望一致"
              : "❌ 未通过：结果与期望不一致（可对照下方期望结果调整）"}
          </div>

          <div>
            <p className="mb-1 text-xs font-semibold text-slate-500">你的结果</p>
            <ResultTable data={result.actual} />
          </div>

          {!result.pass && (
            <div>
              <button
                onClick={() => setShowExpected((v) => !v)}
                className="text-xs text-brand-600 hover:underline"
              >
                {showExpected ? "隐藏期望结果" : "查看期望结果"}
              </button>
              {showExpected && (
                <div className="mt-1">
                  <ResultTable data={result.expected} />
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
