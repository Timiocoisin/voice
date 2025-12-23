"""
统一的响应格式工具
"""
from typing import Any, Dict, Optional
from flask import jsonify


def success_response(data: Optional[Dict[str, Any]] = None, message: str = "操作成功") -> Any:
    """成功响应"""
    response = {
        "success": True,
        "message": message,
    }
    if data:
        response.update(data)
    return jsonify(response)


def error_response(message: str, code: int = 400, error_code: Optional[str] = None) -> Any:
    """错误响应"""
    response = {
        "success": False,
        "message": message,
    }
    if error_code:
        response["error_code"] = error_code
    return jsonify(response), code


# 常用错误码
class ErrorCode:
    """错误码常量"""
    # 验证相关
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    INVALID_USERNAME = "INVALID_USERNAME"
    INVALID_VERIFICATION_CODE = "INVALID_VERIFICATION_CODE"
    
    # 用户相关
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_ALREADY_EXISTS = "USER_ALREADY_EXISTS"
    USER_LOCKED = "USER_LOCKED"
    
    # 认证相关
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # 系统相关
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

