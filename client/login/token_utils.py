"""客户端 Token 工具模块

注意：客户端只做格式和过期时间检查，不验证签名。
真正的签名验证应该通过后端 API /api/check_token 完成。
"""
import base64
import json
import time
from typing import Any, Dict, Optional


def _b64url_decode(data: str) -> bytes:
    """Base64 URL 安全解码"""
    s = data.encode("ascii")
    s += b"=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s)


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    客户端本地验证令牌格式和过期时间（不验证签名）。
    
    注意：这只是初步检查，真正的验证需要通过后端 API /api/check_token。
    
    Returns:
        如果格式正确且未过期，返回 payload dict；否则返回 None
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        
        header_b64, payload_b64, _ = parts  # 不验证签名
        
        # 检查 header 格式
        try:
            header = json.loads(_b64url_decode(header_b64).decode("utf-8"))
            if header.get("alg") != "HS256":
                return None
        except Exception:
            return None
        
        # 检查 payload 格式和过期时间
        try:
            payload: Dict[str, Any] = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
            exp = payload.get("exp")
            if not isinstance(exp, int):
                return None
            # 检查是否过期
            if exp < int(time.time()):
                return None
            return payload
        except Exception:
            return None
    except Exception:
        return None

