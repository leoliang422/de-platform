"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { BackLink, Empty, ErrorText, Loading, Prose } from "@/components/content";
import { ContentInteractions } from "@/components/interactions";
import { ModuleUnlockPanel } from "@/components/unlock";
import {
  getAccessToken,
  getCompanyInterviewsByType,
  INTERVIEW_ROUND_LABEL,
  INTERVIEW_ROUND_ORDER,
  INTERVIEW_TYPE_LABEL,
  INTERVIEW_TYPE_ORDER,
  revealInterview,
  type InterviewCard,
  type InterviewQA,
  type InterviewTypeGroup,
  type ModuleAccessInfo,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function CompanyInterviewsPage({
  params,
}: {
  params: Promise<{ companyId: string }>;
}) {
  const { companyId } = use(params);
  const { refreshUser } = useAuth();
  const [groups, setGroups] = useState<InterviewTypeGroup[]>([]);
  const [access, setAccess] = useState<ModuleAccessInfo | null>(null);
  const [active, setActive] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    (keepActive = false) =>
      getCompanyInterviewsByType(Number(companyId), getAccessToken())
        .then((res) => {
          setGroups(res.groups);
          setAccess(res.access);
          if (!keepActive) {
            const firstNonEmpty = INTERVIEW_TYPE_ORDER.find(
              (t) => (res.groups.find((x) => x.interview_type === t)?.count ?? 0) > 0,
            );
            setActive((prev) => prev ?? firstNonEmpty ?? null);
          }
        })
        .catch(() => setError("无法加载面经"))
        .finally(() => setLoading(false)),
    [companyId],
  );

  useEffect(() => {
    load();
  }, [load]);

  async function onReveal(postId: number) {
    const token = getAccessToken();
    if (!token) return;
    await revealInterview(token, postId);
    await refreshUser();
    await load(true);
  }

  const tabs = useMemo(
    () =>
      INTERVIEW_TYPE_ORDER.map((t) => groups.find((g) => g.interview_type === t)).filter(
        (g): g is InterviewTypeGroup => !!g && g.count > 0,
      ),
    [groups],
  );

  const activeGroup = tabs.find((g) => g.interview_type === active) ?? null;

  return (
    <div>
      <BackLink href="/interview" label="返回企业列表" />
      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : tabs.length === 0 ? (
        <Empty message="该企业暂无面经" />
      ) : (
        <div>
          <div className="mb-5 flex flex-wrap gap-2">
            {tabs.map((g) => (
              <button
                key={g.interview_type}
                onClick={() => setActive(g.interview_type)}
                className={`rounded-full px-4 py-1.5 text-sm font-medium transition ${
                  active === g.interview_type
                    ? "bg-brand-600 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {INTERVIEW_TYPE_LABEL[g.interview_type] ?? g.interview_type}
                <span className="ml-1 opacity-70">({g.count})</span>
              </button>
            ))}
          </div>

          {activeGroup && access && (
            <Carousel
              key={activeGroup.interview_type}
              group={activeGroup}
              access={access}
              onReveal={onReveal}
              onUnlocked={() => load(true)}
            />
          )}
        </div>
      )}
    </div>
  );
}

function Carousel({
  group,
  access,
  onReveal,
  onUnlocked,
}: {
  group: InterviewTypeGroup;
  access: ModuleAccessInfo;
  onReveal: (postId: number) => Promise<void>;
  onUnlocked: () => void;
}) {
  const scroller = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const total = group.posts.length;

  function scrollTo(i: number) {
    const el = scroller.current;
    if (!el) return;
    const clamped = Math.max(0, Math.min(total - 1, i));
    const child = el.children[clamped] as HTMLElement | undefined;
    if (child) el.scrollTo({ left: child.offsetLeft - el.offsetLeft, behavior: "smooth" });
    setIndex(clamped);
  }

  function onScroll() {
    const el = scroller.current;
    if (!el) return;
    const children = Array.from(el.children) as HTMLElement[];
    const mid = el.scrollLeft + el.clientWidth / 2;
    let nearest = 0;
    let best = Infinity;
    children.forEach((c, i) => {
      const center = c.offsetLeft - el.offsetLeft + c.clientWidth / 2;
      const d = Math.abs(center - mid);
      if (d < best) {
        best = d;
        nearest = i;
      }
    });
    setIndex(nearest);
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm text-slate-500">
          第 {index + 1} / {total} 篇面经（左右滑动切换）
        </span>
        {total > 1 && (
          <div className="flex gap-2">
            <button
              onClick={() => scrollTo(index - 1)}
              disabled={index === 0}
              className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              ←
            </button>
            <button
              onClick={() => scrollTo(index + 1)}
              disabled={index === total - 1}
              className="rounded-full border border-slate-300 px-3 py-1 text-sm text-slate-600 hover:bg-slate-50 disabled:opacity-40"
            >
              →
            </button>
          </div>
        )}
      </div>

      <div
        ref={scroller}
        onScroll={onScroll}
        className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-3 [scrollbar-width:thin]"
      >
        {group.posts.map((post) => (
          <div
            key={post.id}
            className="w-full shrink-0 snap-center sm:w-[640px] sm:max-w-[calc(100%-2rem)]"
          >
            <InterviewCardView
              post={post}
              access={access}
              onReveal={onReveal}
              onUnlocked={onUnlocked}
            />
          </div>
        ))}
      </div>
    </div>
  );
}

function InterviewCardView({
  post,
  access,
  onReveal,
  onUnlocked,
}: {
  post: InterviewCard;
  access: ModuleAccessInfo;
  onReveal: (postId: number) => Promise<void>;
  onUnlocked: () => void;
}) {
  const { user } = useAuth();
  const [busy, setBusy] = useState(false);

  const byRound = useMemo(() => {
    const map = new Map<string, InterviewQA[]>();
    for (const qa of post.qa) {
      if (!map.has(qa.section)) map.set(qa.section, []);
      map.get(qa.section)!.push(qa);
    }
    return INTERVIEW_ROUND_ORDER.filter((r) => map.has(r)).map((r) => ({
      round: r,
      items: map.get(r)!,
    }));
  }, [post.qa]);

  const quotaExhausted = !access.unlocked && access.free_used >= access.free_limit;

  async function reveal() {
    setBusy(true);
    try {
      await onReveal(post.id);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <AuthorLink post={post} />
        {(post.rounds_covered.length > 0 || post.position) && (
          <div className="flex shrink-0 flex-wrap items-center justify-end gap-1">
            {post.rounds_covered.map((r) => (
              <span
                key={r}
                className="rounded-full bg-brand-50 px-2 py-0.5 text-xs font-medium text-brand-700"
              >
                {INTERVIEW_ROUND_LABEL[r] ?? r}
              </span>
            ))}
            {post.position && (
              <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-700">
                {post.position}
              </span>
            )}
          </div>
        )}
      </div>

      {post.locked ? (
        <div className="mt-3">
          {!user ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 text-center text-sm text-amber-800">
              <Link href="/login" className="font-medium text-brand-600 hover:underline">
                登录
              </Link>
              后可查看面经（每个模块免费 {access.free_limit} 篇）
            </div>
          ) : quotaExhausted ? (
            <ModuleUnlockPanel
              module="interview"
              freeUsed={access.free_used}
              freeLimit={access.free_limit}
              unlockPoints={access.unlock_points}
              onUnlocked={onUnlocked}
            />
          ) : (
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-5 text-center">
              <p className="text-sm text-slate-600">本篇面经内容已隐藏</p>
              <button
                onClick={reveal}
                disabled={busy}
                className="mt-3 rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
              >
                查看这篇面经（免费剩 {Math.max(0, access.free_limit - access.free_used)} 篇）
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="mt-3 space-y-4">
          {byRound.map(({ round, items }) => (
            <div key={round}>
              {byRound.length > 1 && (
                <p className="mb-2 text-sm font-semibold text-brand-700">
                  {INTERVIEW_ROUND_LABEL[round] ?? round}
                </p>
              )}
              <div className="space-y-2">
                {items.map((qa) => (
                  <QAItem key={qa.id} qa={qa} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-auto">
        <ContentInteractions contentType="interview" contentId={post.id} />
      </div>
    </div>
  );
}

function AuthorLink({ post }: { post: InterviewCard }) {
  const initial = post.author_nickname?.[0] ?? "?";
  const avatar = (
    <span className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-brand-100 text-sm font-medium text-brand-700">
      {post.author_avatar ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={post.author_avatar} alt={post.author_nickname} className="h-full w-full object-cover" />
      ) : (
        initial
      )}
    </span>
  );
  const content = (
    <>
      {avatar}
      <span className="text-sm font-medium text-slate-800">{post.author_nickname}</span>
    </>
  );
  if (post.author_id == null) {
    return <div className="flex items-center gap-2">{content}</div>;
  }
  return (
    <Link
      href={`/users/${post.author_id}`}
      className="flex items-center gap-2 rounded-full transition hover:opacity-80"
      title="查看主页 / 私聊"
    >
      {content}
    </Link>
  );
}

function QAItem({ qa }: { qa: InterviewQA }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-md bg-slate-50 p-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-3 text-left"
      >
        <span className="text-sm font-medium text-slate-900">Q：{qa.question}</span>
        {qa.answer && (
          <span className="shrink-0 text-xs text-brand-600">{open ? "收起" : "查看答案"}</span>
        )}
      </button>
      {open && qa.answer && (
        <div className="mt-2 border-l-2 border-brand-200 pl-3 text-sm text-slate-600">
          <Prose>{qa.answer}</Prose>
        </div>
      )}
    </div>
  );
}
