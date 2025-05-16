import jwt
import datetime
from backend.config.config import SECRET_KEY

def generate_token(email):
    """生成包含用户邮箱和过期时间的令牌"""
    expiration = datetime.datetime.utcnow() + datetime.timedelta(days=7)
    payload = {
        'email': email,
        'exp': expiration
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def verify_token(token):
    """验证令牌的有效性"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None