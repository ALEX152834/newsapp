"""
请求日志中间件

记录每个 HTTP 请求的详细信息，包括：
- method: HTTP 方法
- path: 请求路径
- status_code: 响应状态码
- latency: 响应时间（毫秒）
- request_id: 请求追踪 ID

Requirements: 8.4, 8.5
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    功能：
    - 记录每个请求的 method、path、status_code、latency、request_id
    - 使用 JSON 结构化日志格式
    - 在请求完成后记录日志
    """
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """处理请求并记录日志"""
        # 记录请求开始时间
        start_time = time.perf_counter()
        
        # 获取 request_id（由 RequestIdMiddleware 设置）
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 调用下一个中间件或路由处理器
        response = await call_next(request)
        
        # 计算响应时间（毫秒）
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # 记录请求日志
        logger.info(
            "HTTP request completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": round(latency_ms, 2),
            }
        )
        
        return response
