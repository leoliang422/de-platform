from __future__ import annotations

import re
import uuid
from collections.abc import Iterable, Sequence
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import SECTIONS, Category
from app.modules.catalog.schemas import (
    CategoryCreate,
    CategoryNode,
    CategoryReorderItem,
    CategoryUpdate,
    FolderItem,
    FolderNode,
    FolderTree,
)


def make_slug(name: str) -> str:
    """slug 不参与路由，仅作历史字段：能 ASCII 化就用，否则退回随机短串。"""
    base = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return base or f"c-{uuid.uuid4().hex[:8]}"


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
        slug=data.slug or make_slug(data.name),
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


async def reorder_categories(
    db: AsyncSession, section: str, items: Iterable[CategoryReorderItem]
) -> None:
    """整体持久化拖拽后的层级与顺序：逐条更新 parent_id / order。"""
    items = list(items)
    ids = [it.id for it in items]
    if not ids:
        return
    rows = (
        (
            await db.execute(
                select(Category).where(Category.id.in_(ids), Category.section == section)
            )
        )
        .scalars()
        .all()
    )
    by_id = {c.id: c for c in rows}
    valid_ids = set(by_id)
    for it in items:
        cat = by_id.get(it.id)
        if cat is None:
            continue
        # 只允许挂到同 section 的已存在分类下（或根）。
        parent_id = it.parent_id if it.parent_id in valid_ids else None
        if parent_id == it.id:
            parent_id = None
        cat.parent_id = parent_id
        cat.order = it.order
    await db.commit()


def _section_items(rows: Iterable[Any]) -> dict[int | None, list[FolderItem]]:
    grouped: dict[int | None, list[FolderItem]] = {}
    for r in rows:
        cid = getattr(r, "category_id", None)
        grouped.setdefault(cid, []).append(FolderItem(id=r.id, title=r.title, status=r.status))
    return grouped


async def build_folder_tree(db: AsyncSession, section: str) -> FolderTree:
    """管理端文件夹视图：分类做文件夹，八股/SQL 作为文件夹内的文件。"""
    from app.modules.catalog.repository import CategoryRepository

    categories = await CategoryRepository(db).list_by_section(section)

    # 取该 section 下带 category_id 的内容作为"文件"
    grouped: dict[int | None, list[FolderItem]] = {}
    rows: Sequence[Any]
    if section == "knowledge":
        from app.modules.knowledge.models import KnowledgeItem

        rows = (await db.execute(select(KnowledgeItem))).scalars().all()
        grouped = _section_items(rows)
    elif section == "sql":
        from app.modules.sql_bank.models import SqlQuestion

        rows = (await db.execute(select(SqlQuestion))).scalars().all()
        grouped = _section_items(rows)

    nodes: dict[int, FolderNode] = {
        c.id: FolderNode(
            id=c.id, name=c.name, order=c.order, children=[], items=grouped.get(c.id, [])
        )
        for c in categories
    }
    roots: list[FolderNode] = []
    for c in categories:
        node = nodes[c.id]
        parent = nodes.get(c.parent_id) if c.parent_id is not None else None
        if parent is not None:
            parent.children.append(node)
        else:
            roots.append(node)
    return FolderTree(roots=roots, uncategorized=grouped.get(None, []))
