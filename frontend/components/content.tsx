import Link from "next/link";
import type { ReactNode } from "react";

export function Prose({ children }: { children: string }) {
  // M1：以等宽预格式化展示 Markdown 原文；富文本渲染留待后续里程碑。
  return (
    <pre className="whitespace-pre-wrap break-words rounded-lg bg-slate-50 p-4 font-sans text-sm leading-relaxed text-slate-800">
      {children}
    </pre>
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
