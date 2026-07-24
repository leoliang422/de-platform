import Link from "next/link";
import type { ReactNode } from "react";

// SQL 关键字（大写匹配，忽略大小写）——用于代码块语法高亮。
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

// 轻量 SQL 语法高亮：把代码切成 注释/字符串/数字/关键字/函数/标点，分色渲染。无外部依赖。
function highlightSql(code: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re =
    /(--[^\n]*|#[^\n]*|\/\*[\s\S]*?\*\/)|('(?:[^'\\]|\\.)*')|(`[^`]*`)|(\b\d+(?:\.\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)|(\s+)|([\s\S])/g;
  let m: RegExpExecArray | null;
  let k = 0;
  while ((m = re.exec(code)) !== null) {
    const key = `sql-${k++}`;
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
        // 后接 "(" 视为函数名
        let j = re.lastIndex;
        while (j < code.length && /\s/.test(code[j])) j++;
        if (code[j] === "(") {
          out.push(<span key={key} className="text-violet-300">{word}</span>);
        } else {
          out.push(word);
        }
      }
    } else if (m[6] !== undefined) {
      out.push(m[6]); // 空白原样
    } else {
      out.push(<span key={key} className="text-slate-400">{m[7]}</span>); // 标点/运算符
    }
  }
  return out;
}

