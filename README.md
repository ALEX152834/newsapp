# News APP Backend

基于 FastAPI 的新闻 APP 后端服务，提供新闻列表查询 API。

## 技术栈

- Python 3.11+
- FastAPI
- PostgreSQL 16
- Redis
- SQLAlchemy 2.x
- Alembic (数据库迁移)
- pytest + hypothesis (测试)
- ruff (代码检查和格式化)

## 快速开始

### 前置要求

- Docker & Docker Compose

### 启动服务

```bash
# 启动所有服务 (PostgreSQL, Redis, API)
make up

# 运行数据库迁移
make migrate

# 插入种子数据
make seed
```

### 停止服务

```bash
make down
```

## 环境变量

复制 `.env.example` 为 `.env` 并根据需要修改：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DATABASE_URL | PostgreSQL 连接串 | postgresql://news:news@postgres:5432/news |
| REDIS_URL | Redis 连接串 | redis://redis:6379/0 |
| DEBUG | 调试模式 | false |

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /health | 健康检查 |
| GET | /ready | 就绪检查 (检查 DB/Redis) |
| GET | /v1/news | 获取新闻列表 |

### 新闻列表参数

- `limit`: 每页数量，范围 1-50，默认 20
- `cursor`: 分页游标，可选

## 开发命令

```bash
# 运行测试
make test

# 代码检查
make lint

# 代码格式化
make fmt

# 运行数据库迁移
make migrate

# 插入种子数据
make seed
```

## 生成新迁移

```bash
# 在 api 容器中执行
docker compose -f infra/docker-compose.yml run --rm api alembic revision --autogenerate -m "描述"
```

## 目录结构

```
├── backend/
│   ├── app/           # 应用代码
│   │   ├── models/    # SQLAlchemy 模型
│   │   ├── schemas/   # Pydantic 模型
│   │   ├── repositories/  # 数据访问层
│   │   ├── services/  # 业务逻辑层
│   │   ├── routers/   # API 路由
│   │   └── middleware/  # 中间件
│   ├── tests/         # 测试代码
│   └── alembic/       # 数据库迁移
├── infra/             # Docker Compose 配置
├── scripts/           # 工具脚本
├── .env.example       # 环境变量模板
└── Makefile           # 常用命令
```

## 响应格式

### 成功响应

```json
{
  "data": { ... },
  "meta": {
    "count": 10,
    "next_cursor": "..."
  },
  "error": null
}
```

### 错误响应

```json
{
  "data": null,
  "meta": {},
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed"
  }
}
```

## License

MIT
