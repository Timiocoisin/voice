"""
资源加载器模块
用于从本地文件加载图标和背景图片
"""
import os
from pathlib import Path
from typing import Optional
import logging
from backend.logging_manager import setup_logging  # noqa: F401

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
IMAGES_DIR = RESOURCES_DIR / "images"

# 图标ID到文件路径的映射（相对路径，会在对应的目录下查找）
ICON_MAPPING = {
    1: ("icons", "close.svg"),          # 关闭图标
    2: ("icons", "diamond.svg"),        # 钻石图标
    3: ("icons", "email.svg"),          # 邮箱图标
    4: ("images", "default_avatar.png"), # 默认头像
    5: ("images", "app_icon.png"),       # 应用图标
    6: ("images", "logo.png"),           # Logo
    7: ("icons", "minimize.svg"),        # 最小化图标
    8: ("icons", "password.svg"),        # 密码图标
    9: ("icons", "headset.svg"),         # 耳机图标
    10: ("icons", "speaker.svg"),        # 喇叭图标
    11: ("icons", "username.svg"),       # 用户名图标
    12: ("icons", "code.svg"),           # 验证码图标
    13: ("icons", "vip.svg"),            # VIP图标
    14: ("images", "background.jpg"),    # 背景图片
    15: ("icons", "expression.svg"),     # 表情图标
    16: ("icons", "file.svg"),           # 文件图标
    17: ("icons", "pic.svg"),            # 图片图标
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
    
    subdir, filename = ICON_MAPPING[icon_id]
    
    # 根据子目录类型选择对应的目录
    if subdir == "icons":
        file_path = ICONS_DIR / filename
    elif subdir == "images":
        file_path = IMAGES_DIR / filename
    else:
        # 兼容旧格式，直接放在 resources 根目录
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
    # 默认头像文件可能在某些发行包中缺失，缺失时回退到应用图标
    data = load_icon_data(4)
    if data:
        return data
    logging.warning("默认头像 default_avatar.png 不存在，已回退到 app_icon.png")
    return load_icon_data(5)


def get_logo() -> Optional[bytes]:
    """
    获取Logo数据
    
    Returns:
        Logo的二进制数据
    """
    return load_icon_data(6)

