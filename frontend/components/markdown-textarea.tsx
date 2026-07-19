"use client";

import {
  useEffect,
  useRef,
  useState,
  type ClipboardEvent,
  type DragEvent,
} from "react";

import { ApiError, getAccessToken, uploadImage } from "@/lib/api";

interface Props {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  required?: boolean;
  placeholder?: string;
  className?: string;
  hint?: boolean;
}

const IMG_CLASS =
  "my-1 inline-block max-h-64 max-w-full rounded-lg border border-slate-200 align-top";
const IMG_MD_RE = /!\[([^\]]*)\]\(([^)\s]+)\)/g;

function collectImages(
  items: DataTransferItemList | null | undefined,
  files: FileList | null | undefined,
): File[] {
  const out: File[] = [];
  if (items) {
    for (const it of Array.from(items)) {
      if (it.kind === "file" && it.type.startsWith("image/")) {
        const f = it.getAsFile();
        if (f) out.push(f);
      }
    }
  }
  if (out.length === 0 && files) {
    for (const f of Array.from(files)) {
      if (f.type.startsWith("image/")) out.push(f);
    }
  }
  return out;
}

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Markdown（含图片）→ 可编辑 HTML：图片渲染为 <img>，换行渲染为 <br>。
function mdToHtml(md: string): string {
  let html = "";
  let last = 0;
  for (const m of md.matchAll(IMG_MD_RE)) {
    const idx = m.index ?? 0;
    html += escapeHtml(md.slice(last, idx));
    html += `<img src="${m[2]}" alt="${escapeHtml(m[1])}" class="${IMG_CLASS}" />`;
    last = idx + m[0].length;
  }
  html += escapeHtml(md.slice(last));
  return html.replace(/\n/g, "<br>");
}

// 可编辑 HTML → Markdown：<img> 还原为 ![](url)，块级/换行还原为 \n。
function htmlToMd(node: Node): string {
  let out = "";
  node.childNodes.forEach((child) => {
    if (child.nodeType === Node.TEXT_NODE) {
      out += child.textContent ?? "";
    } else if (child instanceof HTMLImageElement) {
      out += `![${child.getAttribute("alt") || "image"}](${child.getAttribute("src") || ""})`;
    } else if (child instanceof HTMLBRElement) {
      out += "\n";
    } else if (child instanceof HTMLElement) {
      const block = /^(DIV|P)$/.test(child.tagName);
      if (block && out && !out.endsWith("\n")) out += "\n";
      out += htmlToMd(child);
      if (block && !out.endsWith("\n")) out += "\n";
    }
  });
  return out;
}

// 富文本正文编辑器：粘贴/拖拽图片直接以图片形式内联展示，底层仍以 Markdown 存储。
export function MarkdownTextarea({
  value,
  onChange,
  rows = 6,
  required,
  placeholder,
  className,
  hint = true,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const lastValue = useRef<string>("\u0000"); // 哨兵值，保证首次渲染必定写入
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [empty, setEmpty] = useState(!value);

  // 外部 value 变化（初始化 / AI 生成填充）时同步到编辑区；打字时不回写以免光标跳动。
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (value !== lastValue.current) {
      el.innerHTML = mdToHtml(value);
      lastValue.current = value;
      setEmpty(!value);
    }
  }, [value]);

  function emit() {
    const el = ref.current;
    if (!el) return;
    const md = htmlToMd(el);
    lastValue.current = md;
    setEmpty(!el.textContent && !el.querySelector("img"));
    onChange(md);
  }

  function insertImage(url: string, alt: string) {
    const el = ref.current;
    if (!el) return;
    const img = document.createElement("img");
    img.src = url;
    img.alt = alt;
    img.className = IMG_CLASS;
    const sel = window.getSelection();
    if (sel && sel.rangeCount > 0 && el.contains(sel.anchorNode)) {
      const range = sel.getRangeAt(0);
      range.deleteContents();
      range.insertNode(img);
      range.setStartAfter(img);
      range.collapse(true);
      sel.removeAllRanges();
      sel.addRange(range);
    } else {
      el.appendChild(img);
    }
    emit();
  }

  async function uploadAndInsert(files: File[]) {
    const token = getAccessToken();
    if (!token) {
      setErr("请先登录后再上传图片");
      return;
    }
    setUploading(true);
    setErr(null);
    try {
      for (const f of files) {
        const { url } = await uploadImage(token, f);
        insertImage(url, f.name || "image");
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "图片上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function onPaste(e: ClipboardEvent<HTMLDivElement>) {
    const imgs = collectImages(e.clipboardData.items, e.clipboardData.files);
    if (imgs.length > 0) {
      e.preventDefault();
      await uploadAndInsert(imgs);
      return;
    }
    // 纯文本粘贴：强制以纯文本插入，避免带入外部富文本结构。
    e.preventDefault();
    const text = e.clipboardData.getData("text/plain");
    document.execCommand("insertText", false, text);
  }

  async function onDrop(e: DragEvent<HTMLDivElement>) {
    const imgs = collectImages(e.dataTransfer.items, e.dataTransfer.files);
    if (imgs.length === 0) return;
    e.preventDefault();
    await uploadAndInsert(imgs);
  }

  return (
    <div>
      <div className="relative">
        <div
          ref={ref}
          contentEditable
          suppressContentEditableWarning
          role="textbox"
          aria-multiline="true"
          onInput={emit}
          onBlur={emit}
          onPaste={onPaste}
          onDrop={onDrop}
          style={{ minHeight: `${rows * 1.6}rem` }}
          className={`${className ?? ""} overflow-auto whitespace-pre-wrap break-words`}
        />
        {empty && placeholder && (
          <span className="pointer-events-none absolute left-3 top-2 text-sm text-slate-400">
            {placeholder}
          </span>
        )}
      </div>
      {/* 隐藏受控字段：让 contentEditable 也能参与原生表单的必填校验。 */}
      {required && (
        <textarea
          value={value}
          onChange={() => {}}
          required
          tabIndex={-1}
          aria-hidden
          className="absolute h-px w-px border-0 p-0 opacity-0"
        />
      )}
      {hint && (
        <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
          <span>支持直接粘贴 / 拖拽图片，自动上传并以图片形式内嵌</span>
          {uploading && <span className="text-brand-600">图片上传中…</span>}
          {err && <span className="text-red-600">{err}</span>}
        </div>
      )}
    </div>
  );
}
