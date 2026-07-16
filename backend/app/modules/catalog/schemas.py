from __future__ import annotations

from pydantic import BaseModel


class CategoryNode(BaseModel):
    id: int
    name: str
    slug: str
    order: int
    children: list[CategoryNode] = []


CategoryNode.model_rebuild()
