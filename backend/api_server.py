"""
后端 HTTP 服务入口。

本模块将现有的数据库与业务逻辑封装为一组 REST 风格接口，
供客户端（PyQt UI）通过 HTTP 调用，实现真正的前后端分离。

接口约定需与 `client/api_client.py` 严格保持一致。
"""

from __future__ import annotations

import base64
import logging
import secrets
import threading
from datetime import datetime, timedelta
from typing import Any, Dict

# 尽早 monkey_patch，确保 socket、时间等模块被正确补丁
try:
    import eventlet

    eventlet.monkey_patch()
    _ASYNC_MODE = "eventlet"
except Exception:
    eventlet = None  # type: ignore
    _ASYNC_MODE = "threading"

from flask import Flask, jsonify, request
from flask_socketio import SocketIO, emit

from backend.config.config import email_config, SECRET_KEY  # noqa: F401
from backend.database.database_manager import DatabaseManager
from backend.email.email_sender import EmailSender, generate_verification_code
from backend.login.token_utils import generate_token, verify_token
from backend.login.login_attempts import (
    record_failed_attempt,
    clear_attempts,
    is_locked,
    get_remaining_attempts,
)
from backend.logging_manager import setup_logging  # noqa: F401
from backend.membership_service import MembershipService
from backend.validation.validator import validate_email, validate_password
from backend.validation.verification_manager import VerificationManager
from backend.utils.rich_text_processor import process_rich_text, extract_urls_from_text, extract_mentions_from_text
from backend.utils.link_preview import fetch_link_preview, get_simple_preview
from backend.websocket import WebSocketManager


# 初始化日志
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 初始化 SocketIO，用于 WebSocket 实时通信
# 默认使用 eventlet（如已安装并 monkey_patch），否则回退 threading，避免 werkzeug run_wsgi 的 write() before start_response
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=_ASYNC_MODE)
if _ASYNC_MODE != "eventlet":
    logger.warning("SocketIO 未使用 eventlet，已回退 %s，实时能力受限，请安装 eventlet", _ASYNC_MODE)


# 添加 CORS 支持
@app.after_request
def after_request(response):
    """添加 CORS 响应头，允许跨域请求"""
    # 使用 set 而不是 add，避免重复添加
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
    return response


@app.before_request
def handle_preflight():
    """处理 OPTIONS 预检请求"""
    if request.method == "OPTIONS":
        response = jsonify({})
        # 使用 set 而不是 add，避免重复添加
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
        response.headers['Access-Control-Allow-Methods'] = 'GET,POST,PUT,DELETE,OPTIONS'
        return response


# 全局单例：数据库、会员服务、验证码管理、邮件发送器、WebSocket 管理器
db = DatabaseManager()
membership_service = MembershipService(db)
verification_manager = VerificationManager()
email_sender = EmailSender(email_config)
ws_manager = WebSocketManager(socketio, db)

# 启动 WebSocket 管理器
ws_manager.start()


def _vip_dict_from_row(row: Dict[str, Any] | None) -> Dict[str, Any]:
    """将数据库中的 VIP 行转换为统一返回结构。"""
    if not row:
        return {
            "is_vip": False,
            "vip_expiry_date": None,
            "diamonds": 0,
        }
    expiry = row.get("vip_expiry_date")
    if isinstance(expiry, datetime):
        expiry_str = expiry.isoformat()
    else:
        expiry_str = None
    return {
        "is_vip": bool(row.get("is_vip", False)),
        "vip_expiry_date": expiry_str,
        "diamonds": int(row.get("diamonds", 0) or 0),
    }


def _user_dict_with_avatar(user_row: Dict[str, Any] | None) -> Dict[str, Any]:
    """将用户行转换为带 avatar_base64 的 dict。"""
    if not user_row:
        return {}
    avatar_bytes = user_row.get("avatar")
    if isinstance(avatar_bytes, memoryview):
        avatar_bytes = avatar_bytes.tobytes()
    if avatar_bytes:
        avatar_b64 = base64.b64encode(avatar_bytes).decode("ascii")
    else:
        avatar_b64 = None
    return {
        "id": user_row.get("id"),
        "username": user_row.get("username"),
        "avatar_base64": avatar_b64,
    }


@app.get("/api/health")
def health() -> Any:
    """健康检查接口。"""
    return jsonify({"status": "ok"})


def _send_verification_code_async(email: str, code: str) -> None:
    """
    在后台线程中异步发送验证码邮件。
    这样可以避免阻塞 HTTP 响应，提升用户体验。
    """
    try:
        ok = email_sender.send_verification_code(email, code)
        if not ok:
            logger.warning("验证码邮件发送失败：%s（验证码已保存，用户可能无法收到）", email)
        else:
            logger.info("验证码邮件已成功发送至：%s", email)
    except Exception as e:
        logger.error("发送验证码邮件失败：%s", e, exc_info=True)


@app.post("/api/send_verification_code")
def send_verification_code_api() -> Any:
    """
    发送邮箱验证码。
    Request JSON: { "email": str, "mode": "login" | "register" }

    规则：
    - login 模式：邮箱必须已注册，否则不给发码，提示"请先注册"；
    - register 模式：邮箱必须未注册，否则不给发码，提示"邮箱已被注册"。
    
    注意：验证码会立即保存，邮件发送在后台异步执行，避免客户端超时。
    """
    data = request.get_json(force=True) or {}
    email = str(data.get("email", "")).strip()
    mode = str(data.get("mode", "login")).strip().lower()

    if not validate_email(email):
        return jsonify({"success": False, "message": "邮箱格式不正确"}), 400

    existing = db.get_user_by_email(email)
    if mode == "login":
        if not existing:
            return jsonify(
                {
                    "success": False,
                    "message": "该邮箱尚未注册，请先切换到注册并完成注册。",
                }
            ), 400
    elif mode == "register":
        if existing:
            return jsonify(
                {
                    "success": False,
                    "message": "该邮箱已被注册，请直接登录或找回密码。",
                }
            ), 400

    # 生成验证码并立即保存
    code = generate_verification_code()
    verification_manager.set_verification_code(email, code)
    
    # 在后台线程中异步发送邮件，避免阻塞 HTTP 响应
    # 这样可以防止客户端因邮件发送慢而超时
    thread = threading.Thread(target=_send_verification_code_async, args=(email, code), daemon=True)
    thread.start()
    
    # 立即返回成功响应，不等待邮件发送完成
    return jsonify({"success": True})


@app.post("/api/register")
def register_api() -> Any:
    """
    用户注册（客户端注册，默认为普通用户）。
    Request JSON: { email, password, username, code, role? }
    role 可选，默认为 'user'，客户端注册时不需要传此参数
    """
    data = request.get_json(force=True) or {}
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))
    username = str(data.get("username", "")).strip()
    code = str(data.get("code", "")).strip()
    role = str(data.get("role", "user")).strip()  # 默认为普通用户

    if not username:
        return jsonify({"success": False, "message": "用户名不能为空"}), 400
    if not validate_email(email):
        return jsonify({"success": False, "message": "邮箱格式不正确"}), 400
    if not validate_password(password, min_length=6):
        return jsonify({"success": False, "message": "密码至少8位，需包含至少一个字母和一个符号"}), 400
    if not verification_manager.verify_code(email, code):
        return jsonify({"success": False, "message": "验证码错误或已过期"}), 400

    # 验证 role 值
    if role not in ['user', 'admin', 'customer_service']:
        role = 'user'  # 默认值

    # 已存在检查
    if db.get_user_by_email(email):
        return jsonify({"success": False, "message": "该邮箱已被注册"}), 400

    # 写库：DatabaseManager 会负责密码哈希
    ok = db.insert_user_info(username=username, email=email, password=password, role=role)
    if not ok:
        return jsonify({"success": False, "message": "注册失败，请稍后重试"}), 500

    user_row = db.get_user_by_email(email)
    if not user_row:
        return jsonify({"success": False, "message": "注册成功但未能读取用户信息"}), 500

    vip_row = db.get_user_vip_info(user_row["id"]) if role == 'user' else None
    vip = _vip_dict_from_row(vip_row) if vip_row else {}
    user = _user_dict_with_avatar(user_row)
    token = generate_token(email)

    logger.info("用户 %s 注册成功，ID: %s, 角色: %s", user_row.get("username"), user_row.get("id"), role)

    return jsonify(
        {
            "success": True,
            "message": "注册成功",
            "token": token,
            "user": user,
            "vip": vip,
        }
    )


@app.post("/api/login")
def login_api() -> Any:
    """
    用户登录。
    Request JSON: { email, password, code }
    """
    import bcrypt

    data = request.get_json(force=True) or {}
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))
    code = str(data.get("code", "")).strip()

    if not validate_email(email):
        return jsonify({"success": False, "message": "邮箱格式不正确"}), 400
    if not verification_manager.verify_code(email, code):
        return jsonify({"success": False, "message": "验证码错误或已过期"}), 400

    user_row = db.get_user_by_email(email)
    if not user_row:
        return jsonify({"success": False, "message": "邮箱或密码错误"}), 400

    stored_password = user_row.get("password", "")
    try:
        if isinstance(stored_password, bytes):
            hashed = stored_password
        else:
            hashed = str(stored_password).encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), hashed):
            return jsonify({"success": False, "message": "邮箱或密码错误"}), 400
    except Exception as e:
        logger.error("密码验证异常：%s", e, exc_info=True)
        return jsonify({"success": False, "message": "登录失败，请稍后重试"}), 500

    vip_row = db.get_user_vip_info(user_row["id"])
    vip = _vip_dict_from_row(vip_row)
    user = _user_dict_with_avatar(user_row)
    token = generate_token(email)

    logger.info("用户 %s 登录成功，ID: %s", user_row.get("username"), user_row.get("id"))

    return jsonify(
        {
            "success": True,
            "message": "登录成功",
            "token": token,
            "user": user,
            "vip": vip,
        }
    )


