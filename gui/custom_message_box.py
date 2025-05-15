from PyQt6.QtWidgets import QMessageBox, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt, QRect, QRectF, QSize
from PyQt6.QtGui import QColor, QPalette, QFont, QPixmap, QPainter, QRegion, QBrush, QPen, QPainterPath
import sys

class CustomMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 设置无边框窗口
        self.setWindowFlags(
            self.windowFlags() | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.BypassWindowManagerHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        
        # 自定义属性
        self.border_radius = 18
        self.bg_color = QColor(255, 255, 255, 245)  # 背景色带透明度
        
        # 设置样式 (仅保留必要的部件样式)
        self.setStyleSheet("""
            QLabel {
                font-family: "Segoe UI", "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;
                color: #333333;
                padding: 22px 28px 18px 28px;
                background-color: transparent;
            }
            QPushButton {
                font-family: "Segoe UI", "Microsoft YaHei", "SimHei", "Arial";
                background-color: #4285f4;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 22px;
                font-size: 15px;
                margin: 0 12px 18px 12px;
                min-width: 90px;
            }
            QPushButton:hover {
                background-color: #5a95f5;
            }
            QPushButton:pressed {
                background-color: #3367d6;
            }
        """)
        
        # 移除图标处理代码
        # 自定义按钮文本样式
        for button in self.buttons():
            if isinstance(button, QPushButton):
                font = button.font()
                font.setWeight(QFont.Weight.Medium)
                button.setFont(font)
    
    def showEvent(self, event):
        # 创建圆角区域并应用到窗口
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.border_radius, self.border_radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        super().showEvent(event)
    
    def resizeEvent(self, event):
        # 窗口大小改变时重新应用圆角区域
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.border_radius, self.border_radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))
        super().resizeEvent(event)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制带圆角的背景
        rect = self.rect()
        
        # 创建圆角路径
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect), self.border_radius, self.border_radius)
        
        # 绘制背景
        painter.fillPath(path, QBrush(self.bg_color))
        
        # 绘制边框
        pen = QPen(QColor(220, 220, 220, 200), 1)  # 半透明边框
        painter.setPen(pen)
        painter.drawPath(path)
