# Design Document: News APP Backend

## Overview

本设计文档描述新闻 APP 后端系统的技术架构和实现方案。系统采用 Python + FastAPI 构建，使用 PostgreSQL 存储数据，Redis 预留缓存能力，通过 docker-compose 实现一键部署。

核心设计原则：
- **分层架构**：API 层、Service 层、Repository 层分离
- **统一响应**：所有接口使用一致的响应格式
- **可测试性**：支持依赖注入，便于单元测试和集成测试
- **可观测性**：结构化日志，请求追踪

## Architecture

### 系统架构图

```mermaid
graph TB
    subgraph Docker Compose
        subgraph API Container
            FastAPI[FastAPI App]
            Router[API Router]
            Service[Service Layer]
            Repository[Repository Layer]
        end
        
        subgraph Database Container
            PostgreSQL[(PostgreSQL)]
        end
        
        subgraph Cache Container
            Redis[(Redis)]
        end
    end
    
    Client[Client] --> FastAPI
    FastAPI --> Router
    Router --> Service
    Service --> Repository
    Repository --> PostgreSQL
    Service -.-> Redis
```

### 请求处理流程

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant R as Router
    participant S as Service
    participant Repo as Repository
    participant DB as PostgreSQL
    
    C->>M: HTTP Request
    M->>M: Generate request_id
    M->>R: Forward request
    R->>R: Validate params
    alt Invalid params
        R-->>C: 400 Error Response
    else Valid params
        R->>S: Call service
        S->>Repo: Query data
        Repo->>DB: SQL Query
        DB-->>Repo: Result
        Repo-->>S: Domain objects
        S-->>R: Business result
        R-->>C: Success Response
    end
```

### 目录结构

```
project-root/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI 应用入口
│   │   ├── config.py            # 配置管理
│   │   ├── database.py          # 数据库连接
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── __init__.py
│   │   │   └── article.py
│   │   ├── schemas/             # Pydantic 模型
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # 统一响应格式
│   │   │   └── article.py
│   │   ├── repositories/        # 数据访问层
│   │   │   ├── __init__.py
│   │   │   └── article.py
│   │   ├── services/            # 业务逻辑层
│   │   │   ├── __init__.py
│   │   │   └── article.py
│   │   ├── routers/             # API 路由层
│   │   │   ├── __init__.py
│   │   │   ├── health.py
│   │   │   └── news.py
│   │   └── middleware/          # 中间件
│   │       ├── __init__.py
│   │       └── request_id.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py          # pytest fixtures
│   │   ├── test_health.py
│   │   └── test_news.py
│   ├── alembic/                 # 数据库迁移
│   │   ├── versions/
│   │   ├── env.py
│   │   └── alembic.ini
│   ├── pyproject.toml
│   └── requirements.txt
├── infra/
│   └── docker-compose.yml
├── scripts/
│   └── seed.py
├── .env.example
├── Makefile
└── README.md
```

## Components and Interfaces

### 1. 配置管理 (config.py)

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
```

### 2. 统一响应格式 (schemas/base.py)

```python
from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class Meta(BaseModel):
    count: Optional[int] = None
    next_cursor: Optional[str] = None


class ApiResponse(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: Meta = Field(default_factory=Meta)
    error: Optional[ErrorDetail] = None
```

### 3. Article 模型 (models/article.py)

```python
import uuid

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Article(Base):
    __tablename__ = "articles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(500), nullable=False)
    source = Column(String(200), nullable=False)
    url = Column(String(2000), nullable=False, unique=True)
    published_at = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

**时间与时区策略**：

1. **数据库时区固定为 UTC**：在 docker-compose 中通过环境变量强制设置 PostgreSQL 时区：
   ```yaml
   # infra/docker-compose.yml
   services:
     postgres:
       image: postgres:16
       environment:
         POSTGRES_USER: news
         POSTGRES_PASSWORD: news
         POSTGRES_DB: news
         TZ: UTC
         PGTZ: UTC
   ```

2. **created_at 默认值**：使用数据库侧默认值 `server_default=func.now()`，由 PostgreSQL 生成 UTC 时间

3. **禁止事项**：
   - 禁止使用 Python 侧 `datetime.utcnow()` 或任何 naive datetime 作为默认值
   - 禁止对非 UTC 时间直接 `strftime(...Z)`

4. **API 输出时间格式**：ISO 8601 UTC，示例：`2026-01-31T06:12:34Z`

### 4. Article Schema (schemas/article.py)

```python
from datetime import datetime, timezone
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_serializer


