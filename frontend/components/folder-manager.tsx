"use client";

import { useCallback, useEffect, useState, type DragEvent } from "react";

import {
  adminCreateCategory,
  adminDeleteCategory,
  adminGetFolderTree,
  adminReorderCategories,
  adminUpdateCategory,
  adminUpdateContent,
  getAccessToken,
  type FolderItem,
  type FolderNode,
} from "@/lib/api";

type Section = "knowledge" | "sql" | "interview" | "project";

const SECTION_TABS: { value: Section; label: string }[] = [
  { value: "knowledge", label: "八股" },
  { value: "sql", label: "SQL" },
  { value: "interview", label: "面经" },
  { value: "project", label: "项目" },
];

// 是否支持把内容当"文件"放进文件夹（有 category_id 的板块）。
const HAS_FILES: Record<Section, boolean> = {
  knowledge: true,
  sql: true,
  interview: false,
  project: false,
};

interface Flat {
  id: number;
  name: string;
  parent_id: number | null;
  order: number;
}

type DropMode = "inside" | "before" | "after";
interface DragPayload {
  kind: "folder" | "file";
  id: number;
}
interface DropHint {
  id: number | null; // null = 根区域
  mode: DropMode;
}

function flatten(roots: FolderNode[]): { flats: Flat[]; files: Map<number, FolderItem[]> } {
  const flats: Flat[] = [];
  const files = new Map<number, FolderItem[]>();
  const walk = (nodes: FolderNode[], parent: number | null) => {
    nodes.forEach((n, i) => {
      flats.push({ id: n.id, name: n.name, parent_id: parent, order: n.order ?? i });
      files.set(n.id, n.items ?? []);
      walk(n.children ?? [], n.id);
    });
  };
  walk(roots, null);
  return { flats, files };
}

function childrenMap(flats: Flat[]): Map<number | null, Flat[]> {
  const m = new Map<number | null, Flat[]>();
  for (const f of flats) {
    const arr = m.get(f.parent_id) ?? [];
    arr.push(f);
    m.set(f.parent_id, arr);
  }
  for (const arr of m.values()) arr.sort((a, b) => a.order - b.order || a.id - b.id);
  return m;
}

function descendants(flats: Flat[], id: number): Set<number> {
  const cm = childrenMap(flats);
  const out = new Set<number>();
  const stack = [id];
  while (stack.length) {
    const cur = stack.pop()!;
    for (const c of cm.get(cur) ?? []) {
      out.add(c.id);
      stack.push(c.id);
    }
  }
  return out;
}

function computeMove(
  flats: Flat[],
  dragId: number,
  targetId: number | null,
  mode: DropMode,
): Flat[] {
  if (dragId === targetId) return flats;
  const desc = descendants(flats, dragId);
  if (targetId !== null && desc.has(targetId)) return flats; // 不能拖进自己的子孙

  const drag = flats.find((f) => f.id === dragId);
  if (!drag) return flats;

  let newParent: number | null;
  if (mode === "inside") {
    newParent = targetId;
  } else {
    const target = flats.find((f) => f.id === targetId);
    newParent = target ? target.parent_id : null;
  }

  const others = flats.filter((f) => f.id !== dragId);
  const movedDrag: Flat = { ...drag, parent_id: newParent };
  const siblings = others
    .filter((f) => f.parent_id === newParent)
    .sort((a, b) => a.order - b.order || a.id - b.id);

  let insertIdx = siblings.length;
  if (mode !== "inside") {
    const ti = siblings.findIndex((f) => f.id === targetId);
    insertIdx = ti < 0 ? siblings.length : mode === "before" ? ti : ti + 1;
  }
  siblings.splice(insertIdx, 0, movedDrag);

  const orderOf = new Map<number, number>();
  siblings.forEach((f, i) => orderOf.set(f.id, i));

  return [...others, movedDrag].map((f) => {
    if (orderOf.has(f.id)) {
      return { ...f, parent_id: f.id === dragId ? newParent : f.parent_id, order: orderOf.get(f.id)! };
    }
    return f;
  });
}

