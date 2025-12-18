"""全局日志配置模块。

统一在此处配置 logging，其他模块只需 `import logging` 即可使用：

    from backend.logging_manager import setup_logging  # noqa: F401
    import logging

    logger = logging.getLogger(__name__)
    logger.info("something...")

这样可以避免在多个文件中重复调用 ``logging.basicConfig``。
"""

import logging


def setup_logging(level: int = logging.INFO) -> None:
    """初始化全局日志配置（幂等，多次调用只生效一次）。"""
    if getattr(setup_logging, "_configured", False):
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    setup_logging._configured = True  # type: ignore[attr-defined]


# 模块导入时自动配置一次，确保主程序和后台模块均有日志输出
setup_logging()