def serialize_datetime_utc(dt: datetime) -> str:
    """
    统一序列化 datetime 为 ISO 8601 UTC + Z 格式
    
    规则：
    - 先转换为 UTC
    - 输出格式：YYYY-MM-DDTHH:MM:SSZ
    - 禁止输出 +00:00 格式
    """
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArticleResponse(BaseModel):
    id: UUID
    title: str
    source: str
    url: str
    published_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("published_at")
    def serialize_published_at(self, dt: datetime) -> str:
        return serialize_datetime_utc(dt)


class ArticleListData(BaseModel):
    items: List[ArticleResponse]
```

**时间序列化规则**：
- 所有响应模型中的 datetime 字段必须使用 `field_serializer` 统一输出 ISO 8601 UTC + Z 格式
- 输出格式：`YYYY-MM-DDTHH:MM:SSZ`（例如：`2026-01-31T06:12:34Z`）
- 禁止输出 `+00:00` 格式
- 任何新增的响应 datetime 字段也必须遵循同一序列化规则

### 5. Repository 层 (repositories/article.py)

```python
import base64
import binascii
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import desc, or_, and_
from sqlalchemy.orm import Session

from app.models.article import Article


class InvalidCursorError(Exception):
    """游标格式无效时抛出"""
    pass


class ArticleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_list(
        self,
        limit: int,
        cursor: Optional[str] = None
    ) -> Tuple[List[Article], Optional[str]]:
        """
        获取文章列表，返回 (articles, next_cursor)
        
        使用 keyset pagination 基于 (published_at, id) 分页
        排序规则：published_at DESC, id DESC
        """
        query = self.db.query(Article)

        if cursor:
            cursor_published_at, cursor_id = self._parse_cursor(cursor)
            # 严格"小于"上一页最后一条 (published_at, id)
            query = query.filter(
                or_(
                    Article.published_at < cursor_published_at,
                    and_(
                        Article.published_at == cursor_published_at,
                        Article.id < cursor_id
                    )
                )
            )

        query = query.order_by(
            desc(Article.published_at),
            desc(Article.id)
        ).limit(limit + 1)

        articles = query.all()

        # 判断是否有下一页
        if len(articles) > limit:
            articles = articles[:limit]
            last = articles[-1]
            next_cursor = self._build_cursor(last)
        else:
            next_cursor = None

        return articles, next_cursor

    def _parse_cursor(self, cursor: str) -> Tuple[datetime, UUID]:
        """
        解析游标
        
        游标格式：urlsafe_base64(published_at_iso|id_uuid)
        - 编码：URL-safe base64（使用 - 和 _ 替代 + 和 /）
        - 分隔符：|
        - published_at_iso：ISO 8601 UTC 字符串（以 Z 结尾）
        - id_uuid：UUID 字符串
        
        示例解码后：2024-01-15T10:30:00Z|123e4567-e89b-12d3-a456-426614174000
        
        异常处理规则：
        - 捕获所有解码/解析异常并转译为 InvalidCursorError
        - 任何非法 cursor 都返回 400 + INVALID_CURSOR，不得返回 500
        """
        try:
            # 使用 URL-safe base64 解码
            decoded = base64.urlsafe_b64decode(cursor).decode("utf-8")
            parts = decoded.split("|")
            if len(parts) != 2:
                raise InvalidCursorError("Invalid cursor format: expected 2 parts")
            
            published_at_str, id_str = parts
            
            # 校验时间格式必须以 Z 结尾
            if not published_at_str.endswith("Z"):
                raise InvalidCursorError("Invalid cursor format: timestamp must end with Z")
            
            # 解析 ISO 8601 UTC 时间（以 Z 结尾）
            published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            cursor_id = UUID(id_str)
            return published_at, cursor_id
        except (ValueError, UnicodeDecodeError, binascii.Error) as e:
            raise InvalidCursorError(f"Invalid cursor: {e}")

    def _build_cursor(self, article: Article) -> str:
        """
        构建游标
        
        游标格式：urlsafe_base64(published_at_iso|id_uuid)
        - 编码：URL-safe base64（使用 - 和 _ 替代 + 和 /）
        - published_at_iso：ISO 8601 UTC 字符串（以 Z 结尾）
        
        UTC 转换规则：
        - 必须先执行 astimezone(timezone.utc) 转换为 UTC
        - 然后再输出 ISO 8601 的 ...Z 形式
        - 禁止对非 UTC 时间直接 strftime(...Z)
        
        生成的 cursor 仅包含 URL-safe 字符集，不需要额外 URL encode
        """
        # 先转换为 UTC，再格式化
        utc_time = article.published_at.astimezone(timezone.utc)
        published_at_iso = utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")
        cursor_str = f"{published_at_iso}|{article.id}"
        # 使用 URL-safe base64 编码
        return base64.urlsafe_b64encode(cursor_str.encode("utf-8")).decode("utf-8")
