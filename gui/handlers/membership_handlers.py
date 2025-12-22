import logging
from typing import TYPE_CHECKING

from gui import api_client

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def refresh_membership_from_db(main_window: "MainWindow") -> None:
    """通过统一的 API 客户端刷新会员和用户信息。"""
    try:
        if not main_window.user_id:
            main_window.update_membership_info(None, "未登录", False, 0, None)
            return

        vip_info = api_client.get_vip_info_by_user_id(main_window.user_id)
        user_row = api_client.get_user_basic_info(main_window.user_id)

        avatar_bytes = user_row.get("avatar") if user_row else None
        username = user_row.get("username") if user_row else "未登录"

        if vip_info:
            is_vip = getattr(vip_info, "is_vip", False) if not isinstance(vip_info, dict) else vip_info.get("is_vip", False)
            diamonds = getattr(vip_info, "diamonds", 0) if not isinstance(vip_info, dict) else vip_info.get("diamonds", 0)
            vip_expiry = getattr(vip_info, "vip_expiry", None) if not isinstance(vip_info, dict) else vip_info.get("vip_expiry")
        else:
            is_vip = False
            diamonds = 0
            vip_expiry = None

        # 把 vip_expiry 挂到 main_window 上，方便 tooltip 使用
        main_window._vip_expiry = vip_expiry

        main_window.update_membership_info(avatar_bytes, username, bool(is_vip), diamonds, main_window.user_id)
    except Exception as e:
        logging.error("刷新会员信息失败：%s", e, exc_info=True)
        from gui.handlers.message_utils import show_message
        show_message(
            main_window,
            "刷新会员信息失败，请稍后重试",
            "错误",
            variant="error"
        )


def refresh_vip_tooltip(main_window: "MainWindow") -> None:
    if not hasattr(main_window, "vip_status_label"):
        return

    if not main_window.user_id:
        main_window.vip_status_label.setToolTip("未登录，暂无会员信息")
        return

    try:
        vip_info = api_client.get_vip_info_by_user_id(main_window.user_id)
    except Exception as e:
        logging.error("获取 VIP 信息失败：%s", e, exc_info=True)
        main_window.vip_status_label.setToolTip("会员信息获取失败，请稍后重试")
        return

    if not vip_info:
        main_window.vip_status_label.setToolTip("当前未开通会员")
        return

    expiry = getattr(vip_info, "vip_expiry", None) if not isinstance(vip_info, dict) else vip_info.get("vip_expiry")
    if not expiry:
        main_window.vip_status_label.setToolTip("当前未开通会员")
        return

    if expiry.year >= 2099:
        main_window.vip_status_label.setToolTip("已开通永久会员")
    else:
        date_str = expiry.strftime("%Y-%m-%d")
        main_window.vip_status_label.setToolTip(f"VIP 有效期至：{date_str}")