"""Article Pydantic Schemas

定义新闻文章相关的请求/响应模型。
"""

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


def serialize_datetime_utc(dt: datetime) -> str:
    """
    统一序列化 datetime 为 ISO 8601 UTC + Z 格式

    规则：
    - 先转换为 UTC
    - 输出格式：YYYY-MM-DDTHH:MM:SSZ
    - 禁止输出 +00:00 格式
    """
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArticleResponse(BaseModel):
    """单个新闻文章响应模型"""

    id: UUID
    title: str
    source: str
    url: str
    published_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("published_at")
    def serialize_published_at(self, dt: datetime) -> str:
        return serialize_datetime_utc(dt)


class ArticleListData(BaseModel):
    """新闻列表数据模型"""

    items: List[ArticleResponse]
