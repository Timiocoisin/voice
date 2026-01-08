"""数据库配置文件

支持从环境变量读取配置，如果没有设置则使用默认配置。
生产环境建议使用环境变量或加密配置文件。
"""
import os
from typing import Dict, Any

# 数据库配置字典
DATABASE_CONFIG: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "172.16.37.39"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "123456"),
    "database": os.getenv("DB_NAME", "voice"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    "autocommit": False,
}

def get_database_config() -> Dict[str, Any]:
    """获取数据库配置
    
    Returns:
        数据库配置字典，可直接用于 pymysql.connect()
    """
    return DATABASE_CONFIG.copy()
