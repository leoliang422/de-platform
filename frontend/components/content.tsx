import Link from "next/link";
import type { ReactNode } from "react";

const IMG_MD_RE = /!\[([^\]]*)\]\(([^)\s]+)\)/g;

export function Prose({ children }: { children: string }) {
  // 以预格式化展示 Markdown 原文，并把 ![alt](url) 图片语法渲染为内嵌图片。
  const parts: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of children.matchAll(IMG_MD_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) parts.push(<span key={key++}>{children.slice(last, idx)}</span>);
    parts.push(
      // eslint-disable-next-line @next/next/no-img-element
      <img
        key={key++}
        src={m[2]}
        alt={m[1]}
        className="my-2 block max-h-[28rem] max-w-full rounded-lg border border-slate-200"
      />,
    );
    last = idx + m[0].length;
  }
  if (last < children.length) parts.push(<span key={key++}>{children.slice(last)}</span>);

  return (
    <div className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-4 font-sans text-sm leading-relaxed text-slate-800">
      {parts}
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
