"""
资源加载器模块
用于从本地文件加载图标和背景图片
"""
from pathlib import Path
from typing import Optional
import logging
from backend.logging_manager import setup_logging  # noqa: F401

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 兼容旧结构（根目录下的 resources）与新结构（client/resources）
_ROOT_RESOURCES_DIR = PROJECT_ROOT / "resources"
_CLIENT_RESOURCES_DIR = PROJECT_ROOT / "client" / "resources"

# 优先级：根目录 resources -> client/resources
_CANDIDATE_RESOURCE_DIRS = [
    _ROOT_RESOURCES_DIR,
    _CLIENT_RESOURCES_DIR,
]


def _resolve_resource(subdir: str, filename: str) -> Optional[Path]:
    """
    在候选资源目录中解析文件路径，找到第一个存在的文件。
    """
    for base in _CANDIDATE_RESOURCE_DIRS:
        if not base:
            continue
        if subdir == "icons":
            file_path = base / "icons" / filename
        elif subdir == "images":
            file_path = base / "images" / filename
        else:
            # 兼容旧格式，直接放在 resources 根目录
            file_path = base / filename

        if file_path.exists():
            return file_path

    # 所有候选目录均未找到
    logging.warning(
        "资源文件不存在: %s (subdir=%s, candidates=%s)",
        filename,
        subdir,
        ", ".join(str(d) for d in _CANDIDATE_RESOURCE_DIRS),
    )
    return None

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
    return _resolve_resource(subdir, filename)


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

