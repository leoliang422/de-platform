from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge_tree.models import KnowledgeNode
from app.modules.knowledge_tree.schemas import (
    AdminNodeCreate,
    AdminNodeUpdate,
    NodeProposeIn,
    PendingNodeOut,
    TreeNode,
)
from app.modules.notifications.service import NotificationService


class KnowledgeTreeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _all_nodes(self, category_id: int, *, published_only: bool) -> list[KnowledgeNode]:
        stmt = select(KnowledgeNode).where(KnowledgeNode.category_id == category_id)
        if published_only:
            stmt = stmt.where(KnowledgeNode.status == "published")
        stmt = stmt.order_by(KnowledgeNode.order_index, KnowledgeNode.id)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_tree(self, category_id: int, *, published_only: bool = True) -> list[TreeNode]:
        nodes = await self._all_nodes(category_id, published_only=published_only)
        by_parent: dict[int | None, list[KnowledgeNode]] = {}
        for n in nodes:
            by_parent.setdefault(n.parent_id, []).append(n)

        def build(parent_id: int | None) -> list[TreeNode]:
            return [
                TreeNode(
                    id=n.id,
                    title=n.title,
                    knowledge_item_id=n.knowledge_item_id,
                    status=n.status,
                    proposer_id=n.proposer_id,
                    order_index=n.order_index,
                    children=build(n.id),
                )
                for n in by_parent.get(parent_id, [])
            ]

        return build(None)

    async def propose(self, user_id: int, data: NodeProposeIn) -> KnowledgeNode:
        if data.parent_id is not None:
            parent = await self.db.get(KnowledgeNode, data.parent_id)
            if parent is None or parent.category_id != data.category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="父节点不存在或不属于该分类"
                )
        node = KnowledgeNode(
            category_id=data.category_id,
            parent_id=data.parent_id,
            title=data.title.strip(),
            knowledge_item_id=data.knowledge_item_id,
            status="pending",
            proposer_id=user_id,
            note=data.note,
        )
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    # ---- admin ----
    async def list_pending(self) -> list[PendingNodeOut]:
        stmt = (
            select(KnowledgeNode)
            .where(KnowledgeNode.status == "pending")
            .order_by(KnowledgeNode.id.desc())
        )
        nodes = list((await self.db.execute(stmt)).scalars().all())
        titles: dict[int, str] = {}
        parent_ids = {n.parent_id for n in nodes if n.parent_id is not None}
        if parent_ids:
            rows = (
                await self.db.execute(
                    select(KnowledgeNode.id, KnowledgeNode.title).where(
                        KnowledgeNode.id.in_(parent_ids)
                    )
                )
            ).all()
            titles = {i: t for i, t in rows}
        return [
            PendingNodeOut(
                id=n.id,
                category_id=n.category_id,
                parent_id=n.parent_id,
                parent_title=titles.get(n.parent_id) if n.parent_id else None,
                title=n.title,
                knowledge_item_id=n.knowledge_item_id,
                proposer_id=n.proposer_id,
                note=n.note,
                created_at=n.created_at,
            )
            for n in nodes
        ]

    async def _get_or_404(self, node_id: int) -> KnowledgeNode:
        node = await self.db.get(KnowledgeNode, node_id)
        if node is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="节点不存在")
        return node

    async def approve(self, node_id: int) -> KnowledgeNode:
        node = await self._get_or_404(node_id)
        node.status = "published"
        if node.proposer_id is not None:
            await NotificationService(self.db).notify(
                user_id=node.proposer_id,
                type="knowledge_node_approved",
                title="知识树节点已通过审核",
                body=f"你提议的知识点「{node.title}」已上线",
                link=f"/knowledge/tree/{node.category_id}",
            )
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def reject(self, node_id: int) -> None:
        node = await self._get_or_404(node_id)
        proposer_id = node.proposer_id
        title = node.title
        category_id = node.category_id
        await self.db.delete(node)
        if proposer_id is not None:
            await NotificationService(self.db).notify(
                user_id=proposer_id,
                type="knowledge_node_rejected",
                title="知识树节点未通过审核",
                body=f"你提议的知识点「{title}」未通过",
                link=f"/knowledge/tree/{category_id}",
            )
        await self.db.commit()

    async def admin_create(self, data: AdminNodeCreate) -> KnowledgeNode:
        node = KnowledgeNode(
            category_id=data.category_id,
            parent_id=data.parent_id,
            title=data.title.strip(),
            knowledge_item_id=data.knowledge_item_id,
            status="published",
            order_index=data.order_index,
        )
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def admin_update(self, node_id: int, data: AdminNodeUpdate) -> KnowledgeNode:
        node = await self._get_or_404(node_id)
        fields = data.model_dump(exclude_unset=True)
        for key, value in fields.items():
            setattr(node, key, value)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def delete(self, node_id: int) -> None:
        node = await self._get_or_404(node_id)
        await self.db.delete(node)
        await self.db.commit()
