from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.modules.knowledge_tree.schemas import (
    AdminNodeCreate,
    AdminNodeUpdate,
    NodeProposeIn,
    NodeProposeOut,
    PendingNodeOut,
    TreeNode,
)
from app.modules.knowledge_tree.service import KnowledgeTreeService
from app.modules.users.models import User

router = APIRouter(prefix="/knowledge-tree", tags=["knowledge-tree"])


@router.get("", response_model=list[TreeNode])
async def get_tree(
    category_id: int = Query(...),
    db: AsyncSession = Depends(get_db),
) -> list[TreeNode]:
    """返回某大类下已上线的知识树（嵌套）。"""
    return await KnowledgeTreeService(db).get_tree(category_id, published_only=True)


@router.post("/nodes", response_model=NodeProposeOut, status_code=status.HTTP_201_CREATED)
async def propose_node(
    data: NodeProposeIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NodeProposeOut:
    """用户在某位置提议新增知识点，进入审核队列。"""
    node = await KnowledgeTreeService(db).propose(current_user.id, data)
    return NodeProposeOut(id=node.id, status=node.status)


# ---- admin ----
admin_router = APIRouter(
    prefix="/admin/knowledge-tree",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


@admin_router.get("/pending", response_model=list[PendingNodeOut])
async def list_pending(db: AsyncSession = Depends(get_db)) -> list[PendingNodeOut]:
    return await KnowledgeTreeService(db).list_pending()


@admin_router.get("", response_model=list[TreeNode])
async def admin_get_tree(
    category_id: int = Query(...), db: AsyncSession = Depends(get_db)
) -> list[TreeNode]:
    return await KnowledgeTreeService(db).get_tree(category_id, published_only=False)


@admin_router.post("/{node_id}/approve", status_code=status.HTTP_200_OK)
async def approve_node(node_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await KnowledgeTreeService(db).approve(node_id)
    return {"status": "published"}


@admin_router.post("/{node_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_node(node_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await KnowledgeTreeService(db).reject(node_id)


@admin_router.post("/nodes", response_model=NodeProposeOut, status_code=status.HTTP_201_CREATED)
async def admin_create_node(
    data: AdminNodeCreate, db: AsyncSession = Depends(get_db)
) -> NodeProposeOut:
    node = await KnowledgeTreeService(db).admin_create(data)
    return NodeProposeOut(id=node.id, status=node.status)


@admin_router.patch("/{node_id}", response_model=NodeProposeOut)
async def admin_update_node(
    node_id: int, data: AdminNodeUpdate, db: AsyncSession = Depends(get_db)
) -> NodeProposeOut:
    node = await KnowledgeTreeService(db).admin_update(node_id, data)
    return NodeProposeOut(id=node.id, status=node.status)


@admin_router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_node(node_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await KnowledgeTreeService(db).delete(node_id)
