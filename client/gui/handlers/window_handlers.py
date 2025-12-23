from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QApplication, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt, QPoint, QRect, QPropertyAnimation, QTimer
from PyQt6.QtGui import QCursor, QColor

from client.login.token_storage import clear_token
from client.login.login_status_manager import clear_login_status
from gui.handlers import dialog_handlers, avatar_handlers
from gui.components.chat_bubble import LogoutPopup

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def minimize_app(main_window: "MainWindow", event):
    """最小化窗口到任务栏"""
    main_window.showMinimized()
    if event:
        event.accept()


def close_app(main_window: "MainWindow", event):
    QApplication.quit()


def on_avatar_hover_enter(main_window: "MainWindow", event):
    """鼠标移入头像：原地中心放大动画（模拟向用户凸起） + 显示退出按钮"""
    # 停止隐藏计时器
    if hasattr(main_window, "_logout_timer"):
        main_window._logout_timer.stop()

    # 记录初始 geometry
    if main_window._avatar_normal_geometry is None:
        main_window._avatar_normal_geometry = main_window.user_avatar_label.geometry()

    # 目标 geometry：原地向四周均匀扩展
    normal = main_window._avatar_normal_geometry
    scale_px = 10  # 稍微加大，体现"凸起"感
    target = QRect(
        normal.x() - scale_px, 
        normal.y() - scale_px, 
        normal.width() + scale_px * 2, 
        normal.height() + scale_px * 2
    )

    # 动画：原地放大
    if main_window._avatar_anim is not None:
        main_window._avatar_anim.stop()
    main_window._avatar_anim = QPropertyAnimation(main_window.user_avatar_label, b"geometry", main_window)
    main_window._avatar_anim.setDuration(200)
    main_window._avatar_anim.setStartValue(main_window.user_avatar_label.geometry())
    main_window._avatar_anim.setEndValue(target)
    main_window._avatar_anim.start()
    
    # 添加更深更散的阴影，模拟 3D 悬浮高度
    shadow = QGraphicsDropShadowEffect(main_window.user_avatar_label)
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 5) # 稍微向下偏移，模拟光源在上方，增强凸起感
    shadow.setColor(QColor(0, 0, 0, 90))
    main_window.user_avatar_label.setGraphicsEffect(shadow)

    # 提升层级
    main_window.user_avatar_label.raise_()

    # 创建并显示带尖角的退出浮窗
    if main_window.logout_popup is None:
        main_window.logout_popup = LogoutPopup(main_window, main_window=main_window)
        main_window.logout_popup.button.clicked.connect(lambda: handle_logout_click(main_window))

    update_logout_popup_position(main_window)
    main_window.logout_popup.show()
    main_window.logout_popup.raise_()

    if event is not None:
        event.accept()


def on_avatar_hover_leave(main_window: "MainWindow", event):
    """鼠标移出头像：启动延时隐藏，并开始回缩动画"""
    # 启动延时隐藏计时器
    if hasattr(main_window, "_logout_timer"):
        main_window._logout_timer.start(200) # 给用户 200ms 的操作缓冲

    if main_window._avatar_normal_geometry is None:
        return

    # 开始回缩动画
    if main_window._avatar_anim is not None:
        main_window._avatar_anim.stop()
    main_window._avatar_anim = QPropertyAnimation(main_window.user_avatar_label, b"geometry", main_window)
    main_window._avatar_anim.setDuration(200)
    main_window._avatar_anim.setStartValue(main_window.user_avatar_label.geometry())
    main_window._avatar_anim.setEndValue(main_window._avatar_normal_geometry)
    main_window._avatar_anim.start()
    
    if event is not None:
        event.accept()


def really_hide_logout(main_window: "MainWindow"):
    """真正执行隐藏逻辑：隐藏浮窗并重置头像效果"""
    # 如果鼠标现在正在浮窗或者头像容器上，则不隐藏
    cursor_pos = QCursor.pos()
    
    # 检查是否在头像容器上
    container_global_pos = main_window.avatar_container.mapToGlobal(QPoint(0, 0))
    container_rect = QRect(container_global_pos, main_window.avatar_container.size())
    
    # 检查是否在浮窗上
    popup_rect = QRect()
    if main_window.logout_popup and main_window.logout_popup.isVisible():
        popup_global_pos = main_window.logout_popup.mapToGlobal(QPoint(0, 0))
        popup_rect = QRect(popup_global_pos, main_window.logout_popup.size())

    if container_rect.contains(cursor_pos) or popup_rect.contains(cursor_pos):
        return

    # 执行隐藏和重置
    if main_window.logout_popup:
        main_window.logout_popup.hide()
    
    # 确保头像完全回缩并移除特效
    main_window.user_avatar_label.setGraphicsEffect(None)
    if main_window._avatar_normal_geometry:
        main_window.user_avatar_label.setGeometry(main_window._avatar_normal_geometry)


def update_logout_popup_position(main_window: "MainWindow"):
    """根据头像容器位置，更新带尖角退出浮窗的位置"""
    if not main_window.logout_popup or not main_window.avatar_container:
        return

    # 使用容器在主窗口中的坐标作为基准
    container_pos = main_window.avatar_container.mapTo(main_window, QPoint(0, 0))
    
    main_window.logout_popup.adjustSize()
    popup_w = main_window.logout_popup.width()
    
    # X 轴居中对齐容器
    x = container_pos.x() + (main_window.avatar_container.width() - popup_w) // 2
    # Y 轴放在容器下方，减去一点边距让尖角更贴合头像
    y = container_pos.y() + main_window.avatar_container.height() - main_window.avatar_expand_margin - 2
    
    main_window.logout_popup.move(x, y)


def handle_logout_click(main_window: "MainWindow"):
    """处理退出登录：清除 token、重置 UI 并返回登录界面"""
    # 清除本地 token
    try:
        clear_token()
    except Exception:
        pass

    # 清除内存中的登录状态
    try:
        clear_login_status()
    except Exception:
        pass

    # 重置当前窗口中的用户 ID
    main_window.user_id = None

    # 重置会员/用户显示
    avatar_handlers.update_membership_info(main_window, None, "未登录", False, 0, user_id=None)

    # 隐藏退出浮窗
    if main_window.logout_popup:
        main_window.logout_popup.hide()

    # 弹出登录对话框
    dialog_handlers.show_login_dialog(main_window)