@app.post("/api/forgot_password")
def forgot_password_api() -> Any:
    """
    忘记密码：发送密码重置邮件。
    Request JSON: { email }
    """
    data = request.get_json(force=True) or {}
    email = str(data.get("email", "")).strip().lower()

    if not email:
        return jsonify({"success": False, "message": "邮箱不能为空"}), 400
    if not validate_email(email):
        return jsonify({"success": False, "message": "邮箱格式不正确"}), 400

    # 检查用户是否存在
    user_row = db.get_user_by_email(email)
    if not user_row:
        # 为了安全，不透露用户是否存在，统一返回成功消息
        logger.warning("忘记密码请求：用户不存在 email=%s", email)
        return jsonify({"success": True, "message": "如果该邮箱已注册，重置链接已发送到您的邮箱"})

    # 生成重置token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(minutes=30)  # 30分钟有效期

    # 保存token到数据库
    if not db.insert_password_reset_token(email, reset_token, expires_at):
        logger.error("保存密码重置token失败: email=%s", email)
        return jsonify({"success": False, "message": "发送失败，请稍后重试"}), 500

    # 构建重置URL（指向前端页面，前端页面会从URL参数中提取token并调用POST API）
    # 注意：这里使用前端开发服务器地址，生产环境需要改为实际的前端域名
    # 前端页面：/reset-password?token=xxx
    frontend_base_url = "http://localhost:5173"  # Vite 默认端口，生产环境需要配置
    reset_url = f"{frontend_base_url}/reset-password?token={reset_token}"

    # 发送重置邮件
    if not email_sender.send_password_reset_email(email, reset_token, reset_url, expires_in_minutes=30):
        logger.error("发送密码重置邮件失败: email=%s", email)
        return jsonify({"success": False, "message": "邮件发送失败，请稍后重试"}), 500

    logger.info("密码重置邮件已发送: email=%s", email)
    return jsonify({"success": True, "message": "重置链接已发送到您的邮箱，请查收"})


@app.get("/api/reset_password")
def verify_reset_token_api() -> Any:
    """
    验证重置密码token（GET方法，用于邮件链接验证）。
    Request Query: ?token=xxx
    """
    token = request.args.get("token", "").strip()
    
    if not token:
        # 如果没有token，重定向到前端忘记密码页面
        return jsonify({"success": False, "message": "缺少重置token"}), 400
    
    # 验证token
    token_info = db.get_password_reset_token(token)
    if not token_info:
        return jsonify({"success": False, "message": "重置链接无效或已过期"}), 400
    
    # 检查token是否已使用
    if token_info.get("used"):
        return jsonify({"success": False, "message": "该重置链接已被使用"}), 400
    
    # 检查token是否过期
    expires_at = token_info.get("expires_at")
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except:
            return jsonify({"success": False, "message": "重置链接已过期"}), 400
    if isinstance(expires_at, datetime) and expires_at < datetime.now():
        return jsonify({"success": False, "message": "重置链接已过期"}), 400
    
    # Token有效，返回成功（前端可以继续使用这个token调用POST API重置密码）
    return jsonify({"success": True, "message": "重置链接有效"})


@app.post("/api/reset_password")
def reset_password_api() -> Any:
    """
    重置密码：使用token重置密码。
    Request JSON: { token, new_password }
    """
    data = request.get_json(force=True) or {}
    token = str(data.get("token", "")).strip()
    new_password = str(data.get("new_password", ""))

    if not token:
        return jsonify({"success": False, "message": "重置token不能为空"}), 400
    if not new_password:
        return jsonify({"success": False, "message": "新密码不能为空"}), 400
    if not validate_password(new_password, min_length=8):
        return jsonify({"success": False, "message": "密码至少8位，需包含至少一个字母和一个符号"}), 400

    # 验证token
    token_info = db.get_password_reset_token(token)
    if not token_info:
        return jsonify({"success": False, "message": "重置链接无效或已过期"}), 400

    # 检查token是否已使用
    if token_info.get("used"):
        return jsonify({"success": False, "message": "该重置链接已被使用"}), 400

    # 检查token是否过期
    expires_at = token_info.get("expires_at")
    if isinstance(expires_at, str):
        try:
            expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
        except:
            return jsonify({"success": False, "message": "重置链接已过期"}), 400
    if isinstance(expires_at, datetime) and expires_at < datetime.now():
        return jsonify({"success": False, "message": "重置链接已过期"}), 400

    email = token_info.get("email")
    if not email:
        return jsonify({"success": False, "message": "重置链接无效"}), 400

    # 更新密码
    if not db.update_user_password(email, new_password):
        logger.error("更新用户密码失败: email=%s", email)
        return jsonify({"success": False, "message": "重置失败，请稍后重试"}), 500

    # 标记token为已使用
    db.mark_password_reset_token_as_used(token)

    # 清除该邮箱的登录尝试记录（如果存在）
    clear_attempts(email)

    logger.info("用户密码重置成功: email=%s", email)
    return jsonify({"success": True, "message": "密码重置成功，请使用新密码登录"})


@app.post("/api/check_token")
def check_token_api() -> Any:
    """
    校验 token 是否有效并返回用户与 VIP 信息。
    Request JSON: { token }
    """
    data = request.get_json(force=True) or {}
    token = str(data.get("token", "")).strip()
    payload = verify_token(token)
    if not payload:
        return jsonify({"success": False}), 401

    email = payload.get("email")
    if not email:
        return jsonify({"success": False}), 401

    user_row = db.get_user_by_email(email)
    if not user_row:
        return jsonify({"success": False}), 401

    vip_row = db.get_user_vip_info(user_row["id"])
    vip = _vip_dict_from_row(vip_row)
    user = _user_dict_with_avatar(user_row)

    # 如有需要，可以在这里刷新 token；当前保持不变
    return jsonify(
        {
            "success": True,
            "user": user,
            "vip": vip,
            "token": token,
        }
    )


@app.get("/api/announcement/latest")
def get_latest_announcement_api() -> Any:
    """获取最新公告。"""
    content = db.get_latest_announcement()
    if not content:
        return jsonify({"success": False, "content": None})
    return jsonify({"success": True, "content": content})


@app.post("/api/user/change_password")
def change_password_api() -> Any:
    """
    修改密码：已登录用户修改密码。
    Request JSON: { token, old_password, new_password }
    """
    import bcrypt

    data = request.get_json(force=True) or {}
    token = str(data.get("token", "")).strip()
    old_password = str(data.get("old_password", ""))
    new_password = str(data.get("new_password", ""))

    # 验证token
    payload = verify_token(token)
    if not payload:
        return jsonify({"success": False, "message": "登录已过期，请重新登录"}), 401

    email = payload.get("email")
    if not email:
        return jsonify({"success": False, "message": "登录已过期，请重新登录"}), 401

    # 验证旧密码
    if not old_password:
        return jsonify({"success": False, "message": "旧密码不能为空"}), 400
    if not new_password:
        return jsonify({"success": False, "message": "新密码不能为空"}), 400
    if not validate_password(new_password, min_length=8):
        return jsonify({"success": False, "message": "新密码至少8位，需包含至少一个字母和一个符号"}), 400

    # 获取用户信息
    user_row = db.get_user_by_email(email)
    if not user_row:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    # 验证旧密码
    stored_password = user_row.get("password", "")
    try:
        if isinstance(stored_password, bytes):
            hashed = stored_password
        else:
            hashed = str(stored_password).encode("utf-8")
        if not bcrypt.checkpw(old_password.encode("utf-8"), hashed):
            return jsonify({"success": False, "message": "旧密码错误"}), 400
    except Exception as e:
        logger.error("密码验证异常：%s", e, exc_info=True)
        return jsonify({"success": False, "message": "验证失败，请稍后重试"}), 500

    # 检查新旧密码是否相同
    try:
        if isinstance(stored_password, bytes):
            hashed = stored_password
        else:
            hashed = str(stored_password).encode("utf-8")
        if bcrypt.checkpw(new_password.encode("utf-8"), hashed):
            return jsonify({"success": False, "message": "新密码不能与旧密码相同"}), 400
    except Exception:
        pass

    # 更新密码
    if not db.update_user_password(email, new_password):
        logger.error("更新用户密码失败: email=%s", email)
        return jsonify({"success": False, "message": "修改失败，请稍后重试"}), 500

    logger.info("用户密码修改成功: email=%s", email)
    return jsonify({"success": True, "message": "密码修改成功"})


