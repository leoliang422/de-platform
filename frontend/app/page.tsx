import Link from "next/link";

const sections = [
  {
    title: "八股总结",
    desc: "Hive / Spark / Flink / 数仓建模等技术域知识点，分区整理，持续下钻。",
    href: "/knowledge",
    tag: "知识",
  },
  {
    title: "SQL 题库",
    desc: "数据开发高频 SQL 题目与参考答案，按难度与标签检索。",
    href: "/sql",
    tag: "练习",
  },
  {
    title: "面经",
    desc: "按企业组织的真实面试经验，覆盖岗位与考点。",
    href: "/interview",
    tag: "面试",
  },
  {
    title: "项目整理",
    desc: "实战项目的描述、实现与问答讲解，含免费与付费内容。",
    href: "/projects",
    tag: "实战",
  },
];

export default function HomePage() {
  return (
    <div className="space-y-12">
      <section className="text-center">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          数据开发学习 & 面试平台
        </h1>
        <p className="mx-auto mt-4 max-w-2xl text-lg text-slate-600">
          一站式获取八股知识、SQL 练习、企业面经与实战项目。贡献内容赚取积分，解锁付费资源。
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            href="/register"
            className="rounded-lg bg-brand-600 px-5 py-2.5 font-medium text-white hover:bg-brand-700"
          >
            免费注册
          </Link>
          <Link
            href="/login"
            className="rounded-lg border border-slate-300 px-5 py-2.5 font-medium text-slate-700 hover:bg-slate-100"
          >
            登录
          </Link>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-5 sm:grid-cols-2">
        {sections.map((s) => (
          <Link
            key={s.title}
            href={s.href}
            className="group rounded-xl border border-slate-200 bg-white p-6 transition hover:border-brand-500 hover:shadow-sm"
          >
            <div className="mb-2 inline-block rounded-full bg-brand-50 px-2.5 py-0.5 text-xs font-medium text-brand-700">
              {s.tag}
            </div>
            <h2 className="text-xl font-semibold text-slate-900">{s.title}</h2>
            <p className="mt-2 text-sm text-slate-600">{s.desc}</p>
            <span className="mt-4 inline-block text-sm font-medium text-brand-600">
              进入 →
            </span>
          </Link>
        ))}
      </section>
    </div>
  );
}
