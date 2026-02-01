"""Health Check Router

提供健康检查和就绪检查端点：
- GET /health: 仅检查 API 进程存活
- GET /ready: 检查 DB 和 Redis 连通性

Requirements: 3.1, 3.2, 3.3
"""

from datetime import datetime, timezone

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.base import ApiResponse, Meta
from app.schemas.health import HealthData, ReadyData


router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[HealthData])
def health_check() -> ApiResponse[HealthData]:
    """健康检查接口

    仅表示 API 进程存活，不检查 DB/Redis 连通性。
    返回固定 status 和当前 UTC 时间戳。

    Returns:
        ApiResponse[HealthData]: 包含 status 和 timestamp 的响应
    """
    data = HealthData(
        status="ok",
        timestamp=datetime.now(timezone.utc)
    )
    return ApiResponse(data=data, meta=Meta(), error=None)


@router.get("/ready", response_model=ApiResponse[ReadyData])
def readiness_check(
    db: Session = Depends(get_db)
) -> ApiResponse[ReadyData] | JSONResponse:
    """就绪检查接口

    检查 DB 和 Redis 连通性，用于 Kubernetes readiness probe。
    只要 DB 或 Redis 任一检查失败，返回 HTTP 503。

    Args:
        db: 数据库会话（通过依赖注入）

    Returns:
        ApiResponse[ReadyData]: 成功时返回 200
        JSONResponse: 失败时返回 503
    """
    db_status = "ok"
    redis_status = "ok"

    # 检查数据库连通性（使用 text() 包装 raw SQL）
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    # 检查 Redis 连通性（执行 PING 命令）
    try:
        redis_client = redis.from_url(settings.redis_url)
        redis_client.ping()
        redis_client.close()
    except Exception:
        redis_status = "error"

    overall_status = "ok" if db_status == "ok" and redis_status == "ok" else "error"

    if overall_status == "error":
        return JSONResponse(
            status_code=503,
            content={
                "data": {
                    "status": overall_status,
                    "database": db_status,
                    "redis": redis_status
                },
                "meta": {},
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Service dependencies not ready"
                }
            }
        )

    data = ReadyData(status=overall_status, database=db_status, redis=redis_status)
    return ApiResponse(data=data, meta=Meta(), error=None)
