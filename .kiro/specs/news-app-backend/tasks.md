# Implementation Plan: News APP Backend

## Overview

本实现计划将新闻 APP 后端设计转化为可执行的编码任务。采用增量开发方式，每个任务都建立在前一个任务的基础上，确保代码始终可运行。

技术栈：Python + FastAPI + PostgreSQL + Redis + Alembic + pytest + hypothesis + ruff

## Tasks

- [x] 1. 项目结构与基础配置
  - [x] 1.1 创建项目目录结构
    - 创建 `backend/app/`、`backend/tests/`、`infra/`、`scripts/` 目录
    - 创建 `__init__.py` 文件
    - _Requirements: 9.1, 9.2, 9.3, 9.4_
  - [x] 1.2 创建配置管理模块
    - 创建 `backend/app/config.py`，使用 Pydantic Settings v2
    - 字段：`database_url`、`redis_url`、`debug`
    - 使用 `model_config = SettingsConfigDict(env_file=".env", extra="ignore")`
    - _Requirements: 1.3_
  - [x] 1.3 创建 `.env.example` 和 `pyproject.toml`
    - 定义环境变量模板
    - 配置 ruff、pytest 等工具
    - 锁定依赖版本
    - dev/test 依赖必须包含 `hypothesis`，并配置：
      - 最大例数：`max_examples=100`（默认）
      - 超时设置：`deadline=None` 或合理值（避免 CI 超时）
      - 数据库标记：`@settings(suppress_health_check=[HealthCheck.too_slow])`（如需要）
    - _Requirements: 1.3, 9.5_

- [x] 2. Docker Compose 基础设施
  - [x] 2.1 创建 docker-compose.yml
    - 配置 PostgreSQL 服务（设置 `TZ: UTC`、`PGTZ: UTC`）
    - 配置 Redis 服务
    - 配置 API 服务（依赖 DB 和 Redis）
    - 所有服务在同一网络内
    - _Requirements: 1.1, 1.2, 1.5_
  - [x] 2.2 创建 Dockerfile
    - 基于 Python 官方镜像
    - 安装依赖
    - 配置启动命令
    - _Requirements: 1.4_
  - [x] 2.3 创建 Makefile
    - 定义 `up`、`down`、`test`、`lint`、`fmt`、`migrate`、`seed` 命令
    - _Requirements: 7.5_

- [x] 3. 数据库连接与模型
  - [x] 3.1 创建数据库连接模块
    - 创建 `backend/app/database.py`
    - 配置 SQLAlchemy engine 和 session
    - 实现 `get_db` 依赖注入函数
    - _Requirements: 1.5_
  - [x] 3.2 创建 Article 模型
    - 创建 `backend/app/models/article.py`
    - 定义 articles 表结构（id、title、source、url、published_at、summary、created_at）
    - `created_at` 使用 `server_default=func.now()`
    - url 字段设置 `unique=True`
    - _Requirements: 2.1, 2.2_
  - [x] 3.3 配置 Alembic 迁移
    - 初始化 Alembic
    - 创建初始迁移文件（创建 articles 表）
    - 创建分页查询复合索引：`(published_at DESC, id DESC)`
    - _Requirements: 2.3, 2.4_

- [x] 4. Checkpoint - 基础设施验证
  - 执行 `docker-compose up`，确保三个容器都运行
  - 执行迁移，确保 articles 表创建成功
  - 确保 url 唯一约束生效
  - 执行 `SHOW timezone;` 验证 PostgreSQL 时区必须返回 `UTC`
  - 若验证失败：必须输出失败原因、定位步骤、最小修复方案，并立即修复后重新执行验证，直到通过

