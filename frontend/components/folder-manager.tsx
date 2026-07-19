"use client";

import { useCallback, useEffect, useState, type DragEvent } from "react";

import { AiImportPanel, ContentForm } from "@/components/content-manager";
import {
  adminCreateCategory,
  adminCreateCompany,
  adminDeleteCategory,
  adminDeleteContent,
  adminGetFolderTree,
  adminGetInterviewTree,
  adminListContent,
  adminReorderCategories,
  adminUpdateCategory,
  adminUpdateContent,
  getAccessToken,
  INTERVIEW_TYPE_LABEL,
  type ContentSummary,
  type ContentType,
  type FolderItem,
  type FolderNode,
  type InterviewCompanyNode,
} from "@/lib/api";

// 面经四类子文件夹固定展示，顺序：日常实习 / 暑期实习 / 校招 / 社招。
const INTERVIEW_TYPE_FOLDERS = ["daily", "summer", "campus", "social"] as const;

type Section = ContentType;

const SECTION_TABS: { value: Section; label: string }[] = [
  { value: "knowledge", label: "八股" },
  { value: "sql", label: "SQL" },
  { value: "interview", label: "面经" },
  { value: "project", label: "项目" },
];

// 有分类（文件夹）的板块：内容可归到文件夹里。面经/项目没有分类，以文件列表呈现。
const HAS_FOLDERS: Record<Section, boolean> = {
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
  id: number | null;
  mode: DropMode;
}
type Dialog =
  | { mode: "new"; presetCat: number | null; presetCompany?: string; presetType?: string }
  | { mode: "edit"; editingId: number };

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
  if (targetId !== null && desc.has(targetId)) return flats;

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
      return {
        ...f,
        parent_id: f.id === dragId ? newParent : f.parent_id,
        order: orderOf.get(f.id)!,
      };
    }
    return f;
  });
}

const STATUS_BADGE = (status: string) =>
  status === "published" ? "bg-green-100 text-green-700" : "bg-slate-200 text-slate-600";

