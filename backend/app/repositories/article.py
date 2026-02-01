"""
Article Repository

数据访问层，负责 Article 模型的数据库操作。

主要功能：
- get_list: 获取文章列表，支持 keyset pagination
- _parse_cursor: 解析游标
- _build_cursor: 构建游标

游标格式规范：
- 编码格式：urlsafe_base64(published_at_iso|id_uuid)
- 编码方式：URL-safe base64（使用 - 和 _ 替代 + 和 /）
- 分隔符：|
- published_at_iso：ISO 8601 UTC 字符串，必须以 Z 结尾
- id_uuid：UUID 字符串

示例：
- 编码前：2024-01-15T10:30:00Z|123e4567-e89b-12d3-a456-426614174000
- 编码后：MjAyNC0wMS0xNVQxMDozMDowMFp8MTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAw
"""

import base64
import binascii
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session

from app.models.article import Article


class InvalidCursorError(Exception):
    """游标格式无效时抛出"""
    pass


class ArticleRepository:
    """Article 数据访问层"""
    
    def __init__(self, db: Session):
        """
        初始化 Repository
        
        Args:
            db: SQLAlchemy Session 实例
        """
        self.db = db

    def get_list(
        self,
        limit: int,
        cursor: Optional[str] = None
    ) -> Tuple[List[Article], Optional[str]]:
        """
        获取文章列表，返回 (articles, next_cursor)
        
        使用 keyset pagination 基于 (published_at, id) 分页
        排序规则：published_at DESC, id DESC
        
        Args:
            limit: 每页数量
            cursor: 分页游标，可选
            
        Returns:
            Tuple[List[Article], Optional[str]]: (文章列表, 下一页游标)
            
        Raises:
            InvalidCursorError: 当游标格式无效时
        """
        query = self.db.query(Article)

        if cursor:
            cursor_published_at, cursor_id = self._parse_cursor(cursor)
            # 严格"小于"上一页最后一条 (published_at, id)
            # 使用 keyset pagination 条件
            query = query.filter(
                or_(
                    Article.published_at < cursor_published_at,
                    and_(
                        Article.published_at == cursor_published_at,
                        Article.id < cursor_id
                    )
                )
            )

        # 按 published_at DESC, id DESC 排序
        # 多取一条用于判断是否有下一页
        query = query.order_by(
            desc(Article.published_at),
            desc(Article.id)
        ).limit(limit + 1)

        articles = query.all()

        # 判断是否有下一页
        if len(articles) > limit:
            # 有下一页，截取前 limit 条
            articles = articles[:limit]
            last = articles[-1]
            next_cursor = self._build_cursor(last)
        else:
            # 没有下一页
            next_cursor = None

        return articles, next_cursor

    def _parse_cursor(self, cursor: str) -> Tuple[datetime, UUID]:
        """
        解析游标（严格校验版本）
        
        游标格式：base64(published_at_iso|id_uuid)
        - 编码：URL-safe base64（仅允许 A-Z a-z 0-9 _ - 和最多两个 = padding）
        - 分隔符：|
        - published_at_iso：ISO 8601 UTC 字符串（必须以 Z 结尾）
        - id_uuid：UUID 字符串
        
        严格校验规则：
        1. cursor 仅允许 URL-safe base64 字符集：A-Z a-z 0-9 _ -，以及最多两个 = padding
        2. cursor 长度必须是 4 的倍数（len % 4 == 0）
        3. 解码使用 base64.b64decode(cursor, altchars=b"-_", validate=True)
        4. 解码后必须严格为 published_at_iso|id_uuid 两段
        
        示例解码后：2024-01-15T10:30:00Z|123e4567-e89b-12d3-a456-426614174000
        
        异常处理规则：
        - 捕获所有解码/解析异常并转译为 InvalidCursorError
        - 任何非法 cursor 都返回 400 + INVALID_CURSOR，不得返回 500
        
        Args:
            cursor: Base64 编码的游标字符串
            
        Returns:
            Tuple[datetime, UUID]: (发布时间, 文章ID)
            
        Raises:
            InvalidCursorError: 当游标格式无效时
        """
        import re
        
        try:
            # 1. 校验 cursor 长度必须是 4 的倍数
            if len(cursor) == 0 or len(cursor) % 4 != 0:
                raise InvalidCursorError("Invalid cursor: length must be multiple of 4")
            
            # 2. 校验 cursor 仅包含 URL-safe base64 字符集
            # 允许：A-Z a-z 0-9 _ - 和最多两个 = padding（只能在末尾）
            url_safe_pattern = r'^[A-Za-z0-9_-]*={0,2}$'
            if not re.match(url_safe_pattern, cursor):
                raise InvalidCursorError("Invalid cursor: contains invalid characters")
            
            # 3. 检查是否包含标准 base64 字符（+ 或 /），这些不允许
            if '+' in cursor or '/' in cursor:
                raise InvalidCursorError("Invalid cursor: contains + or / characters")
            
            # 4. 使用严格校验解码：base64.b64decode with validate=True
            # altchars=b"-_" 将 URL-safe 的 - 和 _ 映射回标准 base64 的 + 和 /
            decoded_bytes = base64.b64decode(cursor, altchars=b"-_", validate=True)
            decoded = decoded_bytes.decode("utf-8")
            
            # 5. 解码后必须严格为两段
            parts = decoded.split("|")
            if len(parts) != 2:
                raise InvalidCursorError("Invalid cursor format: expected 2 parts")
            
            published_at_str, id_str = parts
            
            # 6. 校验时间格式必须以 Z 结尾
            if not published_at_str.endswith("Z"):
                raise InvalidCursorError("Invalid cursor format: timestamp must end with Z")
            
            # 7. 解析 ISO 8601 UTC 时间（以 Z 结尾）
            # 将 Z 替换为 +00:00 以便 fromisoformat 解析
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            
            # 8. 解析 UUID
            cursor_id = UUID(id_str)
            
            return published_at, cursor_id
        except InvalidCursorError:
            # 重新抛出 InvalidCursorError，不要包装
            raise
        except (ValueError, UnicodeDecodeError, binascii.Error) as e:
            raise InvalidCursorError(f"Invalid cursor: {e}")

    def _build_cursor(self, article: Article) -> str:
        """
        构建游标
        
        游标格式：urlsafe_base64(published_at_iso|id_uuid)
        - 编码：URL-safe base64（使用 - 和 _ 替代 + 和 /）
        - published_at_iso：ISO 8601 UTC 字符串（以 Z 结尾）
        
        UTC 转换规则：
        - 必须先执行 astimezone(timezone.utc) 转换为 UTC
        - 然后再输出 ISO 8601 的 ...Z 形式
        - 禁止对非 UTC 时间直接 strftime(...Z)
        
        生成的 cursor 仅包含 URL-safe 字符集，不需要额外 URL encode
        
        Args:
            article: Article 模型实例
            
        Returns:
            str: URL-safe base64 编码的游标字符串
        """
        # 先转换为 UTC，再格式化
        utc_time = article.published_at.astimezone(timezone.utc)
        published_at_iso = utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor_str = f"{published_at_iso}|{article.id}"
        # 使用 URL-safe base64 编码
        return base64.urlsafe_b64encode(cursor_str.encode("utf-8")).decode("utf-8")
