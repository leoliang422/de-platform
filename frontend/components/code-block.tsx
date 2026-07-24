"use client";

import { useState, type ReactNode } from "react";

// SQL 关键字（大写匹配，忽略大小写）——用于语法高亮。
const SQL_KEYWORDS = new Set([
  "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "NULL", "AS", "ON", "IN", "IS",
  "LIKE", "BETWEEN", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET", "JOIN",
  "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "UNION", "ALL", "DISTINCT",
  "CASE", "WHEN", "THEN", "ELSE", "END", "OVER", "PARTITION", "ROWS", "RANGE",
  "PRECEDING", "FOLLOWING", "CURRENT", "ROW", "UNBOUNDED", "WITH", "INSERT", "INTO",
  "VALUES", "UPDATE", "SET", "DELETE", "CREATE", "TABLE", "VIEW", "DROP", "ALTER",
  "DESC", "ASC", "EXISTS", "IF", "USING", "OVERWRITE", "LATERAL", "EXPLODE", "TRUE",
  "FALSE", "INTERVAL", "CAST", "DATE",
]);

// 单行 SQL 语法高亮（配合逐行渲染的行号）。
function highlightSqlLine(line: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re =
    /(--[^\n]*|#[^\n]*)|('(?:[^'\\]|\\.)*')|(`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(\s+)|([\s\S])/g;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(line)) !== null) {
    const key = `t-${k++}`;
    if (m[1] !== undefined) {
      out.push(<span key={key} className="italic text-slate-500">{m[1]}</span>);
    } else if (m[2] !== undefined || m[3] !== undefined) {
      out.push(<span key={key} className="text-emerald-300">{m[2] ?? m[3]}</span>);
    } else if (m[4] !== undefined) {
      out.push(<span key={key} className="text-amber-300">{m[4]}</span>);
    } else if (m[5] !== undefined) {
      const word = m[5];
      if (SQL_KEYWORDS.has(word.toUpperCase())) {
        out.push(<span key={key} className="font-medium text-sky-400">{word}</span>);
      } else {
        let j = re.lastIndex;
        while (j < line.length && /\s/.test(line[j])) j++;
        if (line[j] === "(") {
          out.push(<span key={key} className="text-violet-300">{word}</span>);
        } else {
          out.push(word);
        }
      }
    } else if (m[6] !== undefined) {
      out.push(m[6]);
    } else {
      out.push(<span key={key} className="text-slate-400">{m[7]}</span>);
    }
  }
  return out;
}

/** 代码块：语言标签 + 复制按钮 + 行号 + SQL 语法高亮。 */
export function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [copied, setCopied] = useState(false);
  const isSql = lang.toLowerCase() === "sql";
  const lines = code.replace(/\n+$/, "").split("\n");

  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // 忽略（部分浏览器无剪贴板权限）
    }
  }

  return (
    <div className="my-3 overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
      <div className="flex items-center justify-between border-b border-slate-700/60 px-3 py-1.5">
        <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
          {lang || "code"}
        </span>
        <button
          onClick={copy}
          className="rounded px-2 py-0.5 text-[11px] text-slate-400 transition hover:bg-slate-700/50 hover:text-slate-100"
        >
          {copied ? "已复制 ✓" : "复制"}
        </button>
      </div>
      <div className="overflow-auto text-xs leading-relaxed">
        <table className="border-collapse">
          <tbody>
            {lines.map((ln, i) => (
              <tr key={i}>
                <td className="select-none whitespace-nowrap px-3 text-right align-top tabular-nums text-slate-600">
                  {i + 1}
                </td>
                <td className="whitespace-pre pr-4 align-top text-slate-100">
                  <code>{isSql ? highlightSqlLine(ln) : ln}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
