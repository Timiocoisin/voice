"""统一异常处理工具模块"""
import logging
import pymysql
from functools import wraps
from typing import Callable, TypeVar, Any, Optional

F = TypeVar('F', bound=Callable[..., Any])


def handle_db_error(func: F) -> F:
    """统一处理数据库错误的装饰器
    
    用法:
        @handle_db_error
        def some_database_function():
            # 数据库操作
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except pymysql.Error as e:
            logging.error(f"数据库操作失败 [{func.__name__}]: {e}", exc_info=True)
            # 显示用户友好的错误提示（如果有main_window参数）
            if args and hasattr(args[0], 'main_window'):
                from gui.custom_message_box import show_message
                show_message(args[0].main_window, "数据库操作失败，请稍后重试", "error", "错误")
            return None
        except Exception as e:
            logging.error(f"操作失败 [{func.__name__}]: {e}", exc_info=True)
            if args and hasattr(args[0], 'main_window'):
                from gui.custom_message_box import show_message
                show_message(args[0].main_window, f"操作失败: {str(e)}", "error", "错误")
            return None
    return wrapper  # type: ignore


def handle_general_error(
    default_return: Any = None,
    error_message: Optional[str] = None,
    show_to_user: bool = False
):
    """通用异常处理装饰器
    
    Args:
        default_return: 发生异常时的默认返回值
        error_message: 自定义错误消息
        show_to_user: 是否向用户显示错误消息
    
    用法:
        @handle_general_error(default_return=None, error_message="操作失败")
        def some_function():
            pass
    """
    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                msg = error_message or f"操作失败: {str(e)}"
                logging.error(f"操作失败 [{func.__name__}]: {e}", exc_info=True)
                
                if show_to_user:
                    # 尝试找到main_window对象
                    main_window = None
                    for arg in args:
                        if hasattr(arg, 'main_window'):
                            main_window = arg.main_window
                            break
                        elif hasattr(arg, '__class__') and 'MainWindow' in str(arg.__class__):
                            main_window = arg
                            break
                    
                    if main_window:
                        from gui.custom_message_box import show_message
                        show_message(main_window, msg, "error", "错误")
                
                return default_return
        return wrapper  # type: ignore
    return decorator
