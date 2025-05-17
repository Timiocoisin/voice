from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGraphicsDropShadowEffect, QPushButton
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QRect, QRectF, QPoint, QByteArray
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QColor, QBrush
from PyQt6.QtSvgWidgets import QSvgWidget
from modules.login_dialog import LoginDialog
from backend.login.login_status_manager import check_login_status
from backend.database.database_manager import create_connection, get_latest_logo, get_latest_announcement, get_icon_by_id
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

        # --------------------- 顶部导航栏布局 ---------------------
        top_bar = QWidget()
        top_bar.setStyleSheet("background-color: transparent;")  # 设置为透明背景
        top_bar.setFixedHeight(70)

        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 0, 20, 0)  # 左侧边距20px用于logo
        top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)  # 垂直居中对齐

        # --------------------- 添加Logo图标 ---------------------
        logo_label = QLabel()

        # 从数据库获取 logo 数据
        connection = create_connection()
        if connection:
            logo_data = get_latest_logo(connection)
            if logo_data:
                logo_pixmap = QPixmap()
                logo_pixmap.loadFromData(logo_data)
            else:
                # 如果数据库中没有 logo 数据，使用空白图标
                logo_pixmap = QPixmap()
            connection.close()
        else:
            # 如果数据库连接失败，使用空白图标
            logo_pixmap = QPixmap()

        logo_height = int(top_bar.height() * 2.5)  # 高度设为顶部栏的150%（可更大）
        logo_pixmap = logo_pixmap.scaled(
            logo_height * 100,       # 宽度设为高度的2倍（可自定义宽高比）
            logo_height, 
            Qt.AspectRatioMode.KeepAspectRatio,  # 保持原始宽高比
            Qt.TransformationMode.SmoothTransformation
        )
        logo_label.setPixmap(logo_pixmap)
        logo_label.setStyleSheet("margin-right: 20px;")  # 右侧间距20px
        top_bar_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # --------------------- 公告显示区域 ---------------------
        announcement_layout = QHBoxLayout()
        announcement_layout.setContentsMargins(0, 0, 0, 0)
        announcement_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 公告左侧喇叭图标
        connection = create_connection()
        if connection:
            try:
                # 从数据库获取公告喇叭图标的二进制数据（ID 为 10）
                icon_data = get_icon_by_id(connection, 10)

                if icon_data:
                    # 创建 QSvgWidget 并加载图标数据
                    speaker_icon = QSvgWidget()
                    byte_array = QByteArray(icon_data)
                    speaker_icon.load(byte_array)
                    speaker_icon.setFixedSize(30, 30)  # 调整图标大小
                    speaker_icon.setStyleSheet("margin: 5px;")  # 添加内边距
                    announcement_layout.addWidget(speaker_icon)
            except Exception as e:
                print(f"加载图标时出错: {str(e)}")
            finally:
                connection.close()

        # 从数据库获取公告文本
        connection = create_connection()
        if connection:
            announcement_text = get_latest_announcement(connection)
            if not announcement_text:
                announcement_text = "暂无公告."
            connection.close()
        announcement_label = QLabel(announcement_text)
        announcement_label.setObjectName("announcementLabel")
        announcement_label.setStyleSheet("""
            #announcementLabel {
                background-color: rgba(245, 245, 245, 0.9);
                border-radius: 15px;
                padding: 5px 12px;
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 16px;
                color: #333333;
                max-width: 800px;
                min-width: 200px;
            }
        """)
        announcement_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        announcement_label.setWordWrap(False)
        announcement_label.setFixedHeight(30)
        announcement_layout.addWidget(announcement_label, stretch=1)

        # 公告右侧耳机图标
        headset_spacer = QWidget()
        headset_spacer.setFixedWidth(20)  # 间距20px
        announcement_layout.addWidget(headset_spacer)

        connection = create_connection()
        if connection:
            try:
                icon_data = get_icon_by_id(connection, 9)

                if icon_data:
                    # 创建 QSvgWidget 并加载图标数据
                    headset_icon = QSvgWidget()
                    byte_array = QByteArray(icon_data)
                    headset_icon.load(byte_array)
                    headset_icon.setFixedSize(30, 30)  # 调整图标大小
                    headset_icon.setStyleSheet("margin: 5px;")  # 添加内边距
                    announcement_layout.addWidget(headset_icon)
            except Exception as e:
                print(f"加载图标时出错: {str(e)}")
            finally:
                connection.close()

        top_bar_layout.addLayout(announcement_layout, stretch=1)  # 公告区域居中拉伸

        # --------------------- 右侧功能按钮 ---------------------
        right_layout = QHBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 头像和用户名布局
        self.user_info_layout = QHBoxLayout()
        self.user_info_layout.setSpacing(20)
        self.user_avatar_label = QLabel()
        avatar_size = int(top_bar.height() * 0.8)
        self.user_avatar_label.setFixedSize(avatar_size, avatar_size)
        self.user_info_layout.addWidget(self.user_avatar_label)
        
        self.username_display_label = QLabel()
        self.username_display_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 18px;
                font-weight: bold;
                color: #333333;
            }
        """)
        self.user_info_layout.addWidget(self.username_display_label)
        
        avatar_username_layout = QVBoxLayout()
        avatar_username_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_username_layout.setContentsMargins(0, 5, 0, 5)
        avatar_username_layout.addLayout(self.user_info_layout)
        right_layout.addLayout(avatar_username_layout)

        # 建立数据库连接
        connection = create_connection()

        if connection:
            try:
                # 获取最小化图标数据，假设其 ID 为 7
                minimize_icon_data = get_icon_by_id(connection, 7)

                if minimize_icon_data:
                    # 创建 QSvgWidget 并加载最小化图标数据
                    minimize_icon = QSvgWidget()
                    byte_array = QByteArray(minimize_icon_data)
                    minimize_icon.load(byte_array)
                    minimize_icon.setFixedSize(30, 30)
                    minimize_icon.setStyleSheet("margin: 10px;")
                    minimize_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    minimize_icon.mousePressEvent = self.minimize_app
                    right_layout.addWidget(minimize_icon)

                # 获取关闭图标数据，假设其 ID 为 1
                close_icon_data = get_icon_by_id(connection, 1)

                if close_icon_data:
                    # 创建 QSvgWidget 并加载关闭图标数据
                    close_icon = QSvgWidget()
                    byte_array = QByteArray(close_icon_data)
                    close_icon.load(byte_array)
                    close_icon.setFixedSize(30, 30)
                    close_icon.setStyleSheet("margin: 10px;")
                    close_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                    close_icon.mousePressEvent = self.close_app
                    right_layout.addWidget(close_icon)

            except Exception as e:
                print(f"加载图标时出错: {str(e)}")
            finally:
                connection.close()

        top_bar_layout.addLayout(right_layout)  # 添加到右侧

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

    def update_membership_info(self, is_vip, diamonds):
        """更新会员信息显示"""
        membership_layout = QHBoxLayout()
        membership_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        membership_layout.setSpacing(10)  # 设置整体布局的间距

        # 创建一个子布局用于放置 VIP 图标和会员状态文本
        vip_layout = QHBoxLayout()
        vip_layout.setSpacing(5)  # 缩小 VIP 图标和文本之间的间距
        vip_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 加载 VIP 图标
        # 建立数据库连接
        connection = create_connection()

        if connection:
            try:
                # 假设 VIP 图标的 ID 为 13，根据实际情况修改
                icon_data = get_icon_by_id(connection, 13)

                if icon_data:
                    # 创建 QSvgWidget 并加载图标数据
                    vip_icon = QSvgWidget()
                    byte_array = QByteArray(icon_data)
                    vip_icon.load(byte_array)
                    vip_icon.setFixedSize(40, 30)  # 统一图标大小
                    vip_icon.setStyleSheet("margin: 5px;")
                    # 假设 vip_layout 是已定义的布局
                    vip_layout.addWidget(vip_icon)

            except Exception as e:
                print(f"加载图标时出错: {str(e)}")
            finally:
                connection.close()

        # 显示 VIP 状态
        vip_status_label = QLabel("非会员" if not is_vip else "会员")
        vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;  /* 字体大小 */
                font-weight: bold;  /* 加粗字体 */
                color: #FF6347;  /* 橙红色字体 */
            }
        """)
        vip_layout.addWidget(vip_status_label)

        # 将 VIP 布局添加到主布局
        membership_layout.addLayout(vip_layout)

        # 在会员信息和钻石信息之间增加间距
        membership_layout.addSpacing(20)  # 增加 20 像素的间距

        # 创建一个子布局用于放置钻石图标和钻石数量文本
        diamond_layout = QHBoxLayout()
        diamond_layout.setSpacing(5)  # 缩小钻石图标和文本之间的间距
        diamond_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 加载钻石图标
        # 建立数据库连接
        connection = create_connection()

        if connection:
            try:
                # 假设钻石图标的 ID 为 2，根据实际情况修改
                icon_data = get_icon_by_id(connection, 2)

                if icon_data:
                    # 创建 QSvgWidget 并加载图标数据
                    diamond_icon = QSvgWidget()
                    byte_array = QByteArray(icon_data)
                    diamond_icon.load(byte_array)
                    diamond_icon.setFixedSize(30, 30)  # 统一图标大小
                    diamond_icon.setStyleSheet("margin: 5px;")
                    # 假设 diamond_layout 是已定义的布局
                    diamond_layout.addWidget(diamond_icon)
                else:
                    print("未找到钻石图标数据")

            except Exception as e:
                print(f"加载图标时出错: {str(e)}")
            finally:
                connection.close()

        # 显示钻石数量
        diamond_count_label = QLabel(f"剩余 {diamonds}")
        diamond_count_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;  /* 字体大小 */
                color: #007BFF;  /* 蓝色字体 */
            }
        """)
        diamond_layout.addWidget(diamond_count_label)

        # 将钻石布局添加到主布局
        membership_layout.addLayout(diamond_layout)

        # 将会员信息布局添加到右侧布局
        self.user_info_layout.addLayout(membership_layout, stretch=0)

class RoundedBackgroundWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.background_image = QPixmap('images/background.png')
        self.radius = 20

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

