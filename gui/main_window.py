# 文件 1：main_window.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QGridLayout,
    QFileDialog, QMessageBox
)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent, QPoint, QByteArray, QRectF
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QBrush, QColor
from modules.login_dialog import LoginDialog
from backend.login.login_status_manager import check_login_status
from backend.database.database_manager import DatabaseManager
from backend.login.token_storage import  read_token
from backend.login.token_utils import verify_token
from backend.login.login_status_manager import check_login_status, save_login_status
from backend.resources import load_icon_data, get_logo
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

        # 初始化拖动窗口的变量
        self.dragging = False
        self.offset = QPoint()
        self.login_dialog_offset = QPoint()
        # 定义可拖动的顶部区域高度
        self.draggable_height = 50  # 顶部50像素区域可拖动

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        # 初始化用户ID
        self.user_id = None

        self.initUI()

        # 创建登录对话框实例，但不立即显示
        self.login_dialog = LoginDialog(self)

        # 创建蒙版控件
        self.mask_widget = QWidget(self)
        self.mask_widget.setStyleSheet("background-color: rgba(50, 50, 50, 150);")
        self.mask_widget.setVisible(False)

        # 检查自动登录状态
        self.check_auto_login()

        self.installEventFilter(self)

    def screen_size(self, ratio, height=False):
        screen = QApplication.primaryScreen()
        size = screen.size()
        if height:
            return int(size.height() * ratio)
        return int(size.width() * ratio)

    def initUI(self):
        # 主窗口布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 圆角背景窗口
        self.rounded_bg = RoundedBackgroundWidget()
        self.rounded_bg.setObjectName("roundedBackground")
        self.rounded_bg.setStyleSheet("""
            #roundedBackground {
                background-color: transparent;
                border-radius: 20px;
            }
        """)

        rounded_layout = QVBoxLayout(self.rounded_bg)
        rounded_layout.setContentsMargins(0, 0, 0, 0)
        rounded_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 顶部导航栏
        top_bar = self.create_top_bar()
        rounded_layout.addWidget(top_bar)

        # 创建主内容区域
        main_content_widget = QWidget()
        main_content_layout = QVBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(15, 15, 15, 15)
        main_content_layout.setSpacing(15)  # 行间距

        # 创建独立的行布局和板块
        # 第一行
        row1_widget = QWidget()
        row1_layout = QHBoxLayout(row1_widget)
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(20)  # 列间距

        # 板块1 - 独立布局
        section1 = self.create_section_widget(0)
        section1_layout = QVBoxLayout()
        section1_layout.addWidget(section1)
        row1_layout.addLayout(section1_layout, 1)  # 权重1

        # 板块2 - 独立布局
        section2 = self.create_section_widget(1)
        section2_layout = QVBoxLayout()
        section2_layout.addWidget(section2)
        row1_layout.addLayout(section2_layout, 3)  # 权重3

        # 板块3 - 独立布局
        section3 = self.create_section_widget(2)
        section3_layout = QVBoxLayout()
        section3_layout.addWidget(section3)
        row1_layout.addLayout(section3_layout, 1)  # 权重1

        main_content_layout.addWidget(row1_widget)

        # 第二行
        row2_widget = QWidget()
        row2_layout = QHBoxLayout(row2_widget)
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(20)  # 列间距

        # 板块4 - 独立布局
        section4 = self.create_section_widget(3)
        section4_layout = QVBoxLayout()
        section4_layout.addWidget(section4)
        row2_layout.addLayout(section4_layout, 1)  # 权重1

        # 板块5 - 独立布局
        section5 = self.create_section_widget(4)
        section5_layout = QVBoxLayout()
        section5_layout.addWidget(section5)
        row2_layout.addLayout(section5_layout, 3)  # 权重3

        # 板块6 - 独立布局
        section6 = self.create_section_widget(5)
        section6_layout = QVBoxLayout()
        section6_layout.addWidget(section6)
        row2_layout.addLayout(section6_layout, 1)  # 权重1

        main_content_layout.addWidget(row2_widget)

        rounded_layout.addWidget(main_content_widget, stretch=3)

        # 底部红色导航栏模块
        bottom_bar = self.create_bottom_bar()
        rounded_layout.addWidget(bottom_bar)

        main_layout.addWidget(self.rounded_bg)

    def create_bottom_bar(self):
        """创建底部红色导航栏模块"""
        bottom_bar = QWidget()
        bottom_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 180);
                border-radius: 10px;
                padding: 10px;
            }
        """)

        # 底部导航栏内容
        title = QLabel("底部导航栏")
        title.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 180);
                font-weight: bold;
                font-size: 16px;
                text-align: center;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(bottom_bar)
        layout.addWidget(title)

        return bottom_bar

    def create_section_widget(self, index):
        section_widget = QWidget()
        section_widget.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(255, 255, 255, 180);
                border: none;
                border-radius: 10px;
                padding: 15px;
            }}
        """)

        title = QLabel(f"板块 {index + 1}")
        title.setStyleSheet("font-weight: bold; font-size: 16px;")

        content = QLabel(f"这是板块 {index + 1} 的内容")

        layout = QVBoxLayout(section_widget)
        layout.addWidget(title)
        layout.addWidget(content)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        return section_widget

    def create_top_bar(self):
        """创建顶部导航栏"""
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setStyleSheet("background-color: transparent;")
        top_bar.setFixedHeight(50)  # 调整顶部导航栏高度，使其更紧凑

        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(10, 0, 10, 0)  # 减小外边距
        top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 添加Logo图标
        logo_label = self.create_logo_label(top_bar)
        top_bar_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # 公告显示区域
        announcement_layout = self.create_announcement_layout()
        top_bar_layout.addLayout(announcement_layout, stretch=1)
        top_bar_layout.addSpacing(20)  # 添加20像素间距

        # 右侧功能按钮
        right_layout = self.create_right_layout(top_bar)
        top_bar_layout.addLayout(right_layout)

        return top_bar

    def create_logo_label(self, parent_widget):
        """创建Logo标签"""
        logo_label = QLabel()

        # 从本地文件加载 logo 数据
        logo_data = get_logo()
        if logo_data:
            logo_pixmap = QPixmap()
            logo_pixmap.loadFromData(logo_data)

            # 调整Logo大小
            logo_height = int(parent_widget.height() * 2.5)  # 调整Logo高度比例
            logo_pixmap = logo_pixmap.scaled(
                logo_height * 3,  # 调整Logo宽度比例
                logo_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        logo_label.setStyleSheet("margin-right: 15px;")

        return logo_label

    def create_announcement_layout(self):
        """创建公告布局"""
        announcement_layout = QHBoxLayout()
        announcement_layout.setContentsMargins(0, 0, 0, 0)
        announcement_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 公告左侧喇叭图标
        speaker_icon = self.create_svg_widget(10, 25, 25, "margin: 5px;")  # 减小图标大小
        if speaker_icon:
            announcement_layout.addWidget(speaker_icon)

        # 从数据库获取公告文本
        announcement_text = self.db_manager.get_latest_announcement()
        if not announcement_text:
            announcement_text = "暂无公告."

        # 公告标签
        announcement_label = QLabel(announcement_text)
        announcement_label.setObjectName("announcementLabel")
        announcement_label.setStyleSheet("""
            #announcementLabel {
                background-color: rgba(245, 245, 245, 0.9);
                border-radius: 10px;  
                padding: 3px 8px;  
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 14px;  
                color: #333333;
                max-width: 600px;  
                min-width: 150px; 
            }
        """)
        announcement_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        announcement_label.setWordWrap(False)
        announcement_label.setFixedHeight(25)  # 减小高度
        announcement_layout.addWidget(announcement_label, stretch=1)

        # 间距
        headset_spacer = QWidget()
        headset_spacer.setFixedWidth(10)  # 减小间距
        announcement_layout.addWidget(headset_spacer)

        # 公告右侧耳机图标
        headset_icon = self.create_svg_widget(9, 25, 25, "margin: 5px;")  # 减小图标大小
        if headset_icon:
            announcement_layout.addWidget(headset_icon)

        announcement_layout.addSpacing(20)

        return announcement_layout

    def create_right_layout(self, parent_widget):
        """创建右侧功能按钮布局"""
        right_layout = QHBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 头像和用户名布局
        self.user_info_layout = QHBoxLayout()
        self.user_info_layout.setSpacing(10)  # 减小间距

        # 头像标签
        self.user_avatar_label = QLabel()
        avatar_size = int(parent_widget.height() * 0.9)  # 减小头像大小
        self.user_avatar_label.setFixedSize(avatar_size, avatar_size)
        self.user_avatar_label.mousePressEvent = self.upload_avatar  # 添加头像点击事件
        self.user_info_layout.addWidget(self.user_avatar_label)

        # 用户名标签
        self.username_display_label = QLabel()
        self.username_display_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 16px; 
                font-weight: bold;
                color: #333333;
            }
        """)
        self.user_info_layout.addWidget(self.username_display_label)

        # 头像和用户名的垂直布局
        avatar_username_layout = QVBoxLayout()
        avatar_username_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_username_layout.setContentsMargins(0, 3, 0, 3)  # 减小上下间距
        avatar_username_layout.addLayout(self.user_info_layout)
        right_layout.addLayout(avatar_username_layout)

        # 最小化图标
        minimize_icon = self.create_svg_widget(7, 25, 25, "margin: 5px;")  # 减小图标大小
        if minimize_icon:
            minimize_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            minimize_icon.mousePressEvent = self.minimize_app
            right_layout.addWidget(minimize_icon)

        # 关闭图标
        close_icon = self.create_svg_widget(1, 25, 25, "margin: 5px;")  # 减小图标大小
        if close_icon:
            close_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            close_icon.mousePressEvent = self.close_app
            right_layout.addWidget(close_icon)

        return right_layout

    def create_svg_widget(self, icon_id, width, height, style):
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

    def show_login_dialog(self):
        is_logged_in, _, _ = check_login_status()
        if not is_logged_in:
            self.login_dialog = LoginDialog(self)
            self.login_dialog.show()

            # 居中显示
            dialog_size = self.login_dialog.size()
            center_x = self.x() + (self.width() - dialog_size.width()) // 2
            center_y = self.y() + (self.height() - dialog_size.height()) // 2
            self.login_dialog.move(center_x, center_y)

            self.login_dialog_offset = self.login_dialog.pos() - self.pos()

            # 显示蒙版
            self.mask_widget.setGeometry(0, 0, self.width(), self.height())
            self.mask_widget.setVisible(True)

    def check_auto_login(self):
        """检查自动登录"""
        token = read_token()
        if token:
            payload = verify_token(token)
            if payload:
                email = payload['email']
                user = self.db_manager.get_user_by_email(email)
                if user:
                    logging.info(f"用户 {user['username']} 自动登录成功，ID: {user['id']}")
                    save_login_status(user['id'], user['username'])

                    vip_info = self.db_manager.get_user_vip_info(user['id'])
                    if vip_info:
                        is_vip = vip_info['is_vip']
                        diamonds = vip_info['diamonds']
                        self.update_membership_info(user['avatar'], user['username'], is_vip, diamonds, user['id'])

                    # 隐藏蒙版
                    self.mask_widget.setVisible(False)
        else:
            self.show_login_dialog()

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

    def update_membership_info(self, avatar_data, username, is_vip, diamonds, user_id=None):
        """更新会员信息显示"""
        # 清空现有会员信息
        while self.user_info_layout.count():
            item = self.user_info_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
            else:
                layout = item.layout()
                if layout:
                    while layout.count():
                        sub_item = layout.takeAt(0)
                        sub_widget = sub_item.widget()
                        if sub_widget:
                            sub_widget.setParent(None)

        # 添加头像和用户名
        self.user_info_layout.addWidget(self.user_avatar_label)
        self.user_info_layout.addWidget(self.username_display_label)

        # 创建会员信息布局
        membership_layout = QHBoxLayout()
        membership_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        membership_layout.setSpacing(10)

        # 添加 VIP 信息
        vip_layout = QHBoxLayout()
        vip_layout.setSpacing(5)
        vip_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # VIP 图标
        vip_icon = self.create_svg_widget(13, 40, 30, "margin: 5px;")
        if vip_icon:
            vip_layout.addWidget(vip_icon)

        # VIP 状态标签
        vip_status_label = QLabel("非会员" if not is_vip else "会员")
        vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;
                font-weight: bold;
                color: #FF6347;
            }
        """)
        vip_layout.addWidget(vip_status_label)

        membership_layout.addLayout(vip_layout)
        membership_layout.addSpacing(20)

        # 添加钻石信息
        diamond_layout = QHBoxLayout()
        diamond_layout.setSpacing(5)
        diamond_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 钻石图标
        diamond_icon = self.create_svg_widget(2, 30, 30, "margin: 5px;")
        if diamond_icon:
            diamond_layout.addWidget(diamond_icon)

        # 钻石数量标签
        diamond_count_label = QLabel(f"剩余 {diamonds}")
        diamond_count_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;
                color: #007BFF;
            }
        """)
        diamond_layout.addWidget(diamond_count_label)

        membership_layout.addLayout(diamond_layout)
        self.user_info_layout.addLayout(membership_layout, stretch=0)

        # 更新用户ID
        self.user_id = user_id

        # 如果有头像数据，更新头像显示
        if avatar_data:
            self.update_user_avatar_display(avatar_data)

    def upload_avatar(self, event):
        """上传头像"""
        if self.user_id:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择头像", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                with open(file_path, "rb") as file:
                    avatar_data = file.read()
                    if self.db_manager.update_user_avatar(self.user_id, avatar_data):
                        # 更新成功后，重新加载头像显示
                        self.update_user_avatar_display(avatar_data)
                    else:
                        QMessageBox.warning(self, "更新失败", "头像更新失败，请稍后重试")
        else:
            QMessageBox.warning(self, "未登录", "请先登录后再尝试上传头像")

    def update_user_avatar_display(self, avatar_data):
        """更新头像显示"""
        pixmap = QPixmap()
        pixmap.loadFromData(avatar_data)
        size = min(pixmap.width(), pixmap.height())
        cropped_pixmap = QPixmap(size, size)
        cropped_pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(cropped_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio))
        painter.end()
        self.user_avatar_label.setPixmap(cropped_pixmap.scaled(
            self.user_avatar_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        ))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.login_dialog and self.login_dialog.isVisible():
            dialog_width = int(self.width() * 0.3)
            dialog_height = min(int(self.height() * 0.5), self.height() - 40)
            self.login_dialog.resize(dialog_width, dialog_height)

            # 保持居中
            center_x = self.x() + (self.width() - dialog_width) // 2
            center_y = self.y() + (self.height() - dialog_height) // 2
            self.login_dialog.move(center_x, center_y)

        # 调整蒙版大小
        self.mask_widget.setGeometry(0, 0, self.width(), self.height())


class RoundedBackgroundWidget(QWidget):
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