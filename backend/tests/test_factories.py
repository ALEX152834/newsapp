"""
测试数据工厂的单元测试

验证工厂函数能正确创建测试数据。

Requirements: 7.2
"""

from datetime import datetime, timedelta, timezone

import pytest

from tests.factories import (
    create_article,
    create_articles_batch,
    create_articles_for_pagination_test,
    create_articles_with_different_published_at,
    create_articles_with_different_sources,
    create_articles_with_same_published_at,
    DEFAULT_SOURCES,
)


class TestCreateArticle:
    """测试单个 Article 创建函数"""
    
    def test_create_article_with_defaults(self, db_session):
        """测试使用默认值创建 Article"""
        article = create_article(db_session)
        
        assert article.id is not None
        assert article.title is not None
        assert article.source is not None
        assert article.url is not None
        assert article.published_at is not None
        assert article.summary is None
    
    def test_create_article_with_custom_values(self, db_session):
        """测试使用自定义值创建 Article"""
        custom_time = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        
        article = create_article(
            db_session,
            title="自定义标题",
            source="自定义来源",
            url="https://custom.example.com/news/1",
            published_at=custom_time,
            summary="自定义摘要",
        )
        
        assert article.title == "自定义标题"
        assert article.source == "自定义来源"
        assert article.url == "https://custom.example.com/news/1"
        assert article.published_at == custom_time
        assert article.summary == "自定义摘要"
    
    def test_create_article_url_uniqueness(self, db_session):
        """测试 URL 唯一性约束"""
        create_article(db_session, url="https://unique.example.com/news/1")
        
        # 尝试创建相同 URL 的 Article 应该失败
        with pytest.raises(Exception):  # IntegrityError
            create_article(db_session, url="https://unique.example.com/news/1")


class TestCreateArticlesWithDifferentPublishedAt:
    """测试创建不同 published_at 的 Article 列表"""
    
    def test_creates_correct_count(self, db_session):
        """测试创建正确数量的 Article"""
        articles = create_articles_with_different_published_at(db_session, count=5)
        assert len(articles) == 5
    
    def test_different_published_at(self, db_session):
        """测试每个 Article 有不同的 published_at"""
        articles = create_articles_with_different_published_at(db_session, count=5)
        
        published_times = [a.published_at for a in articles]
        # 所有时间应该不同
        assert len(set(published_times)) == len(published_times)
    
    def test_time_ordering(self, db_session):
        """测试时间按降序排列"""
        articles = create_articles_with_different_published_at(
            db_session, count=5, interval_minutes=60
        )
        
        # 第一个应该是最新的
        for i in range(len(articles) - 1):
            assert articles[i].published_at > articles[i + 1].published_at


class TestCreateArticlesWithSamePublishedAt:
    """测试创建相同 published_at 的 Article 列表"""
    
    def test_creates_correct_count(self, db_session):
        """测试创建正确数量的 Article"""
        articles = create_articles_with_same_published_at(db_session, count=5)
        assert len(articles) == 5
    
    def test_same_published_at(self, db_session):
        """测试所有 Article 有相同的 published_at"""
        articles = create_articles_with_same_published_at(db_session, count=5)
        
        published_times = [a.published_at for a in articles]
        # 所有时间应该相同
        assert len(set(published_times)) == 1
    
    def test_different_ids(self, db_session):
        """测试每个 Article 有不同的 id"""
        articles = create_articles_with_same_published_at(db_session, count=5)
        
        ids = [a.id for a in articles]
        # 所有 id 应该不同
        assert len(set(ids)) == len(ids)


class TestCreateArticlesWithDifferentSources:
    """测试创建不同来源的 Article 列表"""
    
    def test_uses_default_sources(self, db_session):
        """测试使用默认来源列表"""
        articles = create_articles_with_different_sources(db_session)
        
        assert len(articles) == len(DEFAULT_SOURCES)
        sources = [a.source for a in articles]
        assert set(sources) == set(DEFAULT_SOURCES)
    
    def test_uses_custom_sources(self, db_session):
        """测试使用自定义来源列表"""
        custom_sources = ["来源A", "来源B", "来源C"]
        articles = create_articles_with_different_sources(
            db_session, sources=custom_sources
        )
        
        assert len(articles) == len(custom_sources)
        sources = [a.source for a in articles]
        assert set(sources) == set(custom_sources)


class TestCreateArticlesBatch:
    """测试批量创建 Article"""
    
    def test_creates_correct_count(self, db_session):
        """测试创建正确数量的 Article"""
        articles = create_articles_batch(db_session, count=25)
        assert len(articles) == 25
    
    def test_unique_published_at(self, db_session):
        """测试每个 Article 有唯一的 published_at"""
        articles = create_articles_batch(db_session, count=25)
        
        published_times = [a.published_at for a in articles]
        # 所有时间应该不同
        assert len(set(published_times)) == len(published_times)


class TestCreateArticlesForPaginationTest:
    """测试创建分页测试数据集"""
    
    def test_creates_correct_total_count(self, db_session):
        """测试创建正确的总数量"""
        articles = create_articles_for_pagination_test(
            db_session, total_count=55, same_time_count=5
        )
        assert len(articles) == 55
    
    def test_contains_same_time_articles(self, db_session):
        """测试包含相同时间的 Article"""
        articles = create_articles_for_pagination_test(
            db_session, total_count=55, same_time_count=5
        )
        
        published_times = [a.published_at for a in articles]
        # 应该有一些重复的时间
        unique_times = set(published_times)
        assert len(unique_times) < len(published_times)


class TestFixtures:
    """测试 conftest.py 中的 fixtures"""
    
    def test_article_factory_fixture(self, article_factory):
        """测试 article_factory fixture"""
        article = article_factory(title="Fixture 测试")
        assert article.title == "Fixture 测试"
    
    def test_articles_with_different_times_fixture(self, articles_with_different_times):
        """测试 articles_with_different_times fixture"""
        articles = articles_with_different_times(count=3)
        assert len(articles) == 3
    
    def test_articles_with_same_time_fixture(self, articles_with_same_time):
        """测试 articles_with_same_time fixture"""
        articles = articles_with_same_time(count=3)
        assert len(articles) == 3
        # 所有时间应该相同
        times = [a.published_at for a in articles]
        assert len(set(times)) == 1
    
    def test_articles_batch_fixture(self, articles_batch):
        """测试 articles_batch fixture"""
        articles = articles_batch(count=10)
        assert len(articles) == 10
    
    def test_articles_for_pagination_fixture(self, articles_for_pagination):
        """测试 articles_for_pagination fixture"""
        articles = articles_for_pagination(total_count=20)
        assert len(articles) == 20
