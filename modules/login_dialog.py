# 文件 3：login_dialog.py
from PyQt6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QLineEdit, QSpacerItem, QSizePolicy, QWidget)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent, QByteArray
from PyQt6.QtGui import QCursor, QPainter, QColor, QPixmap, QImage, QPainterPath
from gui.clickable_label import ClickableLabel
from modules.agreement_dialog import AgreementDialog
from backend.validation.validator import validate_email, validate_password
from backend.email.email_sender import EmailSender, generate_verification_code
from backend.validation.verification_manager import VerificationManager
from backend.timer.timer_manager import TimerManager
from backend.config.config import email_config
from gui.custom_message_box import CustomMessageBox
from backend.database.database_manager import DatabaseManager
import bcrypt
from backend.login.token_utils import generate_token, verify_token
from backend.login.token_storage import save_token, read_token
from backend.login.login_status_manager import save_login_status
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


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
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        # 头部布局，包含用户登录和用户注册
        header_layout = QHBoxLayout()

        # 用户登录标签
        self.user_login_label = QLabel("用户登录")
        self.user_login_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 25px; 
            font-weight: bold; 
            color: #429bf7;
            letter-spacing: 1px;
        """)
        self.user_login_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_login_label.mousePressEvent = lambda event: self.switch_mode("login")
        header_layout.addWidget(self.user_login_label)

        spacer = QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        header_layout.addItem(spacer)

        # 用户注册标签
        self.user_register_label = QLabel("用户注册")
        self.user_register_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 25px; 
            font-weight: bold; 
            color: #222;
            letter-spacing: 1px;
        """)
        self.user_register_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.user_register_label.mousePressEvent = lambda event: self.switch_mode("register")
        header_layout.addWidget(self.user_register_label)

        content_layout.addLayout(header_layout)

        input_style = """
            QLineEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;
                color: #333;
                background-color: transparent;
                border: 2px solid #ddd; 
                border-radius: 10px; 
                padding: 10px 15px; 
                margin-bottom: 8px; 
            }
            QLineEdit:focus {
                border-color: #429bf7; 
                background-color: #fff; 
            }
        """

        # 用户名输入框布局（注册专用）
        self.username_layout = QHBoxLayout()
        icon_data = self.db_manager.get_icon_by_id(11)
        if icon_data:
            username_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            username_icon.load(byte_array)
            username_icon.setFixedSize(30, 30)
            username_icon.setStyleSheet("margin-right: 10px;")
            self.username_layout.addWidget(username_icon)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(input_style)
        self.username_layout.addWidget(self.username_input)
        self._set_layout_visible(self.username_layout, False)  # 默认隐藏

        # 登录邮箱输入框布局
        self.login_email_layout = QHBoxLayout()
        icon_data = self.db_manager.get_icon_by_id(3)
        if icon_data:
            login_email_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            login_email_icon.load(byte_array)
            login_email_icon.setFixedSize(30, 30)
            login_email_icon.setStyleSheet("margin-right: 10px;")
            self.login_email_layout.addWidget(login_email_icon)
        self.login_email_input = QLineEdit()
        self.login_email_input.setPlaceholderText("请输入邮箱")
        self.login_email_input.setStyleSheet(input_style)
        self.login_email_layout.addWidget(self.login_email_input)

        # 登录获取验证码按钮
        self.login_get_verification_code_button = QPushButton("获取验证码")
        self.login_get_verification_code_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: #429bf7;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 15px;  /* 减小按钮内边距 */
                font-size: 14px;     /* 减小字体大小 */
            }
            QPushButton:hover {
                background-color: #78b6f6;
            }
            QPushButton:pressed {
                background-color: #429bf7;
            }
        """)
        self.login_get_verification_code_button.clicked.connect(lambda: self.send_verification_code("login"))
        self.login_email_layout.addWidget(self.login_get_verification_code_button)
        self.login_timer_manager = TimerManager(self.login_get_verification_code_button)

        # 注册邮箱输入框布局
        self.register_email_layout = QHBoxLayout()
        icon_data = self.db_manager.get_icon_by_id(3)
        if icon_data:
            register_email_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            register_email_icon.load(byte_array)
            register_email_icon.setFixedSize(30, 30)
            register_email_icon.setStyleSheet("margin-right: 10px;")
            self.register_email_layout.addWidget(register_email_icon)
        self.register_email_input = QLineEdit()
        self.register_email_input.setPlaceholderText("请输入邮箱")
        self.register_email_input.setStyleSheet(input_style)
        self.register_email_layout.addWidget(self.register_email_input)

        # 注册获取验证码按钮
        self.register_get_verification_code_button = QPushButton("获取验证码")
        self.register_get_verification_code_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: #429bf7;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 10px 15px;  /* 减小按钮内边距 */
                font-size: 14px;     /* 减小字体大小 */
            }
            QPushButton:hover {
                background-color: #78b6f6;
            }
            QPushButton:pressed {
                background-color: #429bf7;
            }
        """)
        self.register_get_verification_code_button.clicked.connect(lambda: self.send_verification_code("register"))
        self.register_email_layout.addWidget(self.register_get_verification_code_button)
        self.register_timer_manager = TimerManager(self.register_get_verification_code_button)

        # 验证码输入框布局（共用）
        self.verification_code_layout = QHBoxLayout()
        icon_data = self.db_manager.get_icon_by_id(12)
        if icon_data:
            code_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            code_icon.load(byte_array)
            code_icon.setFixedSize(30, 30)
            code_icon.setStyleSheet("margin-right: 10px;")
            self.verification_code_layout.addWidget(code_icon)
        self.verification_code_input = QLineEdit()
        self.verification_code_input.setPlaceholderText("请输入验证码")
        self.verification_code_input.setStyleSheet(input_style)
        self.verification_code_layout.addWidget(self.verification_code_input)
        self._set_layout_visible(self.verification_code_layout, False)  # 默认隐藏

        # 登录密码输入框布局
        self.login_password_layout = QHBoxLayout()
        icon_data = self.db_manager.get_icon_by_id(8)
        if icon_data:
            login_password_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            login_password_icon.load(byte_array)
            login_password_icon.setFixedSize(30, 30)
            login_password_icon.setStyleSheet("margin-right: 10px;")
            self.login_password_layout.addWidget(login_password_icon)
        self.login_password_input = QLineEdit()
        self.login_password_input.setPlaceholderText("请输入密码")
        self.login_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password_input.setStyleSheet(input_style)
        self.login_password_layout.addWidget(self.login_password_input)

        # 注册密码输入框布局
        self.register_password_layout = QHBoxLayout()
        icon_data = self.db_manager.get_icon_by_id(10)
        if icon_data:
            register_password_icon = QSvgWidget()
            byte_array = QByteArray(icon_data)
            register_password_icon.load(byte_array)
            register_password_icon.setFixedSize(30, 30)
            register_password_icon.setStyleSheet("margin-right: 10px;")
            self.register_password_layout.addWidget(register_password_icon)
        self.register_password_input = QLineEdit()
        self.register_password_input.setPlaceholderText("请输入密码")
        self.register_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password_input.setStyleSheet(input_style)
        self.register_password_layout.addWidget(self.register_password_input)

        # 添加所有输入框布局到内容布局
        content_layout.addLayout(self.username_layout)
        content_layout.addLayout(self.login_email_layout)
        content_layout.addLayout(self.register_email_layout)
        content_layout.addLayout(self.verification_code_layout)
        content_layout.addLayout(self.login_password_layout)
        content_layout.addLayout(self.register_password_layout)

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: #429bf7;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 18px 50px;
                font-size: 20px;
                min-width: 260px;
                font-weight: 500;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #78b6f6;
            }
            QPushButton:pressed {
                background-color: #429bf7;
            }
        """)
        self.login_button.clicked.connect(self.login)
        content_layout.addWidget(self.login_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # 注册按钮
        self.register_button = QPushButton("注册")
        self.register_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                background-color: #429bf7;
                color: white;
                border: none;
                border-radius: 25px;
                padding: 18px 50px;
                font-size: 20px;
                min-width: 260px;
                font-weight: 500;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background-color: #78b6f6;
            }
            QPushButton:pressed {
                background-color: #429bf7;
            }
        """)
        self.register_button.clicked.connect(self.register)
        content_layout.addWidget(self.register_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # 协议布局
        agreement_layout = QHBoxLayout()
        text_label = QLabel("登录即代表你已阅读并同意 ")
        text_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 16px; 
            color: #888;
            letter-spacing: 0.5px;
        """)
        agreement_label = ClickableLabel("《用户协议》")
        agreement_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 16px; 
            color: #007bff; 
            text-decoration: none;
            font-weight: 500;
            letter-spacing: 0.5px;
        """)
        agreement_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        agreement_label.clicked.connect(self.show_agreement)
        agreement_layout.setSpacing(3)
        agreement_layout.addWidget(text_label)
        agreement_layout.addWidget(agreement_label)
        agreement_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addLayout(agreement_layout)

        main_layout.addWidget(content_widget)

        # 初始化模式并移除焦点
        self.switch_mode("login")
        self.installEventFilter(self)
        self.clear_focus()  # 确保初始化时不选中任何输入框

    def screen_size(self, ratio, height=False):
        screen = QApplication.primaryScreen()
        size = screen.size()
        if height:
            return int(size.height() * ratio)
        return int(size.width() * ratio)

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
        if event.type() == QEvent.Type.MouseButtonPress:
            if (self.agreement_dialog and self.agreement_dialog.isVisible() and
                    not self.agreement_dialog.geometry().contains(event.globalPosition().toPoint())):
                self.agreement_dialog.close()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 230))
        painter.drawRoundedRect(rect, 25, 25)
        painter.end()

    def _set_layout_visible(self, layout, visible):
        """设置布局中所有控件的可见性"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(visible)

    def switch_mode(self, mode):
        self.current_mode = mode
        if mode == "login":
            # 登录模式样式
            self.user_login_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 25px; 
                font-weight: bold; 
                color: #429bf7;
                letter-spacing: 1px;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 25px; 
                font-weight: bold; 
                color: #222;
                letter-spacing: 1px;
            """)
            # 显示/隐藏按钮
            self.login_button.setVisible(True)
            self.register_button.setVisible(False)
            # 显示/隐藏输入框布局
            self._set_layout_visible(self.username_layout, False)  # 隐藏用户名（注册专用）
            self._set_layout_visible(self.verification_code_layout, True)  # 显示验证码
            self._set_layout_visible(self.login_email_layout, True)  # 显示登录邮箱
            self._set_layout_visible(self.register_email_layout, False)  # 隐藏注册邮箱
            self._set_layout_visible(self.login_password_layout, True)  # 显示登录密码框
            self._set_layout_visible(self.register_password_layout, False)  # 隐藏注册密码框
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
                font-size: 25px; 
                font-weight: bold; 
                color: #222;
                letter-spacing: 1px;
            """)
            self.user_register_label.setStyleSheet("""
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 25px; 
                font-weight: bold; 
                color: #429bf7;
                letter-spacing: 1px;
            """)
            # 显示/隐藏按钮
            self.login_button.setVisible(False)
            self.register_button.setVisible(True)
            # 显示/隐藏输入框布局
            self._set_layout_visible(self.username_layout, True)  # 显示用户名（注册专用）
            self._set_layout_visible(self.verification_code_layout, True)  # 显示验证码
            self._set_layout_visible(self.login_email_layout, False)  # 隐藏登录邮箱
            self._set_layout_visible(self.register_email_layout, True)  # 显示注册邮箱
            self._set_layout_visible(self.login_password_layout, False)  # 隐藏登录密码框
            self._set_layout_visible(self.register_password_layout, True)  # 显示注册密码框
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
            msg_box.setText("请输入有效的邮箱地址")
            msg_box.setWindowTitle("邮箱格式错误")
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
            msg_box.setText("请输入用户名")
            msg_box.setWindowTitle("用户名缺失")
            msg_box.exec()
            return

        # 校验邮箱
        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("请输入有效的邮箱地址")
            msg_box.setWindowTitle("邮箱格式错误")
            msg_box.exec()
            return

        # 校验密码
        if not validate_password(password):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("密码应包含大小写字母、数字和特殊字符，长度至少8位")
            msg_box.setWindowTitle("密码格式错误")
            msg_box.exec()
            return

        # 校验验证码
        if not self.verification_manager.verify_code(email, input_code):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("验证码已过期或不正确，请重新获取")
            msg_box.setWindowTitle("验证码错误")
            msg_box.exec()
            return

        # 检查用户名是否已存在
        if self.db_manager.get_user_by_email(email):
            msg_box = CustomMessageBox()
            msg_box.setText("用户已存在，请直接登录")
            msg_box.setWindowTitle("用户已存在")
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
            msg_box.setText("注册失败，请稍后重试")
            msg_box.setWindowTitle("注册失败")
            msg_box.exec()

    def login(self):
        email = self.login_email_input.text()
        input_code = self.verification_code_input.text()
        password = self.login_password_input.text()

        # 校验邮箱
        if not validate_email(email):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("请输入有效的邮箱地址")
            msg_box.setWindowTitle("邮箱格式错误")
            msg_box.exec()
            return

        # 校验验证码
        if not self.verification_manager.verify_code(email, input_code):
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("验证码已过期或不正确，请重新获取")
            msg_box.setWindowTitle("验证码错误")
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
                msg_box.setText("密码错误，请重试")
                msg_box.setWindowTitle("登录失败")
                msg_box.exec()
        else:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setText("用户不存在，请先注册")
            msg_box.setWindowTitle("登录失败")
            msg_box.exec()

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

        if avatar:
            image = QImage.fromData(avatar)
            pixmap = QPixmap.fromImage(image)
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
            main_window.user_avatar_label.setPixmap(cropped_pixmap.scaled(
                main_window.user_avatar_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))

        main_window.username_display_label.setText(username)
        main_window.update_membership_info(avatar, username, is_vip, diamonds, user_id)
        logging.info(f"用户 {username} 是 VIP: {is_vip}, 钻石数量: {diamonds}")