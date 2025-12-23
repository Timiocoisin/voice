"""
登录尝试记录模块，用于防止暴力破解
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

# 内存存储登录尝试记录（生产环境建议使用 Redis）
_login_attempts: Dict[str, Dict] = {}

# 配置
MAX_ATTEMPTS = 5  # 最大尝试次数
LOCKOUT_DURATION = timedelta(minutes=15)  # 锁定时长（15分钟）


def record_failed_attempt(email: str) -> None:
    """记录一次失败的登录尝试"""
    now = datetime.now()
    if email not in _login_attempts:
        _login_attempts[email] = {
            "count": 0,
            "first_attempt": now,
            "last_attempt": now,
            "locked_until": None
        }
    
    record = _login_attempts[email]
    record["count"] += 1
    record["last_attempt"] = now
    
    # 如果达到最大尝试次数，锁定账户
    if record["count"] >= MAX_ATTEMPTS:
        record["locked_until"] = now + LOCKOUT_DURATION
        logging.warning("账户 %s 因多次登录失败被锁定15分钟", email)
    
    # 清理过期记录（超过锁定时长2倍的时间）
    if record["last_attempt"] < now - LOCKOUT_DURATION * 2:
        _login_attempts.pop(email, None)


def clear_attempts(email: str) -> None:
    """清除登录尝试记录（登录成功时调用）"""
    _login_attempts.pop(email, None)


def is_locked(email: str) -> Tuple[bool, Optional[str]]:
    """
    检查账户是否被锁定
    
    Returns:
        (is_locked, message) - 是否锁定，锁定消息
    """
    if email not in _login_attempts:
        return False, None
    
    record = _login_attempts[email]
    now = datetime.now()
    
    # 检查是否在锁定期内
    if record.get("locked_until") and now < record["locked_until"]:
        remaining = (record["locked_until"] - now).total_seconds()
        minutes = int(remaining / 60) + 1
        return True, f"账户因多次登录失败已被锁定，请 {minutes} 分钟后再试"
    
    # 如果锁定已过期，清除记录
    if record.get("locked_until") and now >= record["locked_until"]:
        _login_attempts.pop(email, None)
        return False, None
    
    # 检查尝试次数
    if record["count"] >= MAX_ATTEMPTS:
        # 如果还没有设置锁定时间，现在设置
        if not record.get("locked_until"):
            record["locked_until"] = now + LOCKOUT_DURATION
        remaining = LOCKOUT_DURATION.total_seconds()
        minutes = int(remaining / 60) + 1
        return True, f"账户因多次登录失败已被锁定，请 {minutes} 分钟后再试"
    
    return False, None


def get_remaining_attempts(email: str) -> int:
    """获取剩余尝试次数"""
    if email not in _login_attempts:
        return MAX_ATTEMPTS
    
    record = _login_attempts[email]
    return max(0, MAX_ATTEMPTS - record["count"])