```
```

### 6. Service 层 (services/article.py)

```python
from typing import Optional

from sqlalchemy.orm import Session

from app.repositories.article import ArticleRepository
from app.schemas.article import ArticleListData, ArticleResponse
from app.schemas.base import Meta


class ArticleService:
    def __init__(self, db: Session):
        self.repository = ArticleRepository(db)

    def get_news_list(
        self,
        limit: int,
        cursor: Optional[str] = None
    ) -> tuple[ArticleListData, Meta]:
        articles, next_cursor = self.repository.get_list(limit, cursor)

        items = [ArticleResponse.model_validate(a) for a in articles]
        data = ArticleListData(items=items)
        meta = Meta(count=len(items), next_cursor=next_cursor)

        return data, meta
```

### 7. Router 层 (routers/news.py)

```python
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
):
    """
    获取新闻列表
    
    - limit: 每页数量，范围 1-50，默认 20
    - cursor: 分页游标，可选
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
```

### 8. Health 与 Ready Router (routers/health.py)

```python
from datetime import datetime, timezone

import redis
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_serializer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.base import ApiResponse, Meta


router = APIRouter(tags=["health"])


class HealthData(BaseModel):
    status: str
    timestamp: datetime

    @field_serializer("timestamp")
    def serialize_timestamp(self, dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ReadyData(BaseModel):
    status: str
    database: str
    redis: str


@router.get("/health", response_model=ApiResponse[HealthData])
def health_check():
    """
    健康检查接口
    
    仅表示 API 进程存活，不检查 DB/Redis 连通性。
    返回固定 status 和当前 UTC 时间戳。
    """
    data = HealthData(
        status="ok",
        timestamp=datetime.now(timezone.utc)
    )
    return ApiResponse(data=data, meta=Meta(), error=None)


@router.get("/ready", response_model=ApiResponse[ReadyData])
def readiness_check(db: Session = Depends(get_db)):
    """
    就绪检查接口
    
    检查 DB 和 Redis 连通性，用于 Kubernetes readiness probe。
    只要 DB 或 Redis 任一检查失败，返回 HTTP 503。
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
```

### 9. 应用入口与启动 (main.py)

```python
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.database import engine
from app.middleware.request_id import RequestIdMiddleware
from app.routers import health, news

logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
def wait_for_db():
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

# 添加中间件
app.add_middleware(RequestIdMiddleware)

# 注册路由
app.include_router(health.router)
app.include_router(news.router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
async def general_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
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
```

### 10. Request ID 中间件 (middleware/request_id.py)

```python
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

## Data Models

### Articles 表结构

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PRIMARY KEY | 主键，自动生成 |
| title | VARCHAR(500) | NOT NULL | 新闻标题 |
| source | VARCHAR(200) | NOT NULL | 来源名称 |
| url | VARCHAR(2000) | NOT NULL, UNIQUE | 新闻链接，用于去重 |
| published_at | TIMESTAMP WITH TIME ZONE | NOT NULL | 发布时间（UTC） |
| summary | TEXT | NULLABLE | 新闻摘要 |
| created_at | TIMESTAMP WITH TIME ZONE | DEFAULT NOW() | 入库时间（数据库侧默认，UTC） |

### 索引设计

```sql
-- 主键索引（自动创建）
PRIMARY KEY (id)

