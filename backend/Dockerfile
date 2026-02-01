# News APP Backend Dockerfile
# 基于 Python 3.11-slim 官方镜像
# 支持生产和开发模式（开发模式通过 volume mount 实现热重载）

FROM python:3.11-slim

# 设置环境变量
# PYTHONDONTWRITEBYTECODE: 防止 Python 写入 .pyc 文件
# PYTHONUNBUFFERED: 确保 Python 输出直接发送到终端，不缓冲
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    # pip 配置
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# - gcc: 编译某些 Python 包需要
# - libpq-dev: psycopg2 需要的 PostgreSQL 客户端库
# 安装后清理 apt 缓存以减小镜像体积
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖配置文件
COPY pyproject.toml ./

# 安装 Python 依赖
# 使用 pip install . 安装项目及其依赖
# 同时安装 dev 依赖（包含 pytest、hypothesis 等测试工具）
RUN pip install --no-cache-dir -e ".[dev]"

# 复制应用代码
# 注意：开发模式下通过 docker-compose volume mount 覆盖此目录
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
# --host 0.0.0.0: 监听所有网络接口，允许容器外访问
# --port 8000: 监听端口
# --reload: 开发模式下启用热重载（生产环境应移除此参数）
# 开发模式：通过 volume mount 挂载代码目录，配合 --reload 实现热重载
# 生产模式：移除 --reload 参数，或使用 gunicorn 替代 uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
