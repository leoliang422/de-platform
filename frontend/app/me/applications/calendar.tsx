"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import {
  createCalendarEvent,
  deleteCalendarEvent,
  getAccessToken,
  getCalendarEvents,
  updateCalendarEvent,
  type CalendarEvent,
} from "@/lib/api";

const WEEKDAYS = ["一", "二", "三", "四", "五", "六", "日"];

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

function dateKey(year: number, month0: number, day: number): string {
  return `${year}-${pad(month0 + 1)}-${pad(day)}`;
}

function todayKey(): string {
  const d = new Date();
  return dateKey(d.getFullYear(), d.getMonth(), d.getDate());
}

// 返回周一为首列的日期网格（含前置空位）。
function buildGrid(year: number, month0: number): (number | null)[] {
  const first = new Date(year, month0, 1);
  const offset = (first.getDay() + 6) % 7; // 周一=0
  const daysInMonth = new Date(year, month0 + 1, 0).getDate();
  const cells: (number | null)[] = [];
  for (let i = 0; i < offset; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function CalendarPanel() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month0, setMonth0] = useState(now.getMonth());
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selected, setSelected] = useState<string | null>(todayKey());

  const monthKey = `${year}-${pad(month0 + 1)}`;

  const load = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;
    try {
      setEvents(await getCalendarEvents(token, monthKey));
    } catch {
      setEvents([]);
    }
  }, [monthKey]);

  useEffect(() => {
    load();
  }, [load]);

  const grid = useMemo(() => buildGrid(year, month0), [year, month0]);

  const eventsByDay = useMemo(() => {
    const map = new Map<string, CalendarEvent[]>();
    for (const e of events) {
      const arr = map.get(e.event_date) ?? [];
      arr.push(e);
      map.set(e.event_date, arr);
    }
    return map;
  }, [events]);

  function goMonth(delta: number) {
    let m = month0 + delta;
    let y = year;
    if (m < 0) {
      m = 11;
      y -= 1;
    } else if (m > 11) {
      m = 0;
      y += 1;
    }
    setMonth0(m);
    setYear(y);
  }

  function goToday() {
    const d = new Date();
    setYear(d.getFullYear());
    setMonth0(d.getMonth());
    setSelected(todayKey());
  }

  const selectedEvents = selected ? (eventsByDay.get(selected) ?? []) : [];
  const tKey = todayKey();

  return (
    <div className="mt-8 rounded-xl border border-slate-200 bg-white p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-900">面试日历</h2>
        <div className="flex items-center gap-2 text-sm">
          <button
            onClick={() => goMonth(-1)}
            className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50"
          >
            ←
          </button>
          <span className="min-w-[96px] text-center font-medium text-slate-800">
            {year} 年 {month0 + 1} 月
          </span>
          <button
            onClick={() => goMonth(1)}
            className="rounded-full border border-slate-300 px-2.5 py-1 text-slate-600 hover:bg-slate-50"
          >
            →
          </button>
          <button
            onClick={goToday}
            className="rounded-lg border border-slate-300 px-3 py-1 text-slate-600 hover:bg-slate-50"
          >
            今天
          </button>
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 text-center text-xs font-medium text-slate-400">
        {WEEKDAYS.map((w) => (
          <div key={w} className="py-1">
            {w}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {grid.map((day, i) => {
          if (day === null) return <div key={i} className="min-h-[64px]" />;
          const key = dateKey(year, month0, day);
          const dayEvents = eventsByDay.get(key) ?? [];
          const isToday = key === tKey;
          const isSelected = key === selected;
          return (
            <button
              key={i}
              onClick={() => setSelected(key)}
              className={`min-h-[64px] rounded-lg border p-1 text-left align-top transition ${
                isSelected
                  ? "border-brand-500 bg-brand-50"
                  : "border-slate-200 hover:border-brand-300 hover:bg-slate-50"
              }`}
            >
              <div
                className={`flex h-5 w-5 items-center justify-center rounded-full text-xs ${
                  isToday ? "bg-brand-600 font-semibold text-white" : "text-slate-600"
                }`}
              >
                {day}
              </div>
              <div className="mt-0.5 space-y-0.5">
                {dayEvents.slice(0, 2).map((e) => (
                  <div
                    key={e.id}
                    className="truncate rounded bg-brand-100 px-1 py-0.5 text-[10px] leading-tight text-brand-700"
                    title={e.title}
                  >
                    {e.start_time ? `${e.start_time} ` : ""}
                    {e.title}
                  </div>
                ))}
                {dayEvents.length > 2 && (
                  <div className="px-1 text-[10px] text-slate-400">+{dayEvents.length - 2} 更多</div>
                )}
              </div>
            </button>
          );
        })}
      </div>

      {selected && (
        <DayEditor
          date={selected}
          events={selectedEvents}
          onChanged={load}
        />
      )}
    </div>
  );
}

function DayEditor({
  date,
  events,
  onChanged,
}: {
  date: string;
  events: CalendarEvent[];
  onChanged: () => void;
}) {
  const [title, setTitle] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);

  async function add() {
    const token = getAccessToken();
    if (!token || !title.trim()) return;
    setBusy(true);
    try {
      await createCalendarEvent(token, {
        title: title.trim(),
        event_date: date,
        start_time: start || null,
        end_time: end || null,
        note: note.trim() || null,
        color: null,
      });
      setTitle("");
      setStart("");
      setEnd("");
      setNote("");
      onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await deleteCalendarEvent(token, id);
    onChanged();
  }

  async function editTitle(ev: CalendarEvent) {
    const token = getAccessToken();
    if (!token) return;
    const next = window.prompt("修改事项标题", ev.title);
    if (next == null || !next.trim()) return;
    await updateCalendarEvent(token, ev.id, { title: next.trim() });
    onChanged();
  }

  const field = "rounded-lg border border-slate-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none";

  return (
    <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <p className="mb-2 text-sm font-medium text-slate-700">{date} 的安排</p>

      {events.length === 0 ? (
        <p className="mb-3 text-xs text-slate-400">当天暂无安排，添加一条吧。</p>
      ) : (
        <div className="mb-3 space-y-1.5">
          {events.map((e) => (
            <div
              key={e.id}
              className="flex items-start gap-2 rounded-md bg-white px-2.5 py-1.5 text-sm ring-1 ring-slate-200"
            >
              <span className="shrink-0 rounded bg-brand-100 px-1.5 py-0.5 text-xs font-medium text-brand-700">
                {e.start_time || "全天"}
                {e.end_time ? `-${e.end_time}` : ""}
              </span>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-slate-800">{e.title}</div>
                {e.note && <div className="text-xs text-slate-500">{e.note}</div>}
              </div>
              <button onClick={() => editTitle(e)} className="shrink-0 text-xs text-slate-400 hover:text-brand-600">
                改
              </button>
              <button onClick={() => remove(e.id)} className="shrink-0 text-xs text-slate-400 hover:text-red-600">
                删
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="事项，如：字节一面"
          className={`${field} min-w-[160px] flex-1`}
        />
        <input type="time" value={start} onChange={(e) => setStart(e.target.value)} className={field} />
        <span className="text-xs text-slate-400">至</span>
        <input type="time" value={end} onChange={(e) => setEnd(e.target.value)} className={field} />
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="备注（可选）"
          className={`${field} min-w-[120px] flex-1`}
        />
        <button
          onClick={add}
          disabled={busy || !title.trim()}
          className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-50"
        >
          添加
        </button>
      </div>
    </div>
  );
}
