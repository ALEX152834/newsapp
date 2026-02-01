"""
Alembic 环境配置

配置数据库连接和迁移目标元数据。
从 app.config 读取数据库连接 URL，从 app.database 导入 Base 元数据。
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# 导入应用配置和数据库模型
from app.config import settings
from app.database import Base

# 导入所有模型，确保它们被注册到 Base.metadata
from app.models.article import Article  # noqa: F401

# Alembic Config 对象，提供对 .ini 文件的访问
config = context.config

# 设置数据库连接 URL（覆盖 alembic.ini 中的占位符）
config.set_main_option("sqlalchemy.url", settings.database_url)

# 配置 Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置目标元数据，用于 autogenerate 支持
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    离线模式运行迁移。
    
    在此模式下，只需配置 URL，不需要 Engine。
    通过调用 context.execute() 直接输出 SQL 语句。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在线模式运行迁移。
    
    在此模式下，需要创建 Engine 并关联连接。
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