// 行内语法：图片 / 链接 / 加粗 / 行内代码，按出现顺序切分。
const INLINE_RE =
  /!\[([^\]]*)\]\(([^)\s]+)\)|\[([^\]]+)\]\(([^)\s]+)\)|\*\*([^*]+)\*\*|`([^`]+)`/g;

function renderInline(text: string, kp: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let i = 0;
  let m: RegExpExecArray | null;
  INLINE_RE.lastIndex = 0;
  while ((m = INLINE_RE.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1] !== undefined) {
      out.push(
        // eslint-disable-next-line @next/next/no-img-element
        <img
          key={`${kp}-${i++}`}
          src={m[2]}
          alt={m[1]}
          className="my-2 block max-h-[28rem] max-w-full rounded-lg border border-slate-200"
        />,
      );
    } else if (m[3] !== undefined) {
      out.push(
        <a
          key={`${kp}-${i++}`}
          href={m[4]}
          target="_blank"
          rel="noreferrer"
          className="text-brand-600 hover:underline"
        >
          {m[3]}
        </a>,
      );
    } else if (m[5] !== undefined) {
      out.push(<strong key={`${kp}-${i++}`}>{m[5]}</strong>);
    } else if (m[6] !== undefined) {
      out.push(
        <code
          key={`${kp}-${i++}`}
          className="rounded bg-slate-200 px-1 py-0.5 text-[0.85em] text-slate-800"
        >
          {m[6]}
        </code>,
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

// 轻量 Markdown 渲染：标题 / 列表 / 代码块 / 图片 / 段落，无第三方依赖。
function splitTableRow(line: string): string[] {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
  const s = line.trim();
  return s.includes("-") && s.includes("|") && /^[\s|:-]+$/.test(s);
}

function renderMarkdown(md: string): ReactNode[] {
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let key = 0;
  let para: string[] = [];
  let i = 0;

  const flushPara = () => {
    if (para.length === 0) return;
    const nodes: ReactNode[] = [];
    para.forEach((ln, idx) => {
      if (idx > 0) nodes.push(<br key={`br-${key}-${idx}`} />);
      nodes.push(...renderInline(ln, `p-${key}-${idx}`));
    });
    blocks.push(
      <p key={`p-${key}`} className="my-2 leading-relaxed">
        {nodes}
      </p>,
    );
    key++;
    para = [];
  };

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim().startsWith("```")) {
      flushPara();
      const lang = line.trim().slice(3).trim().toLowerCase();
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        buf.push(lines[i]);
        i++;
      }
      i++;
      const codeText = buf.join("\n");
      const isSql = lang === "sql";
      blocks.push(
        <div key={`c-${key++}`} className="my-3 overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
          {lang && (
            <div className="flex items-center justify-between border-b border-slate-700/60 px-3 py-1.5">
              <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                {lang}
              </span>
            </div>
          )}
          <pre className="overflow-auto p-3 text-xs leading-relaxed text-slate-100">
            <code>{isSql ? highlightSql(codeText) : codeText}</code>
          </pre>
        </div>,
      );
      continue;
    }

    if (line.trim() === "") {
      flushPara();
      i++;
      continue;
    }

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushPara();
      const level = heading[1].length;
      const cls =
        level <= 1
          ? "mt-4 mb-2 text-lg font-bold"
          : level === 2
            ? "mt-3 mb-1.5 text-base font-semibold"
            : "mt-2 mb-1 text-sm font-semibold";
      blocks.push(
        <div key={`h-${key++}`} className={`${cls} text-slate-900`}>
          {renderInline(heading[2], `h-${key}`)}
        </div>,
      );
      i++;
      continue;
    }

    if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      flushPara();
      blocks.push(<hr key={`hr-${key++}`} className="my-3 border-slate-200" />);
      i++;
      continue;
    }

    if (/^\s*[-*•]\s+/.test(line)) {
      flushPara();
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*•]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*•]\s+/, ""));
        i++;
      }
      const k = key++;
      blocks.push(
        <ul key={`ul-${k}`} className="my-2 list-disc space-y-1 pl-5">
          {items.map((it, idx) => (
            <li key={idx}>{renderInline(it, `ul-${k}-${idx}`)}</li>
          ))}
        </ul>,
      );
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      flushPara();
      const items: string[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i++;
      }
      const k = key++;
      blocks.push(
        <ol key={`ol-${k}`} className="my-2 list-decimal space-y-1 pl-5">
          {items.map((it, idx) => (
            <li key={idx}>{renderInline(it, `ol-${k}-${idx}`)}</li>
          ))}
        </ol>,
      );
      continue;
    }

    // 表格（GFM 管道语法）：表头行 + 分隔行(---) + 若干数据行
    if (line.includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      flushPara();
      const header = splitTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
        rows.push(splitTableRow(lines[i]));
        i++;
      }
      const k = key++;
      blocks.push(
        <div key={`tbl-${k}`} className="my-2 overflow-x-auto">
          <table className="w-full border-collapse text-sm">
            <thead>
              <tr>
                {header.map((h, ci) => (
                  <th
                    key={ci}
                    className="border border-slate-300 bg-slate-100 px-3 py-1.5 text-left font-semibold"
                  >
                    {renderInline(h, `th-${k}-${ci}`)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>
                  {header.map((_, ci) => (
                    <td key={ci} className="border border-slate-300 px-3 py-1.5 align-top">
                      {renderInline(r[ci] ?? "", `td-${k}-${ri}-${ci}`)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }

    para.push(line);
    i++;
  }
  flushPara();
  return blocks;
}

export function Prose({ children, bare = false }: { children: string; bare?: boolean }) {
  // 渲染 Markdown：标题/列表/代码块/加粗/行内代码/内嵌图片，避免原始符号刷屏。
  // bare=true：不加灰底卡片与内边距，让正文与标题左对齐（文章式阅读）。
  return (
    <div
      className={
        bare
          ? "break-words font-sans text-sm text-slate-800 [&>*:first-child]:mt-0"
          : "break-words rounded-lg bg-slate-50 p-4 font-sans text-sm text-slate-800 [&>*:first-child]:mt-0"
      }
    >
      {renderMarkdown(children)}
    </div>
  );
}

export function PageHeader({ title, desc }: { title: string; desc?: string }) {
  return (
    <div className="mb-6">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      {desc && <p className="mt-1 text-sm text-slate-600">{desc}</p>}
    </div>
  );
}

export function Loading() {
  return <p className="text-sm text-slate-400">加载中…</p>;
}

export function ErrorText({ message }: { message: string }) {
  return <p className="text-sm text-red-600">{message}</p>;
}

export function Empty({ message }: { message: string }) {
  return <p className="text-sm text-slate-400">{message}</p>;
}

export function ListCard({ href, children }: { href: string; children: ReactNode }) {
  return (
    <Link
      href={href}
      className="block rounded-lg border border-slate-200 bg-white p-4 transition hover:border-brand-500 hover:shadow-sm"
    >
      {children}
    </Link>
  );
}

export function BackLink({ href, label }: { href: string; label: string }) {
  return (
    <Link href={href} className="mb-4 inline-block text-sm text-brand-600 hover:underline">
      ← {label}
    </Link>
  );
}
