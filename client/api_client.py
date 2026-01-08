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
    """检查后端服务是否可用"""
    try:
        data = _get("/api/health", timeout=3.0)
        return bool(data.get("status") == "ok")
    except Exception:
        return False


def send_verification_code(email: str, mode: str) -> Dict[str, Any]:
    """发送验证码"""
    return _post("/api/send_verification_code", {"email": email, "mode": mode})


def register_user(email: str, password: str, username: str, code: str) -> Dict[str, Any]:
    """用户注册"""
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
    """用户登录"""
    return _post(
        "/api/login",
        {
            "email": email,
            "password": password,
            "code": code,
        },
    )


def check_token(token: str) -> Dict[str, Any]:
    """校验 token 并获取用户信息"""
    return _post("/api/check_token", {"token": token})


def get_latest_announcement() -> Optional[str]:
    """获取最新公告"""
    try:
        data = _get("/api/announcement/latest")
    except Exception:
        return None
    if not data.get("success"):
        return None
    return data.get("content")


def get_user_profile(user_id: int) -> Optional[Dict[str, Any]]:
    """获取用户信息（包含头像）"""
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
    """更新用户头像"""
    avatar_b64 = base64.b64encode(avatar_bytes).decode("ascii")
    return _post(
        "/api/user/avatar",
        {"user_id": user_id, "avatar_base64": avatar_b64},
    )


def get_vip_info(user_id: int) -> Optional[Dict[str, Any]]:
    """获取 VIP 信息"""
    data = _post("/api/vip/info", {"user_id": user_id})
    if not data.get("success"):
        return None
    return data.get("vip") or {}


def purchase_membership(user_id: int, card_info: Dict[str, Any]) -> Dict[str, Any]:
    """购买会员套餐"""
    return _post(
        "/api/vip/purchase",
        {"user_id": user_id, "card": card_info},
    )


def get_diamond_balance(user_id: int) -> Optional[int]:
    """获取钻石余额"""
    data = _post("/api/diamond/balance", {"user_id": user_id})
    if not data.get("success"):
        return None
    return int(data.get("diamonds", 0))


def forgot_password(email: str) -> Dict[str, Any]:
    """忘记密码：请求发送重置邮件"""
    return _post("/api/forgot_password", {"email": email})


def reset_password(token: str, new_password: str) -> Dict[str, Any]:
    """重置密码：使用token重置密码"""
    return _post("/api/reset_password", {"token": token, "new_password": new_password})


def change_password(token: str, old_password: str, new_password: str) -> Dict[str, Any]:
    """修改密码：已登录用户修改密码"""
    return _post(
        "/api/user/change_password",
        {"token": token, "old_password": old_password, "new_password": new_password},
    )


def match_human_service(user_id: int, session_id: str, token: str) -> Dict[str, Any]:
    """匹配人工客服"""
    return _post(
        "/api/customer_service/match_agent",
        {"user_id": user_id, "session_id": session_id, "token": token},
    )


def get_chat_messages(session_id: str, user_id: int, token: str) -> Dict[str, Any]:
    """获取会话消息（用户端调用）"""
    return _post(
        "/api/user/chat_messages",
        {"session_id": session_id, "user_id": user_id, "token": token},
    )


def send_chat_message(session_id: str, user_id: int, message: str, token: str, message_type: str = "text", reply_to_message_id: Optional[int] = None) -> Dict[str, Any]:
    """发送聊天消息（用户端调用）"""
    data = {"session_id": session_id, "user_id": user_id, "message": message, "token": token, "message_type": message_type}
    if reply_to_message_id:
        data["reply_to_message_id"] = reply_to_message_id
    return _post("/api/user/send_message", data)


def recall_message(message_id: int, user_id: int, token: str) -> Dict[str, Any]:
    """撤回消息（2分钟内可撤回）"""
    return _post(
        "/api/message/recall",
        {"message_id": message_id, "user_id": user_id, "token": token},
    )


def get_reply_message(message_id: int, token: Optional[str] = None) -> Dict[str, Any]:
    """获取被引用的消息详情（用于引用回复显示）"""
    data = {"message_id": message_id}
    if token:
        data["token"] = token
    return _post("/api/message/reply", data)

