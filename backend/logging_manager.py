"""全局日志配置模块。

统一在此处配置 logging，其他模块只需 `import logging` 即可使用：

    from backend.logging_manager import setup_logging  # noqa: F401
    import logging

    logger = logging.getLogger(__name__)
    logger.info("something...")

这样可以避免在多个文件中重复调用 ``logging.basicConfig``。

本模块将日志拆分为三类文件：
- logs/info.log      正常运行日志（INFO 及以上，包含 WARNING、ERROR 等）
- logs/error.log     错误日志（ERROR 及以上）
- logs/exception.log 异常日志（仅记录带有异常堆栈的记录，例如 logger.exception）
"""

import logging
import logging.handlers
import os
from typing import Any


class _ExceptionFilter(logging.Filter):
    """仅通过带有异常信息的日志记录（用于 exception.log）。"""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        return bool(record.exc_info)


def setup_logging(level: int = logging.INFO) -> None:
    """初始化全局日志配置（幂等，多次调用只生效一次）。"""
    if getattr(setup_logging, "_configured", False):
        return

    # 确保日志目录存在：放在后端代码目录下 backend/logs
    backend_dir = os.path.dirname(__file__)
    log_dir = os.path.join(backend_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # 根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # 清理可能已有的默认 handler，避免重复输出
    for h in list(root_logger.handlers):
        root_logger.removeHandler(h)

    # 日志格式
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # 1）控制台输出（方便开发调试）
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 2）正常日志：info.log（INFO 及以上）
    info_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "info.log"),
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding="utf-8",
    )
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)
    root_logger.addHandler(info_handler)

    # 3）错误日志：error.log（ERROR 及以上）
    error_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    root_logger.addHandler(error_handler)

    # 4）异常日志：exception.log（仅记录带异常堆栈的记录）
    exception_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, "exception.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    exception_handler.setLevel(logging.ERROR)
    exception_handler.setFormatter(formatter)
    exception_handler.addFilter(_ExceptionFilter())
    root_logger.addHandler(exception_handler)

    setup_logging._configured = True  # type: ignore[attr-defined]


# 模块导入时自动配置一次，确保主程序和后台模块均有日志输出
setup_logging()

