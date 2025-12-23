"""窗口工具方法模块。"""
import base64

from PyQt6.QtWidgets import QPushButton
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import QSize, QBuffer, QByteArray, QIODevice
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtCore import Qt

from client.resources import load_icon_data, load_icon_path


def create_svg_widget(main_window, icon_id, width, height, style):
    """创建SVG图标控件"""
    # 从本地文件加载图标数据
    icon_data = load_icon_data(icon_id)
    if not icon_data:
        return None

    svg_widget = QSvgWidget()
    svg_widget.load(QByteArray(icon_data))
    svg_widget.setFixedSize(width, height)
    svg_widget.setStyleSheet(style)
    return svg_widget


def set_icon_button(button: QPushButton, icon_id: int, tooltip: str = ""):
    """为按钮设置SVG图标样式（统一尺寸与风格）"""
    button.setToolTip(tooltip)
    from PyQt6.QtGui import QCursor
    from PyQt6.QtCore import Qt
    button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    button.setFixedSize(36, 32)
    button.setStyleSheet("""
        QPushButton {
            background-color: #e2e8f0;
            border: none;
            border-radius: 8px;
            padding: 4px;
        }
        QPushButton:hover {
            background-color: #cbd5e1;
        }
        QPushButton:pressed {
            background-color: #94a3b8;
        }
    """)
    path = load_icon_path(icon_id)
    if path:
        icon = QIcon(path)
        button.setIcon(icon)
        button.setIconSize(QSize(18, 18))


def bytes_to_data_url(data: bytes, mime: str = "image/png") -> str:
    """将二进制图片转换为 data URL，通用小工具"""
    try:
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""


def avatar_bytes_to_data_url(data: bytes, size: int = 32, mime: str = "image/png") -> str:
    """将头像二进制图片缩放到固定尺寸后再转为 data URL

    为了在 QTextEdit 中既清晰又不占太大空间，这里会生成 2×size 像素的图片，
    在 HTML 里用 width/height=size 来显示，相当于"高分辨率小图标"，减少缩小带来的模糊感。
    """
    try:
        pix = QPixmap()
        if not pix.loadFromData(data) or pix.isNull():
            return bytes_to_data_url(data, mime)
        target = size * 2
        scaled = pix.scaled(target, target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        scaled.save(buffer, "PNG")
        b64 = base64.b64encode(buffer.data()).decode("utf-8")
        buffer.close()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return bytes_to_data_url(data, mime)
