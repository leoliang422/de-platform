from __future__ import annotations

from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import SECTIONS, Category
from app.modules.catalog.schemas import CategoryCreate, CategoryNode, CategoryUpdate


def build_tree(categories: Iterable[Category]) -> list[CategoryNode]:
    """Convert a flat, order-sorted category list into a nested tree."""
    categories = list(categories)
    nodes: dict[int, CategoryNode] = {
        c.id: CategoryNode(id=c.id, name=c.name, slug=c.slug, order=c.order, children=[])
        for c in categories
    }
    roots: list[CategoryNode] = []
    for c in categories:
        node = nodes[c.id]
        parent = nodes.get(c.parent_id) if c.parent_id is not None else None
        if parent is not None:
            parent.children.append(node)
        else:
            roots.append(node)
    return roots


async def create_category(db: AsyncSession, data: CategoryCreate) -> Category:
    if data.section not in SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效板块，可选：{', '.join(SECTIONS)}",
        )
    category = Category(
        section=data.section,
        name=data.name,
        slug=data.slug,
        parent_id=data.parent_id,
        order=data.order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(db: AsyncSession, category_id: int, data: CategoryUpdate) -> Category:
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: int) -> None:
    category = await db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    await db.delete(category)
    await db.commit()
