"""create articles table

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

创建 articles 表，包含：
- 所有必需字段（id, title, source, url, published_at, summary, created_at）
- URL 唯一索引（用于去重）
- 分页查询复合索引（published_at DESC, id DESC）

Requirements: 2.1, 2.2, 2.3, 2.4
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    创建 articles 表和索引
    
    表结构：
    - id: UUID 主键
    - title: VARCHAR(500) 非空
    - source: VARCHAR(200) 非空
    - url: VARCHAR(2000) 非空，唯一
    - published_at: TIMESTAMP WITH TIME ZONE 非空
    - summary: TEXT 可空
    - created_at: TIMESTAMP WITH TIME ZONE 默认当前时间
    
    索引：
    - idx_articles_url: URL 唯一索引（用于去重）
    - idx_articles_published_at_id: 分页查询复合索引
    """
    op.create_table(
        "articles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("source", sa.String(200), nullable=False),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # 创建 URL 唯一索引（用于新闻去重）
    # Requirements: 2.2
    op.create_index(
        "idx_articles_url",
        "articles",
        ["url"],
        unique=True,
    )

    # 创建分页查询复合索引（按发布时间和 ID 排序）
    # 用于 keyset pagination: ORDER BY published_at DESC, id DESC
    # Requirements: 2.4 (设计文档中的索引设计)
    op.create_index(
        "idx_articles_published_at_id",
        "articles",
        [sa.text("published_at DESC"), sa.text("id DESC")],
    )


def downgrade() -> None:
    """
    回滚：删除 articles 表和索引
    """
    # 删除索引
    op.drop_index("idx_articles_published_at_id", table_name="articles")
    op.drop_index("idx_articles_url", table_name="articles")
    
    # 删除表
    op.drop_table("articles")
