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
    # slug 不参与路由，可留空由后端按名称自动生成。
    slug: str | None = Field(default=None, max_length=120)
    parent_id: int | None = None
    order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    parent_id: int | None = None
    order: int | None = None


class CategoryReorderItem(BaseModel):
    id: int
    parent_id: int | None = None
    order: int = 0


class CategoryReorderIn(BaseModel):
    section: str
    items: list[CategoryReorderItem]


class FolderItem(BaseModel):
    """文件夹里的一条内容（八股/SQL），供管理端文件夹视图当"文件"展示。"""

    id: int
    title: str
    status: str


class FolderNode(BaseModel):
    id: int
    name: str
    order: int
    children: list[FolderNode] = []
    items: list[FolderItem] = []


FolderNode.model_rebuild()


class FolderTree(BaseModel):
    """管理端文件夹树：根级子文件夹 + 未分类的内容。"""

    roots: list[FolderNode] = []
    uncategorized: list[FolderItem] = []
