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
        # 轻盈风：更通透的白、极淡边框
        content_widget.setStyleSheet("""
            #loginCard {
                background-color: rgba(255, 255, 255, 235);
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 170);
            }
        """)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(36)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 40))
        content_widget.setGraphicsEffect(shadow)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(44, 40, 44, 32)
        content_layout.setSpacing(16)

        # 统一输入控件高度（用于对齐“输入框 + 按钮”）
        field_height = 46
        row_bg_style = "background-color: transparent;"

        # 头部布局，包含用户登录和用户注册
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 6)
        header_layout.setSpacing(20)

        # 用户登录标签
        self.user_login_label = QLabel("用户登录")
        self.user_login_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 28px; 
            font-weight: 700; 
            color: #2563eb;
            letter-spacing: 0.5px;
            padding: 4px 0px 10px 0px;
            border-bottom: 2px solid #2563eb;
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
            font-size: 28px; 
            font-weight: 600; 
            color: #93c5fd;
            letter-spacing: 0.5px;
            padding: 4px 0px 10px 0px;
            border-bottom: 2px solid transparent;
        """)
        self.user_register_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_register_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.user_register_label.mousePressEvent = lambda event: self.switch_mode("register")
        header_layout.addWidget(self.user_register_label)

        content_layout.addLayout(header_layout)

        input_style = """
            QLineEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                color: #2c3e50;
                background-color: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(226, 232, 240, 210);
                border-radius: 14px;
                padding: 12px 18px;
                selection-background-color: #429bf7;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #2563eb;
                background-color: #ffffff;
                border-width: 1.5px;
            }
            QLineEdit:hover {
                border-color: rgba(203, 213, 225, 210);
                background-color: #ffffff;
            }
        """

        # 用户名输入框布局（注册专用）
        self.username_row = QWidget()
        self.username_row.setStyleSheet(row_bg_style)
        self.username_layout = QHBoxLayout(self.username_row)
        self.username_layout.setContentsMargins(0, 0, 0, 0)
        self.username_layout.setSpacing(12)
        icon_data = load_icon_data(11)
        if icon_data:
            username_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            username_icon.load(byte_array)
            username_icon.setFixedSize(24, 24)
            username_icon.setStyleSheet("margin: 0px; opacity: 0.5;")
            self.username_layout.addWidget(username_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(input_style)
        self.username_input.setFixedHeight(field_height)
        self.username_layout.addWidget(self.username_input, stretch=1)
        self.username_row.setVisible(False)  # 默认隐藏

        # 登录邮箱（含获取验证码按钮）外层透明容器：用于统一高度、显隐与间距
        self.login_email_row = QWidget()
        self.login_email_row.setStyleSheet(row_bg_style)
        self.login_email_layout = QHBoxLayout(self.login_email_row)
        self.login_email_layout.setContentsMargins(0, 0, 0, 0)
        self.login_email_layout.setSpacing(8)
        icon_data = load_icon_data(3)
        if icon_data:
            login_email_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            login_email_icon.load(byte_array)
            login_email_icon.setFixedSize(24, 24)
            login_email_icon.setStyleSheet("margin: 0px; opacity: 0.5;")
            self.login_email_layout.addWidget(login_email_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.login_email_input = QLineEdit()
        self.login_email_input.setPlaceholderText("请输入邮箱")
        self.login_email_input.setStyleSheet(input_style)
        self.login_email_input.setFixedHeight(field_height)
        self.login_email_layout.addWidget(self.login_email_input, stretch=1)

        # 登录获取验证码按钮
        self.login_get_verification_code_button = QPushButton("获取验证码")
        self.login_get_verification_code_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 14px;
                padding: 0px 18px;
                font-size: 13px;
                font-weight: 600;
                min-width: 118px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(226, 232, 240, 200);
                color: #94a3b8;
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
        self.register_email_layout = QHBoxLayout(self.register_email_row)
        self.register_email_layout.setContentsMargins(0, 0, 0, 0)
        self.register_email_layout.setSpacing(8)
        icon_data = load_icon_data(3)
        if icon_data:
            register_email_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            register_email_icon.load(byte_array)
            register_email_icon.setFixedSize(24, 24)
            register_email_icon.setStyleSheet("margin: 0px; opacity: 0.5;")
            self.register_email_layout.addWidget(register_email_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.register_email_input = QLineEdit()
        self.register_email_input.setPlaceholderText("请输入邮箱")
        self.register_email_input.setStyleSheet(input_style)
        self.register_email_input.setFixedHeight(field_height)
        self.register_email_layout.addWidget(self.register_email_input, stretch=1)

        # 注册获取验证码按钮
        self.register_get_verification_code_button = QPushButton("获取验证码")
        self.register_get_verification_code_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 14px;
                padding: 0px 18px;
                font-size: 13px;
                font-weight: 600;
                min-width: 118px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(226, 232, 240, 200);
                color: #94a3b8;
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
        self.verification_code_layout.setSpacing(12)
        icon_data = load_icon_data(12)
        if icon_data:
            code_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            code_icon.load(byte_array)
            code_icon.setFixedSize(24, 24)
            code_icon.setStyleSheet("margin: 0px; opacity: 0.5;")
            self.verification_code_layout.addWidget(code_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.verification_code_input = QLineEdit()
        self.verification_code_input.setPlaceholderText("请输入验证码")
        self.verification_code_input.setStyleSheet(input_style)
        self.verification_code_input.setFixedHeight(field_height)
        self.verification_code_layout.addWidget(self.verification_code_input, stretch=1)
        self.verification_code_row.setVisible(False)  # 默认隐藏

        # 登录密码输入框布局
        self.login_password_row = QWidget()
        self.login_password_row.setStyleSheet(row_bg_style)
        self.login_password_layout = QHBoxLayout(self.login_password_row)
        self.login_password_layout.setContentsMargins(0, 0, 0, 0)
        self.login_password_layout.setSpacing(12)
        icon_data = load_icon_data(8)
        if icon_data:
            login_password_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            login_password_icon.load(byte_array)
            login_password_icon.setFixedSize(24, 24)
            login_password_icon.setStyleSheet("margin: 0px; opacity: 0.5;")
            self.login_password_layout.addWidget(login_password_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("请输入密码")
        self.login_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password_input.setStyleSheet(input_style)
        self.login_password_input.setFixedHeight(field_height)
        self.login_password_layout.addWidget(self.login_password_input, stretch=1)

        # 注册密码输入框布局
        self.register_password_row = QWidget()
        self.register_password_row.setStyleSheet(row_bg_style)
        self.register_password_layout = QHBoxLayout(self.register_password_row)
        self.register_password_layout.setContentsMargins(0, 0, 0, 0)
        self.register_password_layout.setSpacing(12)
        icon_data = load_icon_data(8)
        if icon_data:
            register_password_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            register_password_icon.load(byte_array)
            register_password_icon.setFixedSize(24, 24)
            register_password_icon.setStyleSheet("margin: 0px; opacity: 0.5;")
            self.register_password_layout.addWidget(register_password_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("请输入密码")
        self.register_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password_input.setStyleSheet(input_style)
        self.register_password_input.setFixedHeight(field_height)
        self.register_password_layout.addWidget(self.register_password_input, stretch=1)

        # 添加所有输入行（统一用透明容器包裹，便于显隐与间距一致）
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
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 14px;
                padding: 0px 40px;
                font-size: 16px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(226, 232, 240, 200);
                color: #94a3b8;
            }
        """)
        self.login_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.login_button.setFixedHeight(48)
        self.login_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.login_button.clicked.connect(self.login)
        content_layout.addWidget(self.login_button)

        # 注册按钮
        self.register_button = QPushButton("注册")
        self.register_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #60a5fa, stop:1 #3b82f6);
                color: white;
                border: none;
                border-radius: 14px;
                padding: 0px 40px;
                font-size: 16px;
                font-weight: 600;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background-color: #2563eb;
            }
            QPushButton:disabled {
                background-color: rgba(226, 232, 240, 200);
                color: #94a3b8;
            }
        """)
        self.register_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.register_button.setFixedHeight(48)
        self.register_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.register_button.clicked.connect(self.register)
        content_layout.addWidget(self.register_button)

        # 协议布局
        agreement_layout = QHBoxLayout()
        text_label = QLabel("登录即代表你已阅读并同意 ")
        text_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px; 
            color: #94a3b8;
            letter-spacing: 0.3px;
        """)
        agreement_label = ClickableLabel("《用户协议》")
        agreement_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px; 
            color: #429bf7; 
            text-decoration: none;
            font-weight: 500;
            letter-spacing: 0.3px;
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
                font-size: 28px; 
                font-weight: 700; 
                color: #2563eb;
                letter-spacing: 0.5px;
                padding: 4px 0px 10px 0px;
                border-bottom: 2px solid #2563eb;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 28px; 
                font-weight: 600; 
                color: #93c5fd;
                letter-spacing: 0.5px;
                padding: 4px 0px 10px 0px;
                border-bottom: 2px solid transparent;
            """)
            # 显示/隐藏按钮
            self.login_button.setVisible(True)
            self.register_button.setVisible(False)
            # 显示/隐藏输入框布局
            self.username_row.setVisible(False)              # 隐藏用户名（注册专用）
            self.verification_code_row.setVisible(True)      # 显示验证码
            self.login_email_row.setVisible(True)            # 显示登录邮箱
            self.register_email_row.setVisible(False)        # 隐藏注册邮箱
            self.login_password_row.setVisible(True)         # 显示登录密码框
            self.register_password_row.setVisible(False)     # 隐藏注册密码框
            # 清空并移除焦点
            self.login_email_input.clear()
            self.verification_code_input.clear()
            self.login_password_input.clear()
            self.clear_focus()
            # 调整窗口大小
            self.resize(self.original_width, self.original_height)
        elif mode == "register":
            # 注册模式样式
            self.user_login_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 28px; 
                font-weight: 600; 
                color: #93c5fd;
                letter-spacing: 0.5px;
                padding: 4px 0px 10px 0px;
                border-bottom: 2px solid transparent;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 28px; 
                font-weight: 700; 
                color: #2563eb;
                letter-spacing: 0.5px;
                padding: 4px 0px 10px 0px;
                border-bottom: 2px solid #2563eb;
            """)
            # 显示/隐藏按钮
            self.login_button.setVisible(False)
            self.register_button.setVisible(True)
            # 显示/隐藏输入框布局
            self.username_row.setVisible(True)               # 显示用户名（注册专用）
            self.verification_code_row.setVisible(True)      # 显示验证码
            self.login_email_row.setVisible(False)           # 隐藏登录邮箱
            self.register_email_row.setVisible(True)         # 显示注册邮箱
            self.login_password_row.setVisible(False)        # 隐藏登录密码框
            self.register_password_row.setVisible(True)      # 显示注册密码框
            # 清空并移除焦点
            self.register_email_input.clear()
            self.verification_code_input.clear()
            self.register_password_input.clear()
            self.username_input.clear()
            self.clear_focus()
            # 调整窗口大小
            self.resize(self.original_width, self.original_height)

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