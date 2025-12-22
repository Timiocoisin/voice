import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QPoint, QRect, QTimer, Qt

from backend.login.login_status_manager import check_login_status, save_login_status
from backend.login.token_storage import read_token
from backend.login.token_utils import verify_token
from client.api_client import check_token as api_check_token
from backend.config import texts as text_cfg
from gui.custom_message_box import CustomMessageBox
from modules.login_dialog import LoginDialog
from modules.vip_membership_dialog import VipPackageDialog, DiamondPackageDialog
from gui.handlers.message_utils import show_message

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def show_login_dialog(main_window: "MainWindow") -> None:
    is_logged_in, _, _ = check_login_status()
    if is_logged_in:
        return

    main_window.login_dialog = LoginDialog(main_window)
    main_window.login_dialog.show()

    # 居中显示（使用统一的居中函数）
    center_dialog(main_window, main_window.login_dialog)

    main_window.login_dialog_offset = main_window.login_dialog.pos() - main_window.pos()

    # 先更新蒙版几何位置（立即执行一次）
    _update_mask_geometry(main_window)
    # 显示蒙版
    main_window.mask_widget.setVisible(True)
    # 延迟再次更新几何位置，确保rounded_bg的尺寸已完全设置
    QTimer.singleShot(50, lambda: _update_mask_geometry(main_window))
    
    # 聚焦到登录对话框的输入框
    if hasattr(main_window.login_dialog, 'email_input'):
        main_window.login_dialog.email_input.setFocus()


def check_auto_login(main_window: "MainWindow") -> None:
    """检查自动登录（通过后端 HTTP 接口，而非直接访问数据库）。"""
    # 显示加载蒙版
    loading_overlay = None
    try:
        if hasattr(main_window, "rounded_bg") and main_window.rounded_bg:
            loading_overlay = _create_loading_overlay(
                main_window.rounded_bg, "正在自动登录..."
            )
            loading_overlay.setVisible(True)
            _update_loading_geometry(main_window, loading_overlay)
            QTimer.singleShot(
                100,
                lambda: _update_loading_geometry(main_window, loading_overlay)
                if loading_overlay
                else None,
            )

        token = read_token()
        # 没有本地 token 时属于正常情况（首次使用），直接跳过自动登录
        if not token:
            raise StopIteration  # 使用内部哨兵异常，仅用于跳出 try，不视为错误

        # 先做本地 token 签名校验
        if not verify_token(token):
            raise RuntimeError("本地 token 已失效")

        # 通过后端接口校验并获取用户信息
        try:
            resp = api_check_token(token)
        except Exception as e:
            logging.error("自动登录（token 校验）请求失败：%s", e, exc_info=True)
            raise RuntimeError("无法连接后端服务")

        if not resp.get("success", False):
            raise RuntimeError("后端校验 token 失败")

        user = resp.get("user") or {}
        vip_info = resp.get("vip") or {}

        user_id = user.get("id")
        username = user.get("username", "未命名")
        if user_id is not None:
            save_login_status(user_id, username)

            # 通过用户资料接口获取最新头像与 VIP / 钻石信息，确保使用用户上传的头像
            from client.api_client import get_user_profile

            profile = get_user_profile(user_id) or {}
            p_user = profile.get("user") or {}
            p_vip = profile.get("vip") or vip_info

            avatar_bytes = p_user.get("avatar_bytes")
            is_vip = bool(p_vip.get("is_vip", False))
            diamonds = p_vip.get("diamonds", 0)
        else:
            avatar_bytes = None
            is_vip = bool(vip_info.get("is_vip", False))
            diamonds = vip_info.get("diamonds", 0)

        main_window.update_membership_info(
            avatar_bytes, username, is_vip, diamonds, user_id
        )

        # 隐藏蒙版
        if loading_overlay:
            try:
                loading_overlay.setVisible(False)
                loading_overlay.deleteLater()
            except RuntimeError:
                pass
        main_window.mask_widget.setVisible(False)
        return

    except StopIteration:
        # 无 token 或主动中断自动登录：不视为错误，不记录堆栈
        pass
    except Exception as e:
        logging.error("自动登录失败：%s", e, exc_info=True)
        # 自动登录失败时，不弹严重错误，直接走手动登录
    finally:
        if loading_overlay:
            try:
                loading_overlay.setVisible(False)
                loading_overlay.deleteLater()
            except RuntimeError:
                pass

    # 未登录或自动登录失败，显示登录对话框
    show_login_dialog(main_window)


