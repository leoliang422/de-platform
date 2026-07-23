from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.modules.interactions.schemas import (
    AnnotationCreate,
    AnnotationOut,
    AnnotationUpdate,
    CommentCreate,
    CommentOut,
    FavoriteItem,
    StatsOut,
    ViewOut,
)
from app.modules.interactions.service import InteractionService
from app.modules.users.models import User

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.get("/me/favorites", response_model=list[FavoriteItem])
async def my_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FavoriteItem]:
    return await InteractionService(db).list_favorites(current_user.id)


@router.get("/{content_type}/{content_id}", response_model=StatsOut)
async def get_stats(
    content_type: str,
    content_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> StatsOut:
    user_id = current_user.id if current_user else None
    return await InteractionService(db).get_stats(content_type, content_id, user_id)


@router.post("/{content_type}/{content_id}/like", response_model=StatsOut)
async def toggle_like(
    content_type: str,
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsOut:
    return await InteractionService(db).toggle_reaction(
        current_user, content_type, content_id, "like"
    )


@router.post("/{content_type}/{content_id}/favorite", response_model=StatsOut)
async def toggle_favorite(
    content_type: str,
    content_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsOut:
    return await InteractionService(db).toggle_reaction(
        current_user, content_type, content_id, "favorite"
    )


@router.post("/{content_type}/{content_id}/view", response_model=ViewOut)
async def add_view(
    content_type: str,
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> ViewOut:
    views = await InteractionService(db).add_view(content_type, content_id)
    return ViewOut(views=views)


@router.get("/{content_type}/{content_id}/comments", response_model=list[CommentOut])
async def list_comments(
    content_type: str,
    content_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[CommentOut]:
    return await InteractionService(db).list_comments(content_type, content_id)


@router.post(
    "/{content_type}/{content_id}/comments",
    response_model=CommentOut,
    status_code=201,
)
async def create_comment(
    content_type: str,
    content_id: int,
    data: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CommentOut:
    comment = await InteractionService(db).create_comment(
        current_user, content_type, content_id, data.body, data.parent_id
    )
    return CommentOut(
        id=comment.id,
        user_id=comment.user_id,
        author_nickname=current_user.nickname,
        author_avatar=current_user.avatar_url,
        parent_id=comment.parent_id,
        body=comment.body,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await InteractionService(db).delete_comment(current_user, comment_id)


@router.get("/{content_type}/{content_id}/annotations", response_model=list[AnnotationOut])
async def list_annotations(
    content_type: str,
    content_id: int,
    current_user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationOut]:
    # 批注为个人私有笔记，仅返回当前登录用户自己的。
    user_id = current_user.id if current_user else None
    return await InteractionService(db).list_annotations(content_type, content_id, user_id)


@router.post(
    "/{content_type}/{content_id}/annotations",
    response_model=AnnotationOut,
    status_code=201,
)
async def create_annotation(
    content_type: str,
    content_id: int,
    data: AnnotationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnotationOut:
    annotation = await InteractionService(db).create_annotation(
        current_user,
        content_type,
        content_id,
        data.body,
        data.parent_id,
        data.quote,
        data.anchor_offset,
    )
    return AnnotationOut(
        id=annotation.id,
        user_id=annotation.user_id,
        author_nickname=current_user.nickname,
        author_avatar=current_user.avatar_url,
        parent_id=annotation.parent_id,
        quote=annotation.quote or "",
        anchor_offset=annotation.anchor_offset or 0,
        body=annotation.body,
        created_at=annotation.created_at,
    )


@router.patch("/annotations/{annotation_id}", response_model=AnnotationOut)
async def update_annotation(
    annotation_id: int,
    data: AnnotationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AnnotationOut:
    annotation, author = await InteractionService(db).update_annotation(
        current_user, annotation_id, data.body
    )
    return AnnotationOut(
        id=annotation.id,
        user_id=annotation.user_id,
        author_nickname=author.nickname,
        author_avatar=author.avatar_url,
        parent_id=annotation.parent_id,
        quote=annotation.quote or "",
        anchor_offset=annotation.anchor_offset or 0,
        body=annotation.body,
        created_at=annotation.created_at,
    )


@router.delete("/annotations/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await InteractionService(db).delete_annotation(current_user, annotation_id)
