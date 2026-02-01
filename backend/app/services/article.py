"""
Article Service

业务逻辑层，负责新闻文章相关的业务处理。

主要功能：
- get_news_list: 获取新闻列表，调用 Repository 获取数据并转换为 Schema

Requirements: 4.1, 8.1
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.article import ArticleRepository
from app.schemas.article import ArticleListData, ArticleResponse
from app.schemas.base import Meta


class ArticleService:
    """Article 业务逻辑层"""

    def __init__(self, db: Session):
        """
        初始化 Service

        Args:
            db: SQLAlchemy Session 实例
        """
        self.repository = ArticleRepository(db)

    def get_news_list(
        self,
        limit: int,
        cursor: Optional[str] = None
    ) -> tuple[ArticleListData, Meta]:
        """
        获取新闻列表

        调用 Repository 获取文章数据，转换为 Schema 格式返回。

        Args:
            limit: 每页数量
            cursor: 分页游标，可选

        Returns:
            tuple[ArticleListData, Meta]: (新闻列表数据, 分页元数据)

        Raises:
            InvalidCursorError: 当游标格式无效时（由 Repository 抛出）
        """
        articles, next_cursor = self.repository.get_list(limit, cursor)

        items = [ArticleResponse.model_validate(a) for a in articles]
        data = ArticleListData(items=items)
        meta = Meta(count=len(items), next_cursor=next_cursor)

        return data, meta
