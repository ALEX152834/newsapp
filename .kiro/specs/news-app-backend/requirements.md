# Requirements Document

## Introduction

本文档定义了新闻 APP 后端系统的需求规范。该系统是一个基于 FastAPI 的后端服务，通过 docker-compose 启动 PostgreSQL、Redis 和 API 服务，提供新闻列表查询功能。本阶段聚焦于最小可行产品（MVP），实现基础运行环境、数据模型、核心 API、种子数据和质量保障。

## Glossary

- **System**: 新闻 APP 后端系统整体
- **API_Service**: FastAPI 应用服务
- **Database**: PostgreSQL 数据库服务
- **Cache**: Redis 缓存服务
- **Article**: 新闻文章数据实体
- **Health_Endpoint**: 健康检查接口 `/health`
- **News_Endpoint**: 新闻列表接口 `/v1/news`
- **Migration**: Alembic 数据库迁移
- **Seed_Script**: 种子数据脚本
- **Cursor_Pagination**: 基于游标的分页机制

## Requirements

### Requirement 1: 基础运行环境

**User Story:** As a 开发者, I want 通过 docker-compose 一键启动所有服务, so that 我可以快速搭建本地开发环境。

#### Acceptance Criteria

1. WHEN docker-compose up 命令执行后, THE System SHALL 启动 PostgreSQL、Redis、FastAPI 三个容器并使其处于运行状态
2. THE System SHALL 将所有服务配置在同一个 compose 网络内，使服务间可互相访问
3. THE System SHALL 从环境变量读取所有配置，并提供 .env.example 模板文件
4. WHEN API_Service 容器启动时, THE System SHALL 自动执行数据库就绪检查，等待 Database 可用后再启动应用
5. WHEN 所有容器启动完成后, THE API_Service SHALL 能成功连接 Database 和 Cache

### Requirement 2: 数据库模型

**User Story:** As a 开发者, I want 建立 articles 表结构, so that 系统可以存储和查询新闻数据。

#### Acceptance Criteria

1. THE Database SHALL 包含 articles 表，具有以下字段：id（主键）、title（非空）、source（非空）、url（非空唯一）、published_at（UTC 时间）、summary（可空）、created_at（默认当前时间）
2. THE Database SHALL 对 url 字段建立唯一约束，用于新闻去重
3. THE Migration SHALL 通过 Alembic 迁移文件创建表结构，禁止手动建表
4. WHEN docker-compose up 执行后, THE System SHALL 支持一键运行迁移命令
5. IF 插入重复 url 的记录, THEN THE Database SHALL 拒绝插入并返回唯一约束冲突错误

### Requirement 3: 健康检查接口

**User Story:** As a 运维人员, I want 通过健康检查接口监控服务状态, so that 我可以及时发现服务异常。

#### Acceptance Criteria

1. WHEN 客户端请求 GET /health, THE Health_Endpoint SHALL 返回 HTTP 200 状态码
2. THE Health_Endpoint SHALL 返回符合统一响应格式的 JSON，包含服务状态和时间戳
3. THE Health_Endpoint SHALL 在 data 字段中包含 status 和 timestamp 信息

### Requirement 4: 新闻列表接口

**User Story:** As a 客户端开发者, I want 通过 API 获取新闻列表, so that 我可以在 APP 中展示新闻内容。

#### Acceptance Criteria

1. WHEN 客户端请求 GET /v1/news, THE News_Endpoint SHALL 从 articles 表读取新闻列表
2. THE News_Endpoint SHALL 按 published_at DESC, id DESC 排序返回结果
3. THE News_Endpoint SHALL 支持 limit 查询参数，默认值为 20，有效范围为 1-50
4. IF limit 参数超出有效范围（小于 1 或大于 50）, THEN THE News_Endpoint SHALL 返回 HTTP 400 错误
5. THE News_Endpoint SHALL 支持 cursor 查询参数实现游标分页
6. THE News_Endpoint SHALL 返回符合统一响应格式的 JSON
7. THE News_Endpoint SHALL 在 data.items 中返回新闻数组，每项包含 id、title、source、url、published_at 字段
8. THE News_Endpoint SHALL 在 meta 中返回 count（本次返回数量）和 next_cursor（下一页游标，无则为 null）

### Requirement 5: 统一响应格式

**User Story:** As a 客户端开发者, I want 所有接口返回统一的响应格式, so that 我可以用统一的方式处理 API 响应。

#### Acceptance Criteria

1. WHEN 请求成功时, THE API_Service SHALL 返回格式：{ "data": <payload>, "meta": {...}, "error": null }
2. WHEN 请求失败时, THE API_Service SHALL 返回格式：{ "data": null, "meta": {...}, "error": { "code": "...", "message": "...", "details": ... } }
3. THE API_Service SHALL 对所有分页接口在 meta 中包含 next_cursor 和 count 字段

### Requirement 6: 种子数据

**User Story:** As a 开发者, I want 通过脚本插入测试数据, so that 我可以快速验证 API 功能。

#### Acceptance Criteria

1. THE Seed_Script SHALL 向 articles 表插入 5-20 条假数据
2. THE Seed_Script SHALL 支持重复执行而不产生重复数据（通过 upsert 或捕获唯一冲突跳过）
3. WHEN 执行 make seed 命令后, THE Seed_Script SHALL 完成数据插入
4. WHEN seed 完成后, THE News_Endpoint SHALL 能返回插入的数据

### Requirement 7: 测试与质量保障

**User Story:** As a 开发者, I want 有完善的测试和质量检查, so that 我可以确保代码质量和功能正确性。

#### Acceptance Criteria

1. THE System SHALL 提供 pytest 测试覆盖 /health 接口成功场景
2. THE System SHALL 提供 pytest 测试覆盖 /v1/news 接口成功场景，断言响应结构、items 数量和排序
3. THE System SHALL 提供 pytest 测试覆盖 /v1/news?limit=100 返回 400 错误的场景
4. THE System SHALL 支持在容器环境中运行测试
5. THE System SHALL 提供 make test、make lint、make fmt 一键命令
6. WHEN 新环境克隆项目后, THE System SHALL 仅通过 README 步骤即可完成启动、迁移、seed 和测试

### Requirement 8: 代码规范

**User Story:** As a 开发者, I want 代码遵循清晰的分层架构, so that 代码易于维护和扩展。

#### Acceptance Criteria

1. THE System SHALL 采用分层架构：API 层（路由）不直接写 SQL，数据访问单独封装，业务逻辑单独封装
2. THE System SHALL 对所有函数和方法提供完整的类型提示
3. WHEN 接收到非法的外部输入（query 参数、URL 字符串、时间字符串）, THE API_Service SHALL 校验并返回 HTTP 400 错误
4. THE System SHALL 使用结构化日志，包含 timestamp、level、request_id
5. THE System SHALL 禁止在日志或错误信息中输出敏感信息（密码、token、完整连接串）

### Requirement 9: 目录结构

**User Story:** As a 开发者, I want 项目有清晰的目录结构, so that 我可以快速找到相关代码。

#### Acceptance Criteria

1. THE System SHALL 将应用代码放在 backend/app 目录
2. THE System SHALL 将测试代码放在 backend/tests 目录
3. THE System SHALL 将 compose 和环境配置放在 infra 目录
4. THE System SHALL 将脚本工具放在 scripts 目录
5. THE System SHALL 在项目根目录提供 .env.example 文件
