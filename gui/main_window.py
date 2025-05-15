from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout)
from PyQt6.QtCore import Qt, QTimer, QEvent, QRect, QRectF, QPoint
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QColor, QBrush
from PyQt6.QtSvgWidgets import QSvgWidget
from modules.login_dialog import LoginDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("变声器")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # 设置窗口背景透明
        self.setFixedSize(self.screen_size(0.7), self.screen_size(0.6, height=True))  # 窗口大小为屏幕的80%

        self.initUI()

        QTimer.singleShot(3000, self.show_login_dialog)
        self.login_dialog = None
        self.installEventFilter(self)

        # 初始化拖动窗口的变量
        self.dragging = False
        self.offset = QPoint()
        # 记录登录对话框相对于主窗口的偏移量
        self.login_dialog_offset = QPoint()

    def screen_size(self, ratio, height=False):
        screen = QApplication.primaryScreen()
        size = screen.size()
        if height:
            return int(size.height() * ratio)
        return int(size.width() * ratio)

    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.rounded_bg = RoundedBackgroundWidget()  # 使用自定义的背景绘制部件
        self.rounded_bg.setObjectName("roundedBackground")
        self.rounded_bg.setStyleSheet("""
            #roundedBackground {
                background-color: white;
                border-radius: 20px;
            }
        """)

        rounded_layout = QVBoxLayout(self.rounded_bg)

        # 创建顶部布局，用于放置关闭按钮
        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)  # 对齐到右上角

        # 加载关闭图标
        close_icon = QSvgWidget('icons/close.svg')
        close_icon.setFixedSize(30, 30)  # 设置图标大小
        close_icon.setStyleSheet("margin: 10px;")
        close_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_icon.mousePressEvent = self.close_app
        top_layout.addWidget(close_icon)

        rounded_layout.addLayout(top_layout)

        main_layout.addWidget(self.rounded_bg)

    def show_login_dialog(self):
        self.login_dialog = LoginDialog(self)
        self.login_dialog.show()
        # 记录登录对话框相对于主窗口的偏移量
        self.login_dialog_offset = self.login_dialog.pos() - self.pos()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if (self.login_dialog and self.login_dialog.agreement_dialog
                    and self.login_dialog.agreement_dialog.isVisible()):
                if self.geometry().contains(event.globalPosition().toPoint()):
                    self.login_dialog.agreement_dialog.close()
                    return True
                if self.login_dialog.geometry().contains(event.globalPosition().toPoint()):
                    if not self.login_dialog.agreement_dialog.geometry().contains(event.globalPosition().toPoint()):
                        self.login_dialog.agreement_dialog.close()
                        return True
        return super().eventFilter(obj, event)

    def close_app(self, event):
        QApplication.quit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.offset
            self.move(new_pos)
            # 更新登录对话框的位置
            if self.login_dialog:
                self.login_dialog.move(new_pos + self.login_dialog_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False


class RoundedBackgroundWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.background_image = QPixmap('images/background.png')  # 加载背景图
        self.radius = 20  # 圆角半径

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制圆角背景
        painter.setBrush(QBrush(Qt.GlobalColor.white))
        painter.drawRoundedRect(self.rect(), self.radius, self.radius)

        # 绘制背景图，自适应窗口大小，并裁剪为圆角矩形
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), self.radius, self.radius)  # 使用 QRectF
        painter.setClipPath(path)
        painter.drawPixmap(self.rect(), self.background_image)