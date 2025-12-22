import logging
from typing import Optional, Dict, Any

"""
GUI 客户端统一的“远程服务”访问入口。

当前实现仍然直接调用 backend 模块，相当于在本机模拟远程服务。
后续如果要改成真正的 HTTP 调用，只需要在本文件中把具体实现
替换为 requests/httpx 调用后端接口，而无需修改各个 UI 代码。
"""

# 目前仍在本机模拟远程服务，因此这里临时引用 backend。
# 将来部署到真正远程服务器时，可以把这些 import 和实现替换掉。
from backend.database.database_manager import DatabaseManager
from backend.membership_service import MembershipService


def _get_db_manager() -> DatabaseManager:
    """内部辅助函数：每次调用创建一个新的 DatabaseManager。"""
    return DatabaseManager()


def register_user(username: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    注册新用户并返回用户及基础会员信息。

    返回:
        dict: {
            "user": {...},          # 用户基础信息
            "vip_info": {...} | None
        }
        如果注册失败返回 None
    """
    db = _get_db_manager()
    try:
        # 检查是否存在
        if db.get_user_by_email(email):
            return None

        if not db.insert_user_info(username, email, password):
            return None

        user = db.get_user_by_email(email)
        if not user:
            return None

        vip_info = db.get_user_vip_info(user["id"])
        return {"user": user, "vip_info": vip_info}
    except Exception as e:
        logging.error("注册用户失败: %s", e, exc_info=True)
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    使用邮箱 + 密码登录。

    返回:
        dict: {
            "user": {...},
            "vip_info": {...} | None
        }
        登录失败返回 None
    """
    import bcrypt

    db = _get_db_manager()
    try:
        user = db.get_user_by_email(email)
        if not user:
            return None

        hashed = user["password"].encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), hashed):
            return None

        vip_info = db.get_user_vip_info(user["id"])
        return {"user": user, "vip_info": vip_info}
    except Exception as e:
        logging.error("用户登录失败: %s", e, exc_info=True)
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_user_by_token(email_from_token: str) -> Optional[Dict[str, Any]]:
    """
    根据 token 中解析出的 email 获取用户基础信息和会员信息。
    注意：真正远程时应直接把 token 交给后端校验。
    """
    db = _get_db_manager()
    try:
        user = db.get_user_by_email(email_from_token)
        if not user:
            return None
        vip_info = db.get_user_vip_info(user["id"])
        return {"user": user, "vip_info": vip_info}
    except Exception as e:
        logging.error("通过 token 获取用户失败: %s", e, exc_info=True)
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_vip_info_by_user_id(user_id: int) -> Optional[Any]:
    """
    通过用户 ID 获取会员信息。
    """
    db = _get_db_manager()
    try:
        service = MembershipService(db)
        return service.get_vip_info(user_id)
    except Exception as e:
        logging.error("获取 VIP 信息失败: %s", e, exc_info=True)
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_user_basic_info(user_id: int) -> Optional[Dict[str, Any]]:
    """
    通过用户 ID 获取用户基础信息。
    """
    db = _get_db_manager()
    try:
        return db.get_user_by_id(user_id)
    except Exception as e:
        logging.error("获取用户信息失败: %s", e, exc_info=True)
        return None
    finally:
        try:
            db.close()
        except Exception:
            pass


def purchase_membership(user_id: int, card_info: Dict[str, Any]):
    """
    购买会员套餐：扣减钻石并更新 VIP，有关逻辑统一封装在服务层。

    返回:
        (success, new_expiry)
    """
    db = _get_db_manager()
    try:
        service = MembershipService(db)
        return service.purchase_membership(user_id=user_id, card_info=card_info)
    except Exception as e:
        logging.error("购买会员失败: %s", e, exc_info=True)
        return False, None
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_user_basic_with_avatar(user_id: int):
    """
    获取用户名和头像（用于会员/钻石弹窗头部显示）。

    返回:
        (username, QPixmap)
    """
    db = _get_db_manager()
    try:
        service = MembershipService(db)
        return service.get_user_basic_with_avatar(user_id)
    except Exception as e:
        logging.error("获取用户基本信息和头像失败: %s", e, exc_info=True)
        return None, None
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_diamond_balance(user_id: int) -> int:
    """
    获取用户当前钻石余额。
    """
    db = _get_db_manager()
    try:
        service = MembershipService(db)
        return service.get_diamond_balance(user_id)
    except Exception as e:
        logging.error("获取钻石余额失败: %s", e, exc_info=True)
        return 0
    finally:
        try:
            db.close()
        except Exception:
            pass


def update_user_avatar(user_id: int, avatar_bytes: bytes) -> bool:
    """
    更新用户头像。
    """
    db = _get_db_manager()
    try:
        return bool(db.update_user_avatar(user_id, avatar_bytes))
    except Exception as e:
        logging.error("更新用户头像失败: %s", e, exc_info=True)
        return False
    finally:
        try:
            db.close()
        except Exception:
            pass


def get_latest_announcement() -> str:
    """
    获取最新公告文本。
    """
    db = _get_db_manager()
    try:
        text = db.get_latest_announcement()
        return text or ""
    except Exception as e:
        logging.error("获取公告失败: %s", e, exc_info=True)
        return ""
    finally:
        try:
            db.close()
        except Exception:
            pass



