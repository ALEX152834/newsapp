"""
结构化日志配置模块

配置 JSON 格式的结构化日志输出，包含：
- timestamp: 时间戳
- level: 日志级别
- request_id: 请求追踪 ID
- message: 日志消息
- 其他上下文信息

Requirements: 8.4, 8.5
"""

import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.config import settings


class JsonFormatter(logging.Formatter):
    """
    JSON 格式化器
    
    将日志记录格式化为 JSON 结构，包含：
    - timestamp: ISO 8601 UTC 格式时间戳
    - level: 日志级别
    - logger: 日志器名称
    - message: 日志消息
    - 其他 extra 字段
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON 字符串"""
        import json
        
        # 基础日志字段
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # 添加 extra 字段（排除标准 LogRecord 属性）
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "taskName", "message"
        }
        
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                # 确保值可以被 JSON 序列化
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    log_data[key] = str(value)
        
        # 添加异常信息（如果有）
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging() -> None:
    """
    配置应用日志
    
    设置 JSON 结构化日志输出到 stdout。
    日志级别根据 debug 配置决定。
    """
    # 确定日志级别
    log_level = logging.DEBUG if settings.debug else logging.INFO
    
    # 创建 JSON 格式化器
    json_formatter = JsonFormatter()
    
    # 创建 stdout handler
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(json_formatter)
    stdout_handler.setLevel(log_level)
    
    # 配置根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # 清除现有 handlers，避免重复
    root_logger.handlers.clear()
    root_logger.addHandler(stdout_handler)
    
    # 配置 uvicorn 日志器使用相同格式
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error"]:
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.addHandler(stdout_handler)
        uvicorn_logger.setLevel(log_level)
    
    # 配置 sqlalchemy 日志器（仅在 debug 模式下输出 SQL）
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_logger.handlers.clear()
    if settings.debug:
        sqlalchemy_logger.addHandler(stdout_handler)
        sqlalchemy_logger.setLevel(logging.INFO)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)
