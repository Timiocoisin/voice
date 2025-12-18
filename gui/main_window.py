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
from PyQt6.QtCore import Qt, QEvent, QPoint, QRect, QRectF, QSize, QBuffer, QByteArray, QIODevice, QTimer, QPropertyAnimation
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QBrush, QColor, QIcon
from modules.login_dialog import LoginDialog
from modules.vip_membership_dialog import VipMembershipDialog, VipPackageDialog, DiamondPackageDialog
from backend.login.login_status_manager import check_login_status
from backend.database.database_manager import DatabaseManager
from backend.login.token_storage import  read_token, clear_token
from backend.login.token_utils import verify_token
from backend.login.login_status_manager import check_login_status, save_login_status, clear_login_status
from backend.resources import load_icon_data, load_icon_path, get_logo, get_default_avatar
from backend.customer_service.keyword_matcher import get_matcher
from backend.membership_service import MembershipService
from backend.config import texts as text_cfg
from gui.custom_message_box import CustomMessageBox
from gui.avatar_crop_dialog import AvatarCropDialog
from .marquee_label import MarqueeLabel
import logging
from backend.logging_manager import setup_logging  # noqa: F401
import random

# 导入拆分后的模块
from gui.components.chat_bubble import ChatBubble, LogoutPopup, RoundedBackgroundWidget
from gui.components.sections import create_section_widget, create_merged_section_widget, create_bottom_bar
from gui.handlers import dialog_handlers, avatar_handlers



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
        # 会员 / 钻石业务服务（复用同一个 db_manager）
        self.membership_service = MembershipService(self.db_manager)

        # 初始化用户ID
        self.user_id = None

        # 用户头像 hover 动画与退出弹窗相关变量
        self._avatar_normal_geometry = None
        self._avatar_anim = None
        self.logout_popup = None
        
        # 退出登录浮窗的延时隐藏计时器
        self._logout_timer = QTimer(self)
        self._logout_timer.setSingleShot(True)
        self._logout_timer.timeout.connect(self._really_hide_logout)

        # 初始化关键词匹配器（客服系统）
        self.keyword_matcher = get_matcher()

        self.initUI()

        # 创建登录对话框实例，但不立即显示
        self.login_dialog = LoginDialog(self)

        # 创建蒙版控件
        # 只遮罩主内容区域，避免遮罩挡住顶部 Logo / 头像等元素
        # initUI 中已创建 self.main_content_widget，这里可以直接作为父级
        self.mask_widget = QWidget(self.main_content_widget)
        self.mask_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 120);
                border-radius: 20px;
            }
        """)
        self.mask_widget.setVisible(False)

        # 检查自动登录状态
        dialog_handlers.check_auto_login(self)

        self.installEventFilter(self)

    def update_membership_info(self, avatar_data, username, is_vip, diamonds, user_id=None):
        """
        统一对外的会员信息更新接口。

        实际展示逻辑委托给 `gui.handlers.avatar_handlers.update_membership_info`，
        这样其他模块（如登录对话框、自动登录逻辑）可以统一调用
        `main_window.update_membership_info(...)` 来更新头像、用户名、会员与钻石信息。
        """
        avatar_handlers.update_membership_info(
            self,
            avatar_data,
            username,
            is_vip,
            diamonds,
            user_id=user_id,
        )

    def _update_mask_geometry(self):
        """
        更新登录遮罩层的几何位置。

        实际逻辑复用 `gui.handlers.dialog_handlers._update_mask_geometry`，
        这里仅作为 MainWindow 的实例方法包装，便于在 `showEvent` / `resizeEvent`
        等生命周期回调中直接调用 `self._update_mask_geometry()`。
        """
        dialog_handlers._update_mask_geometry(self)

    def refresh_membership_from_db(self):
        """
        从数据库重新拉取当前用户的会员与钻石信息，并刷新顶部展示。

        - 用于：自动登录、会员购买成功、钻石充值成功等场景
        - 若当前未登录（user_id 为空），则回退为“未登录 / 未开通会员 / 0 钻石”
        """
        try:
            if not self.user_id:
                # 未登录：重置为默认状态
                self.update_membership_info(None, "未登录", False, 0, None)
                return

            vip_info = self.membership_service.get_vip_info(self.user_id)
            user_row = self.db_manager.get_user_by_id(self.user_id)

            avatar_bytes = user_row.get("avatar") if user_row else None
            username = user_row.get("username") if user_row else "未登录"
            is_vip = bool(vip_info.is_vip) if vip_info else False
            diamonds = vip_info.diamonds if vip_info else 0

            self.update_membership_info(avatar_bytes, username, is_vip, diamonds, self.user_id)
        except Exception as e:
            logging.error("刷新会员信息失败：%s", e, exc_info=True)

    def _refresh_vip_tooltip(self):
        """
        根据当前 user_id 与 VIP 有效期，更新顶部 VIP 徽章的 tooltip。
        """
        if not hasattr(self, "vip_status_label"):
            return

        if not self.user_id:
            self.vip_status_label.setToolTip("未登录，暂无会员信息")
            return

        try:
            vip_info = self.membership_service.get_vip_info(self.user_id)
        except Exception as e:
            logging.error("获取 VIP 信息失败：%s", e, exc_info=True)
            self.vip_status_label.setToolTip("会员信息获取失败，请稍后重试")
            return

        if not vip_info or not vip_info.vip_expiry:
            self.vip_status_label.setToolTip("当前未开通会员")
            return

        expiry = vip_info.vip_expiry
        if expiry.year >= 2099:
            self.vip_status_label.setToolTip("已开通永久会员")
        else:
            date_str = expiry.strftime("%Y-%m-%d")
            self.vip_status_label.setToolTip(f"VIP 有效期至：{date_str}")

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
        # 还原为透明圆角背景，由外部背景图来决定视觉效果
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
        # 让顶部导航栏的下边界与中间容器的上边界紧贴在一起
        rounded_layout.addWidget(top_bar)

        # 创建主内容区域
        self.main_content_widget = QWidget()
        # 中间容器改回透明，由内部板块自身的白色卡片背景决定视觉块
        self.main_content_layout = QHBoxLayout(self.main_content_widget)
        # 顶部留白再压缩一点，让导航栏与首行版块更紧凑；
        # 底部保持适中留白，避免贴得太满
        self.main_content_layout.setContentsMargins(20, 8, 20, 15)
        self.main_content_layout.setSpacing(18)  # 优化列间距
        self.main_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 左边列：版块1和版块4垂直排列，各占一半
        self.left_column_widget = QWidget()
        left_column_layout = QVBoxLayout(self.left_column_widget)
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        # 左列上下两个版块之间的间距略微减小，使垂直视觉更紧凑、对称
        left_column_layout.setSpacing(15)

        # 版块1（左上）
        section1 = create_section_widget(0)
        # 再拉高版块高度，减少容器内部空隙
        section1.setMinimumHeight(280)
        section1_layout = QVBoxLayout()
        section1_layout.setContentsMargins(0, 0, 0, 0)
        section1_layout.addWidget(section1)
        left_column_layout.addLayout(section1_layout, 1)  # 拉伸因子1，占一半

        # 版块4（左下）
        section4 = create_section_widget(3)
        section4.setMinimumHeight(280)
        section4_layout = QVBoxLayout()
        section4_layout.setContentsMargins(0, 0, 0, 0)
        section4_layout.addWidget(section4)
        left_column_layout.addLayout(section4_layout, 1)  # 拉伸因子1，占一半

        self.main_content_layout.addWidget(self.left_column_widget, 1)  # 权重1

        # 中间列：合并后的版块2（原版块2和版块5合并）——主功能区
        self.merged_section2 = create_merged_section_widget()
        # 中间主功能区整体再拉高一些，让布局更饱满
        self.merged_section2.setMinimumHeight(560)
        self.merged_section2_layout = QVBoxLayout()
        self.merged_section2_layout.setContentsMargins(0, 0, 0, 0)
        self.merged_section2_layout.addWidget(self.merged_section2)
        self.main_content_layout.addLayout(self.merged_section2_layout, 3)  # 权重3

        # 右边列：版块3和版块6垂直排列，各占一半
        self.right_column_widget = QWidget()
        right_column_layout = QVBoxLayout(self.right_column_widget)
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        # 右列上下两个版块之间的间距与左列保持一致
        right_column_layout.setSpacing(15)

        # 版块3（右上）
        section3 = create_section_widget(2)
        section3.setMinimumHeight(280)
        section3_layout = QVBoxLayout()
        section3_layout.setContentsMargins(0, 0, 0, 0)
        section3_layout.addWidget(section3)
        right_column_layout.addLayout(section3_layout, 1)  # 拉伸因子1，占一半

        # 版块6（右下）
        section6 = create_section_widget(5)
        section6.setMinimumHeight(280)
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
        bottom_bar = create_bottom_bar()
        rounded_layout.addWidget(bottom_bar)

        main_layout.addWidget(self.rounded_bg)

    def create_top_bar(self):
        """创建顶部导航栏"""
        top_bar = QWidget()
        top_bar.setObjectName("topBar")
        # 顶部导航栏保持完全透明，不再使用底部分割线
        top_bar.setStyleSheet("""
            #topBar {
                background-color: transparent;
            }
        """)
        # 高度保持当前较高的效果
        top_bar.setFixedHeight(80)

        top_bar_layout = QHBoxLayout(top_bar)
        # 稍微增加上下内边距，让内容不贴边，看起来更精致
        top_bar_layout.setContentsMargins(18, 6, 18, 6)
        # 略微增大左右元素间距，让 Logo、公告、用户区之间更舒展
        top_bar_layout.setSpacing(20)
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

            # 调整Logo大小（整体再缩小一些）
            logo_height = int(parent_widget.height() * 1.6)
            logo_pixmap = logo_pixmap.scaled(
                logo_height * 2,  # 同步缩小宽度比例
                logo_height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            logo_label.setPixmap(logo_pixmap)
        # 略微上移一点，让整体更“贴顶”
        logo_label.setStyleSheet("margin: -4px 0 0 0; padding: 0px;")

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
        # 用一个容器包裹耳机图标和未读消息badge
        self.headset_container = QWidget()
        self.headset_container.setFixedSize(32, 32)
        self.headset_container.setStyleSheet("background: transparent;")
        
        self.headset_icon = self.create_svg_widget(9, 26, 26, "margin: 0px; opacity: 0.85;")
        if self.headset_icon:
            self.headset_icon.setParent(self.headset_container)
            self.headset_icon.move(3, 3)
            self.headset_container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self.headset_container.mousePressEvent = self.open_customer_service_chat
        
        # 未读消息 badge（默认隐藏）
        self.unread_badge = QLabel("0", self.headset_container)
        self.unread_badge.setFixedSize(18, 18)
        self.unread_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.unread_badge.move(16, -2)  # 右上角位置
        self.unread_badge.setStyleSheet("""
            QLabel {
                background-color: #ef4444;
                color: #ffffff;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 10px;
                font-weight: 700;
                border-radius: 9px;
            }
        """)
        self.unread_badge.setVisible(False)
        self.unread_count = 0  # 未读消息计数
        
        announcement_layout.addWidget(self.headset_container, alignment=Qt.AlignmentFlag.AlignVCenter)

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

        # 头像（包装在固定尺寸容器中，实现真正的原地中心放大）
        # 注意：如果头像尺寸过大，会超出顶部导航栏的高度，被下边界“截断”
        # 这里按导航栏高度的 70% 来计算头像大小，避免被遮挡
        avatar_size = int(parent_widget.height() * 0.7)
        avatar_size = max(40, avatar_size)
        self.avatar_expand_margin = 12  # 为放大预留的边距
        self.avatar_container = QWidget()
        self.avatar_container.setFixedSize(avatar_size + self.avatar_expand_margin * 2, avatar_size + self.avatar_expand_margin * 2)
        self.avatar_container.setStyleSheet("background: transparent;")
        
        self.user_avatar_label = QLabel(self.avatar_container)
        self.user_avatar_label.setFixedSize(avatar_size, avatar_size)
        # 初始居中放置
        self.user_avatar_label.move(self.avatar_expand_margin, self.avatar_expand_margin)
        self.user_avatar_label.setScaledContents(True)
        self.user_avatar_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 默认圆形 + 非会员灰色描边
        self.user_avatar_label.setStyleSheet("""
            QLabel {
                border-radius: %dpx;
                border: 2px solid rgba(148, 163, 184, 160);
            }
        """ % (avatar_size // 2))
        # 点击头像仍然可以上传头像
        self.user_avatar_label.mousePressEvent = lambda event: avatar_handlers.upload_avatar(self, event)
        # 悬停时放大并显示“退出登录”浮窗
        self.user_avatar_label.enterEvent = self._on_avatar_hover_enter
        self.user_avatar_label.leaveEvent = self._on_avatar_hover_leave
        
        user_layout.addWidget(self.avatar_container, alignment=Qt.AlignmentFlag.AlignVCenter)

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
            self.vip_icon.mousePressEvent = lambda event: dialog_handlers.show_vip_dialog(self) if event.button() == Qt.MouseButton.LeftButton else None
            vip_group.addWidget(self.vip_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.vip_status_label = QLabel("未开通会员")
        self.vip_status_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: rgba(226, 232, 240, 120);
            }
        """)
        # 设置VIP状态标签也可点击
        self.vip_status_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.vip_status_label.mousePressEvent = lambda event: dialog_handlers.show_vip_dialog(self) if event.button() == Qt.MouseButton.LeftButton else None
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
                lambda event: dialog_handlers.show_diamond_dialog(self)
                if event.button() == Qt.MouseButton.LeftButton
                else None
            )
            diamond_group.addWidget(self.diamond_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.diamond_count_label = QLabel("0 钻石")
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
        avatar_handlers.update_user_avatar_display(self, None)

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

        # 最小化按钮
        minimize_chat_btn = QPushButton("—")
        minimize_chat_btn.setFixedSize(28, 28)
        minimize_chat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        minimize_chat_btn.setToolTip("最小化聊天")
        minimize_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 700;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        minimize_chat_btn.clicked.connect(self._minimize_chat_panel)
        header_layout.addWidget(minimize_chat_btn)

        # 关闭按钮
        close_chat_btn = QPushButton("✕")
        close_chat_btn.setFixedSize(28, 28)
        close_chat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_chat_btn.setToolTip("结束聊天")
        close_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 14px;
                font-size: 14px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.8);
            }
        """)
        close_chat_btn.clicked.connect(self._close_chat_panel)
        header_layout.addWidget(close_chat_btn)

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
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(148, 163, 184, 0);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        # 悬停时显示滚动条手柄
        self.chat_scroll_area.enterEvent = lambda e: self._show_scrollbar_handle(self.chat_scroll_area)
        self.chat_scroll_area.leaveEvent = lambda e: self._hide_scrollbar_handle(self.chat_scroll_area)

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
        faq_container.setFixedWidth(280)
        faq_container.setStyleSheet("""
            #faqContainer {
                background-color: #ffffff;
                border-left: 1px solid rgba(226, 232, 240, 0.5);
            }
        """)
        faq_layout = QVBoxLayout(faq_container)
        faq_layout.setContentsMargins(14, 14, 14, 14)
        faq_layout.setSpacing(8)

        faq_title = QLabel("💡 常见问题")
        faq_title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 700;
                color: #7c3aed;
                padding-bottom: 8px;
            }
        """)
        faq_layout.addWidget(faq_title)

        # 可滚动的 FAQ 内容区域
        faq_scroll = QScrollArea()
        faq_scroll.setWidgetResizable(True)
        faq_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(148, 163, 184, 0);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        # 悬停时显示滚动条手柄
        faq_scroll.enterEvent = lambda e: self._show_scrollbar_handle(faq_scroll)
        faq_scroll.leaveEvent = lambda e: self._hide_scrollbar_handle(faq_scroll)

        faq_content = QWidget()
        faq_content_layout = QVBoxLayout(faq_content)
        faq_content_layout.setContentsMargins(0, 0, 0, 0)
        faq_content_layout.setSpacing(10)

        # FAQ 问题 1：手机能不能使用变声器？
        faq1 = self._create_faq_item(
            "📱 手机能不能使用变声器？",
            """<p style="color:#374151; margin:0 0 8px 0;">软件需要电脑运行，可转接到手机：</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>方法一</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
买转接器（如 <span style="color:#7c3aed;">直播一号</span> / <span style="color:#7c3aed;">ds7pro</span>），把声音转到手机。
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>方法二</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
用支持 OTG 的声卡（如 <span style="color:#7c3aed;">艾肯micu</span> / <span style="color:#7c3aed;">midi r2</span>），直接插上即可。
</p>"""
        )
        faq_content_layout.addWidget(faq1)

        # FAQ 问题 2：变声参数怎么设置？
        faq2 = self._create_faq_item(
            "🎛️ 变声参数怎么设置？",
            """<p style="color:#374151; margin:0 0 8px 0;">参数：<b>音调、音量、延迟、阈值</b></p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>音调</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
男→女：<span style="color:#7c3aed;">10~14</span><br/>
女→男：<span style="color:#7c3aed;">-14~-10</span><br/>
同性：<span style="color:#7c3aed;">0 左右</span>
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>音量</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
不要太高，易爆音失真<br/>
建议 <span style="color:#7c3aed;">0.5 左右</span>
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>延迟</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
一般 <span style="color:#7c3aed;">0.5~0.7</span><br/>
配置好可压低到 <span style="color:#7c3aed;">0.3</span><br/>
打游戏时适当调高
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>阈值</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
默认 <span style="color:#7c3aed;">-60</span><br/>
环境吵选 <span style="color:#7c3aed;">-57</span> 减少噪音
</p>"""
        )
        faq_content_layout.addWidget(faq2)

        # FAQ 问题 3：虚拟声卡安装
        faq3 = self._create_faq_item_with_images(
            "🔊 如何安装虚拟声卡？",
            """<p style="color:#374151; margin:0 0 8px 0;"><b>步骤：</b></p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>打开设置中心，安装虚拟声卡</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
点击虚拟声卡，一键安装后，打开声音设置。<br/>
确保系统声音中：<br/>
• 默认播放：<span style="color:#7c3aed;">耳机</span><br/>
• 默认录制：<span style="color:#7c3aed;">幻音麦克风</span>
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>设置幻音麦克风</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
需要设置采样和监听：<br/>
• 不设置采样 → 无法变声<br/>
• 不设置监听 → 听不到效果
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>对齐采样 48000</b>（点击图片放大）</p>""",
            [("resources/images/play.png", "采样设置")],
            """<p style="margin:8px 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>监听设置</b>（不想听可去掉）</p>""",
            [("resources/images/monitor.png", "监听设置")],
            """<p style="margin:8px 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>无法直接安装？</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
找到安装目录：<br/>
<span style="color:#7c3aed;">\\resources\\server\\driver</span><br/>
右键管理员运行 <span style="color:#7c3aed;">Setup.exe</span>
</p>"""
        )
        faq_content_layout.addWidget(faq3)

        faq_content_layout.addStretch()
        faq_scroll.setWidget(faq_content)
        faq_layout.addWidget(faq_scroll, stretch=1)

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

        # 未登录时，引导用户先登录，再联系客服
        if not self.user_id:
            msg_box = CustomMessageBox(self, variant="warning")
            msg_box.setWindowTitle("请先登录")
            msg_box.setText("登录后即可联系客服为你处理问题。")
            msg_box.exec()
            # 顺便弹出登录框
            dialog_handlers.show_login_dialog(self)
            return

        # 清除未读消息计数
        self._clear_unread_count()

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

    def _minimize_chat_panel(self):
        """最小化聊天面板（隐藏但保留聊天记录）"""
        if hasattr(self, "chat_panel") and self.chat_panel:
            self.chat_panel.setVisible(False)
            self._chat_minimized = True

    def _close_chat_panel(self):
        """关闭聊天面板（结束聊天服务，清空聊天记录）"""
        if hasattr(self, "chat_panel") and self.chat_panel:
            self.chat_panel.setVisible(False)
            # 清空聊天记录
            if hasattr(self, "chat_layout"):
                while self.chat_layout.count():
                    item = self.chat_layout.takeAt(0)
                    widget = item.widget()
                    if widget:
                        widget.deleteLater()
            # 重置状态
            self._chat_minimized = False
            self._clear_unread_count()
            
            # 恢复原来的布局：移除聊天面板，重新按「左列 + 中列 + 右列」顺序添加
            if getattr(self, "_chat_panel_added", False):
                # 1. 从布局中移除聊天面板以及中右列（如果存在），避免重复或顺序错乱
                self.main_content_layout.removeWidget(self.chat_panel)
                if self.merged_section2_layout:
                    self.main_content_layout.removeItem(self.merged_section2_layout)
                if self.right_column_widget:
                    self.main_content_layout.removeWidget(self.right_column_widget)

                # 2. 确保左列在布局中（理论上一直存在，这里做一次兜底）
                if self.left_column_widget and self.main_content_layout.indexOf(self.left_column_widget) == -1:
                    self.main_content_layout.addWidget(self.left_column_widget, 1)

                # 3. 按最初顺序重新添加：左列(1) + 中列(3) + 右列(1)
                if self.merged_section2_layout:
                    self.main_content_layout.addLayout(self.merged_section2_layout, 3)
                    if self.merged_section2:
                        self.merged_section2.show()

                if self.right_column_widget:
                    self.main_content_layout.addWidget(self.right_column_widget, 1)
                    self.right_column_widget.show()

                # 4. 重置标志，以便下次打开时可以重新添加
                self._chat_panel_added = False

    def _add_unread_count(self):
        """增加未读消息计数（聊天面板隐藏时调用）"""
        if not hasattr(self, "unread_count"):
            self.unread_count = 0
        self.unread_count += 1
        self._update_unread_badge()

    def _clear_unread_count(self):
        """清除未读消息计数"""
        self.unread_count = 0
        self._update_unread_badge()

    def _update_unread_badge(self):
        """更新未读消息 badge 显示"""
        if not hasattr(self, "unread_badge"):
            return
        if self.unread_count <= 0:
            self.unread_badge.setVisible(False)
        else:
            self.unread_badge.setVisible(True)
            if self.unread_count > 10:
                self.unread_badge.setText("...")
            else:
                self.unread_badge.setText(str(self.unread_count))

    def _handle_chat_send(self):
        """发送消息并使用关键词匹配生成客服回复"""
        text = self.chat_input.text().strip()
        if not text:
            return
        self._append_chat_message(text, from_self=True)
        self.chat_input.clear()
        
        # 使用关键词匹配生成回复
        reply = self.keyword_matcher.generate_reply(text, add_greeting=True)
        
        # 模拟客服回复延迟（0.5-1.5秒，让对话更自然）
        delay = random.randint(500, 1500)
        QTimer.singleShot(delay, lambda: self.append_support_message(reply))

    def _append_file_message(self, filename: str, size_str: str, from_self: bool = True):
        """以卡片形式追加一条文件消息（用户或客服）"""
        if not hasattr(self, "chat_layout"):
            return

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

        # 主行：文件卡片 + 头像
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

        # 头像
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        if from_self:
            if self.user_avatar_label.pixmap():
                pm = self.user_avatar_label.pixmap().scaled(
                    32, 32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                avatar_label.setPixmap(pm)
        else:
            # 客服头像
            default_bytes = get_default_avatar()
            if default_bytes:
                pm = QPixmap()
                pm.loadFromData(default_bytes)
                pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                # 裁剪成圆形
                cropped = QPixmap(32, 32)
                cropped.fill(Qt.GlobalColor.transparent)
                p = QPainter(cropped)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                clip_path = QPainterPath()
                clip_path.addEllipse(0, 0, 32, 32)
                p.setClipPath(clip_path)
                p.drawPixmap(0, 0, pm)
                p.end()
                avatar_label.setPixmap(cropped)

        avatar_label.setStyleSheet("border-radius:16px;")

        if from_self:
            row.addStretch()
            row.addWidget(card)
            row.addWidget(avatar_label)
        else:
            row.addWidget(avatar_label)
            row.addWidget(card)
            row.addStretch()

        v_layout.addLayout(row)

        self.chat_layout.addWidget(message_widget)

        if hasattr(self, "chat_scroll_area"):
            bar = self.chat_scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _append_chat_message(self, content: str, from_self: bool = True, is_html: bool = False, streaming: bool = False):
        """按左右气泡形式追加一条消息，使用真实圆角控件

        Args:
            content: 文本内容
            from_self: 是否为用户自己发送
            is_html: 是否为富文本
            streaming: 是否启用“打字机式”流式展示（仅对客服消息生效）
        """
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

        # 如果是客服消息且开启了流式展示，则启动“打字机”效果
        if streaming and not from_self and not is_html and isinstance(bubble_label, ChatBubble):
            self._start_streaming_text(bubble_label, content)

        # 滚动到底部
        if hasattr(self, "chat_scroll_area"):
            bar = self.chat_scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _start_streaming_text(self, bubble: "ChatBubble", full_text: str, interval_ms: int = 30):
        """让气泡中的文本以打字机形式逐字出现"""
        if not full_text:
            return

        # 先清空文本
        bubble.label.setText("")

        state = {"i": 0}
        timer = QTimer(bubble)
        timer.setInterval(interval_ms)

        def on_timeout():
            i = state["i"]
            if i >= len(full_text):
                timer.stop()
                timer.deleteLater()
                return
            i += 1
            state["i"] = i
            bubble.label.setText(full_text[:i])

            # 每次更新后，确保滚动条始终在底部
            if hasattr(self, "chat_scroll_area"):
                bar = self.chat_scroll_area.verticalScrollBar()
                bar.setValue(bar.maximum())

        timer.timeout.connect(on_timeout)
        timer.start()

    def append_support_message(self, content: str, is_html: bool = False):
        """供后续真实客服或机器人使用的接口"""
        # HTML 富文本暂时不做流式，避免标签被截断导致显示异常
        streaming = not is_html
        self._append_chat_message(content, from_self=False, is_html=is_html, streaming=streaming)
        # 如果聊天面板隐藏，增加未读消息计数
        if hasattr(self, "chat_panel") and not self.chat_panel.isVisible():
            self._add_unread_count()

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

    def _show_scrollbar_handle(self, scroll_area: QScrollArea):
        """鼠标进入时显示滚动条手柄（不改变宽度，只改变透明度）"""
        style = scroll_area.styleSheet()
        style = style.replace(
            "background: rgba(148, 163, 184, 0);",
            "background: rgba(148, 163, 184, 0.6);"
        )
        scroll_area.setStyleSheet(style)

    def _hide_scrollbar_handle(self, scroll_area: QScrollArea):
        """鼠标离开时隐藏滚动条手柄（不改变宽度，只改变透明度）"""
        style = scroll_area.styleSheet()
        style = style.replace(
            "background: rgba(148, 163, 184, 0.6);",
            "background: rgba(148, 163, 184, 0);"
        )
        scroll_area.setStyleSheet(style)

    def _create_faq_item(self, question: str, answer: str) -> QWidget:
        """创建一个无边框的 FAQ 问答条目"""
        item = QWidget()
        item.setStyleSheet("background-color: transparent;")

        item_layout = QVBoxLayout(item)
        item_layout.setContentsMargins(0, 0, 0, 10)
        item_layout.setSpacing(6)

        # 问题标题
        q_label = QLabel(question)
        q_label.setWordWrap(True)
        q_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                font-weight: 700;
                color: #1e293b;
                background-color: rgba(124, 58, 237, 0.08);
                padding: 6px 8px;
                border-radius: 6px;
            }
        """)
        item_layout.addWidget(q_label)

        # 答案内容（支持 HTML 富文本）
        a_label = QLabel()
        a_label.setWordWrap(True)
        a_label.setTextFormat(Qt.TextFormat.RichText)
        a_label.setText(answer)
        a_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #475569;
                padding: 4px 6px;
                line-height: 1.5;
            }
        """)
        item_layout.addWidget(a_label)

        return item

    def _create_faq_item_with_images(
        self, question: str, text1: str, images1: list,
        text2: str = "", images2: list = None, text3: str = ""
    ) -> QWidget:
        """创建一个带图片的 FAQ 问答条目，图片可点击放大"""
        item = QWidget()
        item.setStyleSheet("background-color: transparent;")

        item_layout = QVBoxLayout(item)
        item_layout.setContentsMargins(0, 0, 0, 10)
        item_layout.setSpacing(6)

        # 问题标题
        q_label = QLabel(question)
        q_label.setWordWrap(True)
        q_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                font-weight: 700;
                color: #1e293b;
                background-color: rgba(124, 58, 237, 0.08);
                padding: 6px 8px;
                border-radius: 6px;
            }
        """)
        item_layout.addWidget(q_label)

        # 第一段文字
        if text1:
            label1 = QLabel()
            label1.setWordWrap(True)
            label1.setTextFormat(Qt.TextFormat.RichText)
            label1.setText(text1)
            label1.setStyleSheet("""
                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 11px;
                    color: #475569;
                    padding: 4px 6px;
                }
            """)
            item_layout.addWidget(label1)

        # 第一组图片
        if images1:
            for img_path, img_title in images1:
                img_widget = self._create_clickable_image(img_path, img_title)
                if img_widget:
                    item_layout.addWidget(img_widget)

        # 第二段文字
        if text2:
            label2 = QLabel()
            label2.setWordWrap(True)
            label2.setTextFormat(Qt.TextFormat.RichText)
            label2.setText(text2)
            label2.setStyleSheet("""
                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 11px;
                    color: #475569;
                    padding: 4px 6px;
                }
            """)
            item_layout.addWidget(label2)

        # 第二组图片
        if images2:
            for img_path, img_title in images2:
                img_widget = self._create_clickable_image(img_path, img_title)
                if img_widget:
                    item_layout.addWidget(img_widget)

        # 第三段文字
        if text3:
            label3 = QLabel()
            label3.setWordWrap(True)
            label3.setTextFormat(Qt.TextFormat.RichText)
            label3.setText(text3)
            label3.setStyleSheet("""
                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 11px;
                    color: #475569;
                    padding: 4px 6px;
                }
            """)
            item_layout.addWidget(label3)

        return item

    def _create_clickable_image(self, img_path: str, title: str) -> QWidget:
        """创建一个可点击放大的图片控件"""
        # 尝试加载图片
        full_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), img_path)
        if not os.path.exists(full_path):
            # 如果相对路径不存在，尝试直接使用
            full_path = img_path
            if not os.path.exists(full_path):
                return None

        pixmap = QPixmap(full_path)
        if pixmap.isNull():
            return None

        # 缩略图容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(6, 4, 6, 4)
        container_layout.setSpacing(4)

        # 缩略图（最大宽度 200，保持比例）
        thumb = pixmap.scaled(
            200, 120,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        img_label = QLabel()
        img_label.setPixmap(thumb)
        img_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        img_label.setStyleSheet("""
            QLabel {
                border: 1px solid #e5e7eb;
                border-radius: 6px;
                padding: 2px;
                background-color: #f8fafc;
            }
            QLabel:hover {
                border-color: #7c3aed;
            }
        """)
        img_label.setToolTip(f"点击查看大图：{title}")

        # 点击事件 - 放大图片
        img_label.mousePressEvent = lambda event, p=full_path, t=title: self._show_image_popup(p, t)
        container_layout.addWidget(img_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # 图片标题
        title_label = QLabel(f"📷 {title}")
        title_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 10px;
                color: #64748b;
                padding-left: 2px;
            }
        """)
        container_layout.addWidget(title_label)

        return container

    def _show_image_popup(self, img_path: str, title: str):
        """显示图片放大弹窗"""
        pixmap = QPixmap(img_path)
        if pixmap.isNull():
            return

        # 创建弹窗对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dialog.setModal(True)

        # 主布局
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 背景容器（带圆角和阴影）
        bg_widget = QWidget()
        bg_widget.setObjectName("imagePopupBg")
        bg_widget.setStyleSheet("""
            #imagePopupBg {
                background-color: #ffffff;
                border-radius: 12px;
                border: 1px solid #e5e7eb;
            }
        """)
        bg_layout = QVBoxLayout(bg_widget)
        bg_layout.setContentsMargins(12, 12, 12, 12)
        bg_layout.setSpacing(8)

        # 标题栏
        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel(f"📷 {title}")
        title_lbl.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 600;
                color: #1e293b;
            }
        """)
        header.addWidget(title_lbl)
        header.addStretch()

        # 关闭按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f1f5f9;
                border: none;
                border-radius: 14px;
                font-size: 14px;
                color: #64748b;
            }
            QPushButton:hover {
                background-color: #fee2e2;
                color: #dc2626;
            }
        """)
        close_btn.clicked.connect(dialog.close)
        header.addWidget(close_btn)

        bg_layout.addLayout(header)

        # 图片（按屏幕大小缩放，最大 80% 屏幕尺寸）
        screen = QApplication.primaryScreen().size()
        max_w = int(screen.width() * 0.7)
        max_h = int(screen.height() * 0.7)

        scaled = pixmap.scaled(
            max_w, max_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        img_label = QLabel()
        img_label.setPixmap(scaled)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setStyleSheet("""
            QLabel {
                border-radius: 8px;
            }
        """)
        bg_layout.addWidget(img_label)

        # 提示文字
        hint = QLabel("点击任意位置关闭")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #94a3b8;
                padding-top: 4px;
            }
        """)
        bg_layout.addWidget(hint)

        layout.addWidget(bg_widget)

        # 点击任意位置关闭
        dialog.mousePressEvent = lambda event: dialog.close()

        # 调整对话框大小并居中
        dialog.adjustSize()
        dialog_rect = dialog.geometry()
        parent_rect = self.geometry()
        x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
        y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
        dialog.move(x, y)

        # 添加阴影
        shadow = QGraphicsDropShadowEffect(bg_widget)
        shadow.setBlurRadius(30)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 60))
        bg_widget.setGraphicsEffect(shadow)

        dialog.exec()

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

        # 发送图片消息（不带气泡）
        self._append_image_message(scaled, from_self=True)
        # 模拟客服回复（图片消息使用默认回复）
        reply = self.keyword_matcher.generate_reply("图片", add_greeting=True)
        delay = random.randint(500, 1500)
        QTimer.singleShot(delay, lambda: self.append_support_message(reply))

    def _append_image_message(self, pixmap: QPixmap, from_self: bool = True):
        """发送图片消息，不使用气泡，直接显示圆角图片 + 头像"""
        if not hasattr(self, "chat_layout"):
            return

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

        # 主行：图片 + 头像
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        # 创建圆角图片 Label
        img_label = QLabel()
        img_label.setFixedSize(pixmap.width(), pixmap.height())
        # 绘制圆角图片
        rounded_pix = QPixmap(pixmap.size())
        rounded_pix.fill(Qt.GlobalColor.transparent)
        painter = QPainter(rounded_pix)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, pixmap.width(), pixmap.height()), 12, 12)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()
        img_label.setPixmap(rounded_pix)

        # 头像
        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        if from_self:
            if self.user_avatar_label.pixmap():
                pm = self.user_avatar_label.pixmap().scaled(
                    32, 32,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                avatar_label.setPixmap(pm)
        else:
            # 客服头像
            default_bytes = get_default_avatar()
            if default_bytes:
                pm = QPixmap()
                pm.loadFromData(default_bytes)
                pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                # 裁剪成圆形
                cropped = QPixmap(32, 32)
                cropped.fill(Qt.GlobalColor.transparent)
                p = QPainter(cropped)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                clip_path = QPainterPath()
                clip_path.addEllipse(0, 0, 32, 32)
                p.setClipPath(clip_path)
                p.drawPixmap(0, 0, pm)
                p.end()
                avatar_label.setPixmap(cropped)

        avatar_label.setStyleSheet("border-radius: 16px;")

        if from_self:
            row.addStretch()
            row.addWidget(img_label)
            row.addWidget(avatar_label)
        else:
            row.addWidget(avatar_label)
            row.addWidget(img_label)
            row.addStretch()

        v_layout.addLayout(row)
        self.chat_layout.addWidget(message_widget)

        if hasattr(self, "chat_scroll_area"):
            bar = self.chat_scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

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
        # 模拟客服回复（文件消息使用默认回复）
        reply = self.keyword_matcher.generate_reply("文件", add_greeting=True)
        delay = random.randint(500, 1500)
        QTimer.singleShot(delay, lambda: self.append_support_message(reply))

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

        # 重新定位“退出登录”浮窗
        self._update_logout_popup_position()

    # ---------------- 用户头像 hover & 退出登录 ----------------

    def _on_avatar_hover_enter(self, event):
        """鼠标移入头像：原地中心放大动画（模拟向用户凸起） + 显示退出按钮"""
        # 停止隐藏计时器
        if hasattr(self, "_logout_timer"):
            self._logout_timer.stop()

        # 记录初始 geometry
        if self._avatar_normal_geometry is None:
            self._avatar_normal_geometry = self.user_avatar_label.geometry()

        # 目标 geometry：原地向四周均匀扩展
        normal = self._avatar_normal_geometry
        scale_px = 10  # 稍微加大，体现“凸起”感
        target = QRect(
            normal.x() - scale_px, 
            normal.y() - scale_px, 
            normal.width() + scale_px * 2, 
            normal.height() + scale_px * 2
        )

        # 动画：原地放大
        if self._avatar_anim is not None:
            self._avatar_anim.stop()
        self._avatar_anim = QPropertyAnimation(self.user_avatar_label, b"geometry", self)
        self._avatar_anim.setDuration(200)
        self._avatar_anim.setStartValue(self.user_avatar_label.geometry())
        self._avatar_anim.setEndValue(target)
        self._avatar_anim.start()
        
        # 添加更深更散的阴影，模拟 3D 悬浮高度
        shadow = QGraphicsDropShadowEffect(self.user_avatar_label)
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 5) # 稍微向下偏移，模拟光源在上方，增强凸起感
        shadow.setColor(QColor(0, 0, 0, 90))
        self.user_avatar_label.setGraphicsEffect(shadow)

        # 提升层级
        self.user_avatar_label.raise_()

        # 创建并显示带尖角的退出浮窗
        if self.logout_popup is None:
            self.logout_popup = LogoutPopup(self, main_window=self)
            self.logout_popup.button.clicked.connect(self._handle_logout_click)

        self._update_logout_popup_position()
        self.logout_popup.show()
        self.logout_popup.raise_()

        if event is not None:
            event.accept()

    def _on_avatar_hover_leave(self, event):
        """鼠标移出头像：启动延时隐藏，并开始回缩动画"""
        # 启动延时隐藏计时器
        if hasattr(self, "_logout_timer"):
            self._logout_timer.start(200) # 给用户 200ms 的操作缓冲

        if self._avatar_normal_geometry is None:
            return

        # 开始回缩动画
        if self._avatar_anim is not None:
            self._avatar_anim.stop()
        self._avatar_anim = QPropertyAnimation(self.user_avatar_label, b"geometry", self)
        self._avatar_anim.setDuration(200)
        self._avatar_anim.setStartValue(self.user_avatar_label.geometry())
        self._avatar_anim.setEndValue(self._avatar_normal_geometry)
        self._avatar_anim.start()

        # 移除阴影效果由 _really_hide_logout 统一处理，或者在这里先弱化
        # 为了动画连贯，我们保留阴影直到完全回缩或彻底隐藏
        
        if event is not None:
            event.accept()

    def _really_hide_logout(self):
        """真正执行隐藏逻辑：隐藏浮窗并重置头像效果"""
        # 如果鼠标现在正在浮窗或者头像容器上，则不隐藏
        # 这是一个双重保险
        cursor_pos = QCursor.pos()
        
        # 检查是否在头像容器上
        container_global_pos = self.avatar_container.mapToGlobal(QPoint(0, 0))
        container_rect = QRect(container_global_pos, self.avatar_container.size())
        
        # 检查是否在浮窗上
        popup_rect = QRect()
        if self.logout_popup and self.logout_popup.isVisible():
            popup_global_pos = self.logout_popup.mapToGlobal(QPoint(0, 0))
            popup_rect = QRect(popup_global_pos, self.logout_popup.size())

        if container_rect.contains(cursor_pos) or popup_rect.contains(cursor_pos):
            return

        # 执行隐藏和重置
        if self.logout_popup:
            self.logout_popup.hide()
        
        # 确保头像完全回缩并移除特效
        self.user_avatar_label.setGraphicsEffect(None)
        if self._avatar_normal_geometry:
            self.user_avatar_label.setGeometry(self._avatar_normal_geometry)

    def _update_logout_popup_position(self):
        """根据头像容器位置，更新带尖角退出浮窗的位置"""
        if not self.logout_popup or not self.avatar_container:
            return

        # 使用容器在主窗口中的坐标作为基准
        container_pos = self.avatar_container.mapTo(self, QPoint(0, 0))
        
        self.logout_popup.adjustSize()
        popup_w = self.logout_popup.width()
        
        # X 轴居中对齐容器
        # 注意：由于容器现在比头像大，我们需要对准容器的中心
        x = container_pos.x() + (self.avatar_container.width() - popup_w) // 2
        # Y 轴放在容器下方，减去一点边距让尖角更贴合头像
        y = container_pos.y() + self.avatar_container.height() - self.avatar_expand_margin - 2
        
        self.logout_popup.move(x, y)

    def _handle_logout_click(self):
        """处理退出登录：清除 token、重置 UI 并返回登录界面"""
        # 清除本地 token
        try:
            clear_token()
        except Exception:
            pass

        # 清除内存中的登录状态
        try:
            clear_login_status()
        except Exception:
            pass

        # 重置当前窗口中的用户 ID
        self.user_id = None

        # 重置会员/用户显示
        avatar_handlers.update_membership_info(self, None, "未登录", False, 0, user_id=None)

        # 隐藏退出浮窗
        if self.logout_popup:
            self.logout_popup.hide()

        # 弹出登录对话框
        dialog_handlers.show_login_dialog(self)
