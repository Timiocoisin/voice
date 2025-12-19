"""加载指示器组件"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, pyqtProperty, QRectF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush


class LoadingIndicator(QWidget):
    """圆形加载指示器，显示旋转的圆环动画"""
    
    def __init__(self, parent=None, size: int = 40, line_width: int = 3):
        super().__init__(parent)
        self._size = size
        self._line_width = line_width
        self._rotation = 0.0
        self.setFixedSize(size, size)
        
        # 旋转动画
        self._animation = QPropertyAnimation(self, b"rotation")
        self._animation.setDuration(1000)
        self._animation.setStartValue(0)
        self._animation.setEndValue(360)
        self._animation.setLoopCount(-1)  # 无限循环
        self._animation.start()
    
    def setRotation(self, value: float):
        """设置旋转角度"""
        self._rotation = value
        self.update()
    
    def getRotation(self) -> float:
        """获取旋转角度"""
        return self._rotation
    
    rotation = pyqtProperty(float, getRotation, setRotation)
    
    def paintEvent(self, event):
        """绘制旋转的圆环"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 计算绘制区域
        margin = self._line_width
        rect = QRectF(margin, margin, 
                     self._size - 2 * margin, 
                     self._size - 2 * margin)
        
        # 设置画笔
        pen = QPen(QColor(100, 150, 255, 180), self._line_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # 绘制旋转的弧线
        start_angle = int(self._rotation * 16)  # Qt使用1/16度为单位
        span_angle = 270 * 16  # 270度弧线
        painter.drawArc(rect, start_angle, span_angle)


def create_loading_overlay(parent: QWidget, text: str = "加载中...") -> QWidget:
    """创建加载遮罩层，包含加载指示器和文本
    
    Args:
        parent: 父窗口
        text: 显示的文本
        
    Returns:
        加载遮罩层组件
    """
    overlay = QWidget(parent)
    overlay.setStyleSheet("""
        QWidget {
            background-color: rgba(0, 0, 0, 120);
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
            font-size: 14px;
            font-weight: 500;
            background-color: transparent;
        }
    """)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    
    return overlay
