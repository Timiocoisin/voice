"""登录认证服务层。"""
import bcrypt
import logging
from typing import Optional, Tuple

from backend.database.database_manager import DatabaseManager
from backend.login.token_utils import generate_token
from backend.login.token_storage import save_token
from backend.login.login_status_manager import save_login_status
from backend.validation.validator import validate_email, validate_password


class AuthService:
    """认证服务：封装登录/注册业务逻辑"""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()
    
    def register(self, email: str, password: str, username: str, verification_code: str, 
                verification_manager) -> Tuple[bool, str]:
        """
        注册新用户
        
        Returns:
            (success, message): 成功标志和提示消息
        """
        # 验证邮箱格式
        if not validate_email(email):
            return False, "邮箱格式不正确"
        
        # 验证密码强度
        if not validate_password(password):
            return False, "密码必须至少8位，且包含字母和数字"
        
        # 验证用户名
        if not username or len(username) < 2:
            return False, "用户名至少2个字符"
        
        # 验证码检查
        if not verification_manager.verify_code(email, verification_code):
            return False, "验证码错误或已过期"
        
        # 检查邮箱是否已注册
        existing = self.db_manager.get_user_by_email(email)
        if existing:
            return False, "该邮箱已被注册"
        
        # 密码加密
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # 插入数据库
        success = self.db_manager.insert_user_info(
            email=email,
            password=hashed.decode('utf-8'),
            username=username
        )
        
        if not success:
            return False, "注册失败，请稍后重试"
        
        logging.info(f"用户 {username} ({email}) 注册成功")
        return True, "注册成功！"
    
    def login(self, email: str, password: str) -> Tuple[bool, str, Optional[dict]]:
        """
        用户登录
        
        Returns:
            (success, message, user_info): 成功标志、消息、用户信息
        """
        # 验证邮箱格式
        if not validate_email(email):
            return False, "邮箱格式不正确", None
        
        # 查询用户
        user = self.db_manager.get_user_by_email(email)
        if not user:
            return False, "邮箱或密码错误", None
        
        # 验证密码
        stored_password = user.get('password', '')
        if not stored_password:
            return False, "密码验证失败", None
        
        try:
            if not bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
                return False, "邮箱或密码错误", None
        except Exception as e:
            logging.error(f"密码验证异常: {e}")
            return False, "登录失败，请稍后重试", None
        
        # 生成token并保存
        token = generate_token(email)
        save_token(token)
        
        # 保存登录状态
        user_id = user.get('id')
        username = user.get('username', '未命名')
        save_login_status(user_id, username)
        
        logging.info(f"用户 {username} ({email}) 登录成功")
        return True, "登录成功！", user
    
    def get_user_vip_info(self, user_id: int) -> Optional[dict]:
        """获取用户VIP信息"""
        return self.db_manager.get_user_vip_info(user_id)
