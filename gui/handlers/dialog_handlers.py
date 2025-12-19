import logging
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import QDialog, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import QPoint, QRect, QTimer, Qt

from backend.login.login_status_manager import check_login_status, save_login_status
from backend.login.token_storage import read_token
from backend.login.token_utils import verify_token
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
    """检查自动登录"""
    # 显示加载蒙版
    loading_overlay = None
    try:
        # 创建加载蒙版
        if hasattr(main_window, 'rounded_bg') and main_window.rounded_bg:
            loading_overlay = _create_loading_overlay(main_window.rounded_bg, "正在自动登录...")
            loading_overlay.setVisible(True)
            # 立即更新几何位置
            _update_loading_geometry(main_window, loading_overlay)
            # 延迟再次更新，确保布局完成
            def safe_update():
                try:
                    if loading_overlay and hasattr(loading_overlay, 'setGeometry'):
                        _update_loading_geometry(main_window, loading_overlay)
                except RuntimeError:
                    pass  # 对象已被删除，忽略
            QTimer.singleShot(100, safe_update)
        
        token = read_token()
        if token:
            payload = verify_token(token)
            if payload:
                email = payload['email']
                # 使用异步数据库查询
                from backend.database.database_thread import DatabaseQueryThread
                
                # 保存线程引用，避免被垃圾回收，设置父对象为main_window以确保生命周期
                user_thread = DatabaseQueryThread('get_user_by_email', email)
                user_thread.setParent(main_window)  # 设置父对象，确保生命周期管理
                
                def on_user_query_finished(user):
                    if user:
                        logging.info(f"用户 {user['username']} 自动登录成功，ID: {user['id']}")
                        save_login_status(user['id'], user['username'])
                        
                        # 查询VIP信息
                        vip_thread = DatabaseQueryThread('get_user_vip_info', user['id'])
                        vip_thread.setParent(main_window)  # 设置父对象
                        vip_thread.finished.connect(vip_thread.deleteLater)  # 完成后自动清理
                        
                        def on_vip_query_finished(vip_info):
                            if vip_info:
                                is_vip = vip_info['is_vip']
                                diamonds = vip_info['diamonds']
                                main_window.update_membership_info(
                                    user['avatar'], user['username'], is_vip, diamonds, user['id']
                                )
                            
                            # 隐藏加载蒙版和mask_widget
                            if loading_overlay:
                                try:
                                    loading_overlay.setVisible(False)
                                    loading_overlay.deleteLater()
                                except RuntimeError:
                                    pass  # 对象已被删除，忽略
                            main_window.mask_widget.setVisible(False)
                        
                        def on_vip_query_error(error_msg):
                            logging.error(f"查询VIP信息失败: {error_msg}")
                            # 即使VIP查询失败，也继续登录流程
                            if loading_overlay:
                                try:
                                    loading_overlay.setVisible(False)
                                    loading_overlay.deleteLater()
                                except RuntimeError:
                                    pass
                            main_window.mask_widget.setVisible(False)
                        
                        vip_thread.query_finished.connect(on_vip_query_finished)
                        vip_thread.query_error.connect(on_vip_query_error)
                        vip_thread.start()
                    else:
                        # 用户查询失败，隐藏加载蒙版
                        if loading_overlay:
                            try:
                                loading_overlay.setVisible(False)
                                loading_overlay.deleteLater()
                            except RuntimeError:
                                pass
                        main_window.mask_widget.setVisible(False)
                
                def on_user_query_error(error_msg):
                    logging.error(f"查询用户信息失败: {error_msg}")
                    # 隐藏加载蒙版
                    if loading_overlay:
                        try:
                            loading_overlay.setVisible(False)
                            loading_overlay.deleteLater()
                        except RuntimeError:
                            pass
                    main_window.mask_widget.setVisible(False)
                
                # 确保线程完成后自动清理
                user_thread.finished.connect(user_thread.deleteLater)
                user_thread.query_finished.connect(on_user_query_finished)
                user_thread.query_error.connect(on_user_query_error)
                user_thread.start()
                return
    except Exception as e:
        logging.error(f"自动登录失败：{e}", exc_info=True)
        # 显示友好的错误提示
        try:
            error_msg = str(e)
            # 简化常见的数据库错误提示
            if "database" in error_msg.lower() or "连接" in error_msg:
                show_message(
                    main_window,
                    "自动登录失败：无法连接到数据库。\n\n请检查数据库服务是否正常运行，然后手动登录。",
                    "自动登录失败",
                    variant="error"
                )
            else:
                show_message(
                    main_window,
                    f"自动登录失败，请手动登录。\n\n错误信息：{error_msg}",
                    "自动登录失败",
                    variant="error"
                )
        except Exception as msg_error:
            # 如果显示消息框也失败，至少记录日志
            logging.error(f"显示自动登录错误提示失败：{msg_error}", exc_info=True)
    finally:
        # 确保加载蒙版被清理
        if loading_overlay:
            try:
                loading_overlay.setVisible(False)
                loading_overlay.deleteLater()
            except RuntimeError:
                pass  # 对象已被删除，忽略
    
    # 未登录或token无效，显示登录对话框
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
