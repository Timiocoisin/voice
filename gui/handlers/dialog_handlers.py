"""对话框处理模块。"""
import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QPoint

from backend.login.login_status_manager import check_login_status, save_login_status
from backend.login.token_storage import read_token
from backend.login.token_utils import verify_token
from backend.config import texts as text_cfg
from gui.custom_message_box import CustomMessageBox
from modules.login_dialog import LoginDialog
from modules.vip_membership_dialog import VipPackageDialog, DiamondPackageDialog

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def show_login_dialog(main_window: "MainWindow") -> None:
    """显示登录对话框"""
    is_logged_in, _, _ = check_login_status()
    if is_logged_in:
        return

    main_window.login_dialog = LoginDialog(main_window)
    main_window.login_dialog.show()

    # 居中显示
    dialog_size = main_window.login_dialog.size()
    center_x = main_window.x() + (main_window.width() - dialog_size.width()) // 2
    center_y = main_window.y() + (main_window.height() - dialog_size.height()) // 2
    main_window.login_dialog.move(center_x, center_y)

    main_window.login_dialog_offset = main_window.login_dialog.pos() - main_window.pos()

    # 显示蒙版
    main_window.mask_widget.setVisible(True)
    _update_mask_geometry(main_window)
    main_window.mask_widget.setVisible(True)


def check_auto_login(main_window: "MainWindow") -> None:
    """检查自动登录"""
    token = read_token()
    if token:
        payload = verify_token(token)
        if payload:
            email = payload['email']
            user = main_window.db_manager.get_user_by_email(email)
            if user:
                logging.info(f"用户 {user['username']} 自动登录成功，ID: {user['id']}")
                save_login_status(user['id'], user['username'])

                vip_info = main_window.db_manager.get_user_vip_info(user['id'])
                if vip_info:
                    is_vip = vip_info['is_vip']
                    diamonds = vip_info['diamonds']
                    main_window.update_membership_info(
                        user['avatar'], user['username'], is_vip, diamonds, user['id']
                    )

                # 隐藏蒙版
                main_window.mask_widget.setVisible(False)
                return
    
    # 未登录或token无效，显示登录对话框
    show_login_dialog(main_window)


def show_vip_dialog(main_window: "MainWindow") -> None:
    """显示VIP会员对话框"""
    if not main_window.user_id:
        msg_box = CustomMessageBox(main_window)
        msg_box.setText(text_cfg.LOGIN_REQUIRED_MESSAGE)
        msg_box.setWindowTitle(text_cfg.LOGIN_REQUIRED_TITLE)
        msg_box.exec()
        return
    
    # 直接显示新版会员套餐对话框
    vip_dialog = VipPackageDialog(main_window, user_id=main_window.user_id)
    exec_centered_dialog(main_window, vip_dialog)


def show_diamond_dialog(main_window: "MainWindow") -> None:
    """显示钻石套餐对话框"""
    if not main_window.user_id:
        msg_box = CustomMessageBox(main_window)
        msg_box.setText(text_cfg.LOGIN_REQUIRED_MESSAGE)
        msg_box.setWindowTitle(text_cfg.LOGIN_REQUIRED_TITLE)
        msg_box.exec()
        return

    dialog = DiamondPackageDialog(main_window, user_id=main_window.user_id)
    exec_centered_dialog(main_window, dialog)


def exec_centered_dialog(main_window: "MainWindow", dialog: QDialog) -> int:
    """居中执行对话框并返回结果"""
    dialog_size = dialog.size()
    center_x = main_window.x() + (main_window.width() - dialog_size.width()) // 2
    center_y = main_window.y() + (main_window.height() - dialog_size.height()) // 2
    dialog.move(center_x, center_y)
    return dialog.exec()


def _update_mask_geometry(main_window: "MainWindow") -> None:
    """更新遮罩层几何位置（内部辅助函数）"""
    # 现在遮罩挂在 main_content_widget 上，只需要覆盖主内容区域，避免挡住顶部导航
    if not hasattr(main_window, "main_content_widget") or not hasattr(main_window, "mask_widget"):
        return
    if not main_window.main_content_widget or not main_window.mask_widget:
        return
    main_window.mask_widget.setGeometry(main_window.main_content_widget.rect())
    main_window.mask_widget.raise_()