@app.post("/api/vip/purchase")
def purchase_vip_api() -> Any:
    """
    购买会员套餐。
    Request JSON: { user_id, card: {...} }
    """
    data = request.get_json(force=True) or {}
    user_id = int(data.get("user_id", 0) or 0)
    card = data.get("card") or {}

    if not user_id:
        return jsonify({"success": False, "message": "未登录，无法购买会员"}), 400

    cost = int(card.get("diamonds", 0) or 0)
    if cost <= 0:
        return jsonify({"success": False, "message": "无效的会员套餐"}), 400

    vip_row = db.get_user_vip_info(user_id)
    vip = _vip_dict_from_row(vip_row)
    diamonds = int(vip.get("diamonds", 0) or 0)
    if diamonds < cost:
        return jsonify(
            {
                "success": False,
                "message": "钻石不足，请先充值钻石后再购买会员",
            }
        )

    # 调用服务层进行扣费与有效期更新
    success, new_expiry = membership_service.purchase_membership(user_id, card)
    if not success:
        return jsonify(
            {
                "success": False,
                "message": "会员购买失败，请稍后重试",
            }
        ), 500

    # 重新查询最新 VIP 信息
    vip_row = db.get_user_vip_info(user_id)
    vip = _vip_dict_from_row(vip_row)
    
    # 推送 VIP 状态和钻石余额更新
    ws_manager.push_vip_status_update(user_id, vip)
    diamonds = int(vip.get("diamonds", 0) or 0)
    ws_manager.push_diamond_balance_update(user_id, diamonds)
    
    return jsonify(
        {
            "success": True,
            "message": "会员购买成功",
            "vip": vip,
        }
    )


# ==================== 客服系统专用接口 ====================

@app.post("/api/customer_service/register")
def customer_service_register_api() -> Any:
    """
    客服系统注册（注册为客服角色）。
    Request JSON: { email, password, username }
    注意：客服系统注册不需要验证码，但需要严格的输入验证
    """
    try:
        data = request.get_json(force=True) or {}
        email = str(data.get("email", "")).strip()
        password = str(data.get("password", ""))
        username = str(data.get("username", "")).strip()

        logger.info("客服注册请求: email=%s, username=%s", email, username)

        # 用户名验证
        if not username:
            return jsonify({"success": False, "message": "昵称不能为空"}), 400
        username = username.strip()
        if len(username) < 2:
            return jsonify({"success": False, "message": "昵称至少2个字符"}), 400
        if len(username) > 20:
            return jsonify({"success": False, "message": "昵称长度不能超过20个字符"}), 400
        # 验证用户名字符（允许中文、英文、数字、下划线）
        import re
        if not re.match(r'^[\u4e00-\u9fa5a-zA-Z0-9_]+$', username):
            return jsonify({"success": False, "message": "昵称只能包含中文、英文、数字和下划线"}), 400

        # 邮箱验证
        if not email:
            return jsonify({"success": False, "message": "邮箱不能为空"}), 400
        email = email.strip().lower()  # 统一转为小写
        if len(email) > 100:
            return jsonify({"success": False, "message": "邮箱长度不能超过100个字符"}), 400
        if not validate_email(email):
            return jsonify({"success": False, "message": "邮箱格式不正确"}), 400

        # 密码验证
        if not password:
            return jsonify({"success": False, "message": "密码不能为空"}), 400
        if not validate_password(password, min_length=6):
            return jsonify({"success": False, "message": "密码至少8位，需包含至少一个字母和一个符号"}), 400
        if len(password) > 50:
            return jsonify({"success": False, "message": "密码长度不能超过50个字符"}), 400

        # 已存在检查
        existing = db.get_user_by_email(email)
        if existing:
            return jsonify({"success": False, "message": "该邮箱已被注册，请直接登录"}), 400

        # 检查用户名是否已被使用（可选，如果需要用户名唯一）
        # 这里暂时不检查，因为用户名可能重复

        # 注册为客服角色
        ok = db.insert_user_info(username=username, email=email, password=password, role='customer_service')
        if not ok:
            logger.error("插入用户信息失败: email=%s", email)
            return jsonify({"success": False, "message": "注册失败，请稍后重试"}), 500

        user_row = db.get_user_by_email(email)
        if not user_row:
            logger.error("注册后无法读取用户信息: email=%s", email)
            return jsonify({"success": False, "message": "注册成功但未能读取用户信息"}), 500

        user = _user_dict_with_avatar(user_row)
        token = generate_token(email)

        logger.info("客服 %s 注册成功，ID: %s", user_row.get("username"), user_row.get("id"))

        return jsonify(
            {
                "success": True,
                "message": "注册成功",
                "token": token,
                "user": user,
            }
        )
    except Exception as e:
        logger.error("客服注册接口异常: %s", e, exc_info=True)
        return jsonify({"success": False, "message": "注册失败，请稍后重试"}), 500


@app.post("/api/customer_service/login")
def customer_service_login_api() -> Any:
    """
    客服系统登录。
    Request JSON: { email, password }
    注意：客服登录不需要验证码，但有防暴力破解保护
    """
    import bcrypt

    try:
        data = request.get_json(force=True) or {}
        email = str(data.get("email", "")).strip().lower()  # 统一转为小写
        password = str(data.get("password", ""))

        # 基础验证
        if not email:
            return jsonify({"success": False, "message": "邮箱不能为空"}), 400
        if not password:
            return jsonify({"success": False, "message": "密码不能为空"}), 400
        if not validate_email(email):
            return jsonify({"success": False, "message": "邮箱格式不正确"}), 400

        # 检查账户是否被锁定
        locked, lock_message = is_locked(email)
        if locked:
            return jsonify({"success": False, "message": lock_message}), 423  # 423 Locked

        # 查询用户
        user_row = db.get_user_by_email(email)
        if not user_row:
            # 记录失败尝试（即使用户不存在也记录，防止枚举攻击）
            record_failed_attempt(email)
            remaining = get_remaining_attempts(email)
            return jsonify({
                "success": False,
                "message": "邮箱或密码错误",
                "remaining_attempts": remaining
            }), 400

        # 检查用户角色是否为客服或管理员
        user_role = user_row.get("role", "user")
        if user_role not in ['customer_service', 'admin']:
            record_failed_attempt(email)
            return jsonify({"success": False, "message": "该账号不是客服账号，无权访问工作台"}), 403

        # 验证密码
        stored_password = user_row.get("password", "")
        try:
            if isinstance(stored_password, bytes):
                hashed = stored_password
            else:
                hashed = str(stored_password).encode("utf-8")
            if not bcrypt.checkpw(password.encode("utf-8"), hashed):
                # 密码错误，记录失败尝试
                record_failed_attempt(email)
                remaining = get_remaining_attempts(email)
                if remaining > 0:
                    return jsonify({
                        "success": False,
                        "message": f"邮箱或密码错误，还可尝试 {remaining} 次",
                        "remaining_attempts": remaining
                    }), 400
                else:
                    locked, lock_message = is_locked(email)
                    return jsonify({
                        "success": False,
                        "message": lock_message or "登录失败次数过多，账户已被锁定"
                    }), 423
        except Exception as e:
            logger.error("密码验证异常: %s", e, exc_info=True)
            record_failed_attempt(email)
            return jsonify({"success": False, "message": "登录失败，请稍后重试"}), 500

        # 登录成功，清除失败记录
        clear_attempts(email)

        user = _user_dict_with_avatar(user_row)
        token = generate_token(email)
        
        # 自动设置客服为在线状态
        user_id = user_row.get("id")
        if user_id:
            db.update_agent_status(user_id, 'online')

        logger.info("客服 %s 登录成功，ID: %s", user_row.get("username"), user_id)

        return jsonify(
            {
                "success": True,
                "message": "登录成功",
                "token": token,
                "user": user,
            }
        )
    except Exception as e:
        logger.error("客服登录接口异常: %s", e, exc_info=True)
        return jsonify({"success": False, "message": "登录失败，请稍后重试"}), 500


@app.post("/api/customer_service/verify_token")
def verify_customer_service_token_api() -> Any:
    """
    验证客服系统的 token 是否有效。
    Request JSON: { token }
    """
    data = request.get_json(force=True) or {}
    token = str(data.get("token", "")).strip()

    if not token:
        return jsonify({"success": False, "message": "Token 不能为空"}), 400

    # 验证 token
    payload = verify_token(token)
    if not payload:
        return jsonify({"success": False, "message": "Token 无效或已过期"}), 401

    email = payload.get("email")
    if not email:
        return jsonify({"success": False, "message": "Token 格式错误"}), 401

    # 获取用户信息并验证角色
    user_row = db.get_user_by_email(email)
    if not user_row:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    user_role = user_row.get("role", "user")
    if user_role not in ['customer_service', 'admin']:
        return jsonify({"success": False, "message": "无权限访问"}), 403

    user = _user_dict_with_avatar(user_row)
    return jsonify({"success": True, "user": user})


### 已移除：HTTP 历史消息接口
### 注意：历史消息获取已迁移至 WebSocket 事件 "get_session_messages"
### 参考：backend/websocket/README.md


# ==================== 已移除：HTTP 消息发送接口 ====================
# 注意：HTTP 消息发送接口已移除，所有消息发送现在都通过 WebSocket 实现。
# 请使用 WebSocket 事件 "send_message" 来发送消息。
# 参考：backend/websocket/README.md


### 已移除：HTTP 撤回消息接口
### 注意：撤回消息已迁移至 WebSocket 事件 "recall_message"
### 参考：backend/websocket/README.md

### 已移除：HTTP 引用消息详情接口
### 注意：引用消息详情已由服务端在消息结构中自动包含（reply_to_message）
### 无需再通过 HTTP 获取


