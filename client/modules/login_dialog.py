from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QLineEdit, QSpacerItem, QSizePolicy, QWidget,
                                QGraphicsDropShadowEffect)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent, QByteArray, QPropertyAnimation, QRect, QEasingCurve, QTimer
from PyQt6.QtGui import QCursor, QPainter, QColor, QPixmap, QImage, QPainterPath, QKeyEvent
from gui.clickable_label import ClickableLabel
from modules.agreement_dialog import AgreementDialog
from client.validation.validator import validate_email, validate_password
from client.timer.timer_manager import TimerManager
from gui.custom_message_box import CustomMessageBox
from client.config import texts as text_cfg
from client.resources import load_icon_data
from gui.styles.login_styles import (
    LOGIN_CARD_STYLE,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
)
from client.api_client import (
    send_verification_code as api_send_verification_code,
    register_user as api_register_user,
    login_user as api_login_user,
    check_token as api_check_token,
)
from client.login.token_utils import verify_token
from client.login.token_storage import save_token, read_token
from client.login.login_status_manager import save_login_status
import logging
from client.logging_manager import setup_logging  # noqa: F401


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        parent_width = parent.width()
        parent_height = parent.height()
        self.original_width = int(parent_width * 0.3)
        self.original_height = min(int(parent_height * 0.5), parent_height - 40)
        self.resize(self.original_width, self.original_height)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.agreement_dialog = None
        # 默认当前模式改为“注册”，让首次打开对话框时优先展示注册页
        self.current_mode = "register"

        main_layout = QVBoxLayout(self)
        # 给阴影留出空间
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_widget.setObjectName("loginCard")
        # 统一使用样式配置中的卡片样式，便于全局风格管理
        content_widget.setStyleSheet(LOGIN_CARD_STYLE)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 16)
        shadow.setColor(QColor(0, 0, 0, 50))
        content_widget.setGraphicsEffect(shadow)

        content_layout = QVBoxLayout(content_widget)
        # 使用相对宽松的边距，保持卡片简洁
        content_layout.setContentsMargins(48, 48, 48, 40)
        content_layout.setSpacing(20)

        # 统一输入控件高度（用于对齐“输入框 + 按钮”）
        field_height = 50
        row_bg_style = "background-color: transparent;"
        # 统一图标容器宽度，确保所有输入框左侧对齐
        icon_container_width = 24
        icon_spacing = 12

        # 头部容器，包含“用户登录 / 用户注册”标题和滑动下划线
        header_widget = QWidget()
        # 固定高度为滑动线预留空间
        header_widget.setFixedHeight(64)
        header_widget_layout = QVBoxLayout(header_widget)
        header_widget_layout.setContentsMargins(0, 0, 0, 0)
        header_widget_layout.setSpacing(0)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(24)

        # 用户注册标签（主标题，放在左侧）
        self.user_register_label = QLabel("用户注册")
        # 只保留文字样式，不再使用 border-bottom，下划线交给 underline_widget 实现
        self.user_register_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
            font-size: 24px;
            font-weight: 700;
            color: #1d4ed8;
            letter-spacing: 1px;
            padding: 4px 0px 10px 0px;
            background: transparent;
        """)
        self.user_register_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_register_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_register_label.mousePressEvent = lambda event: self.switch_mode("register")
        header_layout.addWidget(self.user_register_label)

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        header_layout.addItem(spacer)

        # 用户登录标签（主标题，放在右侧）
        self.user_login_label = QLabel("用户登录")
        self.user_login_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
            font-size: 24px;
            font-weight: 600;
            color: #9ca3af;
            letter-spacing: 1px;
            padding: 4px 0px 10px 0px;
            background: transparent;
        """)
        self.user_login_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_login_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_login_label.mousePressEvent = lambda event: self.switch_mode("login")
        header_layout.addWidget(self.user_login_label)

        # 预先计算两端标签的最大宽度，保持下划线宽度恒定，避免视觉上“一段一段”变化
        self._tab_underline_width = max(
            self.user_login_label.sizeHint().width(),
            self.user_register_label.sizeHint().width(),
        )

        # 将标题行放入顶部容器
        header_widget_layout.addLayout(header_layout)

        # 创建可动画的下划线条，初始几何在界面显示后设置
        self.underline_widget = QWidget(header_widget)
        # 稍微加粗一点，配合慢速动画更顺滑
        self.underline_widget.setFixedHeight(4)
        self.underline_widget.setStyleSheet("""
            background-color: #3b82f6;
            border-radius: 2px;
        """)
        self.underline_widget.hide()

        # 下划线动画（几何动画：x + 宽度）
        self.underline_animation = QPropertyAnimation(self.underline_widget, b"geometry")
        # 接近线性匀速：使用 Linear 缓动，时长适中
        self.underline_animation.setDuration(360)
        self.underline_animation.setEasingCurve(QEasingCurve.Type.Linear)

        content_layout.addWidget(header_widget)

        # 输入框样式（存储为实例变量以便后续使用）
        self.input_style = """
            QLineEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                color: #1e293b;
                background-color: rgba(248, 250, 252, 1);
                border: 1.5px solid rgba(226, 232, 240, 1);
                border-radius: 16px;
                padding: 14px 20px;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #3b82f6;
                background-color: #ffffff;
                border-width: 2px;
            }
            QLineEdit:hover {
                border-color: rgba(203, 213, 225, 1);
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
        """
        
        # 错误状态的输入框样式（存储为实例变量以便后续使用）
        self.input_error_style = """
            QLineEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                color: #1e293b;
                background-color: rgba(254, 242, 242, 1);
                border: 2px solid #ef4444;
                border-radius: 16px;
                padding: 14px 20px;
                selection-background-color: #3b82f6;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #ef4444;
                background-color: #ffffff;
                border-width: 2px;
            }
            QLineEdit:hover {
                border-color: #ef4444;
                background-color: #ffffff;
            }
            QLineEdit::placeholder {
                color: #94a3b8;
            }
        """

        # 用户名输入框布局（注册专用）
        self.username_row = QWidget()
        self.username_row.setStyleSheet(row_bg_style)
        # 使用垂直布局，包含输入框行和错误标签
        username_row_layout = QVBoxLayout(self.username_row)
        username_row_layout.setContentsMargins(0, 0, 0, 0)
        username_row_layout.setSpacing(0)
        
        # 输入框的水平布局
        self.username_layout = QHBoxLayout()
        self.username_layout.setContentsMargins(0, 0, 0, 0)
        self.username_layout.setSpacing(icon_spacing)
        icon_data = load_icon_data(11)
        if icon_data:
            username_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            username_icon.load(byte_array)
            username_icon.setFixedSize(icon_container_width, icon_container_width)
            username_icon.setStyleSheet("margin: 0px; opacity: 0.6;")
            self.username_layout.addWidget(username_icon, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(self.input_style)
        self.username_input.setFixedHeight(field_height)
        self.username_layout.addWidget(self.username_input, stretch=1)
        username_row_layout.addLayout(self.username_layout)
        
        # 用户名错误提示标签（作为输入框行的一部分，不增加额外间距）
        self.username_error_label = QLabel()
        self.username_error_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #ef4444;
                padding: 2px 0px 0px 0px;
                margin: 0px;
            }
        """)
        self.username_error_label.setFixedHeight(0)
        self.username_error_label.setVisible(False)
        username_row_layout.addWidget(self.username_error_label)
        # 初始可见性将在后续统一设置

        # 登录邮箱（含获取验证码按钮）外层透明容器：用于统一高度、显隐与间距
        self.login_email_row = QWidget()
        self.login_email_row.setStyleSheet(row_bg_style)
        # 使用垂直布局，包含输入框行和错误标签
        login_email_row_layout = QVBoxLayout(self.login_email_row)
        login_email_row_layout.setContentsMargins(0, 0, 0, 0)
        login_email_row_layout.setSpacing(0)
        
        # 输入框的水平布局
        self.login_email_layout = QHBoxLayout()
        self.login_email_layout.setContentsMargins(0, 0, 0, 0)
        self.login_email_layout.setSpacing(icon_spacing)
        icon_data = load_icon_data(3)
        if icon_data:
            login_email_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            login_email_icon.load(byte_array)
            login_email_icon.setFixedSize(icon_container_width, icon_container_width)
            login_email_icon.setStyleSheet("margin: 0px; opacity: 0.6;")
            self.login_email_layout.addWidget(login_email_icon, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.login_email_input = QLineEdit()
        self.login_email_input.setPlaceholderText("请输入邮箱")
        self.login_email_input.setStyleSheet(self.input_style)
        self.login_email_input.setFixedHeight(field_height)
        # 让邮箱输入框在水平方向尽可能占满，可见区域更大
        self.login_email_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.login_email_layout.addWidget(self.login_email_input, stretch=1)
        login_email_row_layout.addLayout(self.login_email_layout)
        
        # 登录邮箱错误提示标签（作为输入框行的一部分，不增加额外间距）
        self.login_email_error_label = QLabel()
        self.login_email_error_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #ef4444;
                padding: 2px 0px 0px 0px;
                margin: 0px;
            }
        """)
        self.login_email_error_label.setFixedHeight(0)
        self.login_email_error_label.setVisible(False)
        login_email_row_layout.addWidget(self.login_email_error_label)

        # 登录获取验证码按钮
        self.login_get_verification_code_button = QPushButton("获取验证码")
        # 使用统一的次要按钮样式，让验证码按钮与主按钮形成层级对比
        self.login_get_verification_code_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.login_get_verification_code_button.setFixedHeight(field_height)
        self.login_get_verification_code_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_get_verification_code_button.clicked.connect(lambda: self.send_verification_code("login"))
        self.login_email_layout.addWidget(self.login_get_verification_code_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.login_timer_manager = TimerManager(self.login_get_verification_code_button)

        # 注册邮箱（含获取验证码按钮）外层透明容器：用于统一高度、显隐与间距
        self.register_email_row = QWidget()
        self.register_email_row.setStyleSheet(row_bg_style)
        # 使用垂直布局，包含输入框行和错误标签
        register_email_row_layout = QVBoxLayout(self.register_email_row)
        register_email_row_layout.setContentsMargins(0, 0, 0, 0)
        register_email_row_layout.setSpacing(0)
        
        # 输入框的水平布局
        self.register_email_layout = QHBoxLayout()
        self.register_email_layout.setContentsMargins(0, 0, 0, 0)
        self.register_email_layout.setSpacing(icon_spacing)
        icon_data = load_icon_data(3)
        if icon_data:
            register_email_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            register_email_icon.load(byte_array)
            register_email_icon.setFixedSize(icon_container_width, icon_container_width)
            register_email_icon.setStyleSheet("margin: 0px; opacity: 0.6;")
            self.register_email_layout.addWidget(register_email_icon, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.register_email_input = QLineEdit()
        self.register_email_input.setPlaceholderText("请输入邮箱")
        self.register_email_input.setStyleSheet(self.input_style)
        self.register_email_input.setFixedHeight(field_height)
        # 注册邮箱输入同样设置为可扩展，避免内容被按钮挤得过窄
        self.register_email_input.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self.register_email_layout.addWidget(self.register_email_input, stretch=1)
        register_email_row_layout.addLayout(self.register_email_layout)
        
        # 注册邮箱错误提示标签（作为输入框行的一部分，不增加额外间距）
        self.register_email_error_label = QLabel()
        self.register_email_error_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #ef4444;
                padding: 2px 0px 0px 0px;
                margin: 0px;
            }
        """)
        self.register_email_error_label.setFixedHeight(0)
        self.register_email_error_label.setVisible(False)
        register_email_row_layout.addWidget(self.register_email_error_label)

        # 注册获取验证码按钮
        self.register_get_verification_code_button = QPushButton("获取验证码")
        self.register_get_verification_code_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.register_get_verification_code_button.setFixedHeight(field_height)
        self.register_get_verification_code_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.register_get_verification_code_button.clicked.connect(lambda: self.send_verification_code("register"))
        self.register_email_layout.addWidget(self.register_get_verification_code_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.register_timer_manager = TimerManager(self.register_get_verification_code_button)

        # 验证码输入框布局（共用）
        self.verification_code_row = QWidget()
        self.verification_code_row.setStyleSheet(row_bg_style)
        self.verification_code_layout = QHBoxLayout(self.verification_code_row)
        self.verification_code_layout.setContentsMargins(0, 0, 0, 0)
        self.verification_code_layout.setSpacing(icon_spacing)
        icon_data = load_icon_data(12)
        if icon_data:
            code_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            code_icon.load(byte_array)
            code_icon.setFixedSize(icon_container_width, icon_container_width)
            code_icon.setStyleSheet("margin: 0px; opacity: 0.6;")
            self.verification_code_layout.addWidget(code_icon, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.verification_code_input = QLineEdit()
        self.verification_code_input.setPlaceholderText("请输入验证码")
        self.verification_code_input.setStyleSheet(self.input_style)
        self.verification_code_input.setFixedHeight(field_height)
        self.verification_code_layout.addWidget(self.verification_code_input, stretch=1)
        # 初始可见性将在后续统一设置

        # 登录密码输入框布局
        self.login_password_row = QWidget()
        self.login_password_row.setStyleSheet(row_bg_style)
        # 使用垂直布局，包含输入框行和错误标签
        login_password_row_layout = QVBoxLayout(self.login_password_row)
        login_password_row_layout.setContentsMargins(0, 0, 0, 0)
        login_password_row_layout.setSpacing(0)
        
        # 输入框的水平布局
        self.login_password_layout = QHBoxLayout()
        self.login_password_layout.setContentsMargins(0, 0, 0, 0)
        self.login_password_layout.setSpacing(icon_spacing)
        icon_data = load_icon_data(8)
        if icon_data:
            login_password_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            login_password_icon.load(byte_array)
            login_password_icon.setFixedSize(icon_container_width, icon_container_width)
            login_password_icon.setStyleSheet("margin: 0px; opacity: 0.6;")
            self.login_password_layout.addWidget(login_password_icon, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("请输入密码")
        self.login_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password_input.setStyleSheet(self.input_style)
        self.login_password_input.setFixedHeight(field_height)
        self.login_password_layout.addWidget(self.login_password_input, stretch=1)
        login_password_row_layout.addLayout(self.login_password_layout)
        
        # 登录密码错误提示标签（作为输入框行的一部分，不增加额外间距）
        self.login_password_error_label = QLabel()
        self.login_password_error_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #ef4444;
                padding: 2px 0px 0px 0px;
                margin: 0px;
            }
        """)
        self.login_password_error_label.setFixedHeight(0)
        self.login_password_error_label.setVisible(False)
        login_password_row_layout.addWidget(self.login_password_error_label)

        # 注册密码输入框布局
        self.register_password_row = QWidget()
        self.register_password_row.setStyleSheet(row_bg_style)
        # 使用垂直布局，包含输入框行和错误标签
        register_password_row_layout = QVBoxLayout(self.register_password_row)
        register_password_row_layout.setContentsMargins(0, 0, 0, 0)
        register_password_row_layout.setSpacing(0)
        
        # 输入框的水平布局
        self.register_password_layout = QHBoxLayout()
        self.register_password_layout.setContentsMargins(0, 0, 0, 0)
        self.register_password_layout.setSpacing(icon_spacing)
        icon_data = load_icon_data(8)
        if icon_data:
            register_password_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            register_password_icon.load(byte_array)
            register_password_icon.setFixedSize(icon_container_width, icon_container_width)
            register_password_icon.setStyleSheet("margin: 0px; opacity: 0.6;")
            self.register_password_layout.addWidget(register_password_icon, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("请输入密码")
        self.register_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password_input.setStyleSheet(self.input_style)
        self.register_password_input.setFixedHeight(field_height)
        self.register_password_layout.addWidget(self.register_password_input, stretch=1)
        register_password_row_layout.addLayout(self.register_password_layout)
        
        # 注册密码错误提示标签（作为输入框行的一部分，不增加额外间距）
        self.register_password_error_label = QLabel()
        self.register_password_error_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #ef4444;
                padding: 2px 0px 0px 0px;
                margin: 0px;
            }
        """)
        self.register_password_error_label.setFixedHeight(0)
        self.register_password_error_label.setVisible(False)
        register_password_row_layout.addWidget(self.register_password_error_label)

        # 添加所有输入行（统一用透明容器包裹，便于显隐与间距一致）
        # 注意：初始可见性和高度设置将在 switch_mode 中统一处理
        # 错误提示标签已作为输入框行的一部分，不会增加额外的间距
        content_layout.addWidget(self.username_row)
        content_layout.addWidget(self.login_email_row)
        content_layout.addWidget(self.register_email_row)
        content_layout.addWidget(self.verification_code_row)
        content_layout.addWidget(self.login_password_row)
        content_layout.addWidget(self.register_password_row)

        # 登录按钮
        self.login_button = QPushButton("登录")
        # 使用统一的主按钮样式
        self.login_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.login_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_button.setFixedHeight(52)
        self.login_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.login_button.clicked.connect(self.login)
        content_layout.addWidget(self.login_button)

        # 注册按钮
        self.register_button = QPushButton("注册")
        self.register_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.register_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.register_button.setFixedHeight(52)
        self.register_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.register_button.clicked.connect(self.register)
        content_layout.addWidget(self.register_button)
        
        # 注意：按钮的初始可见性将在 switch_mode 中统一设置

        # 协议布局
        agreement_layout = QHBoxLayout()
        text_label = QLabel("登录即代表你已阅读并同意 ")
        text_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px; 
            color: #64748b;
            letter-spacing: 0.4px;
        """)
        agreement_label = ClickableLabel("《用户协议》")
        agreement_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px; 
            color: #3b82f6; 
            text-decoration: none;
            font-weight: 600;
            letter-spacing: 0.4px;
        """)
        agreement_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        agreement_label.clicked.connect(self.show_agreement)
        agreement_layout.setSpacing(2)
        agreement_layout.addWidget(text_label)
        agreement_layout.addWidget(agreement_label)
        agreement_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addLayout(agreement_layout)

        main_layout.addWidget(content_widget)

        # 初始化模式并移除焦点（默认展示注册页）
        self.switch_mode("register")
        self.installEventFilter(self)
        self.clear_focus()  # 确保初始化时不选中任何输入框

        # 等布局完成后再初始化下划线位置，避免宽度为 0 导致看不到
        QTimer.singleShot(
            0,
            lambda: self._move_underline_to_label(
                self.user_login_label if self.current_mode == "login" else self.user_register_label
            ),
        )
        
        # 设置实时验证
        self._setup_realtime_validation()

    def show_agreement(self):
        if self.agreement_dialog and not self.agreement_dialog.isVisible():
            self.agreement_dialog.show()
            return
        self.agreement_dialog = AgreementDialog(self)
        self.agreement_dialog.setWindowModality(Qt.WindowModality.NonModal)
        center = self.screen().geometry().center()
        self.agreement_dialog.move(center.x() - self.agreement_dialog.width() // 2,
                                   center.y() - self.agreement_dialog.height() // 2)
        self.agreement_dialog.show()

    def eventFilter(self, obj, event):
        # 用户协议对话框现在自己处理外部点击关闭，这里不再需要处理
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        # 整体 Dialog 透明：卡片背景由 content_widget 负责绘制（含阴影）
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()

    def switch_mode(self, mode):
        self.current_mode = mode
        if mode == "login":
            # 登录模式样式（文字颜色高亮，底部下划线由 underline_widget 控制）
            self.user_login_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
                font-size: 24px; 
                font-weight: 700; 
                color: #1d4ed8;
                letter-spacing: 1px;
                padding: 4px 0px 10px 0px;
                background: transparent;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
                font-size: 24px; 
                font-weight: 600; 
                color: #9ca3af;
                letter-spacing: 1px;
                padding: 4px 0px 10px 0px;
                background: transparent;
            """)
            # 下划线滑动到“用户登录”
            self._move_underline_to_label(self.user_login_label)
            # 显示/隐藏按钮
            self.login_button.setVisible(True)
            self.register_button.setVisible(False)
            # 显示/隐藏输入框布局，并使用 setMaximumHeight 确保隐藏的控件不占据空间
            # 先设置最大高度，再设置可见性，确保布局计算一致
            self.username_row.setMaximumHeight(0)
            self.username_row.setVisible(False)
            self.verification_code_row.setMaximumHeight(1000)  # 恢复最大高度
            self.verification_code_row.setVisible(True)
            self.login_email_row.setMaximumHeight(1000)
            self.login_email_row.setVisible(True)
            self.register_email_row.setMaximumHeight(0)
            self.register_email_row.setVisible(False)
            self.login_password_row.setMaximumHeight(1000)
            self.login_password_row.setVisible(True)
            self.register_password_row.setMaximumHeight(0)
            self.register_password_row.setVisible(False)
            # 清空并移除焦点，清除错误提示
            self.login_email_input.clear()
            self.verification_code_input.clear()
            self.login_password_input.clear()
            self._clear_input_error(self.login_email_input, self.login_email_error_label)
            self._clear_input_error(self.login_password_input, self.login_password_error_label)
            self.clear_focus()
        elif mode == "register":
            # 注册模式样式（文字颜色高亮，底部下划线由 underline_widget 控制）
            self.user_login_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
                font-size: 24px; 
                font-weight: 600; 
                color: #9ca3af;
                letter-spacing: 1px;
                padding: 4px 0px 10px 0px;
                background: transparent;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
                font-size: 24px; 
                font-weight: 700; 
                color: #1d4ed8;
                letter-spacing: 1px;
                padding: 4px 0px 10px 0px;
                background: transparent;
            """)
            # 下划线滑动到“用户注册”
            self._move_underline_to_label(self.user_register_label)
            # 显示/隐藏按钮
            self.login_button.setVisible(False)
            self.register_button.setVisible(True)
            # 显示/隐藏输入框布局，并使用 setMaximumHeight 确保隐藏的控件不占据空间
            # 先设置最大高度，再设置可见性，确保布局计算一致
            self.username_row.setMaximumHeight(1000)  # 恢复最大高度
            self.username_row.setVisible(True)
            self.verification_code_row.setMaximumHeight(1000)
            self.verification_code_row.setVisible(True)
            self.login_email_row.setMaximumHeight(0)
            self.login_email_row.setVisible(False)
            self.register_email_row.setMaximumHeight(1000)
            self.register_email_row.setVisible(True)
            self.login_password_row.setMaximumHeight(0)
            self.login_password_row.setVisible(False)
            self.register_password_row.setMaximumHeight(1000)
            self.register_password_row.setVisible(True)
            # 清空并移除焦点，清除错误提示
            self.register_email_input.clear()
            self.verification_code_input.clear()
            self.register_password_input.clear()
            self.username_input.clear()
            self._clear_input_error(self.register_email_input, self.register_email_error_label)
            self._clear_input_error(self.register_password_input, self.register_password_error_label)
            self._clear_input_error(self.username_input, self.username_error_label)
            self.clear_focus()

    def _move_underline_to_label(self, label: QLabel):
        """将下划线平滑移动到指定标题下方（只在 X 方向滑动，形成连续感）"""
        if not hasattr(self, "underline_widget") or self.underline_widget is None:
            return

        parent = self.underline_widget.parent()
        if parent is None:
            return

        # 目标位置：与标题左对齐，宽度固定；Y 固定在 header 底部，避免被裁剪
        label_pos = label.mapTo(parent, label.rect().topLeft())
        target_x = label_pos.x()
        # 使用预计算的最大宽度，避免切换时宽度跳变导致“不连贯”感
        target_width = getattr(self, "_tab_underline_width", label.width() or 40)
        underline_h = self.underline_widget.height() or 3
        base_y = max(0, parent.height() - underline_h - 4)

        current_rect = self.underline_widget.geometry()

        # 第一次显示时：放在当前标题正下方一点，不做动画
        if (not self.underline_widget.isVisible()) or current_rect.isNull():
            init_rect = QRect(target_x, base_y, target_width, underline_h)
            self.underline_widget.setGeometry(init_rect)
            self.underline_widget.show()
            return

        # 后续：仅在 X 和宽度上做动画，保持 Y 和高度不变，实现“从 A 滑到 B”的效果
        target_rect = QRect(
            target_x,
            base_y,
            target_width,
            underline_h,
        )

        self.underline_animation.stop()
        self.underline_animation.setStartValue(current_rect)
        self.underline_animation.setEndValue(target_rect)
        self.underline_animation.start()

    def _setup_realtime_validation(self):
        """设置实时输入验证"""
        # 登录邮箱验证
        self.login_email_input.textChanged.connect(
            lambda: self._validate_email_input(self.login_email_input)
        )
        
        # 注册邮箱验证
        self.register_email_input.textChanged.connect(
            lambda: self._validate_email_input(self.register_email_input)
        )
        
        # 注册密码验证
        self.register_password_input.textChanged.connect(
            lambda: self._validate_password_input(self.register_password_input)
        )
        
        # 用户名验证（仅非空检查）
        self.username_input.textChanged.connect(
            lambda: self._validate_username_input(self.username_input)
        )
    
    def _validate_email_input(self, input_widget: QLineEdit):
        """验证邮箱输入"""
        email = input_widget.text().strip()
        # 根据输入框确定对应的错误标签
        if input_widget == self.login_email_input:
            error_label = self.login_email_error_label
        else:
            error_label = self.register_email_error_label
            
        if not email:
            self._clear_input_error(input_widget, error_label)
            return
        
        if validate_email(email):
            self._clear_input_error(input_widget, error_label)
        else:
            self._show_input_error(input_widget, error_label, "邮箱格式不正确")
    
    def _validate_password_input(self, input_widget: QLineEdit):
        """验证密码输入"""
        password = input_widget.text()
        # 根据输入框确定对应的错误标签
        if input_widget == self.login_password_input:
            error_label = self.login_password_error_label
        else:
            error_label = self.register_password_error_label
            
        if not password:
            self._clear_input_error(input_widget, error_label)
            return
        
        if validate_password(password):
            self._clear_input_error(input_widget, error_label)
        else:
            self._show_input_error(input_widget, error_label, "密码至少8位，需包含大小写字母、数字和特殊字符")
    
    def _validate_username_input(self, input_widget: QLineEdit):
        """验证用户名输入（仅非空检查）"""
        username = input_widget.text().strip()
        if username:
            self._clear_input_error(input_widget, self.username_error_label)
        # 空值时不清除错误，让用户在提交时看到提示
    
    def _show_input_error(self, input_widget: QLineEdit, error_label: QLabel, error_msg: str):
        """显示输入错误（红色边框 + 错误标签文字）"""
        input_widget.setStyleSheet(self.input_error_style)
        error_label.setText(error_msg)
        # 显示错误标签，使用紧凑的高度
        error_label.setFixedHeight(16)
        error_label.setVisible(True)
    
    def _clear_input_error(self, input_widget: QLineEdit, error_label: QLabel):
        """清除输入错误（标签高度设为0，不占用空间）"""
        input_widget.setStyleSheet(self.input_style)
        error_label.setFixedHeight(0)
        error_label.setVisible(False)
        error_label.setText("")

    def clear_focus(self):
        """移除所有输入框的焦点"""
        input_widgets = [
            self.login_email_input,
            self.register_email_input,
            self.verification_code_input,
            self.login_password_input,
            self.register_password_input,
            self.username_input
        ]
        for widget in input_widgets:
            widget.clearFocus()

    def send_verification_code(self, mode):
        if mode == "login":
            email = self.login_email_input.text().strip()
            timer_manager = self.login_timer_manager
        else:
            email = self.register_email_input.text().strip()
            timer_manager = self.register_timer_manager

        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_EMAIL_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_EMAIL_INVALID_TITLE)
            msg_box.exec()
            return

        try:
            resp = api_send_verification_code(email, mode)
        except Exception as e:
            logging.error("发送验证码请求失败：%s", e, exc_info=True)
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("验证码请求失败，请稍后重试")
            msg_box.setWindowTitle("发送失败")
            msg_box.exec()
            return

        if not resp.get("success", False):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(resp.get("message", "验证码发送失败，请稍后重试"))
            msg_box.setWindowTitle("发送失败")
            msg_box.exec()
            return

        timer_manager.start_countdown()

    def register(self):
        email = self.register_email_input.text().strip()
        input_code = self.verification_code_input.text().strip()
        password = self.register_password_input.text()
        username = self.username_input.text().strip()

        # 校验用户名
        if not username:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_USERNAME_REQUIRED_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_USERNAME_REQUIRED_TITLE)
            msg_box.exec()
            return

        # 校验邮箱
        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_EMAIL_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_EMAIL_INVALID_TITLE)
            msg_box.exec()
            return

        # 校验密码
        if not validate_password(password):
            msg_box = CustomMessageBox(self.parent(), variant="error")
            msg_box.setText(text_cfg.LOGIN_PASSWORD_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_PASSWORD_INVALID_TITLE)
            msg_box.exec()
            return

        # 调用后端注册接口
        try:
            resp = api_register_user(email, password, username, input_code)
        except Exception as e:
            logging.error("注册请求失败：%s", e, exc_info=True)
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_REGISTER_FAILED_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_REGISTER_FAILED_TITLE)
            msg_box.exec()
            return

        if not resp.get("success", False):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(resp.get("message", text_cfg.LOGIN_REGISTER_FAILED_MESSAGE))
            msg_box.setWindowTitle(text_cfg.LOGIN_REGISTER_FAILED_TITLE)
            msg_box.exec()
            return

        # 注册成功后，按后端返回的数据更新本地状态
        user = (resp.get("user") or {})
        vip_info = (resp.get("vip") or {})
        token = resp.get("token")

        user_id = user.get("id")
        username = user.get("username") or username

        if user_id is not None:
            save_login_status(user_id, username)
        if token:
            save_token(token)

        is_vip = bool(vip_info.get("is_vip", False))
        diamonds = vip_info.get("diamonds", 0)

        # 头像目前走后端统一维护，这里先传 None
        self.update_user_info(None, username, is_vip, diamonds, user_id)

        # 隐藏蒙版
        if self.parent():
            self.parent().mask_widget.setVisible(False)

        self.clear_focus()
        self.accept()

    def login(self):
        email = self.login_email_input.text().strip()
        input_code = self.verification_code_input.text().strip()
        password = self.login_password_input.text()

        # 校验邮箱
        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_EMAIL_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_EMAIL_INVALID_TITLE)
            msg_box.exec()
            return

        # 调用后端登录接口
        try:
            resp = api_login_user(email, password, input_code)
        except Exception as e:
            logging.error("登录请求失败：%s", e, exc_info=True)
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_FAILED_MESSAGE if hasattr(text_cfg, "LOGIN_FAILED_MESSAGE") else "登录失败，请稍后重试")
            msg_box.setWindowTitle(text_cfg.LOGIN_FAILED_TITLE)
            msg_box.exec()
            return

        if not resp.get("success", False):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(resp.get("message", text_cfg.LOGIN_FAILED_MESSAGE if hasattr(text_cfg, "LOGIN_FAILED_MESSAGE") else "登录失败，请稍后重试"))
            msg_box.setWindowTitle(text_cfg.LOGIN_FAILED_TITLE)
            msg_box.exec()
            return

        user = (resp.get("user") or {})
        vip_info = (resp.get("vip") or {})
        token = resp.get("token")

        user_id = user.get("id")
        username = user.get("username", "未命名")

        if user_id is not None:
            save_login_status(user_id, username)
        if token:
            save_token(token)

        is_vip = bool(vip_info.get("is_vip", False))
        diamonds = vip_info.get("diamonds", 0)

        self.update_user_info(None, username, is_vip, diamonds, user_id)

        # 隐藏蒙版
        if self.parent():
            self.parent().mask_widget.setVisible(False)

        self.clear_focus()
        self.accept()

    def keyPressEvent(self, event: QKeyEvent):
        """支持 ESC 键关闭登录对话框"""
        if event.key() == Qt.Key.Key_Escape:
            if self.parent():
                self.parent().mask_widget.setVisible(False)
            self.reject()
        else:
            super().keyPressEvent(event)
    
    def check_token(self):
        token = read_token()
        if token:
            # 先做本地签名验证，避免明显非法 token
            payload = verify_token(token)
            if not payload:
                return False

            try:
                resp = api_check_token(token)
            except Exception as e:
                logging.error("自动登录（token 校验）请求失败：%s", e, exc_info=True)
                return False

            if not resp.get("success", False):
                return False

            user = (resp.get("user") or {})
            vip_info = (resp.get("vip") or {})
            new_token = resp.get("token")  # 后端可选择刷新 token

            user_id = user.get("id")
            username = user.get("username", "未命名")
            if user_id is not None:
                save_login_status(user_id, username)
            if new_token:
                save_token(new_token)

            is_vip = bool(vip_info.get("is_vip", False))
            diamonds = vip_info.get("diamonds", 0)

            self.update_user_info(None, username, is_vip, diamonds, user_id)

            if self.parent():
                self.parent().mask_widget.setVisible(False)

            self.clear_focus()
            self.accept()
            return True
        return False

    def update_user_info(self, avatar, username, is_vip, diamonds, user_id=None):
        main_window = self.parent()
        # 统一交由 MainWindow 处理头像/用户名/会员信息展示（含默认头像兜底）
        main_window.update_membership_info(avatar, username, is_vip, diamonds, user_id)
        logging.info(f"用户 {username} 是 VIP: {is_vip}, 钻石数量: {diamonds}")