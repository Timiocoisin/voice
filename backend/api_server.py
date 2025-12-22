"""
后端 HTTP 服务入口。

本模块将现有的数据库与业务逻辑封装为一组 REST 风格接口，
供客户端（PyQt UI）通过 HTTP 调用，实现真正的前后端分离。

接口约定需与 `client/api_client.py` 严格保持一致。
"""

from __future__ import annotations

import base64
import logging
from datetime import datetime
from typing import Any, Dict

from flask import Flask, jsonify, request

from backend.config.config import email_config, SECRET_KEY  # noqa: F401
from backend.database.database_manager import DatabaseManager
from backend.email.email_sender import EmailSender, generate_verification_code
from backend.login.token_utils import generate_token, verify_token
from backend.logging_manager import setup_logging  # noqa: F401
from backend.membership_service import MembershipService
from backend.validation.validator import validate_email, validate_password
from backend.validation.verification_manager import VerificationManager


# 初始化日志
logger = logging.getLogger(__name__)

app = Flask(__name__)


# 全局单例：数据库、会员服务、验证码管理、邮件发送器
db = DatabaseManager()
membership_service = MembershipService(db)
verification_manager = VerificationManager()
email_sender = EmailSender(email_config)


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


@app.post("/api/send_verification_code")
def send_verification_code_api() -> Any:
    """
    发送邮箱验证码。
    Request JSON: { "email": str, "mode": "login" | "register" }

    规则：
    - login 模式：邮箱必须已注册，否则不给发码，提示“请先注册”；
    - register 模式：邮箱必须未注册，否则不给发码，提示“邮箱已被注册”。
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
                    "message": "该邮箱尚未注册，请先切换到“注册”并完成注册。",
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

    code = generate_verification_code()
    try:
        ok = email_sender.send_verification_code(email, code)
    except Exception as e:
        logger.error("发送验证码邮件失败：%s", e, exc_info=True)
        ok = False

    if not ok:
        return jsonify({"success": False, "message": "验证码发送失败，请稍后重试"}), 500

    verification_manager.set_verification_code(email, code)
    return jsonify({"success": True})


@app.post("/api/register")
def register_api() -> Any:
    """
    用户注册。
    Request JSON: { email, password, username, code }
    """
    data = request.get_json(force=True) or {}
    email = str(data.get("email", "")).strip()
    password = str(data.get("password", ""))
    username = str(data.get("username", "")).strip()
    code = str(data.get("code", "")).strip()

    if not username:
        return jsonify({"success": False, "message": "用户名不能为空"}), 400
    if not validate_email(email):
        return jsonify({"success": False, "message": "邮箱格式不正确"}), 400
    if not validate_password(password):
        return jsonify({"success": False, "message": "密码至少8位，需包含大小写字母、数字和特殊字符"}), 400
    if not verification_manager.verify_code(email, code):
        return jsonify({"success": False, "message": "验证码错误或已过期"}), 400

    # 已存在检查
    if db.get_user_by_email(email):
        return jsonify({"success": False, "message": "该邮箱已被注册"}), 400

    # 写库：DatabaseManager 会负责密码哈希
    ok = db.insert_user_info(username=username, email=email, password=password)
    if not ok:
        return jsonify({"success": False, "message": "注册失败，请稍后重试"}), 500

    user_row = db.get_user_by_email(email)
    if not user_row:
        return jsonify({"success": False, "message": "注册成功但未能读取用户信息"}), 500

    vip_row = db.get_user_vip_info(user_row["id"])
    vip = _vip_dict_from_row(vip_row)
    user = _user_dict_with_avatar(user_row)
    token = generate_token(email)

    logger.info("用户 %s 注册成功，ID: %s", user_row.get("username"), user_row.get("id"))

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


@app.post("/api/user/profile")
def get_user_profile_api() -> Any:
    """
    获取用户基础信息 + VIP 信息。
    Request JSON: { user_id }
    """
    data = request.get_json(force=True) or {}
    user_id = int(data.get("user_id", 0) or 0)
    if not user_id:
        return jsonify({"success": False, "message": "缺少用户ID"}), 400

    user_row = db.get_user_by_id(user_id)
    vip_row = db.get_user_vip_info(user_id)
    if not user_row:
        return jsonify({"success": False, "message": "用户不存在"}), 404

    user = _user_dict_with_avatar(user_row)
    vip = _vip_dict_from_row(vip_row)
    return jsonify({"success": True, "user": user, "vip": vip})


@app.post("/api/user/avatar")
def update_avatar_api() -> Any:
    """
    更新用户头像。
    Request JSON: { user_id, avatar_base64 }
    """
    data = request.get_json(force=True) or {}
    user_id = int(data.get("user_id", 0) or 0)
    avatar_b64 = data.get("avatar_base64")

    if not user_id or not avatar_b64:
        return jsonify({"success": False, "message": "参数不完整"}), 400

    try:
        avatar_bytes = base64.b64decode(avatar_b64)
    except Exception:
        return jsonify({"success": False, "message": "头像数据格式错误"}), 400

    ok = db.update_user_avatar(user_id, avatar_bytes)
    if not ok:
        return jsonify({"success": False, "message": "头像更新失败，请稍后重试"}), 500

    return jsonify({"success": True, "message": "头像更新成功"})


@app.post("/api/vip/info")
def get_vip_info_api() -> Any:
    """
    获取用户 VIP 信息。
    Request JSON: { user_id }
    """
    data = request.get_json(force=True) or {}
    user_id = int(data.get("user_id", 0) or 0)
    if not user_id:
        return jsonify({"success": False, "message": "缺少用户ID"}), 400

    vip_row = db.get_user_vip_info(user_id)
    vip = _vip_dict_from_row(vip_row)
    return jsonify({"success": True, "vip": vip})


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
    return jsonify(
        {
            "success": True,
            "message": "会员购买成功",
            "vip": vip,
        }
    )


@app.post("/api/diamond/balance")
def diamond_balance_api() -> Any:
    """
    获取钻石余额。
    Request JSON: { user_id }
    """
    data = request.get_json(force=True) or {}
    user_id = int(data.get("user_id", 0) or 0)
    if not user_id:
        return jsonify({"success": False, "message": "缺少用户ID"}), 400

    diamonds = membership_service.get_diamond_balance(user_id)
    return jsonify({"success": True, "diamonds": int(diamonds)})


if __name__ == "__main__":
    # 开发阶段默认启用 debug，部署到服务器时请关闭 debug，并用 WSGI/反向代理托管
    app.run(host="0.0.0.0", port=8000, debug=True)


