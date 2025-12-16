"""
资源加载器模块
用于从本地文件加载图标和背景图片
"""
import os
from pathlib import Path
from typing import Optional
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"

# 图标ID到文件名的映射
ICON_MAPPING = {
    1: "close.svg",          # 关闭图标
    2: "diamond.svg",        # 钻石图标
    3: "email.svg",          # 邮箱图标
    4: "default_avatar.png", # 默认头像
    5: "app_icon.png",       # 应用图标
    6: "logo.png",           # Logo
    7: "minimize.svg",       # 最小化图标
    8: "password.svg",       # 密码图标
    9: "headset.svg",        # 耳机图标
    10: "speaker.svg",       # 喇叭图标/注册密码图标
    11: "username.svg",      # 用户名图标
    12: "code.svg",          # 验证码图标
    13: "vip.svg",           # VIP图标
    14: "background.jpg",    # 背景图片
}


def get_resource_path(icon_id: int) -> Optional[Path]:
    """
    根据图标ID获取资源文件路径
    
    Args:
        icon_id: 图标ID
        
    Returns:
        资源文件路径，如果不存在则返回None
    """
    if icon_id not in ICON_MAPPING:
        logging.warning(f"未找到图标ID {icon_id} 的映射")
        return None
    
    filename = ICON_MAPPING[icon_id]
    file_path = RESOURCES_DIR / filename
    
    if not file_path.exists():
        logging.warning(f"资源文件不存在: {file_path}")
        return None
    
    return file_path


def load_icon_data(icon_id: int) -> Optional[bytes]:
    """
    根据图标ID加载图标数据（二进制）
    
    Args:
        icon_id: 图标ID
        
    Returns:
        图标的二进制数据，如果加载失败则返回None
    """
    file_path = get_resource_path(icon_id)
    if not file_path:
        return None
    
    try:
        with open(file_path, "rb") as f:
            return f.read()
    except Exception as e:
        logging.error(f"加载图标ID {icon_id} 失败: {e}")
        return None


def load_icon_path(icon_id: int) -> Optional[str]:
    """
    根据图标ID获取图标文件路径（字符串）
    
    Args:
        icon_id: 图标ID
        
    Returns:
        图标文件路径（字符串），如果不存在则返回None
    """
    file_path = get_resource_path(icon_id)
    if file_path:
        return str(file_path)
    return None


def get_default_avatar() -> Optional[bytes]:
    """
    获取默认头像数据
    
    Returns:
        默认头像的二进制数据
    """
    return load_icon_data(4)


def get_logo() -> Optional[bytes]:
    """
    获取Logo数据
    
    Returns:
        Logo的二进制数据
    """
    return load_icon_data(6)

