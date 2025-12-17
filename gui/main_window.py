# 文件 1：main_window.py
import os
import base64
from datetime import datetime
from html import escape
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QFileDialog,
    QDialog,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QMenu,
    QWidgetAction,
    QScrollArea,
)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent, QPoint, QByteArray, QRectF, QSize, QBuffer, QIODevice, QTimer
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QBrush, QColor, QIcon
from modules.login_dialog import LoginDialog
from modules.vip_membership_dialog import VipMembershipDialog, VipPackageDialog, DiamondPackageDialog
from backend.login.login_status_manager import check_login_status
from backend.database.database_manager import DatabaseManager
from backend.login.token_storage import  read_token
from backend.login.token_utils import verify_token
from backend.login.login_status_manager import check_login_status, save_login_status
from backend.resources import load_icon_data, load_icon_path, get_logo, get_default_avatar
from gui.custom_message_box import CustomMessageBox
from gui.avatar_crop_dialog import AvatarCropDialog
from .marquee_label import MarqueeLabel
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
        self.draggable_height = 40  # 顶部40像素区域可拖动

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        # 初始化用户ID
        self.user_id = None

        self.initUI()

        # 创建登录对话框实例，但不立即显示
        self.login_dialog = LoginDialog(self)

        # 创建蒙版控件
        # 只遮罩圆角背景区域（避免遮罩覆盖主窗口透明边缘，看起来比主页还大）
        self.mask_widget = QWidget(self.rounded_bg)
        self.mask_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 120);
                border-radius: 20px;
            }
        """)
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
        self.main_content_widget = QWidget()
        self.main_content_layout = QHBoxLayout(self.main_content_widget)
        self.main_content_layout.setContentsMargins(20, 15, 20, 15)  # 优化边距，给内容更多空间
        self.main_content_layout.setSpacing(18)  # 优化列间距
        self.main_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 左边列：版块1和版块4垂直排列，各占一半
        self.left_column_widget = QWidget()
        left_column_layout = QVBoxLayout(self.left_column_widget)
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        left_column_layout.setSpacing(18)  # 优化行间距

        # 版块1
        section1 = self.create_section_widget(0)
        section1.setMinimumHeight(220)  # 设置最小高度，确保内容有足够空间
        section1_layout = QVBoxLayout()
        section1_layout.setContentsMargins(0, 0, 0, 0)
        section1_layout.addWidget(section1)
        left_column_layout.addLayout(section1_layout, 1)  # 拉伸因子1，占一半

        # 版块4
        section4 = self.create_section_widget(3)
        section4.setMinimumHeight(220)  # 设置最小高度
        section4_layout = QVBoxLayout()
        section4_layout.setContentsMargins(0, 0, 0, 0)
        section4_layout.addWidget(section4)
        left_column_layout.addLayout(section4_layout, 1)  # 拉伸因子1，占一半

        self.main_content_layout.addWidget(self.left_column_widget, 1)  # 权重1

        # 中间列：合并后的版块2（原版块2和版块5合并）
        self.merged_section2 = self.create_merged_section_widget()
        self.merged_section2.setMinimumHeight(460)  # 设置最小高度，跨越两行（220 + 220 + 间距）
        self.merged_section2_layout = QVBoxLayout()
        self.merged_section2_layout.setContentsMargins(0, 0, 0, 0)
        self.merged_section2_layout.addWidget(self.merged_section2)
        self.main_content_layout.addLayout(self.merged_section2_layout, 3)  # 权重3

        # 右边列：版块3和版块6垂直排列，各占一半
        self.right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(self.right_column_widget)
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        right_column_layout.setSpacing(18)  # 优化行间距

        # 版块3
        section3 = self.create_section_widget(2)
        section3.setMinimumHeight(220)  # 设置最小高度
        section3_layout = QVBoxLayout()
        section3_layout.setContentsMargins(0, 0, 0, 0)
        section3_layout.addWidget(section3)
        right_column_layout.addLayout(section3_layout, 1)  # 拉伸因子1，占一半

        # 版块6
        section6 = self.create_section_widget(5)
        section6.setMinimumHeight(220)  # 设置最小高度
        section6_layout = QVBoxLayout()
        section6_layout.setContentsMargins(0, 0, 0, 0)
        section6_layout.addWidget(section6)
        right_column_layout.addLayout(section6_layout, 1)  # 拉伸因子1，占一半

        self.main_content_layout.addWidget(self.right_column_widget, 1)  # 权重1

        # 客服聊天大面板（默认隐藏，点击耳机后显示，覆盖中间 + 右侧区域）
        self.chat_panel = self.create_chat_panel(self.main_content_widget)
        self.chat_panel.setVisible(False)

        rounded_layout.addWidget(self.main_content_widget, stretch=1)

        # 底部红色导航栏模块
        bottom_bar = self.create_bottom_bar()
        rounded_layout.addWidget(bottom_bar)

        main_layout.addWidget(self.rounded_bg)

    def create_bottom_bar(self):
        """创建底部导航栏模块"""
        bottom_bar = QWidget()
        bottom_bar.setObjectName("bottomBar")
        bottom_bar.setMinimumHeight(60)  # 设置最小高度，使导航栏更高
        bottom_bar.setStyleSheet("""
            #bottomBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 200),
                    stop:1 rgba(255, 255, 255, 180));
                border-radius: 12px;
                border: 1px solid rgba(226, 232, 240, 200);
                padding: 18px 20px;
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(bottom_bar)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 3)
        shadow.setColor(QColor(0, 0, 0, 25))
        bottom_bar.setGraphicsEffect(shadow)

        # 底部导航栏内容
        title = QLabel("底部导航栏")
        title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-weight: 600;
                font-size: 16px;
                color: #475569;
                text-align: center;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QHBoxLayout(bottom_bar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title)

        return bottom_bar

    def create_section_widget(self, index):
        section_widget = QWidget()
        section_widget.setObjectName(f"section{index}")
        
        # 优化板块样式：添加渐变背景、阴影效果
        section_widget.setStyleSheet(f"""
            #section{index} {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 220),
                    stop:1 rgba(255, 255, 255, 200));
                border: 1px solid rgba(226, 232, 240, 200);
                border-radius: 16px;
                padding: 20px;
            }}
            #section{index}:hover {{
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 240),
                    stop:1 rgba(255, 255, 255, 220));
                border: 1px solid rgba(203, 213, 225, 250);
            }}
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(section_widget)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 30))
        section_widget.setGraphicsEffect(shadow)

        layout = QVBoxLayout(section_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 优化标题样式
        title = QLabel(f"板块 {index + 1}")
        title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-weight: 700;
                font-size: 18px;
                color: #1e293b;
                padding-bottom: 8px;
                border-bottom: 2px solid rgba(226, 232, 240, 200);
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(title)

        # 优化内容区域
        content = QLabel(f"这是板块 {index + 1} 的内容")
        content.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                color: #64748b;
                padding: 8px 0px;
                line-height: 1.6;
            }
        """)
        content.setWordWrap(True)
        layout.addWidget(content)
        
        # 添加弹性空间
        layout.addStretch()

        return section_widget

    def create_merged_section_widget(self):
        """创建合并后的版块2（原版块2和版块5合并）"""
        section_widget = QWidget()
        section_widget.setObjectName("section2_merged")
        
        # 优化板块样式：添加渐变背景、阴影效果
        section_widget.setStyleSheet("""
            #section2_merged {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 220),
                    stop:1 rgba(255, 255, 255, 200));
                border: 1px solid rgba(226, 232, 240, 200);
                border-radius: 16px;
                padding: 20px;
            }
            #section2_merged:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 240),
                    stop:1 rgba(255, 255, 255, 220));
                border: 1px solid rgba(203, 213, 225, 250);
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(section_widget)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 30))
        section_widget.setGraphicsEffect(shadow)

        layout = QVBoxLayout(section_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 标题：版块2
        title = QLabel("板块 2")
        title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-weight: 700;
                font-size: 18px;
                color: #1e293b;
                padding-bottom: 8px;
                border-bottom: 2px solid rgba(226, 232, 240, 200);
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(title)

        # 原版块2的内容
        content1 = QLabel("这是板块 2 的内容")
        content1.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                color: #64748b;
                padding: 8px 0px;
                line-height: 1.6;
            }
        """)
        content1.setWordWrap(True)
        layout.addWidget(content1)
        
        # 添加分隔线
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgba(226, 232, 240, 200); margin: 12px 0px;")
        layout.addWidget(separator)
        
        # 标题：版块5（作为合并版块的一部分）
        title2 = QLabel("板块 5")
        title2.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-weight: 700;
                font-size: 18px;
                color: #1e293b;
                padding-bottom: 8px;
                border-bottom: 2px solid rgba(226, 232, 240, 200);
                margin-bottom: 4px;
            }
        """)
        layout.addWidget(title2)

        # 原版块5的内容
        content2 = QLabel("这是板块 5 的内容")
        content2.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                color: #64748b;
                padding: 8px 0px;
                line-height: 1.6;
            }
        """)
        content2.setWordWrap(True)
        layout.addWidget(content2)
        
        # 添加弹性空间
        layout.addStretch()

        return section_widget

    def create_top_bar(self):
        """创建顶部导航栏"""
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        top_bar.setStyleSheet("background-color: transparent;")
        # 顶部导航栏再加高一些，让头像有更大的显示空间
        top_bar.setFixedHeight(56)

        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(12, 0, 12, 0)  # 优化外边距
        top_bar_layout.setSpacing(16)  # 优化元素间距
        top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 添加Logo图标
        logo_label = self.create_logo_label(top_bar)
        top_bar_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # 添加弹性空间，使公告区域居中
        top_bar_layout.addSpacing(10)

        # 公告显示区域
        announcement_layout = self.create_announcement_layout()
        top_bar_layout.addLayout(announcement_layout, stretch=1)

        # 添加弹性空间
        top_bar_layout.addSpacing(10)

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
            logo_height = int(parent_widget.height() * 2.0)  # 调整Logo高度比例，减小Logo尺寸
            logo_pixmap = logo_pixmap.scaled(
                logo_height * 3,  # 调整Logo宽度比例
                logo_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        logo_label.setStyleSheet("margin: 0px; padding: 0px;")

        return logo_label

    def create_announcement_layout(self):
        """创建公告布局"""
        announcement_layout = QHBoxLayout()
        announcement_layout.setContentsMargins(0, 0, 0, 0)
        announcement_layout.setSpacing(8)  # 公告容器和客服按钮之间的间距
        announcement_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

        # 创建公告容器，包含背景样式
        announcement_container = QWidget()
        announcement_container.setObjectName("announcementContainer")
        announcement_container.setStyleSheet("""
            #announcementContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 0.95),
                    stop:1 rgba(248, 250, 252, 0.95));
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 12px;  
                max-width: 600px;  
                min-width: 120px;
            }
        """)
        announcement_container.setFixedHeight(26)  # 优化高度

        # 容器内部布局
        container_layout = QHBoxLayout(announcement_container)
        container_layout.setContentsMargins(10, 0, 10, 0)  # 内边距
        container_layout.setSpacing(8)  # 图标和文字之间的间距
        container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 公告左侧喇叭图标（放在容器内的最左侧）
        speaker_icon = self.create_svg_widget(10, 20, 20, "margin: 0px; opacity: 0.75;")
        if speaker_icon:
            container_layout.addWidget(speaker_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 从数据库获取公告文本
        announcement_text = self.db_manager.get_latest_announcement()
        if not announcement_text:
            announcement_text = "欢迎使用《声音序章》软件！！！"

        # 公告标签使用自定义滚动组件（跑马灯效果）
        announcement_label = MarqueeLabel()
        announcement_label.setObjectName("announcementLabel")
        announcement_label.setText(announcement_text)
        announcement_label.setStyleSheet("""
            #announcementLabel {
                background: transparent;
                padding: 0px;
                font-family: \"Microsoft YaHei\", \"Roboto\", \"Arial\";
                font-size: 13px;  
                font-weight: 500;
                color: #475569;
            }
        """)
        announcement_label.setFixedHeight(20)
        container_layout.addWidget(announcement_label, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 添加公告容器到布局
        announcement_layout.addWidget(announcement_container, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 客服按钮（耳机图标）- 放在公告容器外面，单独放大一档
        self.headset_icon = self.create_svg_widget(9, 26, 26, "margin: 0px; opacity: 0.85;")
        if self.headset_icon:
            self.headset_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.headset_icon.mousePressEvent = self.open_customer_service_chat
            announcement_layout.addWidget(self.headset_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        return announcement_layout

    def create_right_layout(self, parent_widget):
        """创建右侧功能按钮布局"""
        right_layout = QHBoxLayout()
        right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)  # 优化元素间距

        # 用户信息（头像在左；右侧一列：用户名在上，VIP/钻石并列在下）
        user_widget = QWidget()
        user_widget.setObjectName("userWidget")
        user_widget.setStyleSheet("""
            #userWidget {
                background-color: transparent;
                border-radius: 8px;
                padding: 2px 8px;
            }
        """)
        user_layout = QHBoxLayout(user_widget)
        user_layout.setContentsMargins(0, 0, 0, 0)
        user_layout.setSpacing(8)
        user_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 头像（再放大一些，几乎占满导航栏高度）
        self.user_avatar_label = QLabel()
        avatar_size = max(40, parent_widget.height() - 4)
        self.user_avatar_label.setFixedSize(avatar_size, avatar_size)
        self.user_avatar_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_avatar_label.mousePressEvent = self.upload_avatar
        user_layout.addWidget(self.user_avatar_label, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 右侧信息列
        right_col = QWidget()
        right_col_layout = QVBoxLayout(right_col)
        right_col_layout.setContentsMargins(0, 0, 0, 0)
        right_col_layout.setSpacing(4)  # 优化间距
        right_col_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        # 用户名（右上）- 字体加大
        self.username_display_label = QLabel("未登录")
        self.username_display_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 15px;
                font-weight: 700;
                color: #0f172a;
                padding: 0px;
                margin: 0px;
            }
        """)
        right_col_layout.addWidget(self.username_display_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # 会员 + 钻石（右下并列）
        membership_row = QWidget()
        membership_layout = QHBoxLayout(membership_row)
        membership_layout.setContentsMargins(0, 0, 0, 0)
        membership_layout.setSpacing(8)  # VIP 和钻石之间更紧凑
        membership_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        # VIP - 优化样式
        vip_group = QHBoxLayout()
        vip_group.setContentsMargins(0, 0, 0, 0)
        vip_group.setSpacing(5)  # 优化图标和文字间距
        # VIP 图标稍微放大
        self.vip_icon = self.create_svg_widget(13, 20, 20, "margin: 0px;")
        if self.vip_icon:
            # 设置VIP图标可点击
            self.vip_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.vip_icon.mousePressEvent = lambda event: self.show_vip_dialog() if event.button() == Qt.MouseButton.LeftButton else None
            vip_group.addWidget(self.vip_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.vip_status_label = QLabel("非会员")
        self.vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 600;
                color: #1e293b;
                padding: 0px;
                margin: 0px;
            }
        """)
        # 设置VIP状态标签也可点击
        self.vip_status_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vip_status_label.mousePressEvent = lambda event: self.show_vip_dialog() if event.button() == Qt.MouseButton.LeftButton else None
        vip_group.addWidget(self.vip_status_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        membership_layout.addLayout(vip_group)

        # 钻石 - 优化样式
        diamond_group = QHBoxLayout()
        diamond_group.setContentsMargins(0, 0, 0, 0)
        diamond_group.setSpacing(4)  # 图标和数字紧挨在一起显示
        # 钻石图标稍微放大
        self.diamond_icon = self.create_svg_widget(2, 20, 20, "margin: 0px;")
        if self.diamond_icon:
            # 设置钻石图标可点击，打开钻石套餐弹窗
            self.diamond_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.diamond_icon.mousePressEvent = (
                lambda event: self.show_diamond_dialog()
                if event.button() == Qt.MouseButton.LeftButton
                else None
            )
            diamond_group.addWidget(self.diamond_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.diamond_count_label = QLabel("0")
        self.diamond_count_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 600;
                color: #1e293b;
                padding: 0px;
                margin: 0px;
            }
        """)
        # 预留更大的数字显示空间（支持 1w+ 钻石）
        self.diamond_count_label.setMinimumWidth(80)
        self.diamond_count_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # 与钻石图标紧挨显示，整体仍然靠左
        diamond_group.addWidget(self.diamond_count_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        # 在数字右侧添加伸缩空间，避免被后面的分隔线和按钮“挤回去”
        diamond_group.addStretch()
        membership_layout.addLayout(diamond_group)

        right_col_layout.addWidget(membership_row, alignment=Qt.AlignmentFlag.AlignLeft)
        user_layout.addWidget(right_col)

        # 让用户信息块可以向左扩展，占据更多空间，避免被右侧图标挤压
        from PyQt6.QtWidgets import QSizePolicy
        user_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        right_layout.addWidget(user_widget, stretch=1)

        # 初始化默认头像（资源缺失时会自动回退）
        self.update_user_avatar_display(None)

        # 添加分隔线
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setFixedHeight(24)
        separator.setStyleSheet("background-color: rgba(226, 232, 240, 0.6);")
        right_layout.addWidget(separator, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 最小化图标 - 优化样式和交互
        minimize_icon = self.create_svg_widget(7, 18, 18, "margin: 0px; padding: 4px;")
        if minimize_icon:
            minimize_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            minimize_icon.setStyleSheet("""
                QWidget {
                    border-radius: 4px;
                    padding: 4px;
                }
                QWidget:hover {
                    background-color: rgba(241, 245, 249, 0.8);
                }
            """)
            minimize_icon.mousePressEvent = self.minimize_app
            right_layout.addWidget(minimize_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 关闭图标 - 优化样式和交互
        close_icon = self.create_svg_widget(1, 18, 18, "margin: 0px; padding: 4px;")
        if close_icon:
            close_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            close_icon.setStyleSheet("""
                QWidget {
                    border-radius: 4px;
                    padding: 4px;
                }
                QWidget:hover {
                    background-color: rgba(254, 242, 242, 0.8);
                }
            """)
            close_icon.mousePressEvent = self.close_app
            right_layout.addWidget(close_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        return right_layout

    def create_chat_panel(self, parent=None):
        """创建客服聊天大面板，占据中间+右侧区域"""
        chat_panel = QWidget(parent)
        chat_panel.setObjectName("chatPanel")
        chat_panel.setStyleSheet("""
            #chatPanel {
                background-color: transparent;
            }
        """)

        # 根容器：整体包裹聊天+FAQ，右侧栏目嵌在同一个白色框内
        root_layout = QHBoxLayout(chat_panel)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        container = QWidget()
        container.setObjectName("chatContainer")
        container.setStyleSheet("""
            #chatContainer {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid rgba(226, 232, 240, 200);
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 顶部紫色标题栏（空间加大，标题改为“声音序章”）
        header = QWidget()
        header.setObjectName("chatHeader")
        header.setStyleSheet("""
            #chatHeader {
                background-color: #7c3aed;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)  # 更大的上下内边距
        header_layout.setSpacing(10)

        title_label = QLabel("声音序章")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;
                font-weight: 700;
            }
        """)
        header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        header_layout.addStretch()

        container_layout.addWidget(header)

        # 中部主体：左聊天区 + 右 FAQ（同一容器内）
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧聊天垂直布局
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 滚动区域 + 垂直布局，每条消息是一个独立的圆角气泡控件
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f4f5f7;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #f4f5f7;
            }
        """)

        self.chat_scroll_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_scroll_widget)
        self.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.chat_layout.setSpacing(8)
        self.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.chat_scroll_area.setWidget(self.chat_scroll_widget)
        left_layout.addWidget(self.chat_scroll_area, stretch=1)
        # 预生成默认客服 / 用户头像 Data URL（默认为同一张，可在更新头像时覆盖用户头像）
        self._support_avatar_url = ""
        self._user_avatar_url = ""
        default_bytes = get_default_avatar()
        if default_bytes:
            self._support_avatar_url = self._avatar_bytes_to_data_url(default_bytes)
            self._user_avatar_url = self._support_avatar_url

        # 底部输入栏（高度更大，增加附件/表情/图片按钮占位）
        input_bar = QWidget()
        input_bar.setObjectName("chatInputBar")
        input_bar.setStyleSheet("""
            #chatInputBar {
                background-color: #f8fafc;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border-top: 1px solid rgba(226, 232, 240, 180);
            }
        """)
        input_layout = QVBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 10, 12, 12)
        input_layout.setSpacing(8)

        # 工具栏：表情、图片、文件（使用 SVG 图标）
        tools_row = QHBoxLayout()
        tools_row.setContentsMargins(0, 0, 0, 0)
        tools_row.setSpacing(10)

        self.emoji_button = QPushButton()
        self._set_icon_button(self.emoji_button, 15, "表情")
        self.emoji_button.clicked.connect(self.open_emoji_menu)
        tools_row.addWidget(self.emoji_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.pic_button = QPushButton()
        self._set_icon_button(self.pic_button, 17, "发送图片")
        self.pic_button.clicked.connect(self.send_image)
        tools_row.addWidget(self.pic_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.file_button = QPushButton()
        self._set_icon_button(self.file_button, 16, "发送文件（≤100MB）")
        self.file_button.clicked.connect(self.send_file)
        tools_row.addWidget(self.file_button, alignment=Qt.AlignmentFlag.AlignLeft)

        tools_row.addStretch()
        input_layout.addLayout(tools_row)

        # 输入行
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(10)

        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("输入消息，回车或点击发送")
        self.chat_input.setFixedHeight(40)
        self.chat_input.setStyleSheet("""
            QLineEdit {
                border-radius: 20px;
                border: 1px solid rgba(203, 213, 225, 200);
                padding: 8px 14px;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                background-color: #ffffff;
            }
            QLineEdit:focus {
                border-color: #7c3aed;
            }
        """)
        self.chat_input.returnPressed.connect(self._handle_chat_send)

        send_button = QPushButton("发送")
        send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        send_button.setFixedHeight(40)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: #ffffff;
                border-radius: 20px;
                padding: 8px 20px;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
            QPushButton:pressed {
                background-color: #5b21b6;
            }
        """)
        send_button.clicked.connect(self._handle_chat_send)

        input_row.addWidget(self.chat_input, stretch=1)
        input_row.addWidget(send_button, stretch=0)
        input_layout.addLayout(input_row)

        left_layout.addWidget(input_bar)

        # 右侧常见问题栏目（嵌在同一容器内部）
        faq_container = QWidget()
        faq_container.setObjectName("faqContainer")
        faq_container.setFixedWidth(240)
        faq_container.setStyleSheet("""
            #faqContainer {
                background-color: #ffffff;
                border-left: 1px solid rgba(226, 232, 240, 200);
            }
        """)
        faq_layout = QVBoxLayout(faq_container)
        faq_layout.setContentsMargins(16, 16, 16, 16)
        faq_layout.setSpacing(12)

        faq_title = QLabel("常见问题")
        faq_title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                font-weight: 700;
                color: #1f2937;
            }
        """)
        faq_layout.addWidget(faq_title)

        self.faq_list = QTextEdit()
        self.faq_list.setReadOnly(True)
        self.faq_list.setStyleSheet("""
            QTextEdit {
                border: none;
                background-color: #ffffff;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #334155;
            }
        """)
        self.faq_list.setPlaceholderText("这里展示常见问题列表，可根据需要填充内容。")
        faq_layout.addWidget(self.faq_list, stretch=1)

        # 将聊天与 FAQ 放入同一主体
        body_layout.addLayout(left_layout, stretch=4)
        body_layout.addWidget(faq_container, stretch=1)

        container_layout.addWidget(body)
        root_layout.addWidget(container)

        return chat_panel

    def open_customer_service_chat(self, event):
        """点击顶部耳机图标时，打开客服聊天界面：将中间+右侧版块合并成一个大的聊天对话框"""
        if event.button() != Qt.MouseButton.LeftButton:
            return

        # 只初始化一次布局切换
        if getattr(self, "_chat_panel_added", False):
            self.chat_panel.setVisible(True)
            return

        # 从主布局移除中间和右侧（占原来的 3+1 比例），用一个聊天面板等效占比替换
        # 不再 setParent(None)，避免成为临时顶层窗口闪一下
        if self.merged_section2_layout:
            self.main_content_layout.removeItem(self.merged_section2_layout)
            if self.merged_section2:
                self.merged_section2.hide()
        if self.right_column_widget:
            self.main_content_layout.removeWidget(self.right_column_widget)
            self.right_column_widget.hide()

        # 聊天面板占据原中间+右侧的总宽度（保持左侧宽度不变）
        # 先放入布局再显示，避免无父级时短暂成为顶层窗口闪烁
        self.main_content_layout.addWidget(self.chat_panel, 4)
        self.chat_panel.setVisible(True)
        self._chat_panel_added = True

    def _handle_chat_send(self):
        """简单模拟发送消息，将内容追加到聊天记录中（后续可接入真实客服/机器人）"""
        text = self.chat_input.text().strip()
        if not text:
            return
        self._append_chat_message(text, from_self=True)
        self.chat_input.clear()
        # 模拟客服稍后回复
        QTimer.singleShot(600, lambda: self.append_support_message("请稍后"))

    def _append_file_message(self, filename: str, size_str: str):
        """以卡片形式追加一条用户发送的文件消息"""
        if not hasattr(self, "chat_layout"):
            return

        message_widget = QWidget()
        v_layout = QVBoxLayout(message_widget)
        v_layout.setContentsMargins(4, 0, 4, 0)
        v_layout.setSpacing(2)

        # 时间行（右对齐）
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #9ca3af;
            }
        """)
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.addStretch()
        time_row.addWidget(time_label)
        v_layout.addLayout(time_row)

        # 主行：右侧为文件卡片 + 头像
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        # 文件卡片（白底，圆角，内部左右布局）
        card = QWidget()
        card.setObjectName("fileCard")
        card.setStyleSheet("""
            #fileCard {
                background-color: #ffffff;
                border-radius: 14px;
                border: 1px solid #e5e7eb;
            }
        """)
        # 限制卡片最大宽度，避免撑满整行
        card.setMinimumWidth(200)
        card.setMaximumWidth(260)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(8)

        # 左侧：文件名 + 大小
        text_col = QVBoxLayout()
        text_col.setContentsMargins(0, 0, 0, 0)
        text_col.setSpacing(4)

        name_label = QLabel(filename)
        name_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 600;
                color: #111827;
            }
        """)
        name_label.setMinimumWidth(120)
        name_label.setMaximumWidth(200)

        size_label = QLabel(size_str)
        size_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #6b7280;
            }
        """)

        text_col.addWidget(name_label)
        text_col.addWidget(size_label)
        card_layout.addLayout(text_col, stretch=1)

        # 右侧：小文件图标块
        ext = os.path.splitext(filename)[1].lstrip(".").upper() or "FILE"
        ext = ext[:3]
        icon_bg = QWidget()
        icon_bg.setObjectName("fileIcon")
        icon_bg.setFixedSize(34, 42)
        icon_bg.setStyleSheet("""
            #fileIcon {
                background-color: #2563eb;
                border-radius: 8px;
            }
        """)
        icon_layout = QVBoxLayout(icon_bg)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel(ext)
        icon_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                font-weight: 700;
            }
        """)
        icon_layout.addWidget(icon_label)

        card_layout.addWidget(icon_bg, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 头像（右侧）
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        if self.user_avatar_label.pixmap():
            pm = self.user_avatar_label.pixmap().scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            avatar_label.setPixmap(pm)

        avatar_label.setStyleSheet("border-radius:16px;")

        row.addStretch()
        row.addWidget(card)
        row.addWidget(avatar_label)

        v_layout.addLayout(row)

        self.chat_layout.addWidget(message_widget)

        if hasattr(self, "chat_scroll_area"):
            bar = self.chat_scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _append_chat_message(self, content: str, from_self: bool = True, is_html: bool = False):
        """按左右气泡形式追加一条消息，使用真实圆角控件"""
        if not hasattr(self, "chat_layout"):
            return

        # 容器：一条完整的消息（可包含时间 + 气泡）
        message_widget = QWidget()
        v_layout = QVBoxLayout(message_widget)
        v_layout.setContentsMargins(4, 0, 4, 0)
        v_layout.setSpacing(2)

        # 用户消息：上方一行时间（右对齐）
        if from_self:
            time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            time_label = QLabel(time_str)
            time_label.setStyleSheet("""
                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 11px;
                    color: #9ca3af;
                }
            """)
            time_row = QHBoxLayout()
            time_row.setContentsMargins(0, 0, 0, 0)
            time_row.addStretch()
            time_row.addWidget(time_label)
            v_layout.addLayout(time_row)

        # 气泡 + 头像 行
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        # 头像
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        # 从当前顶部头像获取图像，缩放即可（避免重新处理字节）
        if from_self and self.user_avatar_label.pixmap():
            pm = self.user_avatar_label.pixmap().scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            avatar_label.setPixmap(pm)
        else:
            # 客服头像使用默认头像
            default_bytes = get_default_avatar()
            if default_bytes:
                pm = QPixmap()
                if pm.loadFromData(default_bytes):
                    avatar_label.setPixmap(
                        pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                    )

        if from_self:
            bubble_label = ChatBubble(
                content,
                background=QColor("#dcf8c6"),
                text_color=QColor("#0f172a"),
                max_width=420,
                align_right=True,
                rich_text=is_html,
            )
            avatar_label.setStyleSheet("""
                QLabel {
                    border-radius: 16px;
                }
            """)

            # 行布局：左侧留空，右侧气泡 + 头像
            row.addStretch()
            row.addWidget(bubble_label)
            row.addWidget(avatar_label)
        else:
            bubble_label = ChatBubble(
                content,
                background=QColor("#ffffff"),
                text_color=QColor("#111827"),
                border_color=QColor("#e5e7eb"),
                max_width=420,
                align_right=False,
                rich_text=is_html,
            )
            avatar_label.setStyleSheet("""
                QLabel {
                    border-radius: 16px;
                }
            """)

            # 行布局：左侧头像 + 气泡，右侧留空
            row.addWidget(avatar_label)
            row.addWidget(bubble_label)
            row.addStretch()

        v_layout.addLayout(row)

        self.chat_layout.addWidget(message_widget)

        # 滚动到底部
        if hasattr(self, "chat_scroll_area"):
            bar = self.chat_scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def append_support_message(self, content: str, is_html: bool = False):
        """供后续真实客服或机器人使用的接口"""
        self._append_chat_message(content, from_self=False, is_html=is_html)

    def open_emoji_menu(self):
        """弹出表情选择器：10 个一行的网格布局"""
        emojis = [
            # 常用表情
            "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😉", "😊", "😍",
            "😘", "😗", "😙", "😚", "😋", "😜", "🤪", "😝", "🤑", "🤗",
            "🤭", "🤫", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣",
            "😥", "😮", "🤐", "😯", "😪", "😫", "🥱", "😴", "😌", "😛",
            "😓", "😔", "😕", "🙃", "🫠", "😷", "🤒", "🤕", "🤢", "🤮",
            "🤧", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "😎", "🤓",
            "🧐", "😕", "😟", "🙁", "☹️", "😮‍💨", "😢", "😭", "😤", "😠",
            "😡", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👻", "👽",
        ]

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #ffffff;
                border: 1px solid #e5e7eb;
                padding: 4px;
            }
        """)

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(4, 4, 4, 4)
        grid_layout.setHorizontalSpacing(4)
        grid_layout.setVerticalSpacing(4)

        columns = 10
        for idx, e in enumerate(emojis):
            row = idx // columns
            col = idx % columns
            btn = QPushButton(e)
            btn.setFixedSize(28, 28)
            btn.setStyleSheet("""
                QPushButton {
                    border: none;
                    background: transparent;
                    font-size: 16px;
                }
                QPushButton:hover {
                    background-color: #e5e7eb;
                    border-radius: 4px;
                }
            """)
            btn.clicked.connect(lambda _, em=e: self._insert_emoji(em))
            grid_layout.addWidget(btn, row, col)

        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(grid_widget)
        menu.addAction(widget_action)

        # 让表情面板出现在按钮“上方”
        menu_size = menu.sizeHint()
        button_top_left = self.emoji_button.mapToGlobal(self.emoji_button.rect().topLeft())
        pos = QPoint(button_top_left.x(), button_top_left.y() - menu_size.height())
        menu.exec(pos)

    def _insert_emoji(self, emoji: str):
        self.chat_input.insert(emoji)

    def send_image(self):
        """选择并发送图片（内联展示），限制 100MB"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if not file_path:
            return
        size = os.path.getsize(file_path)
        if size > 100 * 1024 * 1024:
            self._append_chat_message("图片超过 100MB，未发送。", from_self=False)
            return

        # 使用 QPixmap 先缩小图片，再转为 data URL，避免在聊天框中巨幅显示
        pix = QPixmap(file_path)
        if pix.isNull():
            self._append_chat_message("图片加载失败。", from_self=False)
            return
        # 这里设置一个最大边 160，让图片清晰但不会太大
        scaled = pix.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        from PyQt6.QtCore import QBuffer, QIODevice
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        scaled.save(buffer, "PNG")
        data = base64.b64encode(buffer.data()).decode("utf-8")
        buffer.close()

        data_url = f"data:image/png;base64,{data}"
        # 仅发送图片本身，使用 HTML img 标签，气泡将自适应图片大小
        html = f'<img src="{data_url}" />'
        self._append_chat_message(html, from_self=True, is_html=True)
        # 模拟客服稍后回复
        QTimer.singleShot(600, lambda: self.append_support_message("请稍后"))

    def send_file(self):
        """发送文件，限制 100MB；展示文件名和大小"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文件", "", "All Files (*.*)"
        )
        if not file_path:
            return
        size = os.path.getsize(file_path)
        if size > 100 * 1024 * 1024:
            self._append_chat_message("文件超过 100MB，未发送。", from_self=False)
            return

        # 计算文件大小字符串（K / M）
        if size < 1024 * 1024:
            size_kb = size / 1024
            size_str = f"{size_kb:.1f} KB"
        else:
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"

        filename = os.path.basename(file_path)

        # 使用卡片形式的文件消息
        self._append_file_message(filename, size_str)
        # 模拟客服稍后回复
        QTimer.singleShot(600, lambda: self.append_support_message("请稍后"))

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

    def _set_icon_button(self, button: QPushButton, icon_id: int, tooltip: str = ""):
        """为按钮设置SVG图标样式（统一尺寸与风格）"""
        button.setToolTip(tooltip)
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

    def _bytes_to_data_url(self, data: bytes, mime: str = "image/png") -> str:
        """将二进制图片转换为 data URL，通用小工具"""
        try:
            b64 = base64.b64encode(data).decode("utf-8")
            return f"data:{mime};base64,{b64}"
        except Exception:
            return ""

    def _avatar_bytes_to_data_url(self, data: bytes, size: int = 32, mime: str = "image/png") -> str:
        """将头像二进制图片缩放到固定尺寸后再转为 data URL

        为了在 QTextEdit 中既清晰又不占太大空间，这里会生成 2×size 像素的图片，
        在 HTML 里用 width/height=size 来显示，相当于“高分辨率小图标”，减少缩小带来的模糊感。
        """
        try:
            pix = QPixmap()
            if not pix.loadFromData(data) or pix.isNull():
                return self._bytes_to_data_url(data, mime)
            target = size * 2
            scaled = pix.scaled(target, target, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            buffer = QBuffer()
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            scaled.save(buffer, "PNG")
            b64 = base64.b64encode(buffer.data()).decode("utf-8")
            buffer.close()
            return f"data:{mime};base64,{b64}"
        except Exception:
            return self._bytes_to_data_url(data, mime)

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
            self.mask_widget.setVisible(True)
            self._update_mask_geometry()
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

    def _update_mask_geometry(self):
        """让遮罩层始终覆盖 rounded_bg（解决初始化时 rounded_bg 尺寸未定导致遮罩过小的问题）"""
        if not hasattr(self, "rounded_bg") or not hasattr(self, "mask_widget"):
            return
        if not self.rounded_bg or not self.mask_widget:
            return
        # mask_widget 的父级就是 rounded_bg，因此直接用 rect 即可
        self.mask_widget.setGeometry(self.rounded_bg.rect())
        self.mask_widget.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        # 初次显示时布局才最终确定，顺手同步一次遮罩尺寸
        self._update_mask_geometry()

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
        # 更新用户ID
        self.user_id = user_id

        # 更新文本
        if username is not None:
            self.username_display_label.setText(str(username))

        vip = bool(is_vip)
        self.vip_status_label.setText("会员" if vip else "非会员")

        try:
            d = int(diamonds)
        except Exception:
            d = 0
        self.diamond_count_label.setText(str(d))

        # 更新头像（None/bytes/memoryview 都可）
        self.update_user_avatar_display(avatar_data)

    def show_vip_dialog(self):
        """显示VIP会员对话框"""
        if not self.user_id:
            # 如果用户未登录，提示先登录
            msg_box = CustomMessageBox(self)
            msg_box.setText("请先登录")
            msg_box.setWindowTitle("提示")
            msg_box.exec()
            return
        
        # 获取当前会员状态
        vip_info = self.db_manager.get_user_vip_info(self.user_id)
        is_vip = False
        if vip_info:
            is_vip = bool(vip_info.get('is_vip', False))
        
        # 创建并显示VIP对话框
        vip_dialog = VipMembershipDialog(self, user_id=self.user_id, is_vip=is_vip)
        
        # 居中显示对话框
        dialog_rect = vip_dialog.geometry()
        parent_rect = self.geometry()
        x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
        vip_dialog.move(x, y)
        
        vip_dialog.exec()

    def show_diamond_dialog(self):
        """显示钻石套餐对话框"""
        if not self.user_id:
            msg_box = CustomMessageBox(self)
            msg_box.setText("请先登录")
            msg_box.setWindowTitle("提示")
            msg_box.exec()
            return

        dialog = DiamondPackageDialog(self, user_id=self.user_id)
        dialog.exec()

    def upload_avatar(self, event):
        """上传头像"""
        if self.user_id:
            file_path, _ = QFileDialog.getOpenFileName(self, "选择头像", "", "Images (*.png *.jpg *.jpeg *.bmp)")
            if file_path:
                # 打开裁剪对话框
                crop_dialog = AvatarCropDialog(file_path, self)
                # 居中显示
                dialog_rect = crop_dialog.geometry()
                parent_rect = self.geometry()
                x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
                y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
                crop_dialog.move(x, y)
                
                if crop_dialog.exec() == QDialog.DialogCode.Accepted:
                    # 获取裁剪后的头像数据
                    avatar_data = crop_dialog.get_cropped_avatar_bytes()
                    if avatar_data:
                        if self.db_manager.update_user_avatar(self.user_id, avatar_data):
                            # 更新成功后，重新加载头像显示
                            self.update_user_avatar_display(avatar_data)
                            logging.info("头像更新成功")
                        else:
                            msg_box = CustomMessageBox(self, variant="error")
                            msg_box.setWindowTitle("更新失败")
                            msg_box.setText("头像更新失败，请稍后重试")
                            msg_box.exec()
                    else:
                        msg_box = CustomMessageBox(self, variant="error")
                        msg_box.setWindowTitle("错误")
                        msg_box.setText("无法获取裁剪后的头像")
                        msg_box.exec()
        else:
            msg_box = CustomMessageBox(self, variant="error")
            msg_box.setWindowTitle("未登录")
            msg_box.setText("请先登录后再尝试上传头像")
            msg_box.exec()

    def update_user_avatar_display(self, avatar_data):
        """更新头像显示"""
        # 允许 avatar_data 为 None / memoryview
        if not avatar_data:
            avatar_data = get_default_avatar()
        if avatar_data is None:
            # 兜底：画一个浅色圆形占位
            pm = QPixmap(self.user_avatar_label.size())
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor(241, 245, 249))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(0, 0, pm.width(), pm.height())
            painter.end()
            self.user_avatar_label.setPixmap(pm)
            return
        if isinstance(avatar_data, memoryview):
            avatar_bytes = avatar_data.tobytes()
        else:
            avatar_bytes = avatar_data

        pixmap = QPixmap()
        ok = pixmap.loadFromData(avatar_bytes)
        if not ok or pixmap.isNull():
            # 数据非法则回退默认头像
            fallback = get_default_avatar()
            if fallback and fallback is not avatar_bytes:
                pixmap = QPixmap()
                pixmap.loadFromData(fallback)
                avatar_bytes = fallback

        size = min(pixmap.width(), pixmap.height())
        if size <= 0:
            return
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
        # 同步更新聊天中使用的用户头像（缩小后用于 QTextEdit）
        try:
            self._user_avatar_url = self._avatar_bytes_to_data_url(avatar_bytes)
        except Exception:
            pass

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
        self._update_mask_geometry()


from typing import Optional


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