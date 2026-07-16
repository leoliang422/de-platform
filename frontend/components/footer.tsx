export function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="mt-16 border-t border-slate-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <span>© {year} DE Platform · 数据开发学习 &amp; 面试</span>
        <span className="text-slate-400">
          八股 · SQL 题库 · 面经 · 实战项目 · 投稿赚积分
        </span>
      </div>
    </footer>
  );
}
