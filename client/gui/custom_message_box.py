from PyQt6.QtWidgets import QDialog, QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtProperty, QTimer, QPropertyAnimation, QRectF
from PyQt6.QtGui import QPainter, QBrush, QColor, QPen, QLinearGradient, QPainterPath, QKeyEvent
from PyQt6 import QtCore

class CustomMessageBox(QDialog):
    def __init__(self, parent=None, variant: str = "error"):
        super().__init__(parent)
        
        # 自定义属性
        self.border_radius = 12
        self.shadow_offset = 8
        self._opacity = 1.0  # 使用私有变量存储opacity值
        
        # 颜色方案（可切换）
        self.bg_color_start = QColor(245, 247, 255, 250)  # 默认：淡蓝紫色开始
        self.bg_color_end = QColor(235, 238, 250, 250)    # 默认：淡蓝紫色结束
        self.text_color = QColor(72, 85, 106)             # 默认：深灰文本
        self.border_color = QColor(163, 177, 198, 180)    # 默认：边框
        self.shadow_color = QColor(72, 85, 106, 20)       # 默认：阴影
        
        # 创建标签显示文本
        self.label = QLabel(self)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self._apply_label_style()

        # 设置布局
        layout = QHBoxLayout(self)
        layout.addWidget(self.label)
        layout.setContentsMargins(18, 12, 18, 12)

        # 设置定时器，3秒后自动关闭
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fadeOut)
        self.timer.setSingleShot(True)
        
        # 设置对话框属性 - 无边框窗口，不阻挡用户操作
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.NoDropShadowWindowHint  # 移除阴影以避免遮挡
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # 动画效果
        self.fadeInAnimation = QPropertyAnimation(self, b'opacity')
        self.fadeInAnimation.setDuration(300)
        self.fadeInAnimation.setStartValue(0.0)
        self.fadeInAnimation.setEndValue(1.0)
        
        self.fadeOutAnimation = QPropertyAnimation(self, b'opacity')
        self.fadeOutAnimation.setDuration(300)
        self.fadeOutAnimation.setStartValue(1.0)
        self.fadeOutAnimation.setEndValue(0.0)
        self.fadeOutAnimation.finished.connect(self.close)

        # 初始化样式变体
        self.setVariant(variant)

    def _apply_label_style(self):
        self.label.setStyleSheet(f"""
            color: {self.text_color.name()};
            font-size: 14px;
            font-family: 'Segoe UI', 'Roboto', sans-serif;
            font-weight: 500;
            padding: 5px 0;
        """)

    def setVariant(self, variant: str):
        """设置提示样式：info / error / warning（warning 等同 error，统一浅红）"""
        v = (variant or "info").lower().strip()
        if v in ("error", "warning"):
            # 浅红提示（更温和的错误感）
            self.bg_color_start = QColor(255, 241, 242, 250)  # #fff1f2
            self.bg_color_end = QColor(254, 226, 226, 250)    # #fee2e2
            self.text_color = QColor(153, 27, 27)             # #991b1b
            self.border_color = QColor(254, 202, 202, 200)    # #fecaca
            self.shadow_color = QColor(153, 27, 27, 18)
        else:
            # 默认 info：蓝紫色调
            self.bg_color_start = QColor(245, 247, 255, 250)
            self.bg_color_end = QColor(235, 238, 250, 250)
            self.text_color = QColor(72, 85, 106)
            self.border_color = QColor(163, 177, 198, 180)
            self.shadow_color = QColor(72, 85, 106, 20)

        self._apply_label_style()
        self.update()
    
    def setText(self, text):
        self.label.setText(text)
        self._updateSize()  # 更新窗口大小
    
    def setWindowTitle(self, title):
        super().setWindowTitle(title)
    
    def showEvent(self, event):
        self.moveToPosition()
        self.fadeInAnimation.start()
        self.timer.start(1000)  # 3秒后自动关闭
        super().showEvent(event)
    
    def moveToPosition(self):
        if self.parent():
            top_bar = self.parent().findChild(QWidget, "topBar")
            if top_bar:
                top_bar_geometry = top_bar.geometry()
                main_window_pos = self.parent().mapToGlobal(QtCore.QPoint(0, 0))
                x = main_window_pos.x() + (top_bar_geometry.width() - self.width()) // 2
                y = main_window_pos.y() + top_bar_geometry.height() + 15  # 距离顶部导航栏15px
                self.move(x, y)
    
    def fadeOut(self):
        self.fadeOutAnimation.start()
    
    def keyPressEvent(self, event: QKeyEvent):
        """支持 ESC 键关闭对话框"""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setOpacity(self._opacity)  # 使用私有变量
        
        # 绘制阴影效果 - 增强深度感
        for i in range(1, self.shadow_offset + 1):
            shadow_rect = QRectF(i, i, self.width() - 2*i, self.height() - 2*i)
            path = QPainterPath()
            path.addRoundedRect(shadow_rect, self.border_radius, self.border_radius)
            alpha = self.shadow_color.alpha() - (i * 2)
            if alpha < 0:
                alpha = 0
            shadow_color = QColor(self.shadow_color.red(), self.shadow_color.green(), 
                                 self.shadow_color.blue(), alpha)
            painter.fillPath(path, QBrush(shadow_color))
        
        # 绘制渐变背景
        main_rect = QRectF(self.shadow_offset, self.shadow_offset, 
                          self.width() - 2*self.shadow_offset, self.height() - 2*self.shadow_offset)
        gradient = QLinearGradient(main_rect.topLeft(), main_rect.bottomRight())
        gradient.setColorAt(0, self.bg_color_start)
        gradient.setColorAt(1, self.bg_color_end)
        
        path = QPainterPath()
        path.addRoundedRect(main_rect, self.border_radius, self.border_radius)
        painter.fillPath(path, QBrush(gradient))
        
        # 绘制边框 - 轻微内缩使边框更精致
        border_rect = QRectF(self.shadow_offset + 0.5, self.shadow_offset + 0.5, 
                            self.width() - 2*self.shadow_offset - 1, self.height() - 2*self.shadow_offset - 1)
        border_path = QPainterPath()
        border_path.addRoundedRect(border_rect, self.border_radius - 0.5, self.border_radius - 0.5)
        
        pen = QPen(self.border_color, 0.8)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawPath(border_path)
    
    def _updateSize(self):
        """根据文本内容自适应窗口大小"""
        font_metrics = self.label.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.label.text())
        text_height = font_metrics.height()
        margin_x = 36
        margin_y = 24
        min_width = 220
        min_height = text_height + margin_y
        width = max(text_width + margin_x, min_width)
        height = min_height
        self.setFixedSize(width, height)
    
    # 动画属性
    def setOpacity(self, opacity):
        self._opacity = opacity  # 使用私有变量存储值
        self.update()
    
    def getOpacity(self):
        return self._opacity  # 返回私有变量
    
    opacity = pyqtProperty(float, getOpacity, setOpacity)