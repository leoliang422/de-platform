from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.modules.messages.schemas import (
    ConversationOut,
    ConversationStateIn,
    ConversationStateOut,
    MessageOut,
    SendMessageIn,
    UnreadCountOut,
)
from app.modules.messages.service import ContactMessageService
from app.modules.users.models import User

# 用户侧：与管理员的私信会话。
router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=list[MessageOut])
async def my_messages(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    msgs = await ContactMessageService(db).list_for_user(current_user.id)
    return [MessageOut.model_validate(m) for m in msgs]


@router.get("/unread_count", response_model=UnreadCountOut)
async def my_unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountOut:
    n = await ContactMessageService(db).user_unread_count(current_user.id)
    return UnreadCountOut(unread=n)


@router.post("", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: SendMessageIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    msg = await ContactMessageService(db).send_from_user(current_user.id, data)
    return MessageOut.model_validate(msg)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """撤回自己发出的私信。"""
    await ContactMessageService(db).delete_message(
        message_id, requester_id=current_user.id, is_admin=False
    )


# 管理员侧：会话列表 + 与某用户对话。
admin_router = APIRouter(
    prefix="/admin/messages", tags=["admin-messages"], dependencies=[Depends(require_admin)]
)


@admin_router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(db: AsyncSession = Depends(get_db)) -> list[ConversationOut]:
    return await ContactMessageService(db).list_conversations()


@admin_router.get("/unread_count", response_model=UnreadCountOut)
async def admin_unread_count(db: AsyncSession = Depends(get_db)) -> UnreadCountOut:
    n = await ContactMessageService(db).admin_unread_total()
    return UnreadCountOut(unread=n)


@admin_router.get("/{user_id}", response_model=list[MessageOut])
async def conversation(user_id: int, db: AsyncSession = Depends(get_db)) -> list[MessageOut]:
    msgs = await ContactMessageService(db).list_for_conversation(user_id)
    return [MessageOut.model_validate(m) for m in msgs]


@admin_router.post("/{user_id}", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
async def reply(
    user_id: int,
    data: SendMessageIn,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> MessageOut:
    msg = await ContactMessageService(db).send_from_admin(user_id, admin.id, data)
    return MessageOut.model_validate(msg)


@admin_router.delete("/message/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_message(message_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """管理员删除会话内任意单条消息。"""
    await ContactMessageService(db).delete_message(message_id, requester_id=0, is_admin=True)


@admin_router.put("/{user_id}/state", response_model=ConversationStateOut)
async def set_conversation_state(
    user_id: int,
    data: ConversationStateIn,
    db: AsyncSession = Depends(get_db),
) -> ConversationStateOut:
    """置顶 / 屏蔽某个用户会话。"""
    state = await ContactMessageService(db).set_state(
        user_id, pinned=data.pinned, blocked=data.blocked
    )
    return ConversationStateOut(pinned=state.pinned, blocked=state.blocked)


@admin_router.delete("/{user_id}/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_conversation(user_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """清空聊天记录，保留会话。"""
    await ContactMessageService(db).clear_conversation(user_id)


@admin_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(user_id: int, db: AsyncSession = Depends(get_db)) -> None:
    """删除整个会话（消息 + 状态）。"""
    await ContactMessageService(db).delete_conversation(user_id)
