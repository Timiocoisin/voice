import re

def validate_email(email):
    """验证邮箱格式"""
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email) is not None

import re

def validate_password(password, min_length=8):
    """验证密码强度：长度至少min_length位（默认8位），至少包含一个字母和一个符号
    
    Args:
        password: 待验证的密码
        min_length: 最小长度，默认8位
    
    Returns:
        bool: 验证通过返回True，否则返回False
    """
    if not password or len(password) < min_length:
        return False
    
    # 检查是否包含字母
    if not re.search(r'[a-zA-Z]', password):
        return False
    
    # 检查是否包含符号（特殊字符）
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
        return False
    
    return True    