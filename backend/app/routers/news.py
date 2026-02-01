"""
News Router

新闻列表 API 路由层。

主要功能：
- GET /v1/news: 获取新闻列表，支持分页

参数验证：
- limit: 范围 1-50，默认 20
- cursor: 可选的分页游标

错误处理：
- limit 超出范围: 400 + VALIDATION_ERROR（由 FastAPI 自动处理）
- cursor 格式无效: 400 + INVALID_CURSOR

Requirements: 4.1, 4.3, 4.4, 4.6
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.repositories.article import InvalidCursorError
from app.schemas.article import ArticleListData
from app.schemas.base import ApiResponse
from app.services.article import ArticleService

router = APIRouter(prefix="/v1", tags=["news"])


@router.get("/news", response_model=ApiResponse[ArticleListData])
def get_news(
    limit: int = Query(default=20, ge=1, le=50),
    cursor: Optional[str] = Query(default=None),
    db: Session = Depends(get_db)
) -> ApiResponse[ArticleListData] | JSONResponse:
    """
    获取新闻列表

    - limit: 每页数量，范围 1-50，默认 20
    - cursor: 分页游标，可选

    Returns:
        成功: ApiResponse[ArticleListData] 包含新闻列表和分页信息
        失败: JSONResponse 包含错误信息

    Raises:
        400 VALIDATION_ERROR: limit 参数超出范围（由 FastAPI 自动处理）
        400 INVALID_CURSOR: cursor 格式无效
    """
    try:
        service = ArticleService(db)
        data, meta = service.get_news_list(limit, cursor)
        return ApiResponse(data=data, meta=meta, error=None)
    except InvalidCursorError:
        return JSONResponse(
            status_code=400,
            content={
                "data": None,
                "meta": {},
                "error": {
                    "code": "INVALID_CURSOR",
                    "message": "The provided cursor is invalid or malformed"
                }
            }
        )
