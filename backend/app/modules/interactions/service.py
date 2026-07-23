from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interactions.models import (
    CONTENT_TYPES,
    REACTION_KINDS,
    Annotation,
    Comment,
    ContentView,
    Reaction,
)
from app.modules.interactions.schemas import (
    AnnotationOut,
    CommentOut,
    FavoriteItem,
    StatsOut,
)
from app.modules.interview.models import InterviewPost
from app.modules.knowledge.models import KnowledgeItem
from app.modules.notifications.service import NotificationService
from app.modules.projects.models import Project
from app.modules.sql_bank.models import SqlQuestion
from app.modules.users.models import User

_CONTENT_PATH = {
    "knowledge": "/knowledge",
    "sql": "/sql",
    "project": "/projects",
    "interview": "/interview",
}


def _validate_type(content_type: str) -> None:
    if content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容类型不存在")


def _link_for(ct: str, cid: int) -> str | None:
    if ct == "interview":
        return "/interview"  # 卡片在企业页展开，暂指向面经入口
    base = _CONTENT_PATH.get(ct)
    return f"{base}/{cid}" if base else None


class InteractionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _count_reactions(self, ct: str, cid: int, kind: str) -> int:
        stmt = select(func.count()).where(
            Reaction.content_type == ct,
            Reaction.content_id == cid,
            Reaction.kind == kind,
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def _count_comments(self, ct: str, cid: int) -> int:
        stmt = select(func.count()).where(Comment.content_type == ct, Comment.content_id == cid)
        return int((await self.db.execute(stmt)).scalar_one())

    async def _has_reaction(self, user_id: int, ct: str, cid: int, kind: str) -> bool:
        stmt = select(Reaction.id).where(
            Reaction.user_id == user_id,
            Reaction.content_type == ct,
            Reaction.content_id == cid,
            Reaction.kind == kind,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def _get_views(self, ct: str, cid: int) -> int:
        stmt = select(ContentView.count).where(
            ContentView.content_type == ct, ContentView.content_id == cid
        )
        return int((await self.db.execute(stmt)).scalar_one_or_none() or 0)

    async def get_stats(self, ct: str, cid: int, user_id: int | None) -> StatsOut:
        _validate_type(ct)
        liked = favorited = False
        if user_id is not None:
            liked = await self._has_reaction(user_id, ct, cid, "like")
            favorited = await self._has_reaction(user_id, ct, cid, "favorite")
        return StatsOut(
            content_type=ct,
            content_id=cid,
            views=await self._get_views(ct, cid),
            likes=await self._count_reactions(ct, cid, "like"),
            favorites=await self._count_reactions(ct, cid, "favorite"),
            comments=await self._count_comments(ct, cid),
            liked=liked,
            favorited=favorited,
        )

    async def toggle_reaction(self, actor: User, ct: str, cid: int, kind: str) -> StatsOut:
        _validate_type(ct)
        if kind not in REACTION_KINDS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的操作")
        stmt = select(Reaction).where(
            Reaction.user_id == actor.id,
            Reaction.content_type == ct,
            Reaction.content_id == cid,
            Reaction.kind == kind,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            await self.db.delete(existing)
        else:
            self.db.add(Reaction(user_id=actor.id, content_type=ct, content_id=cid, kind=kind))
            # 仅新增（点赞/收藏）时通知内容作者
            await self._notify_owner(
                actor,
                ct,
                cid,
                type=kind,
                title="有人赞了你的内容" if kind == "like" else "有人收藏了你的内容",
                verb="赞了" if kind == "like" else "收藏了",
            )
        await self.db.commit()
        return await self.get_stats(ct, cid, actor.id)

    async def _owner_of(self, ct: str, cid: int) -> int | None:
        if ct == "knowledge":
            item = await self.db.get(KnowledgeItem, cid)
            return item.author_id if item else None
        if ct == "sql":
            q = await self.db.get(SqlQuestion, cid)
            return q.author_id if q else None
        if ct == "project":
            p = await self.db.get(Project, cid)
            return p.author_id if p else None
        if ct == "interview":
            post = await self.db.get(InterviewPost, cid)
            return post.author_id if post else None
        return None

    async def _notify_owner(
        self, actor: User, ct: str, cid: int, *, type: str, title: str, verb: str
    ) -> None:
        owner_id = await self._owner_of(ct, cid)
        if owner_id is None or owner_id == actor.id:
            return
        await NotificationService(self.db).notify(
            user_id=owner_id,
            type=type,
            title=title,
            body=f"{actor.nickname} {verb}你的内容",
            link=_link_for(ct, cid),
        )

    async def add_view(self, ct: str, cid: int) -> int:
        _validate_type(ct)
        stmt = select(ContentView).where(
            ContentView.content_type == ct, ContentView.content_id == cid
        )
        row = (await self.db.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = ContentView(content_type=ct, content_id=cid, count=1)
            self.db.add(row)
        else:
            row.count += 1
        await self.db.commit()
        return row.count

    async def list_comments(self, ct: str, cid: int) -> list[CommentOut]:
        _validate_type(ct)
        stmt = (
            select(Comment, User)
            .join(User, User.id == Comment.user_id)
            .where(Comment.content_type == ct, Comment.content_id == cid)
            .order_by(Comment.id.asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            CommentOut(
                id=c.id,
                user_id=c.user_id,
                author_nickname=u.nickname,
                author_avatar=u.avatar_url,
                parent_id=c.parent_id,
                body=c.body,
                created_at=c.created_at,
            )
            for c, u in rows
        ]

    async def create_comment(
        self, user: User, ct: str, cid: int, body: str, parent_id: int | None
    ) -> Comment:
        _validate_type(ct)
        parent: Comment | None = None
        if parent_id is not None:
            parent = await self.db.get(Comment, parent_id)
            if parent is None or parent.content_type != ct or parent.content_id != cid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="回复的评论不存在"
                )
        comment = Comment(
            user_id=user.id,
            content_type=ct,
            content_id=cid,
            parent_id=parent_id,
            body=body,
        )
        self.db.add(comment)
        await self.db.flush()

        notifier = NotificationService(self.db)
        link = _link_for(ct, cid)
        notified: set[int] = {user.id}

        # 回复他人评论时通知对方
        if parent is not None and parent.user_id not in notified:
            await notifier.notify(
                user_id=parent.user_id,
                type="comment",
                title="收到新回复",
                body=f"{user.nickname} 回复了你的评论：{body[:50]}",
                link=link,
            )
            notified.add(parent.user_id)

        # 通知内容作者（卡片主人）
        owner_id = await self._owner_of(ct, cid)
        if owner_id is not None and owner_id not in notified:
            await notifier.notify(
                user_id=owner_id,
                type="comment",
                title="有人评论了你的内容",
                body=f"{user.nickname} 评论：{body[:50]}",
                link=link,
            )

        await self.db.commit()
        await self.db.refresh(comment)
        return comment

    async def delete_comment(self, user: User, comment_id: int) -> None:
        comment = await self.db.get(Comment, comment_id)
        if comment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
        if user.role != "admin" and comment.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除")
        await self.db.delete(comment)
        await self.db.commit()

    # ---- 划词批注（无需审核、全员可见、可回复/删除） ----

    async def list_annotations(self, ct: str, cid: int, user_id: int | None) -> list[AnnotationOut]:
        _validate_type(ct)
        # 批注为「个人笔记」，仅本人可见；未登录返回空。
        if user_id is None:
            return []
        stmt = (
            select(Annotation, User)
            .join(User, User.id == Annotation.user_id)
            .where(
                Annotation.content_type == ct,
                Annotation.content_id == cid,
                Annotation.user_id == user_id,
            )
            .order_by(Annotation.id.asc())
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            AnnotationOut(
                id=a.id,
                user_id=a.user_id,
                author_nickname=u.nickname,
                author_avatar=u.avatar_url,
                parent_id=a.parent_id,
                quote=a.quote or "",
                anchor_offset=a.anchor_offset or 0,
                body=a.body,
                created_at=a.created_at,
            )
            for a, u in rows
        ]

    async def create_annotation(
        self,
        user: User,
        ct: str,
        cid: int,
        body: str,
        parent_id: int | None,
        quote: str = "",
        anchor_offset: int = 0,
    ) -> Annotation:
        _validate_type(ct)
        parent: Annotation | None = None
        if parent_id is not None:
            parent = await self.db.get(Annotation, parent_id)
            if (
                parent is None
                or parent.content_type != ct
                or parent.content_id != cid
                or parent.user_id != user.id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="回复的批注不存在"
                )
        annotation = Annotation(
            user_id=user.id,
            content_type=ct,
            content_id=cid,
            parent_id=parent_id,
            quote=quote if parent_id is None else "",
            anchor_offset=anchor_offset if parent_id is None else 0,
            body=body,
        )
        self.db.add(annotation)
        # 批注为个人私有笔记，仅本人可见，不产生任何通知。
        await self.db.commit()
        await self.db.refresh(annotation)
        return annotation

    async def update_annotation(
        self, user: User, annotation_id: int, body: str
    ) -> tuple[Annotation, User]:
        annotation = await self.db.get(Annotation, annotation_id)
        if annotation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="笔记不存在")
        if annotation.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权修改")
        annotation.body = body
        await self.db.commit()
        await self.db.refresh(annotation)
        return annotation, user

    async def delete_annotation(self, user: User, annotation_id: int) -> None:
        annotation = await self.db.get(Annotation, annotation_id)
        if annotation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="批注不存在")
        if user.role != "admin" and annotation.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除")
        await self.db.delete(annotation)
        await self.db.commit()

    async def _title_for(self, ct: str, cid: int) -> str | None:
        if ct == "knowledge":
            item = await self.db.get(KnowledgeItem, cid)
            return item.title if item else None
        if ct == "sql":
            q = await self.db.get(SqlQuestion, cid)
            return q.title if q else None
        if ct == "project":
            p = await self.db.get(Project, cid)
            return p.title if p else None
        if ct == "interview":
            post = await self.db.get(InterviewPost, cid)
            return post.title if post else None
        return None

    async def list_favorites(self, user_id: int) -> list[FavoriteItem]:
        stmt = (
            select(Reaction)
            .where(Reaction.user_id == user_id, Reaction.kind == "favorite")
            .order_by(Reaction.id.desc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        items: list[FavoriteItem] = []
        for r in rows:
            title = await self._title_for(r.content_type, r.content_id)
            if title is None:
                continue  # 内容已删除
            items.append(
                FavoriteItem(
                    content_type=r.content_type,
                    content_id=r.content_id,
                    title=title,
                    created_at=r.created_at,
                )
            )
        return items


# 热度权重：浏览 1、点赞 3、收藏 5。
HOTNESS_WEIGHTS = {"views": 1, "likes": 3, "favorites": 5}


class ContentStats:
    __slots__ = ("views", "likes", "favorites", "comments")

    def __init__(self, views: int = 0, likes: int = 0, favorites: int = 0, comments: int = 0):
        self.views = views
        self.likes = likes
        self.favorites = favorites
        self.comments = comments

    @property
    def hotness(self) -> int:
        return (
            self.views * HOTNESS_WEIGHTS["views"]
            + self.likes * HOTNESS_WEIGHTS["likes"]
            + self.favorites * HOTNESS_WEIGHTS["favorites"]
        )


async def bulk_content_stats(db: AsyncSession, ct: str, ids: list[int]) -> dict[int, ContentStats]:
    """批量取一组内容的浏览/点赞/收藏/评论数，用于列表热度排序。"""
    result: dict[int, ContentStats] = {i: ContentStats() for i in ids}
    if not ids:
        return result

    views = await db.execute(
        select(ContentView.content_id, ContentView.count).where(
            ContentView.content_type == ct, ContentView.content_id.in_(ids)
        )
    )
    for cid, count in views.all():
        result[cid].views = int(count or 0)

    reactions = await db.execute(
        select(Reaction.content_id, Reaction.kind, func.count())
        .where(Reaction.content_type == ct, Reaction.content_id.in_(ids))
        .group_by(Reaction.content_id, Reaction.kind)
    )
    for cid, kind, count in reactions.all():
        if kind == "like":
            result[cid].likes = int(count)
        elif kind == "favorite":
            result[cid].favorites = int(count)

    comments = await db.execute(
        select(Comment.content_id, func.count())
        .where(Comment.content_type == ct, Comment.content_id.in_(ids))
        .group_by(Comment.content_id)
    )
    for cid, count in comments.all():
        result[cid].comments = int(count)

    return result
