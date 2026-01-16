"""应用配置文件

所有配置从环境变量读取，通过 .env 文件管理。
"""
import os
from backend.config.env_loader import *  # 确保环境变量已加载

# ==================== 邮件配置 ====================
email_config = {
    'smtp_server': os.getenv("SMTP_SERVER"),
    'smtp_port': int(os.getenv("SMTP_PORT", 465)),
    'sender_email': os.getenv("SMTP_SENDER_EMAIL"),
    'sender_password': os.getenv("SMTP_SENDER_PASSWORD"),
    'sender_name': os.getenv("SMTP_SENDER_NAME", "语音转换系统")
}

# ==================== 安全配置 ====================
SECRET_KEY = os.getenv("SECRET_KEY")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# ==================== 前端配置 ====================
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL")

# 验证必需的配置项
def validate_config():
    """验证必需的配置项是否已设置"""
    required_configs = {
        "SMTP_SERVER": email_config.get('smtp_server'),
        "SMTP_SENDER_EMAIL": email_config.get('sender_email'),
        "SMTP_SENDER_PASSWORD": email_config.get('sender_password'),
        "SECRET_KEY": SECRET_KEY,
        "ENCRYPTION_KEY": ENCRYPTION_KEY,
    }
    
    missing = [key for key, value in required_configs.items() if not value]
    if missing:
        raise ValueError(f"缺少必需的环境变量配置: {', '.join(missing)}")

# 在模块加载时验证配置（可选，根据需要启用）
# validate_config()