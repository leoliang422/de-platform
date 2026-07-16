from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CategoryNode(BaseModel):
    id: int
    name: str
    slug: str
    order: int
    children: list[CategoryNode] = []


CategoryNode.model_rebuild()


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parent_id: int | None = None
    section: str
    name: str
    slug: str
    order: int


class CategoryCreate(BaseModel):
    section: str
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120)
    parent_id: int | None = None
    order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    parent_id: int | None = None
    order: int | None = None
