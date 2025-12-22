import logging
from datetime import datetime
from typing import TYPE_CHECKING

from client.api_client import get_user_profile

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def refresh_membership_from_db(main_window: "MainWindow") -> None:
    """通过后端接口刷新主窗口顶部的会员与钻石信息。"""
    try:
        if not main_window.user_id:
            main_window.update_membership_info(None, "未登录", False, 0, None)
            return

        profile = get_user_profile(main_window.user_id)
        if not profile:
            main_window.update_membership_info(None, "未登录", False, 0, main_window.user_id)
            return

        user = profile.get("user") or {}
        vip = profile.get("vip") or {}

        avatar_bytes = user.get("avatar_bytes")
        username = user.get("username") or "未登录"
        is_vip = bool(vip.get("is_vip", False))
        diamonds = vip.get("diamonds", 0)

        main_window.update_membership_info(
            avatar_bytes, username, is_vip, diamonds, main_window.user_id
        )
    except Exception as e:
        logging.error("刷新会员信息失败：%s", e, exc_info=True)
        from gui.handlers.message_utils import show_message

        show_message(
            main_window,
            "刷新会员信息失败，请稍后重试",
            "错误",
            variant="error",
        )


def refresh_vip_tooltip(main_window: "MainWindow") -> None:
    """根据后端返回的 VIP 信息更新 tooltip。"""
    if not hasattr(main_window, "vip_status_label"):
        return

    if not main_window.user_id:
        main_window.vip_status_label.setToolTip("未登录，暂无会员信息")
        return

    try:
        profile = get_user_profile(main_window.user_id)
    except Exception as e:
        logging.error("获取 VIP 信息失败：%s", e, exc_info=True)
        main_window.vip_status_label.setToolTip("会员信息获取失败，请稍后重试")
        return

    if not profile:
        main_window.vip_status_label.setToolTip("当前未开通会员")
        return

    vip = profile.get("vip") or {}
    expiry_str = vip.get("vip_expiry_date")
    if not expiry_str:
        main_window.vip_status_label.setToolTip("当前未开通会员")
        return

    try:
        # 假设后端以 ISO 格式返回，例如 "2025-12-31T23:59:59"
        expiry = datetime.fromisoformat(expiry_str)
    except Exception:
        main_window.vip_status_label.setToolTip("会员信息获取失败，请稍后重试")
        return

    if expiry.year >= 2099:
        main_window.vip_status_label.setToolTip("已开通永久会员")
    else:
        date_str = expiry.strftime("%Y-%m-%d")
        main_window.vip_status_label.setToolTip(f"VIP 有效期至：{date_str}")