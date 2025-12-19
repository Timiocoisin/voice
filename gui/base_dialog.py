from typing import Tuple
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QGraphicsDropShadowEffect,
)


class BaseDialog(QDialog):
    """应用内弹窗的基础对话框。

    - 统一使用无边框 + 透明背景，由内部卡片负责绘制视觉样式
    - 提供创建带阴影卡片容器的工具方法，减少重复代码
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """绘制透明背景，避免出现默认灰色对话框边框。"""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()

    def create_card_container(
        self,
        object_name: str,
        *,
        blur_radius: int = 40,
        y_offset: int = 12,
        shadow_alpha: int = 50,
        layout_margins: Tuple[int, int, int, int] = (36, 24, 36, 24),
        layout_spacing: int = 20,
    ) -> Tuple[QWidget, QVBoxLayout]:
        """创建带统一阴影与边距的卡片容器，返回 (card_widget, layout)。"""
        card = QWidget()
        card.setObjectName(object_name)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur_radius)
        shadow.setOffset(0, y_offset)
        shadow.setColor(QColor(0, 0, 0, shadow_alpha))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        left, top, right, bottom = layout_margins
        layout.setContentsMargins(left, top, right, bottom)
        layout.setSpacing(layout_spacing)

        return card, layout
    
    def keyPressEvent(self, event: QKeyEvent):
        """支持 ESC 键关闭对话框"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

