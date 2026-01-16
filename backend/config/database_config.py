"""数据库配置文件

支持从环境变量读取配置，所有配置必须通过环境变量设置。
生产环境建议使用环境变量或加密配置文件。
"""
import os
from typing import Dict, Any
from backend.config.env_loader import *  # 确保环境变量已加载

# 数据库配置字典（全部从环境变量读取，无默认值）
DATABASE_CONFIG: Dict[str, Any] = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "database": os.getenv("DB_NAME"),
    "charset": os.getenv("DB_CHARSET", "utf8mb4"),
    "autocommit": False,
}

def get_database_config() -> Dict[str, Any]:
    """获取数据库配置
    
    Returns:
        数据库配置字典，可直接用于 pymysql.connect()
    
    Raises:
        ValueError: 如果缺少必需的配置项
    """
    # 验证必需的配置项
    required_keys = ["host", "user", "password", "database"]
    missing_keys = [key for key in required_keys if not DATABASE_CONFIG.get(key)]
    if missing_keys:
        raise ValueError(f"缺少必需的数据库配置项: {', '.join(missing_keys)}。请检查 .env 文件或环境变量设置。")
    
    return DATABASE_CONFIG.copy()
