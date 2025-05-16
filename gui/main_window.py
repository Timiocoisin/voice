from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel)
from PyQt6.QtCore import Qt, QTimer, QEvent, QRect, QRectF, QPoint
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QColor, QBrush
from PyQt6.QtSvgWidgets import QSvgWidget
from modules.login_dialog import LoginDialog
from backend.login.login_status_manager import check_login_status
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("变声器")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.screen_size(0.8), self.screen_size(0.7, height=True))

        self.initUI()

        # 创建登录对话框实例，但不立即显示
        self.login_dialog = LoginDialog(self)

        # 检查自动登录状态
        self.check_auto_login()

        self.installEventFilter(self)

        # 初始化拖动窗口的变量
        self.dragging = False
        self.offset = QPoint()
        self.login_dialog_offset = QPoint()

        # 定义可拖动的顶部区域高度
        self.draggable_height = 50  # 顶部50像素区域可拖动

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

        self.rounded_bg = RoundedBackgroundWidget()
        self.rounded_bg.setObjectName("roundedBackground")
        self.rounded_bg.setStyleSheet("""
            #roundedBackground {
                background-color: white;
                border-radius: 20px;
            }
        """)

        rounded_layout = QVBoxLayout(self.rounded_bg)
        rounded_layout.setContentsMargins(0, 0, 0, 0)  # 确保内容填充到边缘
        rounded_layout.setAlignment(Qt.AlignmentFlag.AlignTop)  # 明确设置为顶部对齐

        # 创建顶部布局，背景改为透明
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: red;")  # 设置为透明背景transparent
        top_bar.setFixedHeight(70)

        # 创建一个新的水平布局，用于放置 logo、公告和按钮
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 0, 10, 0)  # 调整整体边距
        top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐

        # 加载主 logo
        main_logo = QSvgWidget('icons/main_logo.svg')
        main_logo.setFixedHeight(top_bar.height())  # 设置 logo 高度和顶部区域一致
        logo_width = int(top_bar.height() * 3.0)  # 进一步增加宽度
        main_logo.setFixedWidth(logo_width)  # 设置 logo 的宽度
        top_bar_layout.addWidget(main_logo, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        
        # 增加logo与公告之间的间距
        logo_spacer = QWidget()
        logo_spacer.setFixedWidth(40)  # 增加间距宽度
        top_bar_layout.addWidget(logo_spacer)

        # 创建公告显示区域
        announcement_layout = QHBoxLayout()
        announcement_layout.setContentsMargins(0, 0, 0, 0)  # 重置内边距
        announcement_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 公告左侧喇叭图标
        speaker_icon = QSvgWidget('icons/sound.svg')
        speaker_icon.setFixedSize(24, 24)  # 调整图标大小
        announcement_layout.addWidget(speaker_icon)

        # 公告文本 - 调整样式以适应更长文本
        announcement_text = "欢迎使用AI变声."
        announcement_label = QLabel(announcement_text)
        announcement_label.setObjectName("announcementLabel")
        announcement_label.setStyleSheet("""
            #announcementLabel {
                background-color: rgba(245, 245, 245, 0.9);
                border-radius: 15px;
                padding: 5px 12px;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                color: #333333;
                max-width: 400px;
                min-width: 200px;
            }
        """)
        announcement_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 文本居中
        announcement_label.setWordWrap(False)  # 禁止文本换行
        announcement_label.setScaledContents(False)  # 禁止缩放内容
        announcement_label.setFixedHeight(30)  # 设置固定高度
        announcement_layout.addWidget(announcement_label, stretch=1)

        # 公告右侧耳机图标
        headset_icon = QSvgWidget('icons/service.svg')
        headset_icon.setFixedSize(24, 24)  # 调整图标大小
        announcement_layout.addWidget(headset_icon)

        # 将公告布局添加到顶部布局中间
        top_bar_layout.addLayout(announcement_layout, stretch=1)  # 使用拉伸因子使其居中

        # 添加右侧间距，平衡左侧logo区域
        right_spacer = QWidget()
        right_spacer.setFixedWidth(20)  # 调整间距大小
        top_bar_layout.addWidget(right_spacer)

        # 创建一个新的水平布局，用于放置头像、用户名和按钮
        right_layout = QHBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 创建一个垂直布局来包含头像和用户名，并添加间距
        avatar_username_layout = QVBoxLayout()
        avatar_username_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_username_layout.setContentsMargins(0, 5, 0, 5)  # 上下各5像素间距

        # 头像和用户名布局
        self.user_info_layout = QHBoxLayout()
        self.user_info_layout.setSpacing(20)
        self.user_avatar_label = QLabel()
        # 设置头像高度为 top_bar 高度的 0.8 倍
        avatar_size = int(top_bar.height() * 0.8)
        self.user_avatar_label.setFixedSize(avatar_size, avatar_size)
        self.user_info_layout.addWidget(self.user_avatar_label)
        self.username_display_label = QLabel()
        self.username_display_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;  /* 增大字体大小，原为14px */
                font-weight: 1000; /* 增加字体粗细 */
                color: #333333;
            }
        """)
        self.user_info_layout.addWidget(self.username_display_label)
        
        # 将头像和用户名布局添加到垂直布局中
        avatar_username_layout.addLayout(self.user_info_layout)
        
        # 将垂直布局添加到右侧布局
        right_layout.addLayout(avatar_username_layout)

        # 加载最小化图标
        minimize_icon = QSvgWidget('icons/minimize.svg')
        minimize_icon.setFixedSize(30, 30)
        minimize_icon.setStyleSheet("margin: 10px;")
        minimize_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        minimize_icon.mousePressEvent = self.minimize_app
        right_layout.addWidget(minimize_icon)

        # 加载关闭图标
        close_icon = QSvgWidget('icons/close.svg')
        close_icon.setFixedSize(30, 30)
        close_icon.setStyleSheet("margin: 10px;")
        close_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_icon.mousePressEvent = self.close_app
        right_layout.addWidget(close_icon)

        # 将右侧布局添加到顶部布局的右侧
        top_bar_layout.addLayout(right_layout, stretch=0)  # 不拉伸按钮区域

        # 添加顶部栏
        rounded_layout.addWidget(top_bar)

        main_layout.addWidget(self.rounded_bg)

    def show_login_dialog(self):
        is_logged_in, _, _ = check_login_status()
        if not is_logged_in:
            self.login_dialog = LoginDialog(self)
            self.login_dialog.show()
            self.login_dialog_offset = self.login_dialog.pos() - self.pos()

    def check_auto_login(self):
        """检查自动登录"""
        if self.login_dialog.check_token():
            pass
        else:
            QTimer.singleShot(1000, self.show_login_dialog)  # 如果自动登录失败，延迟显示登录对话框

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

    def minimize_app(self, event):
        """最小化窗口到任务栏"""
        self.showMinimized()
        event.accept()

    def mousePressEvent(self, event):
        # 仅当鼠标点击在顶部可拖动区域时才允许拖动
        if event.button() == Qt.MouseButton.LeftButton and event.pos().y() < self.draggable_height:
            self.dragging = True
            self.offset = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.offset
            self.move(new_pos)
            if self.login_dialog:
                self.login_dialog.move(new_pos + self.login_dialog_offset)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False


class RoundedBackgroundWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.background_image = QPixmap('images/background.png')
        self.radius = 20

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