def show_vip_dialog(main_window: "MainWindow") -> None:
    """显示VIP会员对话框"""
    if not main_window.user_id:
        show_message(
            main_window,
            text_cfg.LOGIN_REQUIRED_MESSAGE,
            text_cfg.LOGIN_REQUIRED_TITLE
        )
        return
    
    # 直接显示新版会员套餐对话框
    vip_dialog = VipPackageDialog(main_window, user_id=main_window.user_id)
    exec_centered_dialog(main_window, vip_dialog)


def show_diamond_dialog(main_window: "MainWindow") -> None:
    """显示钻石套餐对话框"""
    if not main_window.user_id:
        show_message(
            main_window,
            text_cfg.LOGIN_REQUIRED_MESSAGE,
            text_cfg.LOGIN_REQUIRED_TITLE
        )
        return

    dialog = DiamondPackageDialog(main_window, user_id=main_window.user_id)
    exec_centered_dialog(main_window, dialog)


def center_dialog(main_window: "MainWindow", dialog: QDialog) -> None:
    """将对话框居中显示在主窗口中心
    
    Args:
        main_window: 主窗口实例
        dialog: 要居中的对话框
    """
    dialog_size = dialog.size()
    center_x = main_window.x() + (main_window.width() - dialog_size.width()) // 2
    center_y = main_window.y() + (main_window.height() - dialog_size.height()) // 2
    dialog.move(center_x, center_y)


def exec_centered_dialog(main_window: "MainWindow", dialog: QDialog) -> int:
    """居中执行对话框并返回结果
    
    Args:
        main_window: 主窗口实例
        dialog: 要显示的对话框
        
    Returns:
        对话框的执行结果（QDialog.DialogCode）
    """
    center_dialog(main_window, dialog)
    return dialog.exec()


def _create_loading_overlay(parent: QWidget, text: str = "加载中...") -> QWidget:
    """创建加载遮罩层组件"""
    from gui.components.loading_indicator import LoadingIndicator
    
    overlay = QWidget(parent)
    overlay.setStyleSheet("""
        QWidget {
            background-color: rgba(0, 0, 0, 150);
            border-radius: 20px;
        }
    """)
    
    layout = QVBoxLayout(overlay)
    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.setSpacing(16)
    
    # 加载指示器
    indicator = LoadingIndicator(overlay, size=50, line_width=4)
    layout.addWidget(indicator, alignment=Qt.AlignmentFlag.AlignCenter)
    
    # 文本标签
    label = QLabel(text, overlay)
    label.setStyleSheet("""
        QLabel {
            color: white;
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 16px;
            font-weight: 500;
            background-color: transparent;
        }
    """)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    
    overlay.raise_()
    return overlay


def _update_loading_geometry(main_window: "MainWindow", overlay: QWidget) -> None:
    """更新加载蒙版几何位置"""
    try:
        # 检查对象是否仍然存在
        if not overlay or not hasattr(overlay, 'setGeometry'):
            return
        if not hasattr(main_window, "rounded_bg") or not main_window.rounded_bg:
            return
        bg_rect = main_window.rounded_bg.rect()
        if bg_rect.width() > 0 and bg_rect.height() > 0:
            overlay.setGeometry(bg_rect)
        else:
            bg_size = main_window.rounded_bg.size()
            if bg_size.width() > 0 and bg_size.height() > 0:
                from PyQt6.QtCore import QRect
                overlay.setGeometry(QRect(0, 0, bg_size.width(), bg_size.height()))
        overlay.raise_()
    except RuntimeError:
        # 对象已被删除，忽略错误
        pass


def _update_mask_geometry(main_window: "MainWindow") -> None:
    """更新遮罩层几何位置（内部辅助函数）"""
    # 蒙版应该覆盖整个rounded_bg（包括顶部导航栏、主内容区域和底部导航栏）
    # 这样可以阻止用户点击主界面的任何部分
    if not hasattr(main_window, "rounded_bg") or not hasattr(main_window, "mask_widget"):
        return
    if not main_window.rounded_bg or not main_window.mask_widget:
        return
    # 确保使用明确的坐标和尺寸覆盖整个rounded_bg区域
    # 使用 rect() 获取完整的矩形区域（相对于父组件）
    bg_rect = main_window.rounded_bg.rect()
    # 如果 rect 有效，使用它；否则手动获取宽高
    if bg_rect.width() > 0 and bg_rect.height() > 0:
        main_window.mask_widget.setGeometry(bg_rect)
    else:
        # 备用方案：使用 size() 和明确的坐标
        bg_size = main_window.rounded_bg.size()
        if bg_size.width() > 0 and bg_size.height() > 0:
            main_window.mask_widget.setGeometry(QRect(0, 0, bg_size.width(), bg_size.height()))
    # 确保蒙版在最上层
    main_window.mask_widget.raise_()
