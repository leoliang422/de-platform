"use client";

import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";

import { BackLink, ErrorText, Loading, PageHeader } from "@/components/content";
import { useAuth } from "@/lib/auth";
import {
  adminApproveNode,
  adminCreateTreeNode,
  adminDeleteTreeNode,
  adminGetKnowledgeTree,
  adminRejectNode,
  getAccessToken,
  getCategories,
  getKnowledgeTree,
  proposeTreeNode,
  type CategoryNode,
  type TreeNode,
} from "@/lib/api";

function flatten(nodes: CategoryNode[], acc: Record<number, string> = {}): Record<number, string> {
  for (const n of nodes) {
    acc[n.id] = n.name;
    if (n.children.length) flatten(n.children, acc);
  }
  return acc;
}

export default function KnowledgeTreePage({
  params,
}: {
  params: Promise<{ categoryId: string }>;
}) {
  const { categoryId } = use(params);
  const catId = Number(categoryId);
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [tree, setTree] = useState<TreeNode[]>([]);
  const [catName, setCatName] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(() => {
    const token = getAccessToken();
    const p = isAdmin && token ? adminGetKnowledgeTree(token, catId) : getKnowledgeTree(catId);
    p.then(setTree)
      .catch(() => setError("无法加载知识树"))
      .finally(() => setLoading(false));
  }, [catId, isAdmin]);

  useEffect(() => {
    getCategories("knowledge")
      .then((cats) => setCatName(flatten(cats)[catId] ?? ""))
      .catch(() => {});
  }, [catId]);

  useEffect(() => {
    load();
  }, [load]);

  async function propose(parentId: number | null, title: string) {
    const token = getAccessToken();
    if (!token) {
      setNotice("请先登录后再提议知识点");
      return;
    }
    if (isAdmin) {
      await adminCreateTreeNode(token, { category_id: catId, parent_id: parentId, title });
      setNotice("已添加节点");
    } else {
      await proposeTreeNode(token, { category_id: catId, parent_id: parentId, title });
      setNotice("已提交，等待管理员审核后上线");
    }
    load();
  }

  async function approve(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await adminApproveNode(token, id);
    load();
  }

  async function reject(id: number) {
    const token = getAccessToken();
    if (!token) return;
    await adminRejectNode(token, id);
    load();
  }

  async function remove(id: number) {
    const token = getAccessToken();
    if (!token) return;
    if (!window.confirm("确认删除该节点及其所有子节点？")) return;
    await adminDeleteTreeNode(token, id);
    load();
  }

  return (
    <div>
      <BackLink href="/knowledge" label="返回八股" />
      <PageHeader
        title={`${catName || "分类"} · 知识树`}
        desc="点击节点旁的 + 在该位置提议新知识点，审核通过后上线；叶子节点可链接到对应八股"
      />

      {notice && (
        <p className="mb-4 rounded-lg bg-brand-50 px-3 py-2 text-sm text-brand-700">{notice}</p>
      )}

      {loading ? (
        <Loading />
      ) : error ? (
        <ErrorText message={error} />
      ) : (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          {tree.length === 0 && (
            <p className="mb-3 text-sm text-slate-400">该分类暂无知识树节点，添加第一个吧。</p>
          )}
          <NodeList
            nodes={tree}
            depth={0}
            isAdmin={isAdmin}
            onPropose={propose}
            onApprove={approve}
            onReject={reject}
            onDelete={remove}
          />
          <AddRow depth={0} isAdmin={isAdmin} onAdd={(title) => propose(null, title)} />
        </div>
      )}
    </div>
  );
}

function NodeList({
  nodes,
  depth,
  isAdmin,
  onPropose,
  onApprove,
  onReject,
  onDelete,
}: {
  nodes: TreeNode[];
  depth: number;
  isAdmin: boolean;
  onPropose: (parentId: number | null, title: string) => void;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <ul className="space-y-1">
      {nodes.map((n) => (
        <NodeRow
          key={n.id}
          node={n}
          depth={depth}
          isAdmin={isAdmin}
          onPropose={onPropose}
          onApprove={onApprove}
          onReject={onReject}
          onDelete={onDelete}
        />
      ))}
    </ul>
  );
}

