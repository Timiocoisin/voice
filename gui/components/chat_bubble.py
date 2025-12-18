"""聊天气泡和相关UI组件。"""
from typing import Optional

from PyQt6.QtCore import Qt, QSize, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QBrush, QPixmap, QCursor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QGraphicsDropShadowEffect,
)

from backend.resources import load_icon_data


class ChatBubble(QWidget):
    """自绘圆角聊天气泡"""

    def __init__(
        self,
        text: str,
        background: QColor,
        text_color: QColor,
        border_color: Optional[QColor] = None,
        max_width: int = 420,
        align_right: bool = False,
        rich_text: bool = False,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._text = text
        self._bg = background
        self._text_color = text_color
        self._border_color = border_color
        self._radius = 18
        self._padding_h = 14
        self._padding_v = 8
        self._max_width = max_width
        self._rich_text = rich_text

        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._padding_h, self._padding_v, self._padding_h, self._padding_v)
        layout.setSpacing(0)

        self.label = QLabel(text, self)
        self.label.setWordWrap(True)
        self.label.setTextFormat(
            Qt.TextFormat.RichText if self._rich_text else Qt.TextFormat.PlainText
        )
        self.label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
            }
        """)
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignRight if align_right else Qt.AlignmentFlag.AlignLeft
        )
        layout.addWidget(self.label)

        self.setSizePolicy(self.sizePolicy().horizontalPolicy(), self.sizePolicy().verticalPolicy())

    def sizeHint(self):
        """基于内部 QLabel 的尺寸，自动适应文本或图片大小"""
        inner = self.label.sizeHint()
        width = min(self._max_width, inner.width() + self._padding_h * 2)
        height = inner.height() + self._padding_v * 2
        return QSize(width, height)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self._radius, self._radius)

        painter.setBrush(self._bg)
        if self._border_color:
            pen = painter.pen()
            pen.setColor(self._border_color)
            pen.setWidth(1)
            painter.setPen(pen)
        else:
            painter.setPen(Qt.PenStyle.NoPen)

        painter.drawPath(path)
        painter.setPen(self._text_color)

        super().paintEvent(event)


class LogoutPopup(QWidget):
    """自定义带尖角的退出登录浮窗"""
    clicked = Qt.MouseButton.LeftButton  # 仅为占位，实际使用 QPushButton

    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.main_window = main_window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.SubWindow)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 15, 10, 10)  # 顶部留出尖角空间
        
        self.button = QPushButton("退出登录")
        self.button.setObjectName("logoutButton")
        self.button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.button.setStyleSheet("""
            QPushButton#logoutButton {
                background-color: #ffffff;
                border-radius: 12px;
                border: none;
                padding: 8px 20px;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
                color: #1f2933;
            }
            QPushButton#logoutButton:hover {
                background-color: #fee2e2;
                color: #b91c1c;
            }
        """)
        layout.addWidget(self.button)
        
        # 添加阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        """鼠标进入浮窗，停止隐藏计时器"""
        if self.main_window and hasattr(self.main_window, "_logout_timer"):
            self.main_window._logout_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """鼠标离开浮窗，启动隐藏计时器"""
        if self.main_window and hasattr(self.main_window, "_logout_timer"):
            self.main_window._logout_timer.start(200) # 200ms 缓冲区
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen) # 强制不绘制边框线
        
        # 绘制背景气泡
        rect = self.rect()
        # 减去阴影边距和尖角高度
        bubble_rect = QRectF(5, 12, rect.width() - 10, rect.height() - 17)
        
        path = QPainterPath()
        # 尖角位置：顶部中央
        arrow_w = 12
        arrow_h = 8
        center_x = rect.width() / 2
        
        # 绘制带尖角的路径
        path.moveTo(center_x - arrow_w/2, bubble_rect.top())
        path.lineTo(center_x, bubble_rect.top() - arrow_h)
        path.lineTo(center_x + arrow_w/2, bubble_rect.top())
        
        # 添加圆角矩形
        path.addRoundedRect(bubble_rect, 12, 12)
        
        painter.fillPath(path, QBrush(Qt.GlobalColor.white))


class RoundedBackgroundWidget(QWidget):
    """带背景图的圆角背景控件"""
    
    def __init__(self):
        super().__init__()
        self.radius = 20

        # 从本地文件加载背景图片
        background_image_data = load_icon_data(14)
        if background_image_data:
            self.background_image = QPixmap()
            self.background_image.loadFromData(background_image_data)
        else:
            self.background_image = QPixmap()

        # 添加阴影效果
        self.shadow = QGraphicsDropShadowEffect(self)
        self.shadow.setBlurRadius(10)  # 设置阴影模糊半径
        self.shadow.setColor(QColor(0, 0, 0, 150))  # 设置阴影颜色和透明度
        self.shadow.setOffset(0, 4)  # 设置阴影偏移量
        self.setGraphicsEffect(self.shadow)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角背景
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)

        # 绘制背景图，自适应窗口大小，并裁剪为圆角矩形
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)
        painter.setClipPath(path)
        painter.drawPixmap(self.rect(), self.background_image)
