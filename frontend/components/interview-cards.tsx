"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Prose } from "@/components/content";
import {
  getAccessToken,
  getMyInterviews,
  INTERVIEW_ROUND_LABEL,
  INTERVIEW_ROUND_ORDER,
  type InterviewCard,
  type InterviewQA,
} from "@/lib/api";

/** 弹窗：展示当前用户为某公司上传的面经，只读、支持左右滑动切换多篇。 */
export function InterviewCardsModal({
  company,
  onClose,
}: {
  company: string;
  onClose: () => void;
}) {
  const [cards, setCards] = useState<InterviewCard[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAccessToken();
    if (!token) return;
    getMyInterviews(token, company)
      .then(setCards)
      .catch(() => setError("加载失败"));
  }, [company]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[88vh] w-full max-w-2xl overflow-hidden rounded-xl bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-200 px-5 py-3">
          <h3 className="text-base font-semibold text-slate-900">我在「{company}」的面经</h3>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            ✕
          </button>
        </div>

        <div className="max-h-[76vh] overflow-y-auto p-5">
          {error ? (
            <p className="py-8 text-center text-sm text-red-600">{error}</p>
          ) : cards === null ? (
            <p className="py-8 text-center text-sm text-slate-400">加载中…</p>
          ) : cards.length === 0 ? (
            <div className="py-8 text-center text-sm text-slate-500">
              你还没有上传这家公司的面经。
              <Link
                href={`/submit?type=interview&company=${encodeURIComponent(company)}`}
                className="ml-1 font-medium text-brand-600 hover:underline"
              >
                去上传 →
              </Link>
              <p className="mt-2 text-xs text-slate-400">
                （面经需经管理员审核通过后才会在这里显示）
              </p>
            </div>
          ) : (
            <CardCarousel cards={cards} />
          )}
        </div>
      </div>
    </div>
  );
}

function CardCarousel({ cards }: { cards: InterviewCard[] }) {
  const scroller = useRef<HTMLDivElement>(null);
  const [index, setIndex] = useState(0);
  const total = cards.length;

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
      {total > 1 && (
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm text-slate-500">
            第 {index + 1} / {total} 篇（左右滑动切换）
          </span>
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
        </div>
      )}
      <div
        ref={scroller}
        onScroll={onScroll}
        className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 [scrollbar-width:thin]"
      >
        {cards.map((card) => (
          <div key={card.id} className="w-full shrink-0 snap-center">
            <ReadonlyCard post={card} />
          </div>
        ))}
      </div>
    </div>
  );
}

/** 只读面经卡片，样式对齐面经页，但去掉锁定/互动，仅展示。 */
function ReadonlyCard({ post }: { post: InterviewCard }) {
  const map = new Map<string, InterviewQA[]>();
  for (const qa of post.qa) {
    if (!map.has(qa.section)) map.set(qa.section, []);
    map.get(qa.section)!.push(qa);
  }
  const byRound = INTERVIEW_ROUND_ORDER.filter((r) => map.has(r)).map((r) => ({
    round: r,
    items: map.get(r)!,
  }));

  const initial = post.author_nickname?.[0] ?? "?";

  return (
    <div className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 border-b border-slate-100 pb-3">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full bg-brand-100 text-sm font-medium text-brand-700">
            {post.author_avatar ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={post.author_avatar}
                alt={post.author_nickname}
                className="h-full w-full object-cover"
              />
            ) : (
              initial
            )}
          </span>
          <span className="text-sm font-medium text-slate-800">{post.author_nickname}</span>
        </div>
        {(post.position || post.rounds_covered.length > 0) && (
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

      <div className="mt-3 space-y-4">
        {byRound.length === 0 ? (
          <p className="text-sm text-slate-400">这篇面经暂无问答内容。</p>
        ) : (
          byRound.map(({ round, items }) => (
            <div key={round}>
              {byRound.length > 1 && (
                <p className="mb-2 text-sm font-semibold text-brand-700">
                  {INTERVIEW_ROUND_LABEL[round] ?? round}
                </p>
              )}
              <div className="space-y-2">
                {items.map((qa) => (
                  <ReadonlyQA key={qa.id} qa={qa} />
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function ReadonlyQA({ qa }: { qa: InterviewQA }) {
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
