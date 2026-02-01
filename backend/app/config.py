"""
配置管理模块

使用 Pydantic Settings v2 从环境变量读取配置。
支持 .env 文件加载，忽略未定义的额外字段。
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置类"""

    database_url: str
    redis_url: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
