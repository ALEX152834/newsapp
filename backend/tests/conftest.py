"""
pytest 配置文件

包含 hypothesis 属性测试的全局配置和数据库测试 fixtures。

Requirements: 7.4
"""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from hypothesis import HealthCheck, Phase, Verbosity, settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app

# ============================================================
# 测试数据库配置
# ============================================================

# 测试数据库连接串 - 使用 compose 服务名 postgres
# 在 docker-compose 网络内，服务间通过服务名互相访问
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://test:test@postgres:5432/test_news"
)

# ============================================================
# Hypothesis 全局配置
# ============================================================

# 默认 profile - 用于本地开发和 CI
settings.register_profile(
    "default",
    max_examples=100,  # 每个属性测试运行 100 个例子
    deadline=None,  # 禁用超时，避免 CI 超时问题
    suppress_health_check=[
        HealthCheck.too_slow,  # 数据库操作可能较慢
        HealthCheck.data_too_large,  # 允许较大的测试数据
    ],
    verbosity=Verbosity.normal,
    phases=[
        Phase.explicit,
        Phase.reuse,
        Phase.generate,
        Phase.target,
        Phase.shrink,
    ],
)

# CI profile - 用于持续集成，运行更多例子
settings.register_profile(
    "ci",
    max_examples=200,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
    verbosity=Verbosity.verbose,
)

# 开发 profile - 用于快速迭代，运行较少例子
settings.register_profile(
    "dev",
    max_examples=10,
    deadline=None,
    suppress_health_check=[
        HealthCheck.too_slow,
        HealthCheck.data_too_large,
    ],
    verbosity=Verbosity.verbose,
)

# 加载默认 profile
settings.load_profile("default")

# ============================================================
# 数据库 Fixtures
# ============================================================


@pytest.fixture(scope="session")
def engine():
    """
    创建测试数据库引擎（session 级别）
    
    整个测试会话共享同一个引擎实例。
    """
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def tables(engine):
    """
    创建和清理数据库表（session 级别）
    
    在测试会话开始时创建所有表，结束时删除所有表。
    """
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(engine, tables) -> Generator[Session, None, None]:
    """
    提供数据库会话（function 级别）
    
    每个测试函数使用独立的事务，测试结束后回滚，
    确保测试之间数据隔离。
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    提供 FastAPI 测试客户端
    
    覆盖 get_db 依赖，使用测试数据库会话。
    测试结束后清理依赖覆盖。
    """
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ============================================================
# 测试数据工厂 Fixtures
# ============================================================


@pytest.fixture
def article_factory(db_session: Session):
    """
    提供创建单个 Article 的工厂函数
    
    使用方式：
        def test_example(article_factory):
            article = article_factory(title="自定义标题")
    """
    from tests.factories import create_article
    
    def factory(**kwargs):
        return create_article(db_session, **kwargs)
    
    return factory


@pytest.fixture
def articles_with_different_times(db_session: Session):
    """
    提供创建具有不同 published_at 的 Article 列表的工厂函数
    
    使用方式：
        def test_example(articles_with_different_times):
            articles = articles_with_different_times(count=10)
    """
    from tests.factories import create_articles_with_different_published_at
    
    def factory(count: int = 10, **kwargs):
        return create_articles_with_different_published_at(db_session, count, **kwargs)
    
    return factory


@pytest.fixture
def articles_with_same_time(db_session: Session):
    """
    提供创建具有相同 published_at 的 Article 列表的工厂函数
    
    用于测试排序稳定性（相同时间按 id 排序）。
    
    使用方式：
        def test_example(articles_with_same_time):
            articles = articles_with_same_time(count=5)
    """
    from tests.factories import create_articles_with_same_published_at
    
    def factory(count: int = 5, **kwargs):
        return create_articles_with_same_published_at(db_session, count, **kwargs)
    
    return factory


@pytest.fixture
def articles_with_different_sources(db_session: Session):
    """
    提供创建具有不同来源的 Article 列表的工厂函数
    
    使用方式：
        def test_example(articles_with_different_sources):
            articles = articles_with_different_sources()
    """
    from tests.factories import create_articles_with_different_sources
    
    def factory(**kwargs):
        return create_articles_with_different_sources(db_session, **kwargs)
    
    return factory


@pytest.fixture
def articles_batch(db_session: Session):
    """
    提供批量创建 Article 的工厂函数
    
    用于分页测试，每条记录的 published_at 相差指定秒数。
    
    使用方式：
        def test_example(articles_batch):
            articles = articles_batch(count=100)
    """
    from tests.factories import create_articles_batch
    
    def factory(count: int, **kwargs):
        return create_articles_batch(db_session, count, **kwargs)
    
    return factory


@pytest.fixture
def articles_for_pagination(db_session: Session):
    """
    提供创建分页测试数据集的工厂函数
    
    包含不同 published_at 和相同 published_at 的混合数据。
    
    使用方式：
        def test_example(articles_for_pagination):
            articles = articles_for_pagination(total_count=55)
    """
    from tests.factories import create_articles_for_pagination_test
    
    def factory(total_count: int = 55, **kwargs):
        return create_articles_for_pagination_test(db_session, total_count, **kwargs)
    
    return factory