- [x] 5. 统一响应格式与 Schema
  - [x] 5.1 创建统一响应模型
    - 创建 `backend/app/schemas/base.py`
    - 定义 `ErrorDetail`、`Meta`、`ApiResponse` 模型
    - `meta` 使用 `Field(default_factory=Meta)`
    - _Requirements: 5.1, 5.2, 5.3_
  - [x] 5.2 创建 Article Schema
    - 创建 `backend/app/schemas/article.py`
    - 定义 `ArticleResponse`、`ArticleListData` 模型
    - 使用 `field_serializer` 序列化 `published_at` 为 ISO 8601 UTC + Z 格式
    - _Requirements: 4.7_
  - [x] 5.3 创建 Health Schema
    - 创建 `backend/app/schemas/health.py`
    - 定义 `HealthData`、`ReadyData` 模型
    - 对 `timestamp` 使用 `field_serializer` 输出 ISO 8601 UTC + Z 格式
    - _Requirements: 3.2, 3.3_

- [x] 6. Repository 层实现
  - [x] 6.1 创建 Article Repository
    - 创建 `backend/app/repositories/article.py`
    - 实现 `get_list` 方法（keyset pagination）
    - 实现 `_parse_cursor` 方法：
      - 使用 `base64.urlsafe_b64decode()` 解码
      - 解码后格式：`timestamp|uuid`，timestamp 必须以 `Z` 结尾
      - 捕获 `binascii.Error`/`ValueError`/`UnicodeDecodeError` → `InvalidCursorError`
    - 实现 `_build_cursor` 方法（URL-safe base64 编码，先转 UTC）
    - 定义 `InvalidCursorError` 异常
    - _Requirements: 4.2, 4.5_

- [x] 7. Service 层实现
  - [x] 7.1 创建 Article Service
    - 创建 `backend/app/services/article.py`
    - 实现 `get_news_list` 方法
    - 调用 Repository 获取数据，转换为 Schema
    - _Requirements: 4.1, 8.1_

- [x] 8. API 路由实现
  - [x] 8.1 创建 Request ID 中间件
    - 创建 `backend/app/middleware/request_id.py`
    - 生成 UUID 作为 request_id
    - 添加到响应头 `X-Request-ID`
    - _Requirements: 8.4_
  - [x] 8.2 创建 Health Router
    - 创建 `backend/app/routers/health.py`
    - 实现 `GET /health`（仅检查进程存活）
    - 实现 `GET /ready`（检查 DB 和 Redis 连通性，使用 `text()` 和 `redis.ping()`）
    - _Requirements: 3.1, 3.2, 3.3_
  - [x] 8.3 创建 News Router
    - 创建 `backend/app/routers/news.py`
    - 实现 `GET /v1/news`
    - 参数验证：`limit` 范围 1-50，`cursor` 可选
    - 捕获 `InvalidCursorError` 返回 400 + INVALID_CURSOR
    - _Requirements: 4.1, 4.3, 4.4, 4.6_
  - [x] 8.4 创建应用入口
    - 创建 `backend/app/main.py`
    - 配置 lifespan（启动时 `wait_for_db`，使用 `text()`）
    - 注册中间件和路由
    - 配置异常处理器（VALIDATION_ERROR、INTERNAL_ERROR）
    - _Requirements: 1.4, 8.3_
  - [x] 8.5 配置结构化日志
    - 日志输出包含 `request_id`
    - 每个请求记录：`method`、`path`、`status_code`、`latency`、`request_id`
    - 日志格式使用 JSON 结构化输出
    - _Requirements: 8.4, 8.5_

- [x] 9. Checkpoint - API 验证
  - 启动服务，测试 `/health` 返回 200
  - 测试 `/ready` 返回 200（DB 和 Redis 都正常）
  - 测试 `/v1/news` 返回空列表
  - 测试 `/v1/news?limit=100` 返回 400
  - 验证 `/health` 响应中 `timestamp` 格式为 Z 结尾（不含 `+00:00`）
  - 若验证失败：必须输出失败原因并立即修复

