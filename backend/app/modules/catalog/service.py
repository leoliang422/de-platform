from __future__ import annotations

from collections.abc import Iterable

from app.modules.catalog.models import Category
from app.modules.catalog.schemas import CategoryNode


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
