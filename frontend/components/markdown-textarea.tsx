"use client";

import { Image } from "@tiptap/extension-image";
import { TableKit } from "@tiptap/extension-table";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import { StarterKit } from "@tiptap/starter-kit";
import { useEffect, useRef, useState } from "react";
import { Markdown } from "tiptap-markdown";

import { ApiError, getAccessToken, uploadImage } from "@/lib/api";

interface Props {
  value: string;
  onChange: (value: string) => void;
  rows?: number;
  required?: boolean;
  placeholder?: string;
  className?: string;
  hint?: boolean;
  toolbar?: boolean;
}

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

// tiptap-markdown 在 editor.storage.markdown 上挂了 getMarkdown，但类型未被 TS 感知，做窄化。
function getMarkdown(editor: Editor): string {
  const storage = editor.storage as { markdown?: { getMarkdown?: () => string } };
  return storage.markdown?.getMarkdown?.() ?? "";
}

interface BtnProps {
  editor: Editor;
  onImage: (files: File[]) => void;
}

function Toolbar({ editor, onImage }: BtnProps) {
  const fileRef = useRef<HTMLInputElement>(null);

  const btn = (
    active: boolean,
    label: string,
    run: () => void,
    title: string,
  ) => (
    <button
      key={label}
      type="button"
      title={title}
      onMouseDown={(e) => e.preventDefault()}
      onClick={run}
      className={`rounded border px-2 py-0.5 text-xs transition ${
        active
          ? "border-brand-400 bg-brand-50 text-brand-700"
          : "border-slate-200 bg-slate-50 text-slate-600 hover:border-brand-300 hover:bg-brand-50"
      }`}
    >
      {label}
    </button>
  );

  const c = () => editor.chain().focus();

  return (
    <div className="mb-1 flex flex-wrap gap-1">
      {btn(editor.isActive("bold"), "加粗", () => c().toggleBold().run(), "加粗")}
      {btn(editor.isActive("italic"), "斜体", () => c().toggleItalic().run(), "斜体")}
      {btn(editor.isActive("strike"), "删除线", () => c().toggleStrike().run(), "删除线")}
      {btn(
        editor.isActive("heading", { level: 2 }),
        "标题",
        () => c().toggleHeading({ level: 2 }).run(),
        "二级标题",
      )}
      {btn(
        editor.isActive("heading", { level: 3 }),
        "小标题",
        () => c().toggleHeading({ level: 3 }).run(),
        "三级标题",
      )}
      {btn(editor.isActive("bulletList"), "列表", () => c().toggleBulletList().run(), "无序列表")}
      {btn(
        editor.isActive("orderedList"),
        "有序",
        () => c().toggleOrderedList().run(),
        "有序列表",
      )}
      {btn(editor.isActive("blockquote"), "引用", () => c().toggleBlockquote().run(), "引用")}
      {btn(editor.isActive("codeBlock"), "代码块", () => c().toggleCodeBlock().run(), "代码块")}
      {btn(
        false,
        "表格",
        () => c().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
        "插入表格",
      )}
      {btn(
        editor.isActive("link"),
        "链接",
        () => {
          const prev = editor.getAttributes("link").href as string | undefined;
          const url = window.prompt("链接地址：", prev ?? "https://");
          if (url === null) return;
          if (url === "") {
            c().unsetLink().run();
            return;
          }
          c().extendMarkRange("link").setLink({ href: url }).run();
        },
        "插入/编辑链接",
      )}
      {btn(false, "图片", () => fileRef.current?.click(), "插入图片")}
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          e.target.value = "";
          if (files.length) onImage(files);
        }}
      />
    </div>
  );
}

// 真·所见即所得富文本编辑器（TipTap）：编辑区即最终呈现，底层以 Markdown 存储，
// 兼容既有内容与展示端 Prose。支持加粗/斜体/标题/列表/引用/代码块/表格/链接/图片。
export function MarkdownTextarea({
  value,
  onChange,
  rows = 6,
  required,
  placeholder,
  hint = true,
  toolbar = true,
}: Props) {
  const editorRef = useRef<Editor | null>(null);
  const lastEmitted = useRef<string>("\u0000");
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function uploadAndInsert(files: File[]) {
    const ed = editorRef.current;
    if (!ed) return;
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
        ed.chain().focus().setImage({ src: url, alt: f.name || "image" }).run();
      }
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : "图片上传失败");
    } finally {
      setUploading(false);
    }
  }

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({ link: { openOnClick: false } }),
      Image,
      TableKit,
      Markdown.configure({ html: false, transformPastedText: true, transformCopiedText: true }),
    ],
    content: value || "",
    editorProps: {
      attributes: {
        class: "px-3 py-2",
        style: `min-height:${rows * 1.7}rem`,
      },
      handlePaste: (_view, event) => {
        const imgs = collectImages(event.clipboardData?.items, event.clipboardData?.files);
        if (imgs.length > 0) {
          void uploadAndInsert(imgs);
          return true;
        }
        return false;
      },
      handleDrop: (_view, event) => {
        const dt = (event as DragEvent).dataTransfer;
        const imgs = collectImages(dt?.items, dt?.files);
        if (imgs.length > 0) {
          event.preventDefault();
          void uploadAndInsert(imgs);
          return true;
        }
        return false;
      },
    },
    onUpdate: ({ editor: ed }) => {
      const md = getMarkdown(ed);
      lastEmitted.current = md;
      onChange(md);
    },
  });

  editorRef.current = editor;

  // 外部 value 变化（初始化 / AI 生成填充）时同步；打字回写不触发以免光标跳动。
  useEffect(() => {
    if (!editor) return;
    if (value !== lastEmitted.current) {
      editor.commands.setContent(value || "");
      lastEmitted.current = value;
    }
  }, [value, editor]);

  const isEmpty = editor?.isEmpty ?? !value;

  return (
    <div>
      {toolbar && editor && <Toolbar editor={editor} onImage={uploadAndInsert} />}
      <div className="rich-editor relative rounded-lg border border-slate-300 focus-within:border-brand-500">
        <EditorContent editor={editor} />
        {isEmpty && placeholder && (
          <span className="pointer-events-none absolute left-3 top-2 text-sm text-slate-400">
            {placeholder}
          </span>
        )}
      </div>
      {/* 隐藏受控字段：让富文本也能参与原生表单的必填校验。 */}
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
          <span>支持粘贴 / 拖拽图片，工具栏可插入表格、链接、代码块等</span>
          {uploading && <span className="text-brand-600">图片上传中…</span>}
          {err && <span className="text-red-600">{err}</span>}
        </div>
      )}
    </div>
  );
}
