# Makefile for News APP Backend
# 提供一键命令用于开发、测试和部署

.PHONY: up down test lint fmt migrate seed help

# Docker Compose 文件路径
COMPOSE_FILE := infra/docker-compose.yml

# 帮助信息
help:
	@echo "News APP Backend - 可用命令:"
	@echo ""
	@echo "  make up       - 启动所有服务 (PostgreSQL, Redis, API)"
	@echo "  make down     - 停止所有服务"
	@echo "  make test     - 在 api 容器中运行 pytest 测试"
	@echo "  make lint     - 在 api 容器中运行 ruff 代码检查"
	@echo "  make fmt      - 在 api 容器中运行 ruff 代码格式化"
	@echo "  make migrate  - 在 api 容器中运行 Alembic 数据库迁移"
	@echo "  make seed     - 在 api 容器中运行种子数据脚本"
	@echo ""

# 启动所有服务
up:
	docker compose -f $(COMPOSE_FILE) up -d

# 停止所有服务
down:
	docker compose -f $(COMPOSE_FILE) down

# 运行测试
# 显式注入 TEST_DATABASE_URL 确保连接到 test_postgres 测试库
test:
	docker compose -f $(COMPOSE_FILE) run --rm -e TEST_DATABASE_URL=postgresql://test:test@test_postgres:5432/test api pytest -q

# 代码检查
lint:
	docker compose -f $(COMPOSE_FILE) run --rm api ruff check .

# 代码格式化
fmt:
	docker compose -f $(COMPOSE_FILE) run --rm api ruff format .

# 运行数据库迁移
migrate:
	docker compose -f $(COMPOSE_FILE) run --rm api alembic upgrade head

# 运行种子数据脚本
# 注意：需要将 scripts 目录挂载到容器中，或在 docker-compose.yml 中添加挂载配置
seed:
	docker compose -f $(COMPOSE_FILE) run --rm -v $(PWD)/scripts:/app/scripts api python /app/scripts/seed.py
