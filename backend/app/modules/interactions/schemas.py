import datetime as dt

from pydantic import BaseModel, Field


class StatsOut(BaseModel):
    content_type: str
    content_id: int
    views: int
    likes: int
    favorites: int
    comments: int
    liked: bool = False
    favorited: bool = False


class ViewOut(BaseModel):
    views: int


class CommentOut(BaseModel):
    id: int
    user_id: int
    author_nickname: str
    author_avatar: str | None = None
    parent_id: int | None = None
    body: str
    created_at: dt.datetime


class CommentCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None


class FavoriteItem(BaseModel):
    content_type: str
    content_id: int
    title: str
    created_at: dt.datetime


class AnnotationOut(BaseModel):
    id: int
    user_id: int
    author_nickname: str
    author_avatar: str | None = None
    parent_id: int | None = None
    body: str
    created_at: dt.datetime


class AnnotationCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = None
