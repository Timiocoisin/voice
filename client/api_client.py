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


def get_vip_info(user_id: int) -> Dict[str, Any]:
    """
    获取 VIP 信息（包含 diamonds/vip_expiry_date 等）。

    注意：当前后端没有单独的 /api/vip/info 接口，此处复用 /api/check_token 返回的 vip。
    """
    try:
        from client.login.token_storage import read_token
        token = read_token()
        if not token:
            return {}
        data = check_token(token)
        if not data.get("success"):
            return {}
        vip = data.get("vip") or {}
        # 轻量校验：若传入 user_id 与 token 对应 user_id 不一致，则返回空
        user = data.get("user") or {}
        token_user_id = user.get("id")
        if token_user_id is not None:
            try:
                if int(token_user_id) != int(user_id):
                    return {}
            except Exception:
                return {}
        return vip
    except Exception:
        return {}


def get_diamond_balance(user_id: int) -> int:
    """获取钻石余额（来自 VIP 信息）"""
    vip = get_vip_info(user_id) or {}
    try:
        return int(vip.get("diamonds", 0) or 0)
    except Exception:
        return 0


def get_user_profile(user_id: int) -> Dict[str, Any]:
    """
    获取用户资料（包含 avatar 等）。

    注意：当前后端已移除独立的 HTTP 用户资料接口，此处复用 /api/check_token 返回的 user。
    """
    try:
        from client.login.token_storage import read_token
        token = read_token()
        if not token:
            return {}
        data = check_token(token)
        if not data.get("success"):
            return {}
        user = data.get("user") or {}
        vip = data.get("vip") or {}
        token_user_id = user.get("id")

        # 后端统一返回 avatar_base64，这里为桌面端补充 avatar_bytes 字段，便于现有代码复用
        avatar_b64 = user.get("avatar_base64")
        if avatar_b64 and not user.get("avatar_bytes"):
            try:
                b64 = avatar_b64
                if isinstance(b64, str) and b64.startswith("data:image"):
                    b64 = b64.split(",", 1)[1]
                avatar_bytes = base64.b64decode(b64)
                user["avatar_bytes"] = avatar_bytes
            except Exception:
                # 解码失败时忽略，保持兼容
                pass
        if token_user_id is not None:
            try:
                if int(token_user_id) != int(user_id):
                    return {}
            except Exception:
                return {}
        # 兼容桌面端历史调用：上层期望 profile 结构包含 user/vip 两个字段
        return {"user": user, "vip": vip}
    except Exception:
        return {}


def update_avatar(user_id: int, avatar_bytes: bytes) -> Dict[str, Any]:
    """
    更新头像。

    说明：
    - 之前存在 HTTP 头像更新接口，但已在“全量迁移 WebSocket + 删除废弃 HTTP”中移除。
    - 目前后端仅提供用户资料订阅推送（subscribe_user_profile），未提供“设置头像”的 WS 事件。
    - 为了避免桌面端启动阶段 ImportError，这里保留同名函数并返回友好错误。
    """
    _ = user_id
    _ = avatar_bytes
    return {
        "success": False,
        "message": "头像更新接口已移除（HTTP 已删除，WS 暂未实现设置头像事件）。",
    }


def get_latest_announcement() -> Optional[str]:
    """获取最新公告"""
    try:
        data = _get("/api/announcement/latest")
    except Exception:
        return None
    if not data.get("success"):
        return None
    return data.get("content")




def purchase_membership(user_id: int, card_info: Dict[str, Any]) -> Dict[str, Any]:
    """购买会员套餐"""
    return _post(
        "/api/vip/purchase",
        {"user_id": user_id, "card": card_info},
    )


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
    raise ApiError(
        "HTTP 匹配客服接口已移除，请使用 WebSocket：\n"
        "1. 通过 client.websocket_client.WebSocketClient 连接\n"
        "2. 调用 ws_client.match_agent(session_id) 触发匹配\n"
        "3. 通过会话列表/待接入推送获取结果"
    )


def get_chat_messages(session_id: str, user_id: int, token: str) -> Dict[str, Any]:
    """
    获取会话消息（用户端调用，已废弃）。

    @deprecated 此 HTTP 接口已废弃，请使用 WebSocket 获取历史消息：
    - 使用 client.websocket_client.WebSocketClient
    - 连接后通过 on_message 回调接收实时消息，并在客户端自行维护消息列表。
    """
    raise ApiError(
        "HTTP 获取会话消息接口已废弃，请使用 WebSocket 获取历史消息。\n"
        "请使用 client.websocket_client.WebSocketClient 建立连接，并在 on_message 回调中维护消息列表。"
    )


def send_chat_message(session_id: str, user_id: int, message: str, token: str, message_type: str = "text", reply_to_message_id: Optional[int] = None) -> Dict[str, Any]:
    """
    发送聊天消息（已废弃，请使用 WebSocket）
    
    注意：HTTP 消息发送接口已移除，现在必须使用 WebSocket 发送消息。
    请使用 client.websocket_client.WebSocketClient.send_message() 方法。
    
    此函数保留仅为向后兼容，但会抛出错误提示使用 WebSocket。
    """
    raise NotImplementedError(
        "HTTP 消息发送接口已移除。请使用 WebSocket 发送消息：\n"
        "1. 使用 client.websocket_client.WebSocketClient 创建 WebSocket 客户端\n"
        "2. 连接后调用 ws_client.send_message(session_id, message, role='user', ...)\n"
        "参考：backend/websocket/README.md 和 client/websocket_client.py"
    )
    # 旧代码（已移除）
    # data = {"session_id": session_id, "user_id": user_id, "message": message, "token": token, "message_type": message_type}
    # if reply_to_message_id:
    #     data["reply_to_message_id"] = reply_to_message_id
    # return _post("/api/user/send_message", data)


def get_reply_message(message_id: int, token: str) -> Dict[str, Any]:
    """
    获取被引用的消息摘要（已废弃）。

    说明：引用摘要已由服务端随消息推送（reply_to_message），不再提供 HTTP 获取。
    这里保留函数仅用于避免旧代码 import 失败。
    """
    _ = message_id
    _ = token
    raise ApiError("HTTP 引用消息详情接口已移除，请使用 WebSocket 推送的 reply_to_message 字段。")


### 已删除：HTTP 撤回消息接口（改用 WebSocket recall_message）


### 已删除：HTTP 引用消息详情接口（引用摘要已随消息推送）

