import base64
from typing import Any, Dict, Optional

import requests


# 后端基础地址：开发阶段使用本机端口，部署时改为服务器 IP / 域名
BASE_URL = "http://127.0.0.1:8000"


class ApiError(RuntimeError):
    """后端接口调用错误（HTTP 层或业务层）。"""


def _full_url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return BASE_URL.rstrip("/") + path


def _get(path: str, *, timeout: float = 5.0) -> Dict[str, Any]:
    resp = requests.get(_full_url(path), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, data: Dict[str, Any], *, timeout: float = 5.0) -> Dict[str, Any]:
    resp = requests.post(_full_url(path), json=data, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def health_check() -> bool:
    """检查后端服务是否可用。"""
    try:
        data = _get("/api/health", timeout=3.0)
        return bool(data.get("status") == "ok")
    except Exception:
        return False


def send_verification_code(email: str, mode: str) -> Dict[str, Any]:
    """
    发送邮箱验证码。

    预期后端接口：POST /api/send_verification_code
    Request: { "email": str, "mode": "login" | "register" }
    Response: { "success": bool, "message"?: str }
    """
    return _post("/api/send_verification_code", {"email": email, "mode": mode})


def register_user(email: str, password: str, username: str, code: str) -> Dict[str, Any]:
    """
    用户注册。

    预期后端接口：POST /api/register
    Request: { email, password, username, code }
    Response: {
        success: bool,
        message: str,
        token?: str,
        user?: { id, username, avatar_base64? },
        vip?: { is_vip: bool, vip_expiry_date?: str, diamonds: int }
    }
    """
    return _post(
        "/api/register",
        {
            "email": email,
            "password": password,
            "username": username,
            "code": code,
        },
    )


def login_user(email: str, password: str, code: str) -> Dict[str, Any]:
    """
    用户登录。

    预期后端接口：POST /api/login
    """
    return _post(
        "/api/login",
        {
            "email": email,
            "password": password,
            "code": code,
        },
    )


def check_token(token: str) -> Dict[str, Any]:
    """
    校验本地保存的 token。

    预期后端接口：POST /api/check_token
    Response: { success: bool, user?: {...}, vip?: {...}, token?: str }
    """
    return _post("/api/check_token", {"token": token})


def get_latest_announcement() -> Optional[str]:
    """
    获取最新公告文本。

    预期后端接口：GET /api/announcement/latest
    Response: { success: bool, content?: str }
    """
    try:
        data = _get("/api/announcement/latest")
    except Exception:
        return None
    if not data.get("success"):
        return None
    return data.get("content")


def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """
    获取用户基础信息 + VIP / 钻石信息。

    预期后端接口：POST /api/user/profile
    Response: {
        success: bool,
        user: { id, username, avatar_base64?: str },
        vip: { is_vip: bool, vip_expiry_date?: str, diamonds: int }
    }
    """
    data = _post("/api/user/profile", {"user_id": user_id})
    if not data.get("success"):
        return None
    user = data.get("user") or {}
    avatar_b64 = user.get("avatar_base64")
    if avatar_b64:
        try:
            user["avatar_bytes"] = base64.b64decode(avatar_b64)
        except Exception:
            user["avatar_bytes"] = None
    else:
        user["avatar_bytes"] = None
    return data


def update_avatar(user_id: int, avatar_bytes: bytes) -> Dict[str, Any]:
    """
    更新用户头像。

    预期后端接口：POST /api/user/avatar
    Request: { user_id, avatar_base64 }
    """
    avatar_b64 = base64.b64encode(avatar_bytes).decode("ascii")
    return _post(
        "/api/user/avatar",
        {"user_id": user_id, "avatar_base64": avatar_b64},
    )


def get_vip_info(user_id: int) -> Optional[Dict[str, Any]]:
    """
    获取用户 VIP 信息。

    预期后端接口：POST /api/vip/info
    Response: { success: bool, vip: {...} }
    """
    data = _post("/api/vip/info", {"user_id": user_id})
    if not data.get("success"):
        return None
    return data.get("vip") or {}


def purchase_membership(user_id: int, card_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    购买会员套餐。

    预期后端接口：POST /api/vip/purchase
    Request: { user_id, card: {...} }
    Response: { success: bool, message: str, vip?: {...} }
    """
    return _post(
        "/api/vip/purchase",
        {"user_id": user_id, "card": card_info},
    )


def get_diamond_balance(user_id: int) -> Optional[int]:
    """
    获取钻石余额。

    预期后端接口：POST /api/diamond/balance
    Response: { success: bool, diamonds: int }
    """
    data = _post("/api/diamond/balance", {"user_id": user_id})
    if not data.get("success"):
        return None
    return int(data.get("diamonds", 0))