export function FolderManager() {
  const [section, setSection] = useState<Section>("knowledge");
  const [flats, setFlats] = useState<Flat[]>([]);
  const [files, setFiles] = useState<Map<number, FolderItem[]>>(new Map());
  const [uncategorized, setUncategorized] = useState<FolderItem[]>([]);
  const [flatFiles, setFlatFiles] = useState<ContentSummary[]>([]);
  const [interviewTree, setInterviewTree] = useState<InterviewCompanyNode[]>([]);
  const [expandedCo, setExpandedCo] = useState<Set<number>>(new Set());
  const [expandedType, setExpandedType] = useState<Set<string>>(new Set());
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [addingParent, setAddingParent] = useState<number | "root" | null>(null);
  const [addName, setAddName] = useState("");

  const [dragging, setDragging] = useState<DragPayload | null>(null);
  const [hint, setHint] = useState<DropHint | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);

  const withFolders = HAS_FOLDERS[section];

  const load = useCallback((s: Section) => {
    const token = getAccessToken();
    if (!token) return;
    if (HAS_FOLDERS[s]) {
      adminGetFolderTree(token, s)
        .then((tree) => {
          const { flats: fl, files: fm } = flatten(tree.roots);
          setFlats(fl);
          setFiles(fm);
          setUncategorized(tree.uncategorized ?? []);
          setExpanded(new Set(fl.map((f) => f.id)));
        })
        .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
    } else if (s === "interview") {
      adminGetInterviewTree(token)
        .then(setInterviewTree)
        .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
    } else {
      adminListContent(token, s)
        .then(setFlatFiles)
        .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
    }
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

  // ---- 文件（内容）操作 ----
  async function toggleFileStatus(id: number, status: string) {
    const token = getAccessToken();
    if (!token) return;
    const next = status === "published" ? "draft" : "published";
    await adminUpdateContent(token, section, id, { status: next });
    load(section);
  }

  async function deleteFile(id: number) {
    if (!window.confirm("确认删除该内容？此操作不可恢复。")) return;
    const token = getAccessToken();
    if (!token) return;
    await adminDeleteContent(token, section, id);
    load(section);
  }

  function closeDialogAndReload() {
    setDialog(null);
    load(section);
  }

  function toggleSet<T>(setter: (fn: (prev: Set<T>) => Set<T>) => void, key: T) {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  async function addCompany() {
    const name = window.prompt("新建公司名称：");
    if (!name || !name.trim()) return;
    const token = getAccessToken();
    if (!token) return;
    try {
      await adminCreateCompany(token, name.trim());
      load("interview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "新建公司失败");
    }
  }

  function renderInterviewTree() {
    if (interviewTree.length === 0) {
      return (
        <p className="py-4 text-center text-sm text-slate-400">
          还没有公司，点右上角「+ 新建公司」或「+ 添加文件」开始。
        </p>
      );
    }
    return interviewTree.map((co) => {
      const coOpen = expandedCo.has(co.id);
      const known = new Set<string>(INTERVIEW_TYPE_FOLDERS);
      const others = co.posts.filter((p) => !p.interview_type || !known.has(p.interview_type));
      return (
        <div key={co.id}>
          <div
            className="group flex items-center gap-1 rounded py-1 pr-2 text-sm hover:bg-slate-50"
            style={{ paddingLeft: "4px" }}
          >
            <button
              onClick={() => toggleSet(setExpandedCo, co.id)}
              className="w-4 shrink-0 text-xs text-slate-400"
              aria-label="展开/折叠"
            >
              {coOpen ? "▾" : "▸"}
            </button>
            <span className="text-base">🏢</span>
            <span className="flex-1 truncate font-medium text-slate-800">{co.name}</span>
            <span className="text-xs text-slate-400">{co.posts.length} 篇</span>
            <span className="ml-2 hidden shrink-0 gap-2 text-xs group-hover:flex">
              <button
                onClick={() => {
                  setExpandedCo((p) => new Set(p).add(co.id));
                  setDialog({ mode: "new", presetCat: null, presetCompany: co.name });
                }}
                className="text-green-600 hover:underline"
              >
                ＋面经
              </button>
            </span>
          </div>

          {coOpen && (
            <div>
              {INTERVIEW_TYPE_FOLDERS.map((t) => {
                const key = `${co.id}:${t}`;
                const typeOpen = expandedType.has(key);
                const posts = co.posts.filter((p) => p.interview_type === t);
                return (
                  <div key={key}>
                    <div
                      className="group flex items-center gap-1 rounded py-1 pr-2 text-sm hover:bg-slate-50"
                      style={{ paddingLeft: "22px" }}
                    >
                      <button
                        onClick={() => toggleSet(setExpandedType, key)}
                        className="w-4 shrink-0 text-xs text-slate-400"
                        aria-label="展开/折叠"
                      >
                        {posts.length ? (typeOpen ? "▾" : "▸") : "·"}
                      </button>
                      <span>📁</span>
                      <span className="flex-1 truncate text-slate-700">
                        {INTERVIEW_TYPE_LABEL[t] ?? t}
                      </span>
                      <span className="text-xs text-slate-400">{posts.length}</span>
                      <span className="ml-2 hidden shrink-0 text-xs group-hover:flex">
                        <button
                          onClick={() => {
                            setExpandedType((p) => new Set(p).add(key));
                            setDialog({
                              mode: "new",
                              presetCat: null,
                              presetCompany: co.name,
                              presetType: t,
                            });
                          }}
                          className="text-green-600 hover:underline"
                        >
                          ＋新建面经
                        </button>
                      </span>
                    </div>
                    {typeOpen &&
                      posts.map((p) =>
                        fileRow(
                          { id: p.id, title: p.label, status: p.status },
                          { draggable: false, paddingLeft: 46 },
                        ),
                      )}
                  </div>
                );
              })}
              {others.length > 0 && (
                <div>
                  <div
                    className="flex items-center gap-1 py-1 text-sm text-slate-400"
                    style={{ paddingLeft: "22px" }}
                  >
                    <span className="w-4" />📁 其他 / 未标类型（{others.length}）
                  </div>
                  {others.map((p) =>
                    fileRow(
                      { id: p.id, title: p.label, status: p.status },
                      { draggable: false, paddingLeft: 46 },
                    ),
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      );
    });
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
    const mode: DropMode =
      y < rect.height * 0.3 ? "before" : y > rect.height * 0.7 ? "after" : "inside";
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

  function fileRow(
    f: { id: number; title: string; status: string },
    opts: { draggable: boolean; paddingLeft: number },
  ) {
    return (
      <div
        key={`file-${f.id}`}
        draggable={opts.draggable}
        onDragStart={opts.draggable ? () => setDragging({ kind: "file", id: f.id }) : undefined}
        onDragEnd={opts.draggable ? () => setDragging(null) : undefined}
        style={{ paddingLeft: `${opts.paddingLeft}px` }}
        className={`group flex items-center gap-2 rounded py-1 pr-2 text-sm hover:bg-slate-50 ${
          opts.draggable ? "cursor-grab" : ""
        }`}
      >
        <span>📄</span>
        <span className="flex-1 truncate text-slate-700">{f.title}</span>
        <span className={`rounded px-1.5 py-0.5 text-xs ${STATUS_BADGE(f.status)}`}>
          {f.status === "published" ? "已发布" : "草稿"}
        </span>
        <span className="ml-1 hidden shrink-0 gap-2 text-xs group-hover:flex">
          <button
            onClick={() => setDialog({ mode: "edit", editingId: f.id })}
            className="text-brand-600 hover:underline"
          >
            编辑
          </button>
          <button
            onClick={() => toggleFileStatus(f.id, f.status)}
            className="text-slate-500 hover:underline"
          >
            {f.status === "published" ? "下架" : "上架"}
          </button>
          <button onClick={() => deleteFile(f.id)} className="text-red-500 hover:underline">
            删除
          </button>
        </span>
      </div>
    );
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
            hinted && hint?.mode === "inside"
              ? "bg-brand-100 ring-1 ring-brand-400"
              : "hover:bg-slate-50"
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
                setExpanded((p) => new Set(p).add(node.id));
                setDialog({ mode: "new", presetCat: node.id });
              }}
              className="text-green-600 hover:underline"
            >
              ＋文件
            </button>
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
            {nodeFiles.map((f) => fileRow(f, { draggable: true, paddingLeft: (depth + 1) * 18 + 24 }))}
          </div>
        )}
      </div>
    );
  }

  const roots = cm.get(null) ?? [];
  const dialogTitle =
    dialog?.mode === "edit" ? "编辑内容" : `添加${SECTION_TABS.find((t) => t.value === section)?.label}`;

  return (
    <div className="mt-10">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">目录管理</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setDialog({ mode: "new", presetCat: null })}
            className="rounded-lg bg-green-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-green-700"
          >
            + 添加文件
          </button>
          {withFolders && (
            <button
              onClick={() => {
                setAddingParent("root");
                setAddName("");
              }}
              className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              + 新建顶层文件夹
            </button>
          )}
          {section === "interview" && (
            <button
              onClick={addCompany}
              className="rounded-lg bg-brand-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-brand-700"
            >
              + 新建公司
            </button>
          )}
        </div>
      </div>

      <p className="mb-3 text-xs text-slate-500">
        {withFolders
          ? "像管理文件夹一样：拖拽文件夹移动/改变层级（中间=放入其中，上/下沿=同级排序）；把内容（📄）拖进文件夹即归类；双击名称可重命名。悬停文件可编辑/下架/删除。"
          : section === "interview"
            ? "公司=文件夹，日常实习/暑期实习/校招/社招=固定子文件夹，每篇面经=一个文件。在某类型下「＋新建面经」即新增一次面经；悬停文件可编辑/下架/删除。"
            : "该板块无需分类，直接以文件列表管理。「添加文件」可 AI 解析或手动录入；悬停文件可编辑/下架/删除。"}
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

      {withFolders ? (
        <>
          <div className="rounded-xl border border-slate-200 bg-white p-3">
            <div
              onDragOver={(e) => {
                if (dragging) e.preventDefault();
              }}
              onDrop={onRootDrop}
              className={`mb-1 rounded border border-dashed px-3 py-1.5 text-center text-xs ${
                dragging
                  ? "border-brand-400 bg-brand-50 text-brand-600"
                  : "border-slate-200 text-slate-400"
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

          {uncategorized.length > 0 && (
            <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50/50 p-3">
              <p className="mb-2 text-sm font-medium text-amber-800">
                未分类（{uncategorized.length}）— 拖进上面的文件夹即可归类
              </p>
              <div className="space-y-0.5">
                {uncategorized.map((f) => fileRow(f, { draggable: true, paddingLeft: 8 }))}
              </div>
            </div>
          )}
        </>
      ) : section === "interview" ? (
        <div className="rounded-xl border border-slate-200 bg-white p-3">{renderInterviewTree()}</div>
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-3">
          {flatFiles.length === 0 ? (
            <p className="py-4 text-center text-sm text-slate-400">
              该板块暂无内容，点右上角「+ 添加文件」开始。
            </p>
          ) : (
            <div className="space-y-0.5">
              {flatFiles.map((f) => fileRow(f, { draggable: false, paddingLeft: 8 }))}
            </div>
          )}
        </div>
      )}

      {dialog && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-auto bg-black/40 p-4">
          <div className="my-8 w-full max-w-2xl rounded-xl bg-white p-5 shadow-xl">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900">{dialogTitle}</h3>
              <button
                onClick={() => setDialog(null)}
                className="text-sm text-slate-400 hover:text-slate-700"
              >
                ✕ 关闭
              </button>
            </div>

            {dialog.mode === "new" ? (
              <>
                <AiImportPanel
                  type={section}
                  presetCategoryId={dialog.presetCat}
                  presetCompanyName={dialog.presetCompany}
                  presetInterviewType={dialog.presetType}
                  onDone={closeDialogAndReload}
                />
                <div className="my-4 flex items-center gap-3 text-xs text-slate-400">
                  <span className="h-px flex-1 bg-slate-200" />
                  或 手动新建单条
                  <span className="h-px flex-1 bg-slate-200" />
                </div>
                <ContentForm
                  type={section}
                  editingId={null}
                  presetCategoryId={dialog.presetCat}
                  presetCompanyName={dialog.presetCompany}
                  presetInterviewType={dialog.presetType}
                  onSaved={closeDialogAndReload}
                  onCancel={() => setDialog(null)}
                />
              </>
            ) : (
              <ContentForm
                type={section}
                editingId={dialog.editingId}
                onSaved={closeDialogAndReload}
                onCancel={() => setDialog(null)}
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
