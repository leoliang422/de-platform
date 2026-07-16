import type { Metadata } from "next";

import { Navbar } from "@/components/navbar";
import { AuthProvider } from "@/lib/auth";

import "./globals.css";

export const metadata: Metadata = {
  title: "DE Platform · 数据开发学习 & 面试",
  description: "数据开发方向的八股、SQL 题库、面经与实战项目一站式平台",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-slate-50 text-slate-900">
        <AuthProvider>
          <Navbar />
          <main className="mx-auto max-w-6xl px-4 py-10">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