### 注意：所有消息发送现在都通过 WebSocket 事件 "send_message" 实现
### HTTP 消息发送接口已移除，请使用 WebSocket 客户端发送消息
### 参考：backend/websocket/README.md 和 client/websocket_client.py
def _match_agent_logic(user_id: int, session_id: str) -> Dict[str, Any]:
    """匹配在线客服的核心逻辑（供 WebSocket 复用）"""
    # 获取在线客服列表
    online_agents = db.get_online_agents()
    if not online_agents:
        db.create_pending_session(session_id, user_id)
        pending_sessions = db.get_pending_sessions()
        target_session = next((s for s in pending_sessions if s['session_id'] == session_id), None)
        if target_session:
            formatted_session = _format_session_list([target_session], include_duration=False)
            if formatted_session:
                ws_manager.push_new_pending_session(formatted_session[0])
        return {
            "success": False,
            "message": "暂无在线客服，您的请求已加入等待队列",
            "matched": False,
            "session_id": session_id
        }

    # 选择当前会话最少的客服
    best_agent = None
    min_sessions = float('inf')
    for agent in online_agents:
        agent_sessions = db.get_agent_sessions(agent['id'], include_pending=False)
        session_count = len(agent_sessions)
        if session_count < min_sessions:
            min_sessions = session_count
            best_agent = agent

    # 无论是否已匹配到具体客服，先创建为待接入会话，并推送到“待接入”队列
    db.create_pending_session(session_id, user_id)
    pending_sessions = db.get_pending_sessions()
    target_session = next((s for s in pending_sessions if s['session_id'] == session_id), None)
    if target_session:
        formatted_session = _format_session_list([target_session], include_duration=False)
        if formatted_session:
            # 推送一条新的待接入会话卡片给客服端，用于更新待接入列表和右上角排队数量
            ws_manager.push_new_pending_session(formatted_session[0])

    if best_agent:
        # 返回“已为您匹配到在线客服”，用于用户侧 UI 切换为对话模式
        return {
            "success": True,
            "matched": True,
            "agent_id": best_agent['id'],
            "agent_name": best_agent['username'],
            "session_id": session_id,
            "message": "已为您匹配到在线客服"
        }

    return {
        "success": False,
        "message": "暂无在线客服，您的请求已加入等待队列",
        "matched": False,
        "session_id": session_id
    }


def _accept_session_logic(user_id: int, session_id: str) -> Dict[str, Any]:
    """客服接入会话的核心逻辑（供 WebSocket 复用）"""
    success = db.assign_session_to_agent(session_id, user_id)
    if not success:
        return {"success": False, "message": "接入失败，会话可能已被其他客服接入"}

    session_info = db.get_pending_sessions()
    target_session = next((s for s in session_info if s['session_id'] == session_id), None)
    user_side_id = None
    if target_session:
        user_side_id = target_session.get('user_id')
        db.insert_chat_message(
            session_id,
            user_id,
            target_session['user_id'],
            "您好，我是客服，有什么可以帮您的吗？"
        )

    # 推送给所有客服：该待接入会话已被接入
    ws_manager.push_pending_session_accepted(session_id, user_id)

    # 推送给最终用户：会话已被客服接入
    if user_side_id:
        try:
            agent_row = db.get_user_by_id(user_id)
            agent_name = agent_row.get("username") if agent_row else None
        except Exception:
            agent_name = None
        ws_manager.push_session_accepted_for_user(user_side_id, session_id, user_id, agent_name)

    sessions = db.get_agent_sessions(user_id, include_pending=False)
    formatted_sessions = _format_session_list(sessions)
    ws_manager.push_session_list_update(user_id, "my", formatted_sessions)

    pending_sessions = db.get_pending_sessions()
    formatted_pending = _format_session_list(pending_sessions, include_duration=False)
    online_agents = db.get_online_agents()
    for agent in online_agents:
        agent_id = agent.get('id')
        if agent_id:
            ws_manager.push_session_list_update(agent_id, "pending", formatted_pending)

    return {"success": True, "message": "接入成功"}


