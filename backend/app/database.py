"""
数据库连接模块

配置 SQLAlchemy engine、session 和 Base 类。
提供 get_db 依赖注入函数供 FastAPI 路由使用。

使用 SQLAlchemy 2.x 模式。
"""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

# 创建 SQLAlchemy engine
# pool_pre_ping=True 确保连接池中的连接在使用前检查有效性
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# 创建 SessionLocal 类
# autocommit=False: 不自动提交，需要显式调用 commit()
# autoflush=False: 不自动刷新，避免意外的数据库操作
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# 创建 Base 类，所有模型都继承自此类
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入函数，提供数据库会话。
    
    使用 yield 确保会话在请求结束后正确关闭。
    
    Usage:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    
    Yields:
        Session: SQLAlchemy 数据库会话
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
