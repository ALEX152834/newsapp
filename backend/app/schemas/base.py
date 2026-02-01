"""统一响应格式模型

定义 API 统一响应结构，包括：
- ErrorDetail: 错误详情
- Meta: 分页元数据
- ApiResponse: 统一响应包装器

Requirements: 5.1, 5.2, 5.3
"""

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """错误详情模型

    Attributes:
        code: 错误码（如 VALIDATION_ERROR、INVALID_CURSOR、INTERNAL_ERROR）
        message: 错误消息
        details: 可选的错误详情
    """

    code: str
    message: str
    details: Optional[Any] = None


class Meta(BaseModel):
    """分页元数据模型

    Attributes:
        count: 本次返回的数量
        next_cursor: 下一页游标，无则为 null
    """

    count: Optional[int] = None
    next_cursor: Optional[str] = None


class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应模型

    成功时：data 包含数据，error 为 null
    失败时：data 为 null，error 包含错误信息

    Attributes:
        data: 响应数据
        meta: 分页元数据
        error: 错误详情
    """

    data: Optional[T] = None
    meta: Meta = Field(default_factory=Meta)
    error: Optional[ErrorDetail] = None