-- URL 唯一索引（用于去重）
UNIQUE INDEX idx_articles_url ON articles(url)

-- 分页查询索引（按发布时间和 ID 排序）
INDEX idx_articles_published_at_id ON articles(published_at DESC, id DESC)
```

### 游标分页设计

**游标格式规范**：

- 编码格式：`urlsafe_base64(published_at_iso|id_uuid)`
- 编码方式：URL-safe base64（使用 `-` 和 `_` 替代 `+` 和 `/`）
- 分隔符：`|`
- `published_at_iso`：ISO 8601 UTC 字符串，必须以 `Z` 结尾
- `id_uuid`：UUID 字符串

**编码/解码方法**：
- 编码：`base64.urlsafe_b64encode()`
- 解码：`base64.urlsafe_b64decode()`

**示例**：

编码前：`2024-01-15T10:30:00Z|123e4567-e89b-12d3-a456-426614174000`

编码后（URL-safe）：`MjAyNC0wMS0xNVQxMDozMDowMFp8MTIzZTQ1NjctZTg5Yi0xMmQzLWE0NTYtNDI2NjE0MTc0MDAw`

**分页算法（Keyset Pagination）**：

1. 排序规则：`published_at DESC, id DESC`
2. 取下一页过滤条件（严格"小于"上一页最后一条）：
   ```sql
   WHERE published_at < :last_published_at
      OR (published_at = :last_published_at AND id < :last_id)
   ```
3. `meta.next_cursor` 由当前页最后一条记录生成
4. 当不存在下一页时，`next_cursor` 为 `null`

**cursor 异常处理规则**：
- 捕获所有解码/解析异常（包括 `binascii.Error`、`ValueError`、`UnicodeDecodeError`）
- 转译为 `InvalidCursorError`
- 返回 HTTP 400 + `error.code = INVALID_CURSOR`
- 任何非法 cursor 都返回 400，不得返回 500

### ER 图

```mermaid
erDiagram
    ARTICLES {
        uuid id PK
        varchar title
        varchar source
        varchar url UK
        timestamp published_at
        text summary
        timestamp created_at
    }
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

基于需求分析，以下是本系统需要验证的正确性属性：

### Property 1: URL 唯一约束

*For any* 两条 Article 记录，如果它们具有相同的 url 值，则第二条记录的插入操作应该失败并抛出唯一约束冲突错误。

**Validates: Requirements 2.2, 2.5**

### Property 2: 新闻列表排序正确性

*For any* 从 /v1/news 接口返回的新闻列表，列表中的每一项的 (published_at, id) 都应该大于等于其后一项的 (published_at, id)，即按 published_at DESC, id DESC 排序。

**Validates: Requirements 4.2**

### Property 3: limit 参数范围验证

*For any* 对 /v1/news 接口的请求：
- 当 limit 在 1-50 范围内时，返回的 items 数量应该不超过 limit
- 当 limit 小于 1 或大于 50 时，应该返回 HTTP 400 错误，error.code 为 VALIDATION_ERROR

**Validates: Requirements 4.3, 4.4**

### Property 4: 游标分页正确性

*For any* 包含 N 条记录的数据集，使用游标分页遍历所有数据时：
- 每次请求返回的数据不应与之前请求的数据重复
- 所有分页请求返回的数据合集应该等于完整数据集
- 分页顺序应该与单次请求大量数据的顺序一致

**Validates: Requirements 4.5**

### Property 5: 成功响应格式一致性

*For any* 成功的 API 请求，响应 JSON 应该符合以下结构：
- 包含 data 字段（非 null）
- 包含 meta 字段
- error 字段为 null
- 对于分页接口，meta 应包含 count 和 next_cursor 字段
- 对于新闻列表，data.items 中每项应包含 id、title、source、url、published_at 字段
- 时间字段格式为 ISO 8601 UTC（以 Z 结尾）

**Validates: Requirements 4.6, 4.7, 4.8, 5.1, 5.3**

### Property 6: 错误响应格式一致性