export function FolderManager() {
  const [section, setSection] = useState<Section>("knowledge");
  const [flats, setFlats] = useState<Flat[]>([]);
  const [files, setFiles] = useState<Map<number, FolderItem[]>>(new Map());
  const [uncategorized, setUncategorized] = useState<FolderItem[]>([]);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [addingParent, setAddingParent] = useState<number | "root" | null>(null);
  const [addName, setAddName] = useState("");

  const [dragging, setDragging] = useState<DragPayload | null>(null);
  const [hint, setHint] = useState<DropHint | null>(null);

  const load = useCallback((s: Section) => {
    const token = getAccessToken();
    if (!token) return;
    adminGetFolderTree(token, s)
      .then((tree) => {
        const { flats: fl, files: fm } = flatten(tree.roots);
        setFlats(fl);
        setFiles(fm);
        setUncategorized(tree.uncategorized ?? []);
        setExpanded(new Set(fl.map((f) => f.id)));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, []);

  useEffect(() => {
    load(section);
  }, [section, load]);

  const cm = childrenMap(flats);

  async function persistFolders(next: Flat[]) {
    setFlats(next);
    const token = getAccessToken();
    if (!token) return;
    try {
      await adminReorderCategories(
        token,
        section,
        next.map((f) => ({ id: f.id, parent_id: f.parent_id, order: f.order })),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "保存失败");
      load(section);
    }
  }

  async function moveFile(fileId: number, catId: number | null) {
    const token = getAccessToken();
    if (!token) return;
    // 本地乐观更新
    setFiles((prev) => {
      const next = new Map(prev);
      for (const [k, arr] of next) next.set(k, arr.filter((i) => i.id !== fileId));
      return next;
    });
    setUncategorized((prev) => prev.filter((i) => i.id !== fileId));
    try {
      await adminUpdateContent(token, section, fileId, { category_id: catId });
    } finally {
      load(section);
    }
  }

  function toggle(id: number) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function rename(id: number) {
    const name = editName.trim();
    setEditingId(null);
    if (!name) return;
    const token = getAccessToken();
    if (!token) return;
    setFlats((prev) => prev.map((f) => (f.id === id ? { ...f, name } : f)));
    try {
      await adminUpdateCategory(token, id, { name });
    } catch (e) {
      setError(e instanceof Error ? e.message : "重命名失败");
      load(section);
    }
  }

  async function addFolder(parent: number | null) {
    const name = addName.trim();
    setAddingParent(null);
    setAddName("");
    if (!name) return;
    const token = getAccessToken();
    if (!token) return;
    try {
      await adminCreateCategory(token, { section, name, parent_id: parent });
      load(section);
    } catch (e) {
      setError(e instanceof Error ? e.message : "新建失败");
    }
  }

  async function removeFolder(id: number) {
    const hasChildren = flats.some((f) => f.parent_id === id);
    const hasFiles = (files.get(id)?.length ?? 0) > 0;
    const warn =
      hasChildren || hasFiles
        ? "该文件夹下有子文件夹或内容，删除后子文件夹会一并删除、内容将变为未分类。确认删除？"
        : "确认删除该文件夹？";
    if (!window.confirm(warn)) return;
    const token = getAccessToken();
    if (!token) return;
    try {
      await adminDeleteCategory(token, id);
      load(section);
    } catch (e) {
      setError(e instanceof Error ? e.message : "删除失败");
    }
  }

  // ---- 拖拽 ----
  function onFolderDragOver(e: DragEvent, targetId: number) {
    if (!dragging) return;
    e.preventDefault();
    if (dragging.kind === "file") {
      setHint({ id: targetId, mode: "inside" });
      return;
    }
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const mode: DropMode = y < rect.height * 0.3 ? "before" : y > rect.height * 0.7 ? "after" : "inside";
    setHint({ id: targetId, mode });
  }

  function onFolderDrop(e: DragEvent, targetId: number) {
    e.preventDefault();
    const h = hint;
    setHint(null);
    const payload = dragging;
    setDragging(null);
    if (!payload || !h) return;
    if (payload.kind === "file") {
      moveFile(payload.id, targetId);
      return;
    }
    persistFolders(computeMove(flats, payload.id, targetId, h.mode));
  }

  function onRootDrop(e: DragEvent) {
    e.preventDefault();
    setHint(null);
    const payload = dragging;
    setDragging(null);
    if (!payload) return;
    if (payload.kind === "file") {
      moveFile(payload.id, null);
      return;
    }
    persistFolders(computeMove(flats, payload.id, null, "inside"));
  }

  function renderFolder(node: Flat, depth: number) {
    const children = cm.get(node.id) ?? [];
    const nodeFiles = files.get(node.id) ?? [];
    const isOpen = expanded.has(node.id);
    const hinted = hint?.id === node.id;
    return (
      <div key={node.id}>
        <div
          draggable={editingId !== node.id}
          onDragStart={() => setDragging({ kind: "folder", id: node.id })}
          onDragEnd={() => {
            setDragging(null);
            setHint(null);
          }}
          onDragOver={(e) => onFolderDragOver(e, node.id)}
          onDrop={(e) => onFolderDrop(e, node.id)}
          style={{ paddingLeft: `${depth * 18 + 4}px` }}
          className={`group flex items-center gap-1 rounded py-1 pr-2 text-sm ${
            hinted && hint?.mode === "inside" ? "bg-brand-100 ring-1 ring-brand-400" : "hover:bg-slate-50"
          } ${hinted && hint?.mode === "before" ? "border-t-2 border-brand-500" : ""} ${
            hinted && hint?.mode === "after" ? "border-b-2 border-brand-500" : ""
          }`}
        >
          <button
            onClick={() => toggle(node.id)}
            className="w-4 shrink-0 text-xs text-slate-400"
            aria-label="展开/折叠"
          >
            {children.length || nodeFiles.length ? (isOpen ? "▾" : "▸") : "·"}
          </button>
          <span className="cursor-grab select-none text-base">📁</span>
          {editingId === node.id ? (
            <input
              autoFocus
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => rename(node.id)}
              onKeyDown={(e) => {
                if (e.key === "Enter") rename(node.id);
                if (e.key === "Escape") setEditingId(null);
              }}
              className="rounded border border-brand-400 px-1 py-0.5 text-sm focus:outline-none"
            />
          ) : (
            <span
              className="flex-1 truncate font-medium text-slate-800"
              onDoubleClick={() => {
                setEditingId(node.id);
                setEditName(node.name);
              }}
              title="双击重命名"
            >
              {node.name}
            </span>
          )}
          <span className="ml-auto hidden shrink-0 gap-2 text-xs group-hover:flex">
            <button
              onClick={() => {
                setAddingParent(node.id);
                setAddName("");
                setExpanded((p) => new Set(p).add(node.id));
              }}
              className="text-brand-600 hover:underline"
            >
              ＋子文件夹
            </button>
            <button
              onClick={() => {
                setEditingId(node.id);
                setEditName(node.name);
              }}
              className="text-slate-500 hover:underline"
            >
              重命名
            </button>
            <button onClick={() => removeFolder(node.id)} className="text-red-500 hover:underline">
              删除
            </button>
          </span>
        </div>

        {isOpen && (
          <div>
            {addingParent === node.id && (
              <div style={{ paddingLeft: `${(depth + 1) * 18 + 24}px` }} className="py-1">
                <input
                  autoFocus
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  onBlur={() => addFolder(node.id)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") addFolder(node.id);
                    if (e.key === "Escape") setAddingParent(null);
                  }}
                  placeholder="新子文件夹名称，回车确认"
                  className="w-56 rounded border border-brand-400 px-2 py-1 text-sm focus:outline-none"
                />
              </div>
            )}
            {children.map((c) => renderFolder(c, depth + 1))}
            {HAS_FILES[section] &&
              nodeFiles.map((f) => (
                <div
                  key={`file-${f.id}`}
                  draggable
                  onDragStart={() => setDragging({ kind: "file", id: f.id })}
                  onDragEnd={() => setDragging(null)}
                  style={{ paddingLeft: `${(depth + 1) * 18 + 24}px` }}
                  className="flex cursor-grab items-center gap-2 py-0.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  <span>📄</span>
                  <span className="flex-1 truncate">{f.title}</span>
                  {f.status !== "published" && (
                    <span className="rounded bg-slate-200 px-1 text-xs text-slate-500">草稿</span>
                  )}
                </div>
              ))}
          </div>
        )}
      </div>
    );
  }

  const roots = cm.get(null) ?? [];

  return (
    <div className="mt-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">目录管理（文件夹式）</h2>
        <button
          onClick={() => {
            setAddingParent("root");
            setAddName("");
          }}
          className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
        >
          + 新建顶层文件夹
        </button>
      </div>

      <p className="mb-3 text-xs text-slate-500">
        像管理文件夹一样：拖拽文件夹可移动/改变层级（拖到中间=放入其中，拖到上/下沿=同级排序）；
        {HAS_FILES[section] ? "把内容（📄）拖进文件夹即归类；" : ""}双击名称可重命名。
      </p>

      <div className="mb-4 flex gap-2">
        {SECTION_TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setSection(t.value)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              section === t.value ? "bg-brand-600 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-red-600">{error}</p>}

      <div className="rounded-xl border border-slate-200 bg-white p-3">
        {/* 顶层拖放区 */}
        <div
          onDragOver={(e) => {
            if (dragging) e.preventDefault();
          }}
          onDrop={onRootDrop}
          className={`mb-1 rounded border border-dashed px-3 py-1.5 text-center text-xs ${
            dragging ? "border-brand-400 bg-brand-50 text-brand-600" : "border-slate-200 text-slate-400"
          }`}
        >
          拖到这里放到「顶层」
        </div>

        {addingParent === "root" && (
          <div className="py-1 pl-6">
            <input
              autoFocus
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
              onBlur={() => addFolder(null)}
              onKeyDown={(e) => {
                if (e.key === "Enter") addFolder(null);
                if (e.key === "Escape") setAddingParent(null);
              }}
              placeholder="新顶层文件夹名称，回车确认"
              className="w-56 rounded border border-brand-400 px-2 py-1 text-sm focus:outline-none"
            />
          </div>
        )}

        {roots.length === 0 && addingParent !== "root" ? (
          <p className="py-4 text-center text-sm text-slate-400">
            还没有文件夹，点右上角「+ 新建顶层文件夹」开始。
          </p>
        ) : (
          roots.map((r) => renderFolder(r, 0))
        )}
      </div>

      {HAS_FILES[section] && uncategorized.length > 0 && (
        <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/50 p-3">
          <p className="mb-2 text-sm font-medium text-amber-800">
            未分类（{uncategorized.length}）— 拖进上面的文件夹即可归类
          </p>
          <div className="space-y-0.5">
            {uncategorized.map((f) => (
              <div
                key={`unc-${f.id}`}
                draggable
                onDragStart={() => setDragging({ kind: "file", id: f.id })}
                onDragEnd={() => setDragging(null)}
                className="flex cursor-grab items-center gap-2 rounded px-2 py-0.5 text-sm text-slate-600 hover:bg-white"
              >
                <span>📄</span>
                <span className="flex-1 truncate">{f.title}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
