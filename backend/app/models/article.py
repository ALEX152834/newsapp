"""
Article 模型

定义 articles 表结构，用于存储新闻文章数据。

字段说明：
- id: UUID 主键，自动生成
- title: 新闻标题，非空，最大 500 字符
- source: 来源名称，非空，最大 200 字符
- url: 新闻链接，非空，唯一约束用于去重，最大 2000 字符
- published_at: 发布时间，带时区，非空
- summary: 新闻摘要，可空
- created_at: 入库时间，数据库侧默认值（UTC）
"""

import uuid

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Article(Base):
    """新闻文章模型"""
    
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False, unique=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Article(id={self.id}, title={self.title[:30]}...)>"