*For any* 失败的 API 请求（如参数验证失败），响应 JSON 应该符合以下结构：
- data 字段为 null
- 包含 meta 字段
- error 字段非 null，包含 code 和 message
- error.code 必须为 MVP 允许的错误码之一：VALIDATION_ERROR、INVALID_CURSOR、INTERNAL_ERROR

**Validates: Requirements 5.2, 8.3**

### Property 7: 种子脚本幂等性

*For any* 执行次数 N（N >= 1），多次执行种子脚本后数据库中的记录数应该与执行一次相同，即 f(x) = f(f(x))。

**Validates: Requirements 6.2**

## Error Handling

### MVP 阶段错误码集合

**MVP 阶段允许且仅允许以下 error.code**：

| error.code | HTTP 状态码 | 场景 |
|------------|-------------|------|
| VALIDATION_ERROR | 400 | 参数验证失败（如 limit 超出范围） |
| INVALID_CURSOR | 400 | 游标格式无效或解析失败 |
| INTERNAL_ERROR | 500 | 未捕获异常/服务内部错误 |
| INTERNAL_ERROR | 503 | 依赖未就绪（/ready 检查 DB/Redis 失败） |

**INTERNAL_ERROR 状态码区分规则**：
- **500**：未捕获异常、服务内部错误
- **503**：依赖未就绪（readiness not ready），仅用于 /ready 端点

**禁止在 MVP 阶段使用的错误码**：NOT_FOUND、SERVICE_UNAVAILABLE 等其他错误码在 MVP 阶段不应出现在接口契约中。

### 异常处理策略

```python
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
async def general_exception_handler(request: Request, exc: Exception):
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
```

### 数据库连接重试

数据库重试逻辑挂载在 FastAPI 启动阶段（lifespan），用于 readiness：

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from tenacity import retry, stop_after_attempt, wait_exponential

from app.database import engine


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
def wait_for_db():
    """等待数据库就绪，用于启动阶段 readiness"""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    wait_for_db()
    yield


app = FastAPI(lifespan=lifespan)
```

### /health 与 /ready 职责分离

| 端点 | 职责 | 检查内容 | 用途 |
|------|------|----------|------|
| GET /health | 存活检查 | 仅检查 API 进程存活 | Kubernetes liveness probe |
| GET /ready | 就绪检查 | 检查 DB/Redis 连通性 | Kubernetes readiness probe |

## Testing Strategy

### 测试框架选择

- **单元测试**: pytest
- **属性测试**: hypothesis（Python 的属性测试库）
- **HTTP 测试**: httpx + pytest-asyncio
- **数据库测试**: 使用测试数据库 + 事务回滚

### 测试执行环境

**关键约束**：
- pytest 必须在 api 容器内执行
- 测试数据库连接串的 host 必须使用 compose 服务名 `postgres`，禁止使用 `localhost`

**测试数据库连接串格式**：
```
postgresql://test:test@postgres:5432/test_news
```

**compose 网络内服务名解析规则**：
- 所有服务在同一个 compose 网络内
- 服务间通过服务名（如 `postgres`、`redis`）互相访问
- 容器内不使用 `localhost`，因为 `localhost` 指向容器自身

### 测试分类

#### 1. 单元测试

针对具体示例和边界情况：

- `/health` 接口返回 200
- `/v1/news` 接口返回正确结构
- `/v1/news?limit=100` 返回 400，error.code 为 VALIDATION_ERROR
- `/v1/news?limit=0` 返回 400
- `/v1/news?limit=-1` 返回 400
- 游标格式无效时返回 400，error.code 为 INVALID_CURSOR

#### 2. 属性测试

针对通用属性，每个属性测试至少运行 100 次迭代：

- **Property 1**: URL 唯一约束
  - Tag: **Feature: news-app-backend, Property 1: URL 唯一约束**
  
- **Property 2**: 新闻列表排序正确性
  - Tag: **Feature: news-app-backend, Property 2: 新闻列表排序正确性**
  
- **Property 3**: limit 参数范围验证
  - Tag: **Feature: news-app-backend, Property 3: limit 参数范围验证**
  
- **Property 4**: 游标分页正确性
  - Tag: **Feature: news-app-backend, Property 4: 游标分页正确性**
  
- **Property 5**: 成功响应格式一致性
  - Tag: **Feature: news-app-backend, Property 5: 成功响应格式一致性**
  
- **Property 6**: 错误响应格式一致性
  - Tag: **Feature: news-app-backend, Property 6: 错误响应格式一致性**
  
- **Property 7**: 种子脚本幂等性
  - Tag: **Feature: news-app-backend, Property 7: 种子脚本幂等性**

### 测试配置

```python
# conftest.py
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

