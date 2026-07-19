"use client";

import { useRef, useState, type ClipboardEvent, type DragEvent } from "react";

import { Prose } from "@/components/content";
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

const IMG_MD_RE = /!\[[^\]]*\]\([^)\s]+\)/;

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

// 正文编辑器：原生 textarea（输入稳定、支持原生必填校验），
// 粘贴/拖拽图片自动上传并在光标处插入 Markdown，下方实时预览渲染成图片。
export function MarkdownTextarea({
  value,
  onChange,
  rows = 6,
  required,
  placeholder,
  className,
  hint = true,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  function insertAtCursor(snippet: string) {
    const el = ref.current;
    if (!el) {
      onChange(value + snippet);
      return;
    }
    const start = el.selectionStart ?? value.length;
    const end = el.selectionEnd ?? value.length;
    onChange(value.slice(0, start) + snippet + value.slice(end));
    // 等 React 写回后把光标移到插入内容之后。
    requestAnimationFrame(() => {
      const pos = start + snippet.length;
      el.focus();
      el.setSelectionRange(pos, pos);
    });
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
        insertAtCursor(`\n![${f.name || "image"}](${url})\n`);
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "图片上传失败");
    } finally {
      setUploading(false);
    }
  }

  async function onPaste(e: ClipboardEvent<HTMLTextAreaElement>) {
    const imgs = collectImages(e.clipboardData.items, e.clipboardData.files);
    if (imgs.length > 0) {
      e.preventDefault();
      await uploadAndInsert(imgs);
    }
  }

  async function onDrop(e: DragEvent<HTMLTextAreaElement>) {
    const imgs = collectImages(e.dataTransfer.items, e.dataTransfer.files);
    if (imgs.length > 0) {
      e.preventDefault();
      await uploadAndInsert(imgs);
    }
  }

  const hasImage = IMG_MD_RE.test(value);

  return (
    <div>
      <textarea
        ref={ref}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onPaste={onPaste}
        onDrop={onDrop}
        rows={rows}
        required={required}
        placeholder={placeholder}
        className={className}
      />
      {hint && (
        <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
          <span>支持直接粘贴 / 拖拽图片，自动上传并插入，下方可预览</span>
          {uploading && <span className="text-brand-600">图片上传中…</span>}
          {err && <span className="text-red-600">{err}</span>}
        </div>
      )}
      {hasImage && (
        <div className="mt-2">
          <p className="mb-1 text-xs text-slate-400">预览</p>
          <Prose>{value}</Prose>
        </div>
      )}
    </div>
  );
}
