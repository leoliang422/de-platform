from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.messages.models import ContactMessage, ConversationState
from app.modules.messages.schemas import ConversationOut, SendMessageIn
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User


def _preview(msg: ContactMessage) -> str:
    """会话列表里的最后一条预览文案（附件消息给出占位）。"""
    if msg.body.strip():
        return msg.body
    if msg.attachment_kind == "image":
        return "[图片]"
    if msg.attachment_url:
        return f"[文件] {msg.attachment_name or ''}".strip()
    return ""


class ContactMessageService:
    """用户 ↔ 管理员私信业务逻辑。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ---- 用户侧 ----
    async def list_for_user(self, user_id: int) -> list[ContactMessage]:
        result = await self.db.execute(
            select(ContactMessage)
            .where(ContactMessage.user_id == user_id)
            .order_by(ContactMessage.created_at, ContactMessage.id)
        )
        msgs = list(result.scalars().all())
        # 打开会话即把管理员发来的未读标记为已读。
        await self._mark_read(user_id, from_admin=True)
        return msgs

    async def user_unread_count(self, user_id: int) -> int:
        count = await self.db.scalar(
            select(func.count(ContactMessage.id)).where(
                ContactMessage.user_id == user_id,
                ContactMessage.from_admin.is_(True),
                ContactMessage.read_at.is_(None),
            )
        )
        return int(count or 0)

    async def send_from_user(self, user_id: int, data: SendMessageIn) -> ContactMessage:
        state = await self.db.get(ConversationState, user_id)
        if state is not None and state.blocked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="你已被管理员屏蔽，暂时无法发送私信"
            )
        msg = ContactMessage(
            user_id=user_id,
            from_admin=False,
            sender_id=user_id,
            body=data.body.strip(),
            attachment_url=data.attachment_url,
            attachment_name=data.attachment_name,
            attachment_kind=data.attachment_kind,
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def delete_message(
        self, message_id: int, *, requester_id: int, is_admin: bool
    ) -> None:
        """删除单条私信。管理员可删会话内任意消息；普通用户仅能撤回自己发出的消息。"""
        msg = await self.db.get(ContactMessage, message_id)
        if msg is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
        if not is_admin and (msg.user_id != requester_id or msg.from_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权删除该消息")
        await self.db.delete(msg)
        await self.db.commit()

    # ---- 管理员侧 ----
    async def list_conversations(self) -> list[ConversationOut]:
        # 取每个会话的最后一条消息时间与未读数，联表用户信息。
        result = await self.db.execute(
            select(ContactMessage).order_by(
                ContactMessage.created_at.desc(), ContactMessage.id.desc()
            )
        )
        msgs = list(result.scalars().all())

        last_by_user: dict[int, ContactMessage] = {}
        unread_by_user: dict[int, int] = {}
        for m in msgs:
            if m.user_id not in last_by_user:
                last_by_user[m.user_id] = m  # 已按时间倒序，首个即最新
            if not m.from_admin and m.read_at is None:
                unread_by_user[m.user_id] = unread_by_user.get(m.user_id, 0) + 1

        # 会话状态（置顶/屏蔽）：即使会话被清空、无消息，只要有状态也应保留在列表里。
        states = {
            s.user_id: s
            for s in (await self.db.execute(select(ConversationState))).scalars().all()
        }
        user_ids = set(last_by_user) | set(states)
        if not user_ids:
            return []

        users = {
            u.id: u
            for u in (await self.db.execute(select(User).where(User.id.in_(user_ids))))
            .scalars()
            .all()
        }
        out: list[ConversationOut] = []
        for uid in user_ids:
            user = users.get(uid)
            last = last_by_user.get(uid)
            state = states.get(uid)
            out.append(
                ConversationOut(
                    user_id=uid,
                    nickname=user.nickname if user else f"用户#{uid}",
                    avatar_url=user.avatar_url if user else None,
                    last_body=_preview(last) if last else "",
                    last_at=last.created_at if last else (state.created_at if state else None),
                    unread=unread_by_user.get(uid, 0),
                    pinned=bool(state and state.pinned),
                    blocked=bool(state and state.blocked),
                )
            )
        # 置顶优先，再按最后活跃时间倒序。
        _epoch = dt.datetime.min.replace(tzinfo=dt.UTC)
        out.sort(key=lambda c: (c.pinned, c.last_at or _epoch), reverse=True)
        return out

    async def _get_or_create_state(self, user_id: int) -> ConversationState:
        state = await self.db.get(ConversationState, user_id)
        if state is None:
            state = ConversationState(user_id=user_id)
            self.db.add(state)
        return state

    async def set_state(
        self, user_id: int, *, pinned: bool | None = None, blocked: bool | None = None
    ) -> ConversationState:
        state = await self._get_or_create_state(user_id)
        if pinned is not None:
            state.pinned = pinned
        if blocked is not None:
            state.blocked = blocked
        await self.db.commit()
        await self.db.refresh(state)
        return state

    async def clear_conversation(self, user_id: int) -> None:
        """清空聊天：删除该会话全部消息，但保留会话（置顶/屏蔽状态不变）。"""
        await self.db.execute(
            delete(ContactMessage).where(ContactMessage.user_id == user_id)
        )
        await self.db.commit()

    async def delete_conversation(self, user_id: int) -> None:
        """删除聊天：删除全部消息并移除会话状态，会话从列表消失。"""
        await self.db.execute(
            delete(ContactMessage).where(ContactMessage.user_id == user_id)
        )
        await self.db.execute(
            delete(ConversationState).where(ConversationState.user_id == user_id)
        )
        await self.db.commit()

    async def admin_unread_total(self) -> int:
        count = await self.db.scalar(
            select(func.count(ContactMessage.id)).where(
                ContactMessage.from_admin.is_(False),
                ContactMessage.read_at.is_(None),
            )
        )
        return int(count or 0)

    async def list_for_conversation(self, user_id: int) -> list[ContactMessage]:
        result = await self.db.execute(
            select(ContactMessage)
            .where(ContactMessage.user_id == user_id)
            .order_by(ContactMessage.created_at, ContactMessage.id)
        )
        msgs = list(result.scalars().all())
        # 管理员打开会话，把用户发来的未读标记已读。
        await self._mark_read(user_id, from_admin=False)
        return msgs

    async def send_from_admin(
        self, user_id: int, admin_id: int, data: SendMessageIn
    ) -> ContactMessage:
        msg = ContactMessage(
            user_id=user_id,
            from_admin=True,
            sender_id=admin_id,
            body=data.body.strip(),
            attachment_url=data.attachment_url,
            attachment_name=data.attachment_name,
            attachment_kind=data.attachment_kind,
        )
        self.db.add(msg)
        # 给用户发一条站内通知，提示有管理员回复。
        await NotificationService(self.db).notify(
            user_id=user_id,
            type="message",
            title="管理员回复了你",
            body=_preview(msg)[:80],
            link="/contact",
        )
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    # ---- 内部 ----
    async def _mark_read(self, user_id: int, *, from_admin: bool) -> None:
        stmt = (
            update(ContactMessage)
            .where(
                ContactMessage.user_id == user_id,
                ContactMessage.from_admin.is_(from_admin),
                ContactMessage.read_at.is_(None),
            )
            .values(read_at=dt.datetime.now(dt.UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()
