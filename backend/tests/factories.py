"""
测试数据工厂

提供创建测试用 Article 数据的工厂函数，支持：
- 创建单个 Article
- 批量创建 Article
- 自定义字段值
- 生成不同 published_at、相同 published_at 不同 id、不同 source 的数据

Requirements: 7.2
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from sqlalchemy.orm import Session

from app.models.article import Article


# ============================================================
# 默认值常量
# ============================================================

DEFAULT_SOURCES = [
    "新华社",
    "人民日报",
    "央视新闻",
    "澎湃新闻",
    "财新网",
    "界面新闻",
    "36氪",
    "虎嗅网",
    "钛媒体",
    "第一财经",
]


# ============================================================
# 单个 Article 创建函数
# ============================================================


def create_article(
    db: Session,
    *,
    title: Optional[str] = None,
    source: Optional[str] = None,
    url: Optional[str] = None,
    published_at: Optional[datetime] = None,
    summary: Optional[str] = None,
    article_id: Optional[uuid.UUID] = None,
    commit: bool = True,
) -> Article:
    """
    创建单个 Article 并插入数据库
    
    Args:
        db: 数据库会话
        title: 新闻标题，默认自动生成
        source: 来源名称，默认随机选择
        url: 新闻链接，默认自动生成唯一 URL
        published_at: 发布时间，默认当前 UTC 时间
        summary: 新闻摘要，默认为 None
        article_id: 指定 UUID，默认自动生成
        commit: 是否立即提交，默认 True
        
    Returns:
        创建的 Article 实例
    """
    # 生成唯一标识符用于默认值
    unique_id = uuid.uuid4().hex[:8]
    
    article = Article(
        id=article_id or uuid.uuid4(),
        title=title or f"测试新闻标题 {unique_id}",
        source=source or DEFAULT_SOURCES[hash(unique_id) % len(DEFAULT_SOURCES)],
        url=url or f"https://example.com/news/{unique_id}",
        published_at=published_at or datetime.now(timezone.utc),
        summary=summary,
    )
    
    db.add(article)
    if commit:
        db.commit()
        db.refresh(article)
    else:
        db.flush()
    
    return article


# ============================================================
# 批量 Article 创建函数
# ============================================================


def create_articles_with_different_published_at(
    db: Session,
    count: int = 10,
    *,
    base_time: Optional[datetime] = None,
    interval_minutes: int = 60,
    source: Optional[str] = None,
    commit: bool = True,
) -> List[Article]:
    """
    创建多个具有不同 published_at 的 Article
    
    用于测试按时间排序的场景。
    
    Args:
        db: 数据库会话
        count: 创建数量
        base_time: 基准时间，默认当前 UTC 时间
        interval_minutes: 每条记录之间的时间间隔（分钟）
        source: 统一来源，默认随机
        commit: 是否立即提交
        
    Returns:
        创建的 Article 列表（按 published_at 降序）
    """
    base = base_time or datetime.now(timezone.utc)
    articles = []
    
    for i in range(count):
        published_at = base - timedelta(minutes=i * interval_minutes)
        article = create_article(
            db,
            published_at=published_at,
            source=source,
            commit=False,
        )
        articles.append(article)
    
    if commit:
        db.commit()
        for article in articles:
            db.refresh(article)
    else:
        db.flush()
    
    return articles


def create_articles_with_same_published_at(
    db: Session,
    count: int = 5,
    *,
    published_at: Optional[datetime] = None,
    source: Optional[str] = None,
    commit: bool = True,
) -> List[Article]:
    """
    创建多个具有相同 published_at 但不同 id 的 Article
    
    用于测试排序稳定性（相同时间按 id 排序）。
    
    Args:
        db: 数据库会话
        count: 创建数量
        published_at: 统一发布时间，默认当前 UTC 时间
        source: 统一来源，默认随机
        commit: 是否立即提交
        
    Returns:
        创建的 Article 列表
    """
    time = published_at or datetime.now(timezone.utc)
    articles = []
    
    for _ in range(count):
        article = create_article(
            db,
            published_at=time,
            source=source,
            commit=False,
        )
        articles.append(article)
    
    if commit:
        db.commit()
        for article in articles:
            db.refresh(article)
    else:
        db.flush()
    
    return articles


def create_articles_with_different_sources(
    db: Session,
    sources: Optional[List[str]] = None,
    *,
    base_time: Optional[datetime] = None,
    commit: bool = True,
) -> List[Article]:
    """
    创建具有不同来源的 Article
    
    用于测试按来源筛选的场景（如果将来需要）。
    
    Args:
        db: 数据库会话
        sources: 来源列表，默认使用 DEFAULT_SOURCES
        base_time: 基准时间，默认当前 UTC 时间
        commit: 是否立即提交
        
    Returns:
        创建的 Article 列表
    """
    source_list = sources or DEFAULT_SOURCES
    base = base_time or datetime.now(timezone.utc)
    articles = []
    
    for i, source in enumerate(source_list):
        published_at = base - timedelta(minutes=i * 30)
        article = create_article(
            db,
            source=source,
            published_at=published_at,
            commit=False,
        )
        articles.append(article)
    
    if commit:
        db.commit()
        for article in articles:
            db.refresh(article)
    else:
        db.flush()
    
    return articles


def create_articles_batch(
    db: Session,
    count: int,
    *,
    base_time: Optional[datetime] = None,
    interval_seconds: int = 1,
    commit: bool = True,
) -> List[Article]:
    """
    批量创建 Article，用于分页测试
    
    每条记录的 published_at 相差指定秒数，确保排序唯一。
    
    Args:
        db: 数据库会话
        count: 创建数量
        base_time: 基准时间，默认当前 UTC 时间
        interval_seconds: 每条记录之间的时间间隔（秒）
        commit: 是否立即提交
        
    Returns:
        创建的 Article 列表（按 published_at 降序）
    """
    base = base_time or datetime.now(timezone.utc)
    articles = []
    
    for i in range(count):
        published_at = base - timedelta(seconds=i * interval_seconds)
        article = create_article(
            db,
            published_at=published_at,
            commit=False,
        )
        articles.append(article)
    
    if commit:
        db.commit()
        for article in articles:
            db.refresh(article)
    else:
        db.flush()
    
    return articles


# ============================================================
# 混合场景创建函数
# ============================================================


def create_articles_for_pagination_test(
    db: Session,
    total_count: int = 55,
    *,
    same_time_count: int = 5,
    commit: bool = True,
) -> List[Article]:
    """
    创建用于分页测试的混合数据集
    
    包含：
    - 大部分记录具有不同的 published_at
    - 部分记录具有相同的 published_at（测试排序稳定性）
    
    Args:
        db: 数据库会话
        total_count: 总记录数
        same_time_count: 具有相同 published_at 的记录数
        commit: 是否立即提交
        
    Returns:
        创建的 Article 列表
    """
    base_time = datetime.now(timezone.utc)
    articles = []
    
    # 创建具有不同 published_at 的记录
    different_time_count = total_count - same_time_count
    for i in range(different_time_count):
        published_at = base_time - timedelta(minutes=i + 1)
        article = create_article(
            db,
            published_at=published_at,
            commit=False,
        )
        articles.append(article)
    
    # 创建具有相同 published_at 的记录（使用最新时间）
    same_time = base_time
    for _ in range(same_time_count):
        article = create_article(
            db,
            published_at=same_time,
            commit=False,
        )
        articles.append(article)
    
    if commit:
        db.commit()
        for article in articles:
            db.refresh(article)
    else:
        db.flush()
    
    return articles


# ============================================================
# Hypothesis 策略生成器
# ============================================================


def article_data_strategy() -> dict[str, Any]:
    """
    返回用于 Hypothesis 的 Article 数据字典
    
    注意：这不是 Hypothesis strategy，而是返回随机数据的辅助函数。
    实际的 Hypothesis strategy 应该在测试文件中使用 @st.composite 定义。
    """
    unique_id = uuid.uuid4().hex[:8]
    return {
        "title": f"测试新闻标题 {unique_id}",
        "source": DEFAULT_SOURCES[hash(unique_id) % len(DEFAULT_SOURCES)],
        "url": f"https://example.com/news/{unique_id}",
        "published_at": datetime.now(timezone.utc),
        "summary": None,
    }
