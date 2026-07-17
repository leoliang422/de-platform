from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interactions.models import (
    CONTENT_TYPES,
    REACTION_KINDS,
    Comment,
    ContentView,
    Reaction,
)
from app.modules.interactions.schemas import (
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
}


def _validate_type(content_type: str) -> None:
    if content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容类型不存在")


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

    async def toggle_reaction(self, user_id: int, ct: str, cid: int, kind: str) -> StatsOut:
        _validate_type(ct)
        if kind not in REACTION_KINDS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的操作")
        stmt = select(Reaction).where(
            Reaction.user_id == user_id,
            Reaction.content_type == ct,
            Reaction.content_id == cid,
            Reaction.kind == kind,
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing is not None:
            await self.db.delete(existing)
        else:
            self.db.add(Reaction(user_id=user_id, content_type=ct, content_id=cid, kind=kind))
        await self.db.commit()
        return await self.get_stats(ct, cid, user_id)

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

        # 回复他人评论时通知对方
        if parent is not None and parent.user_id != user.id:
            link = _CONTENT_PATH.get(ct)
            await NotificationService(self.db).notify(
                user_id=parent.user_id,
                type="comment",
                title="收到新回复",
                body=f"{user.nickname} 回复了你的评论：{body[:50]}",
                link=f"{link}/{cid}" if link else None,
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
            return post.position if post else None
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
