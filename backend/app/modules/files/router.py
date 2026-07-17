from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.core.deps import get_current_user
from app.modules.files.storage import StorageNotConfigured, get_storage
from app.modules.users.models import User

router = APIRouter(prefix="/files", tags=["files"])

# 允许的图片类型 → 扩展名
IMAGE_TYPES: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
}
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
