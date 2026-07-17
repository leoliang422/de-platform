from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class TreeNode(BaseModel):
    id: int
    title: str
    knowledge_item_id: int | None = None
    status: str = "published"
    proposer_id: int | None = None
    order_index: int = 0
    children: list[TreeNode] = []


class NodeProposeIn(BaseModel):
    category_id: int
    parent_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    knowledge_item_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class NodeProposeOut(BaseModel):
    id: int
    status: str


class PendingNodeOut(BaseModel):
    id: int
    category_id: int
    parent_id: int | None
    parent_title: str | None
    title: str
    knowledge_item_id: int | None
    proposer_id: int | None
    note: str | None
    created_at: dt.datetime


class AdminNodeCreate(BaseModel):
    category_id: int
    parent_id: int | None = None
    title: str = Field(min_length=1, max_length=200)
    knowledge_item_id: int | None = None
    order_index: int = 0


class AdminNodeUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    parent_id: int | None = None
    knowledge_item_id: int | None = None
    order_index: int | None = None
    status: str | None = None
