from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.core.deps import get_current_user
from app.modules.files.extract import (
    ALLOWED_TYPES,
    DOCUMENT_TYPES,
    IMAGE_TYPES,
    TEXT_TYPES,
    ExtractorNotConfigured,
    MockExtractor,
    get_extractor,
)
from app.modules.files.storage import StorageNotConfigured, get_storage
from app.modules.users.models import User

router = APIRouter(prefix="/files", tags=["files"])

# 允许的图片类型 → 扩展名（与 extract 模块共用同一张表）
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    ext = IMAGE_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="仅支持 PNG / JPEG / GIF / WEBP 图片",
        )
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="图片不能超过 5MB",
        )
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")

    storage = get_storage()
    try:
        key = await storage.save(data=data, ext=ext, content_type=file.content_type or "")
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc

    return {"url": storage.public_url(key, str(request.base_url))}


MAX_EXTRACT_BYTES = 10 * 1024 * 1024  # 10MB


@router.post("/extract", status_code=status.HTTP_201_CREATED)
async def extract_file(
    request: Request,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """解析本地文件为可插入投稿正文的 Markdown 片段。

    - 文本/Markdown/CSV/JSON：直接解码（真实可用）。
    - 图片：落盘后返回 Markdown 图片语法，前端可直接展示（真实可用）。
    - Word/PDF：落盘留存下载链接，解析交给大模型/文档服务（当前占位）。
    """
    content_type = file.content_type or ""
    ext = ALLOWED_TYPES.get(content_type)
    if ext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="暂不支持该文件类型，支持：文本/Markdown/CSV/JSON、Word/PDF、图片",
        )
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")
    if len(data) > MAX_EXTRACT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="文件不能超过 10MB",
        )
    filename = file.filename or f"upload{ext}"

    # 文本类：无需落盘，直接解码
    if content_type in TEXT_TYPES:
        text = data.decode("utf-8", errors="replace")
        return {
            "filename": filename,
            "kind": "text",
            "placeholder": False,
            "text": text,
            "url": None,
        }

    # 图片 / 文档：先落盘（图片可展示、文档留存下载链接）
    storage = get_storage()
    try:
        key = await storage.save(data=data, ext=ext, content_type=content_type)
    except StorageNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    url = storage.public_url(key, str(request.base_url))

    if content_type in IMAGE_TYPES:
        return {
            "filename": filename,
            "kind": "image",
            "placeholder": False,
            "text": f"![{filename}]({url})",
            "url": url,
        }

    # 文档（Word/PDF）：交给解析器（默认占位，链接到大模型的真实实现待接入）
    assert content_type in DOCUMENT_TYPES
    extractor = get_extractor()
    try:
        text = await extractor.extract(
            data=data, filename=filename, content_type=content_type, url=url
        )
        placeholder = extractor.name == "mock"
    except ExtractorNotConfigured:
        text = await MockExtractor().extract(
            data=data, filename=filename, content_type=content_type, url=url
        )
        placeholder = True
    return {
        "filename": filename,
        "kind": "document",
        "placeholder": placeholder,
        "text": text,
        "url": url,
    }
