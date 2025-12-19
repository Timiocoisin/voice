"""数据库查询异步线程模块"""
from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional, Dict, Any, Callable
import logging
from backend.database.database_manager import DatabaseManager


class DatabaseQueryThread(QThread):
    """数据库查询异步线程
    
    用于在后台线程执行数据库查询操作，避免阻塞UI线程。
    注意：每个线程会创建独立的数据库连接，因为PyMySQL连接不是线程安全的。
    """
    query_finished = pyqtSignal(object)  # 查询结果信号
    query_error = pyqtSignal(str)  # 查询错误信号
    
    def __init__(self, query_method_name: str, *args, **kwargs):
        """
        Args:
            query_method_name: 数据库管理器方法名（如 'get_user_by_email'）
            *args, **kwargs: 传递给查询方法的参数
        """
        super().__init__()
        self.query_method_name = query_method_name
        self.query_args = args
        self.query_kwargs = kwargs
        self.db_manager = None
    
    def run(self):
        """在线程中执行查询"""
        try:
            # 在线程中创建新的数据库连接
            self.db_manager = DatabaseManager()
            # 获取查询方法
            query_method = getattr(self.db_manager, self.query_method_name, None)
            if not query_method:
                raise AttributeError(f"DatabaseManager 没有方法: {self.query_method_name}")
            
            # 执行查询
            result = query_method(*self.query_args, **self.query_kwargs)
            self.query_finished.emit(result)
        except Exception as e:
            error_msg = f"数据库查询失败: {str(e)}"
            logging.error(error_msg)
            self.query_error.emit(error_msg)
        finally:
            # 清理数据库连接
            if self.db_manager:
                try:
                    self.db_manager.close()
                except Exception:
                    pass
