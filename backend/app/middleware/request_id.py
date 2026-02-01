"""Request ID 中间件

为每个请求生成唯一的 request_id，用于请求追踪和日志关联。
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Request ID 中间件
    
    功能：
    - 为每个请求生成唯一的 UUID 作为 request_id
    - 将 request_id 存储在 request.state 中，供后续处理使用
    - 在响应头中添加 X-Request-ID，便于客户端追踪
    """
    
    async def dispatch(self, request: Request, call_next):
        """处理请求，添加 request_id"""
        # 生成唯一的 request_id
        request_id = str(uuid.uuid4())
        
        # 存储到 request.state 中，供日志和异常处理使用
        request.state.request_id = request_id
        
        # 调用下一个中间件或路由处理器
        response = await call_next(request)
        
        # 在响应头中添加 X-Request-ID
        response.headers["X-Request-ID"] = request_id
        
        return response