# 测试数据库连接串 - 使用 compose 服务名 postgres
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql://test:test@postgres:5432/test_news"
)


@pytest.fixture(scope="session")
def engine():
    return create_engine(TEST_DATABASE_URL)


@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
```

### 质量闸门命令

```makefile
# Makefile
.PHONY: test lint fmt

test:
	docker compose -f infra/docker-compose.yml run --rm api pytest

lint:
	docker compose -f infra/docker-compose.yml run --rm api ruff check .

fmt:
	docker compose -f infra/docker-compose.yml run --rm api ruff format .
```


## 实现验收清单

以下验收项必须全部通过，实现才算完成。

### 时间格式验收

| 验收项 | 验收方法 |
|--------|----------|
| `/health` 响应中 `timestamp` 格式为 `Z` 结尾 | 正则匹配 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` |
| `/v1/news` 响应中 `items[*].published_at` 格式为 `Z` 结尾 | 正则匹配 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$` |
| 响应中不得出现 `+00:00` 格式 | 响应 JSON 中不包含 `+00:00` 字符串 |

### cursor 验收

| 验收项 | 验收方法 |
|--------|----------|
| `cursor=not_base64!!` 返回 400 + INVALID_CURSOR | 请求 `/v1/news?cursor=not_base64!!`，断言 status=400, error.code=INVALID_CURSOR |
| `cursor` 包含空格时返回 400 | 请求 `/v1/news?cursor=abc%20def`，断言 status=400 |
| `cursor` 缺 padding 时返回 400 | 请求 `/v1/news?cursor=abc`，断言 status=400 |
| 非法 cursor 不得返回 500 | 任何非法 cursor 输入，status 必须为 400 |
| `meta.next_cursor` 仅包含 URL-safe 字符 | 正则匹配 `^[A-Za-z0-9_-]*=*$` |

### /ready 验收

| 验收项 | 验收方法 |
|--------|----------|
| DB 和 Redis 都正常时返回 200 | 启动所有服务后请求 `/ready`，断言 status=200 |
| 断开 Redis 时返回 503 | 停止 Redis 容器后请求 `/ready`，断言 status=503, error.code=INTERNAL_ERROR |
| 断开 DB 时返回 503 | 停止 Postgres 容器后请求 `/ready`，断言 status=503, error.code=INTERNAL_ERROR |

### 错误码验收

| 验收项 | 验收方法 |
|--------|----------|
| `limit=100` 返回 400 + VALIDATION_ERROR | 请求 `/v1/news?limit=100`，断言 status=400, error.code=VALIDATION_ERROR |
| `limit=0` 返回 400 + VALIDATION_ERROR | 请求 `/v1/news?limit=0`，断言 status=400, error.code=VALIDATION_ERROR |
| 非法 cursor 返回 400 + INVALID_CURSOR | 请求 `/v1/news?cursor=invalid`，断言 status=400, error.code=INVALID_CURSOR |

### SQLAlchemy 2.x 验收

| 验收项 | 验收方法 |
|--------|----------|
| 所有 raw SQL 使用 `text()` 包装 | 代码审查：`execute("SELECT 1")` 必须改为 `execute(text("SELECT 1"))` |
| 启动和 /ready 不因 SQLAlchemy 2.x 报错 | 启动服务后请求 `/health` 和 `/ready`，无 500 错误 |

### UTC 时区验收

| 验收项 | 验收方法 |
|--------|----------|
| PostgreSQL 时区为 UTC | 连接数据库执行 `SHOW timezone`，结果为 `UTC` |
| cursor 构建时先转 UTC | 代码审查：`_build_cursor` 包含 `astimezone(timezone.utc)` |
| 分页无时区偏移导致的错页/重复 | 属性测试：分页遍历所有数据，无重复无遗漏 |
