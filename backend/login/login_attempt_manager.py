"""
登录尝试限制管理器
防止暴力破解攻击
"""
from datetime import datetime, timedelta
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class LoginAttemptManager:
    """管理登录尝试次数，防止暴力破解"""
    
    def __init__(self):
        # 存储格式: {email: (attempt_count, lock_until)}
        self.attempts: Dict[str, Tuple[int, datetime]] = {}
        self.max_attempts = 5  # 最大尝试次数
        self.lock_duration = timedelta(minutes=15)  # 锁定时间15分钟
    
    def record_failed_attempt(self, email: str) -> None:
        """记录一次失败的登录尝试"""
        email = email.lower().strip()
        now = datetime.now()
        
        if email in self.attempts:
            count, lock_until = self.attempts[email]
            # 如果还在锁定期间，增加尝试次数
            if now < lock_until:
                count += 1
            else:
                # 锁定已过期，重置计数
                count = 1
                lock_until = None
        else:
            count = 1
            lock_until = None
        
        # 如果达到最大尝试次数，锁定账户
        if count >= self.max_attempts:
            lock_until = now + self.lock_duration
            logger.warning(f"账户 {email} 因多次登录失败被锁定，锁定至 {lock_until}")
        
        self.attempts[email] = (count, lock_until)
    
    def clear_attempts(self, email: str) -> None:
        """清除登录尝试记录（登录成功时调用）"""
        email = email.lower().strip()
        if email in self.attempts:
            del self.attempts[email]
    
    def is_locked(self, email: str) -> Tuple[bool, str]:
        """
        检查账户是否被锁定
        
        Returns:
            (is_locked, message): 是否锁定，锁定消息
        """
        email = email.lower().strip()
        
        if email not in self.attempts:
            return False, ""
        
        count, lock_until = self.attempts[email]
        
        if lock_until is None:
            return False, ""
        
        now = datetime.now()
        if now < lock_until:
            remaining_minutes = int((lock_until - now).total_seconds() / 60)
            return True, f"账户因多次登录失败已被锁定，请在 {remaining_minutes} 分钟后重试"
        
        # 锁定已过期，清除记录
        del self.attempts[email]
        return False, ""
    
    def get_remaining_attempts(self, email: str) -> int:
        """获取剩余尝试次数"""
        email = email.lower().strip()
        
        if email not in self.attempts:
            return self.max_attempts
        
        count, lock_until = self.attempts[email]
        
        # 如果已锁定，返回0
        if lock_until and datetime.now() < lock_until:
            return 0
        
        return max(0, self.max_attempts - count)
    
    def cleanup_expired_locks(self) -> None:
        """清理过期的锁定记录"""
        now = datetime.now()
        expired_emails = [
            email for email, (count, lock_until) in self.attempts.items()
            if lock_until and now >= lock_until
        ]
        for email in expired_emails:
            del self.attempts[email]


# 全局单例
_login_attempt_manager = LoginAttemptManager()


def get_login_attempt_manager() -> LoginAttemptManager:
    """获取登录尝试管理器单例"""
    return _login_attempt_manager

