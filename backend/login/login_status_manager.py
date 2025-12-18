"""应用内登录状态管理（进程内简单状态中心）。

当前实现为内存级别的全局状态，主要用于：
- 判断用户是否已登录（避免重复弹出登录框）
- 为 UI 层提供当前用户的基本信息（id、username）

后续如需持久化或多进程共享，可在此模块内扩展实现。
"""

from typing import Optional, Tuple, Dict, Any


_current_user: Optional[Dict[str, Any]] = None


def save_login_status(user_id: int, username: str) -> None:
    """保存当前登录用户的基础信息到内存状态中心。"""
    global _current_user
    _current_user = {
        "user_id": user_id,
        "username": username,
    }


def check_login_status() -> Tuple[bool, Optional[int], Optional[str]]:
    """检查是否已有登录用户。

    Returns:
        (is_logged_in, user_id, username)
    """
    if not _current_user:
        return False, None, None
    return True, _current_user.get("user_id"), _current_user.get("username")


def clear_login_status() -> None:
    """清除当前登录状态。"""
    global _current_user
    _current_user = None
