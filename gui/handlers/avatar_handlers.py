"""头像上传和更新处理模块。"""
import logging
from typing import TYPE_CHECKING, Optional

from PyQt6.QtWidgets import QFileDialog, QDialog
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QColor, QPainterPath

from backend.resources import get_default_avatar
from backend.config import texts as text_cfg
from gui.custom_message_box import CustomMessageBox
from gui.avatar_crop_dialog import AvatarCropDialog
from gui.handlers.dialog_handlers import exec_centered_dialog

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def upload_avatar(main_window: "MainWindow", event) -> None:
    """上传头像"""
    if main_window.user_id:
        file_path, _ = QFileDialog.getOpenFileName(
            main_window, "选择头像", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            # 打开裁剪对话框
            crop_dialog = AvatarCropDialog(file_path, main_window)
            result = exec_centered_dialog(main_window, crop_dialog)
            if result == QDialog.DialogCode.Accepted:
                # 获取裁剪后的头像数据
                avatar_data = crop_dialog.get_cropped_avatar_bytes()
                if avatar_data:
                    if main_window.db_manager.update_user_avatar(main_window.user_id, avatar_data):
                        # 更新成功后，重新加载头像显示
                        update_user_avatar_display(main_window, avatar_data)
                        logging.info("头像更新成功")
                    else:
                        msg_box = CustomMessageBox(main_window, variant="error")
                        msg_box.setWindowTitle("更新失败")
                        msg_box.setText("头像更新失败，请稍后重试")
                        msg_box.exec()
                else:
                    msg_box = CustomMessageBox(main_window, variant="error")
                    msg_box.setWindowTitle("错误")
                    msg_box.setText("无法获取裁剪后的头像")
                    msg_box.exec()
    else:
        msg_box = CustomMessageBox(main_window, variant="error")
        msg_box.setWindowTitle(text_cfg.LOGIN_REQUIRED_TITLE)
        msg_box.setText(text_cfg.LOGIN_REQUIRED_BEFORE_UPLOAD_AVATAR)
        msg_box.exec()


def update_user_avatar_display(main_window: "MainWindow", avatar_data) -> None:
    """更新头像显示"""
    # 允许 avatar_data 为 None / memoryview
    if not avatar_data:
        avatar_data = get_default_avatar()
    if avatar_data is None:
        # 兜底：画一个浅色圆形占位
        pm = QPixmap(main_window.user_avatar_label.size())
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(241, 245, 249))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(0, 0, pm.width(), pm.height())
        painter.end()
        main_window.user_avatar_label.setPixmap(pm)
        return
    if isinstance(avatar_data, memoryview):
        avatar_bytes = avatar_data.tobytes()
    else:
        avatar_bytes = avatar_data

    pixmap = QPixmap()
    ok = pixmap.loadFromData(avatar_bytes)
    if not ok or pixmap.isNull():
        # 数据非法则回退默认头像
        fallback = get_default_avatar()
        if fallback and fallback is not avatar_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(fallback)
            avatar_bytes = fallback

    size = min(pixmap.width(), pixmap.height())
    if size <= 0:
        return
    cropped_pixmap = QPixmap(size, size)
    cropped_pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(cropped_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap.scaled(
        size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    ))
    painter.end()
    
    # 使用足够大的尺寸（例如 100x100）作为 Pixmap 源，配合 setScaledContents(True)
    # 这样在放大动画过程中图像依然保持清晰
    display_size = 100
    main_window.user_avatar_label.setPixmap(cropped_pixmap.scaled(
        display_size, display_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    ))
    # 同步更新聊天中使用的用户头像（缩小后用于 QTextEdit）
    try:
        main_window._user_avatar_url = _avatar_bytes_to_data_url(avatar_bytes, main_window)
    except Exception:
        pass


def update_membership_info(
    main_window: "MainWindow", avatar_data, username, is_vip, diamonds, user_id=None
) -> None:
    """更新会员信息显示（用户名 / VIP 徽章 / 钻石数量 / 头像）"""
    # 更新用户ID
    main_window.user_id = user_id

    # 更新文本
    if username is not None:
        main_window.username_display_label.setText(str(username))

    vip = bool(is_vip)
    # VIP 徽章文案与样式
    if vip:
        main_window.vip_status_label.setText("VIP 会员")
        main_window.vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 700;
                color: #f97316;
                padding: 2px 10px;
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #fef3c7, stop:1 #fbd38d);
            }
        """)
        # VIP 用户头像描边改为金色
        main_window.user_avatar_label.setStyleSheet(f"""
            QLabel {{
                border-radius: {main_window.user_avatar_label.width() // 2}px;
                border: 2px solid #f59e0b;
            }}
        """)
    else:
        main_window.vip_status_label.setText("未开通会员")
        main_window.vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: rgba(226, 232, 240, 120);
            }
        """)
        # 非会员头像恢复为淡灰边框
        main_window.user_avatar_label.setStyleSheet(f"""
            QLabel {{
                border-radius: {main_window.user_avatar_label.width() // 2}px;
                border: 2px solid rgba(148, 163, 184, 160);
            }}
        """)

    try:
        d = int(diamonds)
    except Exception:
        d = 0
    # 钻石文案：0 钻石 时给出引导
    if d <= 0:
        main_window.diamond_count_label.setText("0 钻石")
    else:
        main_window.diamond_count_label.setText(f"{d} 钻石")

    # 同步刷新 VIP tooltip（若主窗口实现了该方法）
    if hasattr(main_window, "_refresh_vip_tooltip"):
        try:
            main_window._refresh_vip_tooltip()
        except Exception:
            # tooltip 失败不影响主流程
            pass

    # 更新头像（None/bytes/memoryview 都可）
    update_user_avatar_display(main_window, avatar_data)


def _avatar_bytes_to_data_url(data: bytes, main_window: "MainWindow", size: int = 32, mime: str = "image/png") -> str:
    """将头像字节数据转换为 Data URL（用于富文本嵌入）"""
    return main_window._avatar_bytes_to_data_url(data, size, mime)
