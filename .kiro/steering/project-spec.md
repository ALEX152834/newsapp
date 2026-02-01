# 新闻 APP 后端工程规范

## 本阶段目标

本地 `docker-compose up` 后能启动 Postgres、Redis、API（FastAPI），并提供：
- `GET /health`
- `GET /v1/news`（从数据库读 articles，允许先用 seed 数据）

**不做**：登录、推送、AI 总结、本地定位、复杂推荐、全文抓取。

## 技术约束

- 所有技术选择与用法必须以官方文档为准；需要做决定时，优先选择"稳定、主流、维护活跃"的方案，并把版本锁定在依赖文件里
- 后端使用 Python + FastAPI
- 数据库使用 PostgreSQL
- 缓存/队列预留 Redis（本阶段不要求用上，但必须启动并可连通）
- 使用 Pydantic 做请求/响应模型
- 所有接口返回必须有一致的响应结构（见"接口契约"）
- 必须有数据库迁移（Alembic 或等价方案）；禁止手改数据库而不写迁移
- 必须有基础自动化测试（pytest）；至少覆盖：`/health`、`/v1/news` 的成功路径与参数校验失败路径
- 必须有静态检查与格式化（例如 ruff + formatter）；CI/本地命令必须能一键跑完检查与测试
- 必须提供 README.md：包含启动命令、环境变量说明、如何跑测试、如何生成迁移

## 代码规范

- 分层清晰：API 层（路由）不直接写 SQL；数据访问单独封装；业务逻辑单独封装
- 类型提示必须完整（mypy 可选，但类型注解必需）
- 任何可能失败的外部输入（query 参数、URL 字符串、时间字符串）必须校验并返回 400
- 日志必须结构化，至少包含：timestamp、level、request_id（可用中间件生成）
- 禁止在日志/报错中输出敏感信息（密码、token、连接串全量）

## 接口契约（统一返回格式）

成功：
```json
{ "data": <payload>, "meta": {...}, "error": null }
```

失败：
```json
{ "data": null, "meta": {...}, "error": { "code": "...", "message": "...", "details": ... } }
```

分页：`meta` 必须包含 `next_cursor`（没有则为 null）与 `count`。

## 目录结构约束

必须分出：
- `backend/app` — 代码
- `backend/tests` — 测试
- `infra` — compose/环境
- `scripts` — seed/工具
- `.env.example`

禁止把 compose、脚本、源代码混在一个目录里。

## 可复现性

- 依赖必须锁版本
- 提供固定的启动方式（make 或脚本均可）
- `docker-compose up` 是唯一必需入口，不依赖本机装数据库