- [x] 10. Seed 数据脚本
  - [x] 10.1 创建 seed 脚本
    - 创建 `scripts/seed.py`
    - 插入 10 条假新闻数据
    - 使用 upsert 或捕获唯一冲突，支持重复执行
    - 通过 `make seed` 在 api 容器内执行
    - 复用 `backend/app/config.py` 读取环境变量
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 11. 测试实现
  - [x] 11.1 创建测试配置
    - 创建 `backend/tests/conftest.py`
    - 配置测试数据库连接（使用 `postgres` 服务名）
    - 配置 fixtures（engine、db_session、client）
    - _Requirements: 7.4_
  - [x] 11.2 创建测试数据工厂
    - 创建 `backend/tests/factories.py` 或在 `conftest.py` 中定义
    - 提供批量插入 article 的工厂函数/fixture
    - 数据包含不同 `published_at`、相同 `published_at` 不同 `id`、不同 `source`
    - _Requirements: 7.2_
  - [x] 11.3 创建 Health 测试
    - 创建 `backend/tests/test_health.py`
    - 测试 `/health` 返回 200
    - 测试响应结构符合统一格式
    - 测试 `timestamp` 格式为 Z 结尾
    - _Requirements: 7.1_
  - [x] 11.4 创建 News 测试
    - 创建 `backend/tests/test_news.py`
    - 测试 `/v1/news` 成功场景
    - 测试响应结构、items 数量
    - 测试 `published_at` 格式为 Z 结尾
    - 测试排序正确性
    - _Requirements: 7.2_
  - [x] 11.5 创建参数验证测试
    - 测试 `/v1/news?limit=100` 返回 400 + VALIDATION_ERROR
    - 测试 `/v1/news?limit=0` 返回 400
    - 测试 `/v1/news?limit=-1` 返回 400
    - _Requirements: 7.3_
  - [x] 11.6 创建 cursor 验证测试
    - 测试非法 cursor 返回 400 + INVALID_CURSOR
    - 测试 `cursor=not_base64!!` 返回 400
    - 测试 cursor 包含空格返回 400
    - 确保非法 cursor 不返回 500
    - _Requirements: 4.4, 8.3_
  - [x] 11.7 创建 Ready 失败测试
    - 使用 `monkeypatch` mock DB/Redis 检查函数
    - mock DB 检查抛异常 → 断言 `/ready` 返回 503 + INTERNAL_ERROR
    - mock Redis 检查抛异常 → 断言 `/ready` 返回 503 + INTERNAL_ERROR
    - _Requirements: 3.2, 3.3_
  - [x] 11.8 创建属性测试 - URL 唯一约束
    - **Property 1: URL 唯一约束**
    - **Validates: Requirements 2.2, 2.5**
  - [x] 11.9 创建属性测试 - 新闻列表排序
    - **Property 2: 新闻列表排序正确性**
    - **Validates: Requirements 4.2**
  - [x] 11.10 创建属性测试 - limit 参数验证
    - **Property 3: limit 参数范围验证**
    - **Validates: Requirements 4.3, 4.4**
  - [x] 11.11 创建属性测试 - 游标分页
    - **Property 4: 游标分页正确性**
    - 使用测试数据工厂生成多条数据
    - **Validates: Requirements 4.5**
  - [x] 11.12 创建属性测试 - 成功响应格式
    - **Property 5: 成功响应格式一致性**
    - **Validates: Requirements 4.6, 4.7, 4.8, 5.1, 5.3**
  - [x] 11.13 创建属性测试 - 错误响应格式
    - **Property 6: 错误响应格式一致性**
    - **Validates: Requirements 5.2, 8.3**
  - [x] 11.14 创建属性测试 - 种子脚本幂等性
    - **Property 7: 种子脚本幂等性**
    - **Validates: Requirements 6.2**

- [x] 12. 文档与最终验证
  - [x] 12.1 创建 README.md
    - 启动命令说明
    - 环境变量说明
    - 如何跑测试
    - 如何生成迁移
    - _Requirements: 7.6_
  - [x] 12.2 最终验证
    - 新环境克隆项目
    - 仅通过 README 步骤完成启动、迁移、seed、测试
    - 验证所有测试通过
    - _Requirements: 7.6_

- [x] 13. Final Checkpoint
  - 确保所有测试通过
  - 确保 `make lint` 无错误
  - 确保实现验收清单全部通过
  - 若验证失败：必须输出失败原因并立即修复

## Notes

- 所有任务都是必需的，包括属性测试
- 每个任务都引用了具体的需求条款，确保可追溯性
- Checkpoint 任务用于增量验证，确保每个阶段都可运行
- 属性测试验证通用正确性属性，单元测试验证具体示例和边界情况
