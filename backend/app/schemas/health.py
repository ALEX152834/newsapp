"""Health Check Pydantic Schemas

定义健康检查相关的响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, field_serializer

from app.schemas.article import serialize_datetime_utc


class HealthData(BaseModel):
    """健康检查响应数据模型

    用于 /health 端点，表示 API 进程存活状态。
    """

    status: str
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        """序列化 timestamp 为 ISO 8601 UTC + Z 格式"""
        return serialize_datetime_utc(dt)


class ReadyData(BaseModel):
    """就绪检查响应数据模型

    用于 /ready 端点，表示服务依赖（DB、Redis）的连通性状态。
    """

    status: str
    database: str
    redis: str
