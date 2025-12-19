from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QLineEdit, QSpacerItem, QSizePolicy, QWidget,
                                QGraphicsDropShadowEffect)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent, QByteArray
from PyQt6.QtGui import QCursor, QPainter, QColor, QPixmap, QImage, QPainterPath, QKeyEvent
from gui.clickable_label import ClickableLabel
from modules.agreement_dialog import AgreementDialog
from backend.validation.validator import validate_email, validate_password
from backend.email.email_sender import EmailSender, generate_verification_code
from backend.validation.verification_manager import VerificationManager
from backend.timer.timer_manager import TimerManager
from backend.config.config import email_config
from gui.custom_message_box import CustomMessageBox
from backend.config import texts as text_cfg
from backend.database.database_manager import DatabaseManager
from backend.resources import load_icon_data
import bcrypt
from backend.login.token_utils import generate_token, verify_token
from backend.login.token_storage import save_token, read_token
from backend.login.login_status_manager import save_login_status
import logging
from backend.logging_manager import setup_logging  # noqa: F401


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
        self.current_mode = "login"  # 默认当前模式为登录
        self.verification_manager = VerificationManager()
        self.email_sender = EmailSender(email_config)

        # 初始化数据库管理器
        self.db_manager = DatabaseManager()

        main_layout = QVBoxLayout(self)
        # 给阴影留出空间
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_widget.setObjectName("loginCard")
        # 现代化设计：渐变背景、柔和阴影、精致边框
        content_widget.setStyleSheet("""
            #loginCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 250),
                    stop:1 rgba(249, 250, 251, 250));
                border-radius: 28px;
                border: 1px solid rgba(226, 232, 240, 200);
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(48)
        shadow.setOffset(0, 16)
        shadow.setColor(QColor(0, 0, 0, 50))
        content_widget.setGraphicsEffect(shadow)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(48, 48, 48, 40)
        content_layout.setSpacing(20)

        # 统一输入控件高度（用于对齐“输入框 + 按钮”）
        field_height = 50
        row_bg_style = "background-color: transparent;"
        # 统一图标容器宽度，确保所有输入框左侧对齐
        icon_container_width = 24
        icon_spacing = 12

        # 头部布局，包含用户登录和用户注册
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 8)
        header_layout.setSpacing(24)

        # 用户登录标签
        self.user_login_label = QLabel("用户登录")
        self.user_login_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 30px; 
            font-weight: 700; 
            color: #1e40af;
            letter-spacing: 0.8px;
            padding: 6px 0px 12px 0px;
            border-bottom: 3px solid #3b82f6;
            background: transparent;
        """)
        self.user_login_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_login_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_login_label.mousePressEvent = lambda event: self.switch_mode("login")
        header_layout.addWidget(self.user_login_label)

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        header_layout.addItem(spacer)

        # 用户注册标签
        self.user_register_label = QLabel("用户注册")
        self.user_register_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 30px; 
            font-weight: 600; 
            color: #94a3b8;
            letter-spacing: 0.8px;
            padding: 6px 0px 12px 0px;
            border-bottom: 3px solid transparent;
            background: transparent;
        """)
        self.user_register_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_register_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_register_label.mousePressEvent = lambda event: self.switch_mode("register")
        header_layout.addWidget(self.user_register_label)

        content_layout.addLayout(header_layout)

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
        self.login_get_verification_code_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 16px;
                padding: 0px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(241, 245, 249, 1);
                color: #cbd5e1;
                border: 1px solid rgba(226, 232, 240, 1);
            }
        """)
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
        self.register_get_verification_code_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 16px;
                padding: 0px 20px;
                font-size: 13px;
                font-weight: 600;
                min-width: 120px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(241, 245, 249, 1);
                color: #cbd5e1;
                border: 1px solid rgba(226, 232, 240, 1);
            }
        """)
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
        self.login_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 16px;
                padding: 0px 40px;
                font-size: 17px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(241, 245, 249, 1);
                color: #cbd5e1;
                border: 1px solid rgba(226, 232, 240, 1);
            }
        """)
        self.login_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_button.setFixedHeight(52)
        self.login_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.login_button.clicked.connect(self.login)
        content_layout.addWidget(self.login_button)

        # 注册按钮
        self.register_button = QPushButton("注册")
        self.register_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 16px;
                padding: 0px 40px;
                font-size: 17px;
                font-weight: 600;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(241, 245, 249, 1);
                color: #cbd5e1;
                border: 1px solid rgba(226, 232, 240, 1);
            }
        """)
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

        # 初始化模式并移除焦点
        self.switch_mode("login")
        self.installEventFilter(self)
        self.clear_focus()  # 确保初始化时不选中任何输入框
        
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
            # 登录模式样式
            self.user_login_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 30px; 
                font-weight: 700; 
                color: #1e40af;
                letter-spacing: 0.8px;
                padding: 6px 0px 12px 0px;
                border-bottom: 3px solid #3b82f6;
                background: transparent;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 30px; 
                font-weight: 600; 
                color: #94a3b8;
                letter-spacing: 0.8px;
                padding: 6px 0px 12px 0px;
                border-bottom: 3px solid transparent;
                background: transparent;
            """)
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
            # 强制重新计算布局，确保间距一致
            # 先更新几何信息，然后处理事件，最后更新显示
            self.updateGeometry()
            QApplication.processEvents()
            self.update()
        elif mode == "register":
            # 注册模式样式
            self.user_login_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 30px; 
                font-weight: 600; 
                color: #94a3b8;
                letter-spacing: 0.8px;
                padding: 6px 0px 12px 0px;
                border-bottom: 3px solid transparent;
                background: transparent;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 30px; 
                font-weight: 700; 
                color: #1e40af;
                letter-spacing: 0.8px;
                padding: 6px 0px 12px 0px;
                border-bottom: 3px solid #3b82f6;
                background: transparent;
            """)
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
            # 强制重新计算布局，确保间距一致
            # 先更新几何信息，然后处理事件，最后更新显示
            self.updateGeometry()
            QApplication.processEvents()
            self.update()

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
            email = self.login_email_input.text()
            timer_manager = self.login_timer_manager
        else:
            email = self.register_email_input.text()
            timer_manager = self.register_timer_manager

        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_EMAIL_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_EMAIL_INVALID_TITLE)
            msg_box.exec()
            return

        code = generate_verification_code()
        if self.email_sender.send_verification_code(email, code):
            self.verification_manager.set_verification_code(email, code)
            timer_manager.start_countdown()
        else:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("验证码邮件发送失败，请稍后重试")
            msg_box.setWindowTitle("发送失败")
            msg_box.exec()

    def register(self):
        email = self.register_email_input.text()
        input_code = self.verification_code_input.text()
        password = self.register_password_input.text()
        username = self.username_input.text()

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

        # 校验验证码
        if not self.verification_manager.verify_code(email, input_code):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_VERIFICATION_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_VERIFICATION_INVALID_TITLE)
            msg_box.exec()
            return

        # 检查用户名是否已存在
        if self.db_manager.get_user_by_email(email):
            msg_box = CustomMessageBox()
            msg_box.setText(text_cfg.LOGIN_USER_EXISTS_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_USER_EXISTS_TITLE)
            msg_box.exec()
            return

        # 插入用户信息
        if self.db_manager.insert_user_info(username, email, password):
            # 注册成功后，模拟登录操作
            user = self.db_manager.get_user_by_email(email)
            if user:
                logging.info(f"用户 {user['username']} 注册成功，ID: {user['id']}")
                save_login_status(user['id'], user['username'])
                token = generate_token(email)
                save_token(token)

                vip_info = self.db_manager.get_user_vip_info(user['id'])
                if vip_info:
                    is_vip = vip_info['is_vip']
                    diamonds = vip_info['diamonds']
                    self.update_user_info(user['avatar'], user['username'], is_vip, diamonds, user['id'])

                # 隐藏蒙版
                if self.parent():
                    self.parent().mask_widget.setVisible(False)

                self.clear_focus()  # 关闭前移除焦点
                self.accept()  # 关闭登录对话框
        else:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_REGISTER_FAILED_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_REGISTER_FAILED_TITLE)
            msg_box.exec()

    def login(self):
        email = self.login_email_input.text()
        input_code = self.verification_code_input.text()
        password = self.login_password_input.text()

        # 校验邮箱
        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_EMAIL_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_EMAIL_INVALID_TITLE)
            msg_box.exec()
            return

        # 校验验证码
        if not self.verification_manager.verify_code(email, input_code):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_VERIFICATION_INVALID_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_VERIFICATION_INVALID_TITLE)
            msg_box.exec()
            return

        user = self.db_manager.get_user_by_email(email)
        if user:
            hashed = user['password'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), hashed):
                logging.info(f"用户 {user['username']} 登录成功，ID: {user['id']}")
                save_login_status(user['id'], user['username'])
                token = generate_token(email)
                save_token(token)

                vip_info = self.db_manager.get_user_vip_info(user['id'])
                if vip_info:
                    is_vip = vip_info['is_vip']
                    diamonds = vip_info['diamonds']
                    self.update_user_info(user['avatar'], user['username'], is_vip, diamonds, user['id'])

                # 隐藏蒙版
                if self.parent():
                    self.parent().mask_widget.setVisible(False)

                self.clear_focus()  # 关闭前移除焦点
                self.accept()  # 关闭登录对话框
            else:
                msg_box = CustomMessageBox(self.parent())
                msg_box.setText(text_cfg.LOGIN_PASSWORD_WRONG_MESSAGE)
                msg_box.setWindowTitle(text_cfg.LOGIN_FAILED_TITLE)
                msg_box.exec()
        else:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText(text_cfg.LOGIN_USER_NOT_FOUND_MESSAGE)
            msg_box.setWindowTitle(text_cfg.LOGIN_FAILED_TITLE)
            msg_box.exec()

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
                        self.update_user_info(user['avatar'], user['username'], is_vip, diamonds, user['id'])

                    # 隐藏蒙版
                    if self.parent():
                        self.parent().mask_widget.setVisible(False)

                    self.clear_focus()  # 关闭前移除焦点
                    self.accept()  # 关闭登录对话框
                    return True
        return False

    def update_user_info(self, avatar, username, is_vip, diamonds, user_id=None):
        main_window = self.parent()
        # 统一交由 MainWindow 处理头像/用户名/会员信息展示（含默认头像兜底）
        main_window.update_membership_info(avatar, username, is_vip, diamonds, user_id)
        logging.info(f"用户 {username} 是 VIP: {is_vip}, 钻石数量: {diamonds}")