function NodeRow({
  node,
  depth,
  isAdmin,
  onPropose,
  onApprove,
  onReject,
  onDelete,
}: {
  node: TreeNode;
  depth: number;
  isAdmin: boolean;
  onPropose: (parentId: number | null, title: string) => void;
  onApprove: (id: number) => void;
  onReject: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  const [addingChild, setAddingChild] = useState(false);
  const pending = node.status === "pending";

  return (
    <li>
      <div
        className="group flex items-center gap-2 rounded-md py-1.5 pr-2 hover:bg-slate-50"
        style={{ paddingLeft: `${depth * 20 + 8}px` }}
      >
        <span className="text-slate-300">{node.children.length > 0 ? "├─" : "└─"}</span>
        {node.knowledge_item_id ? (
          <Link
            href={`/knowledge/${node.knowledge_item_id}`}
            className="text-sm font-medium text-brand-700 hover:underline"
          >
            {node.title}
          </Link>
        ) : (
          <span className="text-sm font-medium text-slate-800">{node.title}</span>
        )}
        {node.knowledge_item_id && (
          <span className="rounded bg-brand-50 px-1.5 py-0.5 text-[10px] text-brand-600">
            链接八股
          </span>
        )}
        {pending && (
          <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] text-amber-700">
            待审核
          </span>
        )}

        <span className="ml-auto flex items-center gap-2 opacity-0 transition group-hover:opacity-100">
          <button
            onClick={() => setAddingChild((v) => !v)}
            title="在此节点下添加"
            className="text-xs text-brand-600 hover:underline"
          >
            + 子知识点
          </button>
          {isAdmin && pending && (
            <>
              <button onClick={() => onApprove(node.id)} className="text-xs text-green-600 hover:underline">
                通过
              </button>
              <button onClick={() => onReject(node.id)} className="text-xs text-red-500 hover:underline">
                驳回
              </button>
            </>
          )}
          {isAdmin && !pending && (
            <button onClick={() => onDelete(node.id)} className="text-xs text-red-400 hover:underline">
              删除
            </button>
          )}
        </span>
      </div>

      {addingChild && (
        <div style={{ paddingLeft: `${(depth + 1) * 20 + 8}px` }} className="py-1">
          <InlineAdd
            isAdmin={isAdmin}
            onAdd={(title) => {
              onPropose(node.id, title);
              setAddingChild(false);
            }}
            onCancel={() => setAddingChild(false)}
          />
        </div>
      )}

      {node.children.length > 0 && (
        <NodeList
          nodes={node.children}
          depth={depth + 1}
          isAdmin={isAdmin}
          onPropose={onPropose}
          onApprove={onApprove}
          onReject={onReject}
          onDelete={onDelete}
        />
      )}
    </li>
  );
}

function AddRow({
  depth,
  isAdmin,
  onAdd,
}: {
  depth: number;
  isAdmin: boolean;
  onAdd: (title: string) => void;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ paddingLeft: `${depth * 20 + 8}px` }} className="mt-2">
      {open ? (
        <InlineAdd
          isAdmin={isAdmin}
          onAdd={(title) => {
            onAdd(title);
            setOpen(false);
          }}
          onCancel={() => setOpen(false)}
        />
      ) : (
        <button
          onClick={() => setOpen(true)}
          className="rounded-lg border border-dashed border-slate-300 px-3 py-1.5 text-sm text-slate-500 hover:border-brand-400 hover:text-brand-600"
        >
          + 添加顶层知识点
        </button>
      )}
    </div>
  );
}

function InlineAdd({
  isAdmin,
  onAdd,
  onCancel,
}: {
  isAdmin: boolean;
  onAdd: (title: string) => void;
  onCancel: () => void;
}) {
  const [title, setTitle] = useState("");
  return (
    <div className="flex items-center gap-2">
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="知识点名称"
        className="w-56 rounded border border-slate-300 px-2 py-1 text-sm focus:border-brand-500 focus:outline-none"
        onKeyDown={(e) => {
          if (e.key === "Enter" && title.trim()) onAdd(title.trim());
          if (e.key === "Escape") onCancel();
        }}
      />
      <button
        onClick={() => title.trim() && onAdd(title.trim())}
        disabled={!title.trim()}
        className="rounded bg-brand-600 px-3 py-1 text-xs text-white hover:bg-brand-700 disabled:opacity-50"
      >
        {isAdmin ? "添加" : "提交审核"}
      </button>
      <button onClick={onCancel} className="text-xs text-slate-400 hover:underline">
        取消
      </button>
    </div>
  );
}
