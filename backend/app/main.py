"""
FastAPI 应用入口

配置应用生命周期、中间件、路由和异常处理器。

主要功能：
- 启动时配置结构化日志
- 启动时等待数据库就绪
- 注册 Request ID 中间件和日志中间件
- 注册 health 和 news 路由
- 配置统一异常处理器

Requirements: 1.4, 8.3, 8.4, 8.5
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from app.database import engine
from app.logging_config import setup_logging
from app.middleware.logging_middleware import LoggingMiddleware
from app.middleware.request_id import RequestIdMiddleware
from app.routers import health, news

# 配置结构化日志（在模块加载时执行）
setup_logging()

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
def wait_for_db() -> None:
    """等待数据库就绪，用于启动阶段 readiness"""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Database connection established")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时等待数据库就绪
    wait_for_db()
    yield
    # 关闭时清理资源（如需要）


app = FastAPI(title="News API", lifespan=lifespan)

# 添加中间件（注意顺序：先添加的后执行，所以 LoggingMiddleware 先添加）
# 执行顺序：RequestIdMiddleware -> LoggingMiddleware -> 路由处理
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIdMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(news.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    处理请求验证错误
    
    当参数验证失败时（如 limit 超出范围），返回统一格式的错误响应。
    """
    return JSONResponse(
        status_code=400,
        content={
            "data": None,
            "meta": {},
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    处理未捕获的异常
    
    记录错误日志但不暴露内部错误详情给客户端。
    """
    request_id = getattr(request.state, "request_id", "unknown")
    # 记录日志但不暴露内部错误详情
    logger.error("Internal error", extra={"request_id": request_id, "error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "meta": {},
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred"
            }
        }
    )
