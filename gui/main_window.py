# 文件 1：main_window.py
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect, QGridLayout,
    QFileDialog, QDialog
)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent, QPoint, QByteArray, QRectF
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QBrush, QColor
from modules.login_dialog import LoginDialog
from modules.vip_membership_dialog import VipMembershipDialog, VipPackageDialog, DiamondPackageDialog
from backend.login.login_status_manager import check_login_status
from backend.database.database_manager import DatabaseManager
from backend.login.token_storage import  read_token
from backend.login.token_utils import verify_token
from backend.login.login_status_manager import check_login_status, save_login_status
from backend.resources import load_icon_data, get_logo, get_default_avatar
from gui.custom_message_box import CustomMessageBox
from gui.avatar_crop_dialog import AvatarCropDialog
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
        main_content_widget = QWidget()
        main_content_layout = QHBoxLayout(main_content_widget)
        main_content_layout.setContentsMargins(20, 15, 20, 15)  # 优化边距，给内容更多空间
        main_content_layout.setSpacing(18)  # 优化列间距
        main_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 左边列：版块1和版块4垂直排列，各占一半
        left_column_widget = QWidget()
        left_column_layout = QVBoxLayout(left_column_widget)
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

        main_content_layout.addWidget(left_column_widget, 1)  # 权重1

        # 中间列：合并后的版块2（原版块2和版块5合并）
        merged_section2 = self.create_merged_section_widget()
        merged_section2.setMinimumHeight(460)  # 设置最小高度，跨越两行（220 + 220 + 间距）
        merged_section2_layout = QVBoxLayout()
        merged_section2_layout.setContentsMargins(0, 0, 0, 0)
        merged_section2_layout.addWidget(merged_section2)
        main_content_layout.addLayout(merged_section2_layout, 3)  # 权重3

        # 右边列：版块3和版块6垂直排列，各占一半
        right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(right_column_widget)
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

        main_content_layout.addWidget(right_column_widget, 1)  # 权重1

        rounded_layout.addWidget(main_content_widget, stretch=1)

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
        top_bar.setFixedHeight(40)  # 调整顶部导航栏高度，使其更紧凑

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
        speaker_icon = self.create_svg_widget(10, 18, 18, "margin: 0px; opacity: 0.7;")
        if speaker_icon:
            container_layout.addWidget(speaker_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 从数据库获取公告文本
        announcement_text = self.db_manager.get_latest_announcement()
        if not announcement_text:
            announcement_text = "欢迎使用《声音序章》软件！！！"

        # 公告标签 - 移除背景样式，因为背景已经在容器上
        announcement_label = QLabel(announcement_text)
        announcement_label.setObjectName("announcementLabel")
        announcement_label.setStyleSheet("""
            #announcementLabel {
                background: transparent;
                padding: 0px;
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 13px;  
                font-weight: 500;
                color: #475569;
            }
        """)
        announcement_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        announcement_label.setWordWrap(False)
        container_layout.addWidget(announcement_label, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 添加公告容器到布局
        announcement_layout.addWidget(announcement_container, alignment=Qt.AlignmentFlag.AlignVCenter)

        # 客服按钮（耳机图标）- 放在公告容器外面
        headset_icon = self.create_svg_widget(9, 18, 18, "margin: 0px; opacity: 0.7;")
        if headset_icon:
            announcement_layout.addWidget(headset_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

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
        avatar_size = max(32, parent_widget.height() - 4)
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

        # 用户名（右上）
        self.username_display_label = QLabel("未登录")
        self.username_display_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "Roboto", "Arial";
                font-size: 13px;
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
        self.vip_icon = self.create_svg_widget(13, 18, 18, "margin: 0px;")
        if self.vip_icon:
            # 设置VIP图标可点击
            self.vip_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.vip_icon.mousePressEvent = lambda event: self.show_vip_dialog() if event.button() == Qt.MouseButton.LeftButton else None
            vip_group.addWidget(self.vip_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.vip_status_label = QLabel("非会员")
        self.vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
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
        self.diamond_icon = self.create_svg_widget(2, 18, 18, "margin: 0px;")
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
                font-size: 13px;
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
        # 会员/非会员颜色统一为深灰色
        self.vip_status_label.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
                color: #1e293b;
                padding: 0px;
                margin: 0px;
            }}
        """)

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
            avatar_data = avatar_data.tobytes()

        pixmap = QPixmap()
        ok = pixmap.loadFromData(avatar_data)
        if not ok or pixmap.isNull():
            # 数据非法则回退默认头像
            fallback = get_default_avatar()
            if fallback and fallback is not avatar_data:
                pixmap = QPixmap()
                pixmap.loadFromData(fallback)

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