@socketio.on("match_agent")
def handle_match_agent_ws(data):
    """
    WebSocket 事件：匹配在线客服
    data: { user_id, session_id, token }
    """
    try:
        from flask import request as flask_request
        _ = flask_request.sid  # 保留获取 socket_id 的能力，便于未来扩展

        user_id = int(data.get("user_id", 0) or 0)
        session_id = str(data.get("session_id", "")).strip()
        token = str(data.get("token", "")).strip()

        if not user_id or not session_id or not token:
            return {"success": False, "message": "缺少必要参数"}

        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}

        user_row = db.get_user_by_id(user_id)
        if not user_row:
            return {"success": False, "message": "用户不存在"}

        # token 与用户匹配检查
        token_uid = payload.get("user_id")
        if token_uid and int(token_uid) != int(user_id):
            return {"success": False, "message": "Token 与用户不匹配"}

        return _match_agent_logic(user_id, session_id)
    except Exception as e:
        logger.error(f"匹配客服失败（WS）: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("accept_session")
def handle_accept_session_ws(data):
    """
    WebSocket 事件：客服接入会话
    data: { user_id, session_id, token }
    """
    try:
        from flask import request as flask_request
        _ = flask_request.sid

        user_id = int(data.get("user_id", 0) or 0)
        session_id = str(data.get("session_id", "")).strip()
        token = str(data.get("token", "")).strip()

        if not user_id or not session_id or not token:
            return {"success": False, "message": "缺少必要参数"}

        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}

        user_row = db.get_user_by_id(user_id)
        if not user_row:
            return {"success": False, "message": "用户不存在"}

        user_role = user_row.get("role", "user")
        if user_role not in ['customer_service', 'admin']:
            return {"success": False, "message": "无权限访问"}

        token_uid = payload.get("user_id")
        if token_uid and int(token_uid) != int(user_id):
            return {"success": False, "message": "Token 与用户不匹配"}

        return _accept_session_logic(user_id, session_id)
    except Exception as e:
        logger.error(f"接入会话失败（WS）: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


def _get_reply_message_info(reply_to_message_id: int | None) -> Dict[str, Any] | None:
    """
    获取引用消息的摘要信息
    
    Args:
        reply_to_message_id: 引用消息的ID
        
    Returns:
        引用消息摘要信息，如果不存在或出错则返回None
    """
    if not reply_to_message_id:
        return None
    
    try:
        reply_msg = db.get_message_by_id(reply_to_message_id)
        if not reply_msg:
            return None
        
        # 获取引用消息的发送者用户名
        reply_from_user_id = reply_msg.get("from_user_id")
        reply_from_username = None
        if reply_from_user_id:
            try:
                reply_from_user = db.get_user_by_id(reply_from_user_id)
                if reply_from_user:
                    reply_from_username = reply_from_user.get("username")
            except Exception:
                pass
        
        # 格式化 created_at
        created_at_str = None
        if reply_msg.get('created_at'):
            if isinstance(reply_msg['created_at'], datetime):
                created_at_str = reply_msg['created_at'].isoformat()
            elif isinstance(reply_msg['created_at'], str):
                created_at_str = reply_msg['created_at']
        
        # 构建引用消息摘要信息
        return {
            "id": reply_msg.get("id"),
            "message": "[消息已撤回]" if reply_msg.get("is_recalled") else reply_msg.get("message", ""),
            "message_type": reply_msg.get("message_type", "text"),
            "is_recalled": reply_msg.get("is_recalled", False),
            "from_user_id": reply_from_user_id,
            "from_username": reply_from_username,
            "created_at": created_at_str
        }
    except Exception as e:
        logger.error(f"获取引用消息摘要失败: message_id={reply_to_message_id}, error={e}", exc_info=True)
        return None


def _format_time(dt) -> str:
    """格式化时间为可读字符串"""
    if not dt:
        return "刚刚"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return "刚刚"
    if isinstance(dt, datetime):
        now = datetime.now()
        diff = now - dt
        if diff.total_seconds() < 60:
            return "刚刚"
        elif diff.total_seconds() < 3600:
            return f"{int(diff.total_seconds() / 60)} 分钟前"
        elif diff.total_seconds() < 86400:
            return f"{int(diff.total_seconds() / 3600)} 小时前"
        else:
            return dt.strftime("%m-%d %H:%M")
    return "刚刚"


def _format_session_list(sessions: list, include_duration: bool = True) -> list:
    """
    格式化会话列表
    
    Args:
        sessions: 会话列表
        include_duration: 是否包含会话时长（待接入会话不需要）
    
    Returns:
        格式化后的会话列表
    """
    formatted_sessions = []
    for session in sessions:
        # 安全获取 user_id（可能在不同的查询中字段名不同）
        user_id = session.get('user_id') or session.get('userId')
        if not user_id:
            # 如果还是没有，跳过这条记录
            logging.warning(f"会话 {session.get('session_id', 'unknown')} 缺少 user_id，跳过")
            continue
        
        # 获取用户 VIP 信息
        vip_info = db.get_user_vip_info(user_id)
        is_vip = bool(vip_info and vip_info.get('is_vip', False)) if vip_info else False

        # 计算会话时长
        duration = "00:00"
        if include_duration and session.get('started_at'):
            start_time = session['started_at']
            if isinstance(start_time, str):
                try:
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                except:
                    start_time = None
            if isinstance(start_time, datetime):
                diff = datetime.now() - start_time
                hours = int(diff.total_seconds() // 3600)
                minutes = int((diff.total_seconds() % 3600) // 60)
                duration = f"{hours:02d}:{minutes:02d}"

        # 获取用户头像
        user_info = db.get_user_by_id(user_id)
        avatar_base64 = None
        if user_info and user_info.get('avatar'):
            import base64
            try:
                avatar_base64 = f"data:image/png;base64,{base64.b64encode(user_info['avatar']).decode('utf-8')}"
            except:
                pass
        
        formatted_sessions.append({
            "id": session.get('session_id', ''),
            "userName": session.get('username', '未知用户'),
            "userId": user_id,
            "isVip": is_vip,
            "category": "待分类",
            "lastMessage": session.get('last_message', '')[:50] if session.get('last_message') else '',
            "lastTime": _format_time(session.get('last_time') or session.get('created_at')),
            "duration": duration,
            "unread": int(session.get('unread_count', 0) or 0),
            "avatar": avatar_base64
        })
    
    return formatted_sessions


# ==================== WebSocket 事件处理器 ====================

@socketio.on("connect")
def handle_connect():
    """WebSocket 连接建立"""
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        logger.debug(f"WebSocket 连接建立: {socket_id}")
        return {"success": True, "socket_id": socket_id}
    except Exception as e:
        logger.error(f"处理连接事件失败: {e}", exc_info=True)
        return {"success": False, "message": str(e)}


@socketio.on("disconnect")
def handle_disconnect():
    """WebSocket 连接断开"""
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        logger.debug(f"WebSocket 连接断开: {socket_id}")
        
        # 断开连接
        ws_manager.disconnect(socket_id=socket_id)
        
    except Exception as e:
        logger.error(f"处理断开事件失败: {e}", exc_info=True)


@socketio.on("register")
def handle_register(data):
    """
    注册 WebSocket 连接
    data: {
        user_id: int,
        token: str,
        connection_id: str,
        device_id?: str,
        device_info?: {...}
    }
    """
    try:
        from flask import request as flask_request
        
        user_id = int(data.get("user_id", 0) or 0)
        token = str(data.get("token", "")).strip()
        connection_id = str(data.get("connection_id", "")).strip()
        device_id = data.get("device_id")
        device_info = data.get("device_info", {})
        
        if not user_id or not token or not connection_id:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 验证用户
        user_row = db.get_user_by_id(user_id)
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 获取连接信息
        socket_id = flask_request.sid
        ip_address = flask_request.remote_addr
        user_agent = flask_request.headers.get('User-Agent')
        
        # 注册设备（如果提供）
        if device_id and device_info:
            db.register_user_device(
                user_id=user_id,
                device_id=device_id,
                device_name=device_info.get('device_name'),
                device_type=device_info.get('device_type', 'other'),
                platform=device_info.get('platform'),
                browser=device_info.get('browser'),
                os_version=device_info.get('os_version'),
                app_version=device_info.get('app_version')
            )
        
        # 注册连接
        success = ws_manager.connect(
            user_id=user_id,
            socket_id=socket_id,
            connection_id=connection_id,
            device_id=device_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        if success:
            logger.debug(f"用户 {user_id} 注册 WebSocket 连接成功: {connection_id}")
            return {
                "success": True,
                "connection_id": connection_id,
                "socket_id": socket_id,
                "message": "连接注册成功"
            }
        else:
            return {"success": False, "message": "注册连接失败"}
    
    except Exception as e:
        logger.error(f"注册连接失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("heartbeat")
def handle_heartbeat(data):
    """
    心跳检测
    data: {
        connection_id: str
    }
    """
    try:
        connection_id = data.get("connection_id")
        if not connection_id:
            logger.warning("收到心跳但缺少连接ID")
            return {"success": False, "message": "缺少连接ID"}
        
        success = ws_manager.update_heartbeat(connection_id=connection_id)
        
        if success:
            logger.debug(f"收到心跳并更新成功: connection_id={connection_id}")
            return {"success": True, "timestamp": datetime.now().isoformat()}
        else:
            logger.warning(f"收到心跳但连接不存在: connection_id={connection_id}")
            return {"success": False, "message": "连接不存在"}
    
    except Exception as e:
        logger.error(f"处理心跳失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("message_delivered")
def handle_message_delivered(data):
    """
    消息送达回执
    data: {
        message_id: int,
        user_id: int
    }
    """
    try:
        message_id = int(data.get("message_id", 0) or 0)
        user_id = int(data.get("user_id", 0) or 0)
        
        if not message_id or not user_id:
            return {"success": False, "message": "参数缺失"}
        
        # 更新消息状态为已送达
        ws_manager.handle_message_status(message_id, 'delivered', user_id)
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"处理消息送达回执失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("message_read")
def handle_message_read(data):
    """
    消息已读回执
    data: {
        message_id: int,
        user_id: int
    }
    """
    try:
        message_id = int(data.get("message_id", 0) or 0)
        user_id = int(data.get("user_id", 0) or 0)
        
        if not message_id or not user_id:
            return {"success": False, "message": "参数缺失"}
        
        # 更新消息状态为已读
        ws_manager.handle_message_status(message_id, 'read', user_id)
        
        return {"success": True}
    
    except Exception as e:
        logger.error(f"处理消息已读回执失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("subscribe_sessions")
def handle_subscribe_sessions(data):
    """
    订阅会话列表
    data: { user_id, token, type }  # type: 'my' 或 'pending'
    """
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        
        user_id = int(data.get("user_id", 0) or 0)
        token = str(data.get("token", "")).strip()
        session_type = str(data.get("type", "my")).strip()
        
        if not user_id or not token:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 验证用户和权限
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("订阅会话列表时数据库异常: %s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        user_role = user_row.get("role", "user")
        if user_role not in ['customer_service', 'admin']:
            return {"success": False, "message": "无权限访问"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 获取会话列表
        if session_type == 'pending':
            sessions = db.get_pending_sessions()
        else:
            sessions = db.get_agent_sessions(user_id, include_pending=False)
        
        # 格式化会话列表
        formatted_sessions = _format_session_list(sessions, include_duration=(session_type != 'pending'))
        
        # 推送初始会话列表
        ws_manager.push_session_list_update(user_id, session_type, formatted_sessions)
        
        logger.debug(f"用户 {user_id} 订阅会话列表: type={session_type}, count={len(formatted_sessions)}")
        return {"success": True, "message": "订阅成功", "count": len(formatted_sessions)}
    
    except Exception as e:
        logger.error(f"订阅会话列表失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("subscribe_pending_sessions")
def handle_subscribe_pending_sessions(data):
    """
    订阅待接入会话列表
    data: { user_id, token }
    """
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        
        user_id = int(data.get("user_id", 0) or 0)
        token = str(data.get("token", "")).strip()
        
        if not user_id or not token:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 验证用户和权限
        user_row = db.get_user_by_id(user_id)
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        user_role = user_row.get("role", "user")
        if user_role not in ['customer_service', 'admin']:
            return {"success": False, "message": "无权限访问"}
        
        # 获取待接入会话列表
        pending_sessions = db.get_pending_sessions()
        
        # 格式化会话列表
        formatted_sessions = _format_session_list(pending_sessions, include_duration=False)
        
        # 推送初始待接入会话列表
        ws_manager.push_session_list_update(user_id, "pending", formatted_sessions)
        
        logger.debug(f"用户 {user_id} 订阅待接入会话列表: count={len(formatted_sessions)}")
        return {"success": True, "message": "订阅成功", "count": len(formatted_sessions)}
    
    except Exception as e:
        logger.error(f"订阅待接入会话列表失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("update_agent_status")
def handle_update_agent_status(data):
    """
    更新客服在线状态（WebSocket）
    data: { user_id, status, token }
    """
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        
        user_id = int(data.get("user_id", 0) or 0)
        status = str(data.get("status", "")).strip()
        token = str(data.get("token", "")).strip()
        
        if not user_id:
            return {"success": False, "message": "缺少用户ID"}
        if status not in ['online', 'offline', 'away', 'busy']:
            return {"success": False, "message": "无效的状态"}
        if not token:
            return {"success": False, "message": "缺少 Token"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 验证用户和权限
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("更新客服在线状态时数据库异常: %s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        user_role = user_row.get("role", "user")
        if user_role not in ['customer_service', 'admin']:
            return {"success": False, "message": "无权限访问"}
        
        # 更新状态
        success = db.update_agent_status(user_id, status)
        if not success:
            return {"success": False, "message": "更新状态失败"}
        
        # 推送状态变化给所有客服
        ws_manager.push_agent_status_changed(user_id, status)
        
        logger.debug(f"客服 {user_id} 状态更新: {status}")
        return {"success": True, "message": "状态更新成功"}
    
    except Exception as e:
        logger.error(f"更新客服状态失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("subscribe_vip_info")
def handle_subscribe_vip_info(data):
    """
    订阅 VIP 信息
    data: { user_id, token }
    """
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        
        user_id = int(data.get("user_id", 0) or 0)
        token = str(data.get("token", "")).strip()
        
        if not user_id or not token:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 验证用户
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("订阅 VIP 信息时数据库异常: %s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 获取初始 VIP 信息
        vip_row = db.get_user_vip_info(user_id)
        vip_info = _vip_dict_from_row(vip_row)
        
        # 推送初始 VIP 信息
        ws_manager.push_vip_status_update(user_id, vip_info)
        
        logger.debug(f"用户 {user_id} 订阅 VIP 信息成功")
        return {"success": True, "message": "订阅成功", "vip_info": vip_info}
    
    except Exception as e:
        logger.error(f"订阅 VIP 信息失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("subscribe_user_profile")
def handle_subscribe_user_profile(data):
    """
    订阅用户资料更新
    data: { user_id, token }
    """
    try:
        from flask import request as flask_request
        socket_id = flask_request.sid
        
        user_id = int(data.get("user_id", 0) or 0)
        token = str(data.get("token", "")).strip()
        
        if not user_id or not token:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 验证用户
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("订阅用户资料时数据库异常: %s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 获取初始用户资料
        user = _user_dict_with_avatar(user_row)
        vip_row = db.get_user_vip_info(user_id)
        vip = _vip_dict_from_row(vip_row)
        profile_data = {"user": user, "vip": vip}
        
        # 推送初始用户资料
        ws_manager.push_user_profile_update(user_id, profile_data)
        
        logger.debug(f"用户 {user_id} 订阅用户资料成功")
        return {"success": True, "message": "订阅成功", "profile": profile_data}
    
    except Exception as e:
        logger.error(f"订阅用户资料失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("edit_message")
def handle_edit_message(data):
    """
    编辑消息（WebSocket）
    data: {
      message_id, user_id, session_id, new_content, token
    }
    返回给回调：{success, message?}
    """
    try:
        message_id = data.get("message_id")
        user_id = int(data.get("user_id", 0) or 0)
        session_id = str(data.get("session_id", "")).strip()
        new_content = str(data.get("new_content", "")).strip()
        token = str(data.get("token", "")).strip()
        
        if not message_id or not user_id or not session_id or not new_content or not token:
            return {"success": False, "message": "参数缺失"}
        
        if not new_content:
            return {"success": False, "message": "消息内容不能为空"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 获取用户信息
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("编辑消息时获取用户信息失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 编辑消息
        try:
            success = db.edit_message(message_id, user_id, new_content)
            if not success:
                return {"success": False, "message": "编辑失败，可能是无权限或消息已过期"}
            
            # 获取编辑后的消息信息
            message = db.get_message_by_id(message_id)
            if not message:
                return {"success": False, "message": "编辑成功但获取消息信息失败"}
            
            # 获取编辑时间
            edited_at = message.get("edited_at")
            if isinstance(edited_at, datetime):
                edited_at_str = edited_at.isoformat()
            else:
                edited_at_str = datetime.now().isoformat()
            
            # 推送消息编辑事件给会话中的所有用户
            ws_manager.push_message_edited(session_id, message_id, new_content, edited_at_str)
            
            logger.debug(f"消息 {message_id} 编辑成功")
            return {"success": True, "message": "编辑成功", "edited_at": edited_at_str}
        
        except Exception as e:
            logger.error(f"编辑消息失败: {e}", exc_info=True)
            return {"success": False, "message": "编辑失败，请稍后重试"}
    
    except Exception as e:
        logger.error(f"处理消息编辑失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("close_session")
def handle_close_session(data):
    """
    关闭会话（WebSocket）
    data: {
      session_id, user_id, token
    }
    返回给回调：{success, message?}
    """
    try:
        session_id = str(data.get("session_id", "")).strip()
        user_id = int(data.get("user_id", 0) or 0)
        token = str(data.get("token", "")).strip()
        
        if not session_id or not user_id or not token:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 获取用户信息
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("关闭会话时获取用户信息失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 关闭会话
        try:
            success = db.close_session(session_id, user_id)
            if not success:
                return {"success": False, "message": "关闭失败，可能是无权限或会话不存在"}
            
            # 获取会话信息
            session = db.get_chat_session_by_id(session_id)
            if not session:
                return {"success": False, "message": "关闭成功但获取会话信息失败"}
            
            session_user_id = session.get("user_id")
            session_agent_id = session.get("agent_id")
            
            # 推送会话状态更新给会话相关用户
            ws_manager.push_session_status_update(session_id, "closed", session_user_id, session_agent_id)
            
            # 如果用户是客服，同时推送会话列表更新
            if user_row.get("role") in ['customer_service', 'admin']:
                sessions = db.get_agent_sessions(user_id, include_pending=False)
                formatted_sessions = _format_session_list(sessions, include_duration=True)
                ws_manager.push_session_list_update(user_id, "my", formatted_sessions)
            
            logger.debug(f"会话 {session_id} 已关闭（由用户 {user_id} 关闭）")
            return {"success": True, "message": "会话已关闭"}
        
        except Exception as e:
            logger.error(f"关闭会话失败: {e}", exc_info=True)
            return {"success": False, "message": "关闭失败，请稍后重试"}
    
    except Exception as e:
        logger.error(f"处理关闭会话失败: {e}", exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("recall_message")
def handle_recall_message(data):
    """
    WebSocket 撤回消息：
    data: {
      message_id, user_id, token
    }
    返回给回调：{success, message?}
    """
    try:
        message_id = data.get("message_id")
        user_id = data.get("user_id")
        token = str(data.get("token", "")).strip()
        
        if not message_id or not user_id or not token:
            return {"success": False, "message": "参数缺失"}
        
        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}
        
        # 获取用户信息
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("撤回消息时获取用户信息失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        if not user_row:
            return {"success": False, "message": "用户不存在"}
        
        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}
        
        # 撤回消息
        try:
            success = db.recall_message(int(message_id), user_id)
            logger.info(f"撤回消息数据库操作结果: message_id={message_id}, user_id={user_id}, success={success}")
            if success:
                # 获取消息详情
                message = db.get_message_by_id(int(message_id))
                if message:
                    session_id = message.get("session_id")
                    from_user_id = message.get("from_user_id")
                    to_user_id = message.get("to_user_id")
                    
                    # 如果数据库中的 to_user_id 为空，但会话已经有客服/用户绑定，尝试补全接收方，确保 Web 端也能收到撤回事件
                    if not to_user_id and session_id:
                        try:
                            chat_session = db.get_chat_session_by_id(session_id)
                        except Exception as e:
                            logger.error(f"撤回消息时获取会话失败: session_id={session_id}, error={e}", exc_info=True)
                            chat_session = None
                        
                        if chat_session:
                            cs_user_id = chat_session.get("user_id")
                            cs_agent_id = chat_session.get("agent_id")
                            # 如果当前撤回的是用户消息，则接收方应为客服；反之亦然
                            if from_user_id and cs_user_id and cs_agent_id:
                                try:
                                    if int(from_user_id) == int(cs_user_id):
                                        to_user_id = cs_agent_id
                                    elif int(from_user_id) == int(cs_agent_id):
                                        to_user_id = cs_user_id
                                except Exception:
                                    # 回退逻辑：直接根据等号比较
                                    if from_user_id == cs_user_id:
                                        to_user_id = cs_agent_id
                                    elif from_user_id == cs_agent_id:
                                        to_user_id = cs_user_id
                        
                        # 如果仍然为空，再尝试从最近的消息中推断接收方（与发送逻辑保持一致）
                        if not to_user_id and session_id:
                            try:
                                recent_messages = db.get_chat_messages(session_id, limit=10)
                                for msg in recent_messages:
                                    msg_from_uid = msg.get("from_user_id")
                                    msg_to_uid = msg.get("to_user_id")
                                    if msg_from_uid != from_user_id and msg_to_uid:
                                        to_user_id = msg_to_uid
                                        break
                                    if msg_to_uid == from_user_id:
                                        to_user_id = msg_from_uid
                                        break
                            except Exception as e:
                                logger.error(f"撤回消息时从历史消息推断接收方失败: message_id={message_id}, session_id={session_id}, error={e}", exc_info=True)
                    
                    # 获取发送者的用户名
                    from_username = None
                    try:
                        from_user_row = db.get_user_by_id(from_user_id)
                        if from_user_row:
                            from_username = from_user_row.get("username")
                    except Exception:
                        pass
                    
                    # 推送撤回消息事件给会话中的所有用户
                    recall_data = {
                        "message_id": str(message_id),
                        "session_id": session_id,
                        "from_user_id": from_user_id,
                        "username": from_username,
                        "is_recalled": True,
                        "time": _format_time(datetime.now()),
                    }
                    
                    # 发送给接收方
                    if to_user_id:
                        ws_manager.send_message_to_user(to_user_id, "message_recalled", recall_data)
                    else:
                        logger.warning(f"撤回消息时 to_user_id 为 None: message_id={message_id}, from_user_id={from_user_id}, session_id={session_id}")
                    
                    # 发送给发送方（多设备同步）
                    ws_manager.send_message_to_user(from_user_id, "message_recalled", recall_data)
                else:
                    logger.warning(f"撤回消息后无法获取消息详情: message_id={message_id}")
                
                return {"success": True, "message": "消息已撤回"}
            else:
                return {"success": False, "message": "撤回失败，可能是消息不存在、无权撤回、已撤回或超过2分钟"}
        except ConnectionError as e:
            logger.error("撤回消息失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        except Exception as e:
            logger.error("撤回消息时发生错误: %s", e, exc_info=True)
            return {"success": False, "message": "撤回消息失败"}
    
    except Exception as e:
        logger.error("WebSocket 撤回消息失败: %s", e, exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("get_session_messages")
def handle_get_session_messages(data):
    """
    WebSocket 获取会话历史消息：
    data: {
      session_id, user_id, token, limit?
    }
    返回给回调：{success, messages: []}

    说明：
    - 统一为用户端 / 客服端提供历史消息接口；
    - 权限校验：
      * 普通用户只能访问自己的会话；
      * 客服 / 管理员只能访问分配给自己的会话；
    - 为兼容前端，消息结构与 HTTP 接口保持一致，并包含引用消息摘要、编辑标记等字段。
    """
    try:
        session_id = str(data.get("session_id", "")).strip()
        user_id = data.get("user_id")
        token = str(data.get("token", "")).strip()
        limit = int(data.get("limit", 200) or 200)

        if not session_id or not user_id or not token:
            return {"success": False, "message": "参数缺失"}

        # 验证 token
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}

        # 验证用户
        try:
            user_row = db.get_user_by_id(user_id)
        except ConnectionError as e:
            logger.error("WebSocket 获取会话消息时获取用户信息失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}

        if not user_row:
            return {"success": False, "message": "用户不存在"}

        # 验证 token 与用户匹配
        token_email = payload.get("email")
        if token_email and user_row.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}

        # 验证会话权限
        try:
            chat_session = db.get_chat_session_by_id(session_id)
        except ConnectionError as e:
            logger.error("WebSocket 获取会话消息时获取会话失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}

        if not chat_session:
            return {"success": False, "message": "会话不存在"}

        session_user_id = chat_session.get("user_id")
        session_agent_id = chat_session.get("agent_id")
        user_role = user_row.get("role", "user")

        # 普通用户只能访问自己的会话；客服 / 管理员只能访问与自己关联的会话
        if user_role == "user":
            if session_user_id != user_id:
                return {"success": False, "message": "无权限访问此会话"}
        else:  # customer_service 或 admin
            if session_agent_id != user_id and session_user_id != user_id:
                return {"success": False, "message": "无权限访问此会话"}

        # 限制 limit 范围（防止过大请求）
        limit = min(max(limit, 1), 200)

        # 获取消息
        try:
            messages = db.get_chat_messages(
                session_id=session_id,
                limit=limit,
            )
        except ConnectionError as e:
            logger.error("WebSocket 获取会话消息时数据库异常: %s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}

        # 格式化消息数据（结构尽量与 HTTP 接口保持一致）
        formatted_messages = []
        for msg in messages:
            msg_user_id = msg["from_user_id"]

            # 获取发送者的用户信息（包括头像）
            msg_user = db.get_user_by_id(msg_user_id)
            avatar_base64 = None
            if msg_user and msg_user.get("avatar"):
                try:
                    avatar_base64 = f"data:image/png;base64,{base64.b64encode(msg_user['avatar']).decode('utf-8')}"
                except Exception:
                    pass

            # 获取发送者用户名
            msg_username = None
            if msg_user:
                msg_username = msg_user.get("username")

            # 格式化 created_at 为 ISO 字符串
            created_at_str = None
            if msg.get("created_at"):
                if isinstance(msg["created_at"], datetime):
                    created_at_str = msg["created_at"].isoformat()
                elif isinstance(msg["created_at"], str):
                    created_at_str = msg["created_at"]

            # from 字段：对于客服/管理员，自己的消息标记为 agent；对于普通用户，自己的消息标记为 user
            if user_role in ["customer_service", "admin"]:
                from_field = "agent" if msg_user_id == user_id else "user"
            else:
                from_field = "user" if msg_user_id == user_id else "agent"

            formatted_msg = {
                "id": str(msg["id"]),
                "from": from_field,
                "text": "[消息已撤回]" if msg.get("is_recalled") else msg["message"],
                "time": _format_time(msg["created_at"]),
                "created_at": created_at_str,
                "userId": msg_user_id,
                "username": msg_username,
                "avatar": avatar_base64,
                "message_type": msg.get("message_type", "text"),
                "is_recalled": msg.get("is_recalled", False),
                "is_edited": msg.get("is_edited", False),
                "edited_at": msg.get("edited_at").isoformat() if msg.get("edited_at") else None,
                "reply_to_message_id": msg.get("reply_to_message_id"),
            }

            # 如果存在引用消息，添加引用消息摘要
            reply_to_message_id = msg.get("reply_to_message_id")
            if reply_to_message_id:
                reply_info = _get_reply_message_info(reply_to_message_id)
                if reply_info:
                    formatted_msg["reply_to_message"] = reply_info

            formatted_messages.append(formatted_msg)

        return {"success": True, "messages": formatted_messages}
    except Exception as e:
        logger.error("WebSocket 获取会话消息失败: %s", e, exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("send_message")
def handle_send_message(data):
    """
    WebSocket 发送消息：
    data: {
      session_id, from_user_id, to_user_id?, message, role: 'user' | 'agent', token, message_type?, reply_to_message_id?
    }
    返回给回调：{success, message_id?, time?, message?}
    """
    try:
        session_id = str(data.get("session_id", "")).strip()
        from_user_id = data.get("from_user_id")
        to_user_id = data.get("to_user_id")
        message = str(data.get("message", "")).strip()
        role = str(data.get("role", "user")).strip()
        token = str(data.get("token", "")).strip()
        message_type = str(data.get("message_type", "text") or "text").strip()
        reply_to_message_id = data.get("reply_to_message_id")

        if not session_id or not from_user_id or not message or not token:
            return {"success": False, "message": "参数缺失"}

        # 校验并解析 Token，确保与发送者匹配
        payload = verify_token(token)
        if not payload:
            return {"success": False, "message": "Token 无效或已过期"}

        sender = db.get_user_by_id(from_user_id)
        if not sender:
            return {"success": False, "message": "发送者不存在"}

        token_email = payload.get("email")
        if token_email and sender.get("email") != token_email:
            return {"success": False, "message": "Token 与用户不匹配"}

        try:
            chat_session = db.get_chat_session_by_id(session_id)
        except ConnectionError as e:
            logger.error("WebSocket 发送消息时获取会话失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}
        if not chat_session:
            return {"success": False, "message": "会话不存在"}

        # 决定接收方
        if role == "user":
            to_user_id = chat_session.get("agent_id")
        else:
            # 客服发送消息时，优先使用传入的to_user_id，否则从会话中获取user_id
            to_user_id = to_user_id or chat_session.get("user_id")
            # 如果仍然为None，尝试从会话的历史消息中获取接收方用户ID（备用机制）
            if to_user_id is None:
                logger.warning(f"客服发送消息时无法从会话获取接收方，尝试从历史消息中获取: session_id={session_id}, from_user_id={from_user_id}, role={role}")
                try:
                    # 查询会话中最近的一条消息，获取接收方用户ID
                    recent_messages = db.get_chat_messages(session_id, limit=10)
                    for msg in recent_messages:
                        # 如果消息的from_user_id不是当前发送者，且to_user_id不为None，则使用它
                        msg_from_user_id = msg.get("from_user_id")
                        msg_to_user_id = msg.get("to_user_id")
                        if msg_from_user_id != from_user_id and msg_to_user_id:
                            to_user_id = msg_to_user_id
                            logger.info(f"从历史消息中获取到接收方用户ID: {to_user_id}, session_id={session_id}")
                            break
                        # 或者如果消息的to_user_id是当前发送者，则from_user_id就是接收方
                        if msg_to_user_id == from_user_id:
                            to_user_id = msg_from_user_id
                            logger.info(f"从历史消息中获取到接收方用户ID: {to_user_id}, session_id={session_id}")
                            break
                except Exception as e:
                    logger.error(f"从历史消息中获取接收方用户ID失败: {e}", exc_info=True)
                # 如果仍然为None，记录错误日志
                if to_user_id is None:
                    logger.error(f"客服发送消息时无法确定接收方: session_id={session_id}, chat_session={chat_session}, from_user_id={from_user_id}, role={role}")

        # 统一将用户ID转换为整数，避免类型不一致导致在线状态判断失败
        try:
            from_user_id = int(from_user_id)
        except (TypeError, ValueError):
            return {"success": False, "message": "发送者ID无效"}
        try:
            to_user_id = int(to_user_id) if to_user_id is not None else None
        except (TypeError, ValueError):
            logger.warning(f"无法解析接收方用户ID: {to_user_id}，将不推送实时消息")
            to_user_id = None

        if message_type not in ["text", "image", "file"]:
            message_type = "text"

        # 验证引用消息（如果提供）
        reply_to_id = None
        if reply_to_message_id:
            try:
                reply_to_id = int(reply_to_message_id)
                # 检查ID是否有效（必须大于0）
                if reply_to_id <= 0:
                    logger.warning(f"引用消息ID无效: message_id={reply_to_id}（ID必须大于0），已按普通消息处理")
                    reply_to_id = None
                else:
                    reply_msg = db.get_message_by_id(reply_to_id)
                    if not reply_msg:
                        # 引用的原消息在数据库中不存在时，降级为普通消息发送，避免阻塞发送流程
                        logger.warning(f"引用消息不存在: message_id={reply_to_id}, session_id={session_id}，已按普通消息处理")
                        reply_to_id = None
                    else:
                        # 确保 session_id 都是字符串类型进行比较
                        reply_session_id = str(reply_msg.get("session_id") or "").strip()
                        current_session_id = str(session_id).strip()
                        
                        if reply_session_id != current_session_id:
                            # 引用不属于当前会话，同样降级为普通消息
                            logger.warning(
                                f"引用消息不属于当前会话: "
                                f"reply_msg_session_id={reply_session_id}, "
                                f"current_session_id={current_session_id}, "
                                f"reply_msg_id={reply_to_id}，已按普通消息处理"
                            )
                            reply_to_id = None
                        elif reply_msg.get("is_recalled"):
                            # 不能引用已撤回消息，这种情况直接返回错误提示
                            return {"success": False, "message": "不能引用已撤回的消息"}
            except (ValueError, TypeError) as e:
                # ID 格式异常时，同样降级为普通消息，避免报错阻塞
                logger.error(f"引用消息ID格式错误: {reply_to_message_id}, error: {e}，已按普通消息处理")
                reply_to_id = None

        try:
            message_id = db.insert_chat_message(
                session_id=session_id,
                from_user_id=from_user_id,
                to_user_id=to_user_id,
                message=message,
                message_type=message_type,
                reply_to_message_id=reply_to_id
            )
        except ConnectionError as e:
            logger.error("WebSocket 发送消息写库失败（数据库异常）：%s", e, exc_info=True)
            return {"success": False, "message": "数据库连接错误，请稍后重试"}

        if not message_id:
            return {"success": False, "message": "写入消息失败"}

        # 获取消息详情（包括创建时间）
        message_info = db.get_message_by_id(message_id)
        created_at = datetime.now()
        if message_info and message_info.get('created_at'):
            created_at = message_info['created_at']
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = datetime.now()

        # 获取发送者头像和用户名
        sender_info = db.get_user_by_id(from_user_id)
        avatar_base64 = None
        username = None
        if sender_info:
            if sender_info.get("avatar"):
                try:
                    avatar_base64 = f"data:image/png;base64,{base64.b64encode(sender_info['avatar']).decode('utf-8')}"
                except Exception:
                    pass
            username = sender_info.get("username")

        # 获取引用消息摘要信息（如果存在）
        reply_to_message_info = None
        if reply_to_id:
            try:
                reply_msg = db.get_message_by_id(reply_to_id)
                if reply_msg:
                    # 获取引用消息的发送者用户名
                    reply_from_user_id = reply_msg.get("from_user_id")
                    reply_from_username = None
                    if reply_from_user_id:
                        try:
                            reply_from_user = db.get_user_by_id(reply_from_user_id)
                            if reply_from_user:
                                reply_from_username = reply_from_user.get("username")
                        except Exception:
                            pass
                    
                    # 构建引用消息摘要信息
                    reply_to_message_info = {
                        "id": reply_msg.get("id"),
                        "message": "[消息已撤回]" if reply_msg.get("is_recalled") else reply_msg.get("message", ""),
                        "message_type": reply_msg.get("message_type", "text"),
                        "is_recalled": reply_msg.get("is_recalled", False),
                        "from_user_id": reply_from_user_id,
                        "from_username": reply_from_username,
                        "created_at": reply_msg.get("created_at").isoformat() if reply_msg.get("created_at") else None
                    }
            except Exception as e:
                logger.error(f"获取引用消息摘要失败: message_id={reply_to_id}, error={e}", exc_info=True)
                # 如果获取失败，不影响主消息发送，只是没有引用消息摘要

        # 确保 reply_to_id 为 None 时，返回的消息中也不包含引用信息
        # 为接收方添加 is_from_self 标记（False，因为这是对方发送的）
        payload_data = {
            "id": str(message_id),
            "session_id": session_id,
            "from": "agent" if role == "agent" else "user",
            "from_user_id": from_user_id,
            "to_user_id": to_user_id,
            "text": message,
            "time": _format_time(created_at),
            "created_at": created_at.isoformat(),  # 添加原始创建时间（ISO 格式）
            "avatar": avatar_base64,
            "username": username,  # 添加发送者用户名
            "message_type": message_type,
            "reply_to_message_id": reply_to_id,  # 即使为None也传递，让前端判断
            "status": "sent",
            "is_from_self": False,  # 对于接收方，这是对方发送的消息
        }
        
        # 如果存在引用消息摘要，添加到 payload_data
        if reply_to_message_info:
            payload_data["reply_to_message"] = reply_to_message_info
        
        # 记录日志，便于调试
        if reply_to_id:
            logger.debug(f"消息 {message_id} 包含引用消息ID: {reply_to_id}, 会话: {session_id}, 引用消息摘要已包含")
        else:
            logger.debug(f"消息 {message_id} 不包含引用消息，会话: {session_id}")

        # 使用 WebSocket 管理器推送消息
        if to_user_id:
            # 尝试推送给接收方，无论在线检测结果如何都尝试一次，避免误判导致漏推
            logger.debug(f"准备向用户 {to_user_id} 推送消息: message_id={message_id}, session_id={session_id}, from_user_id={from_user_id}, role={role}")
            delivered_count = ws_manager.send_message_to_user(to_user_id, "new_message", payload_data)
            logger.debug(f"消息推送完成: message_id={message_id}, to_user_id={to_user_id}, delivered_count={delivered_count}")
            if delivered_count == 0:
                logger.warning(f"发送给用户 {to_user_id} 的实时消息未送达（delivered_count=0），可能离线或房间未正确加入")
        else:
            logger.error(f"无法推送消息：to_user_id为None, message_id={message_id}, session_id={session_id}, from_user_id={from_user_id}, role={role}, chat_session={chat_session}")
            # 更新消息状态为已送达（基于数据库事务确认，使用重试机制）
            import threading
            def update_delivered_status():
                # 使用重试机制，最多重试3次，每次间隔100ms
                max_retries = 3
                retry_interval = 0.1  # 100ms
                for attempt in range(max_retries):
                    msg = db.get_message_by_id(message_id)
                    if msg:
                        # 消息已确认存在，更新状态
                        ws_manager.handle_message_status(message_id, 'delivered')
                        return
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_interval)
                # 所有重试都失败，记录警告但不中断流程
                logger.warning(f"消息 {message_id} 在更新已送达状态时未找到（已重试{max_retries}次）")
            threading.Thread(target=update_delivered_status, daemon=True).start()
        
        # 也广播给发送者（多设备同步）
        # 添加 is_from_self 标记，方便客户端判断
        payload_data_with_self = payload_data.copy()
        payload_data_with_self["is_from_self"] = True
        ws_manager.send_message_to_user(from_user_id, "new_message", payload_data_with_self)
        
        # 更新会话列表（如果发送者是客服，更新其会话列表）
        try:
            sender = db.get_user_by_id(from_user_id)
            if sender and sender.get('role') in ['customer_service', 'admin']:
                # 更新客服的会话列表
                sessions = db.get_agent_sessions(from_user_id, include_pending=False)
                formatted_sessions = _format_session_list(sessions)
                ws_manager.push_session_list_update(from_user_id, "my", formatted_sessions)
        except Exception as e:
            logger.debug(f"更新会话列表失败（可忽略）: {e}")
        
        # 更新消息状态为已发送（基于数据库事务确认，使用重试机制）
        import threading
        def update_sent_status():
            # 使用重试机制，最多重试3次，每次间隔100ms
            max_retries = 3
            retry_interval = 0.1  # 100ms
            for attempt in range(max_retries):
                msg = db.get_message_by_id(message_id)
                if msg:
                    # 消息已确认存在，更新状态
                    ws_manager.handle_message_status(message_id, 'sent')
                    return
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_interval)
            # 所有重试都失败，记录警告但不中断流程
            logger.warning(f"消息 {message_id} 在更新已发送状态时未找到（已重试{max_retries}次）")
        threading.Thread(target=update_sent_status, daemon=True).start()
        
        return {"success": True, "message_id": message_id, "time": payload_data["time"]}
    except Exception as e:
        logger.error("WebSocket 发送消息失败: %s", e, exc_info=True)
        return {"success": False, "message": "服务器错误"}


@socketio.on("link_preview")
def handle_link_preview_ws(data):
    """
    WebSocket 事件：获取链接预览
    data: { url, token? }
    """
    try:
        url = str(data.get("url", "")).strip()
        token = str(data.get("token", "")).strip()

        if not url:
            return {"success": False, "message": "缺少URL参数"}

        if token:
            payload = verify_token(token)
            if not payload:
                return {"success": False, "message": "Token 无效或已过期"}

        preview = fetch_link_preview(url, timeout=5)
        if not preview.get("success"):
            preview = get_simple_preview(url)

        return {"success": True, "preview": preview}
    except Exception as e:
        logger.error(f"获取链接预览失败: {e}", exc_info=True)
        preview = get_simple_preview(data.get("url", ""))
        return {"success": True, "preview": preview}


@socketio.on("process_rich_text")
def handle_process_rich_text_ws(data):
    """
    WebSocket 事件：处理富文本消息
    data: { content, user_id?, token? }
    """
    try:
        content = str(data.get("content", "")).strip()
        user_id = data.get("user_id")
        token = str(data.get("token", "")).strip()

        if not content:
            return {
                "success": True,
                "html": "",
                "is_rich": False,
                "urls": [],
                "mentions": []
            }

        if token:
            payload = verify_token(token)
            if not payload:
                return {"success": False, "message": "Token 无效或已过期"}
            if user_id and payload.get("user_id"):
                if int(user_id) != int(payload.get("user_id", 0)):
                    return {"success": False, "message": "Token 与用户ID不匹配"}

        result = process_rich_text(content, user_id)
        return {"success": True, **result}
    except Exception as e:
        logger.error(f"处理富文本失败: {e}", exc_info=True)
        return {"success": False, "message": "处理富文本时出错"}


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=8000,
        debug=False,
        use_reloader=False,
    )


