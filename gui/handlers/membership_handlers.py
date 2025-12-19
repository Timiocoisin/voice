import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def refresh_membership_from_db(main_window: "MainWindow") -> None:
    try:
        if not main_window.user_id:
            main_window.update_membership_info(None, "未登录", False, 0, None)
            return

        vip_info = main_window.membership_service.get_vip_info(main_window.user_id)
        user_row = main_window.db_manager.get_user_by_id(main_window.user_id)

        avatar_bytes = user_row.get("avatar") if user_row else None
        username = user_row.get("username") if user_row else "未登录"
        is_vip = bool(vip_info.is_vip) if vip_info else False
        diamonds = vip_info.diamonds if vip_info else 0

        main_window.update_membership_info(avatar_bytes, username, is_vip, diamonds, main_window.user_id)
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
        vip_info = main_window.membership_service.get_vip_info(main_window.user_id)
    except Exception as e:
        logging.error("获取 VIP 信息失败：%s", e, exc_info=True)
        main_window.vip_status_label.setToolTip("会员信息获取失败，请稍后重试")
        return

    if not vip_info or not vip_info.vip_expiry:
        main_window.vip_status_label.setToolTip("当前未开通会员")
        return

    expiry = vip_info.vip_expiry
    if expiry.year >= 2099:
        main_window.vip_status_label.setToolTip("已开通永久会员")
    else:
        date_str = expiry.strftime("%Y-%m-%d")
        main_window.vip_status_label.setToolTip(f"VIP 有效期至：{date_str}")