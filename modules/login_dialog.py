from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QDialog, QLineEdit, QSpacerItem, QSizePolicy)
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QCursor, QPainter, QColor
from gui.clickable_label import ClickableLabel
from modules.agreement_dialog import AgreementDialog

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        screen_width = self.screen_size(0.2)
        self.setFixedSize(screen_width, int(screen_width * 1.2))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.agreement_dialog = None
        self.current_mode = "login"  # 默认当前模式为登录

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        # 头部布局，包含用户登录和用户注册
        header_layout = QHBoxLayout()
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

        # 用户名输入框布局
        self.username_layout = QHBoxLayout()
        username_icon = QSvgWidget('icons/user.svg')  
        username_icon.setFixedSize(30, 30)  
        username_icon.setStyleSheet("margin-right: 10px;")
        self.username_layout.addWidget(username_icon)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setStyleSheet(input_style)
        self.username_layout.addWidget(self.username_input)
        self._set_layout_visible(self.username_layout, False)  # 默认隐藏

        # 邮箱输入框布局
        self.email_layout = QHBoxLayout()
        email_icon = QSvgWidget('icons/email.svg')  
        email_icon.setFixedSize(30, 30)  
        email_icon.setStyleSheet("margin-right: 10px;")
        self.email_layout.addWidget(email_icon)
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱")
        self.email_input.setStyleSheet(input_style)
        self.email_layout.addWidget(self.email_input)

        # 获取验证码按钮
        self.get_verification_code_button = QPushButton("获取验证码")
        self.get_verification_code_button.setStyleSheet("""
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
        self.get_verification_code_button.setVisible(False)  # 默认隐藏
        self.email_layout.addWidget(self.get_verification_code_button)

        # 验证码输入框布局
        self.verification_code_layout = QHBoxLayout()
        code_icon = QSvgWidget('icons/verification_code.svg')  
        code_icon.setFixedSize(30, 30)  
        code_icon.setStyleSheet("margin-right: 10px;")
        self.verification_code_layout.addWidget(code_icon)
        self.verification_code_input = QLineEdit()
        self.verification_code_input.setPlaceholderText("请输入验证码")
        self.verification_code_input.setStyleSheet(input_style)
        self.verification_code_layout.addWidget(self.verification_code_input)
        self._set_layout_visible(self.verification_code_layout, False)  # 默认隐藏

        # 密码输入框布局
        self.password_layout = QHBoxLayout()
        password_icon = QSvgWidget('icons/password.svg')  
        password_icon.setFixedSize(30, 30)  
        password_icon.setStyleSheet("margin-right: 10px;")
        self.password_layout.addWidget(password_icon)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setStyleSheet(input_style)
        self.password_layout.addWidget(self.password_input)

        content_layout.addLayout(self.username_layout)
        content_layout.addLayout(self.email_layout)
        content_layout.addLayout(self.verification_code_layout)
        content_layout.addLayout(self.password_layout)

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
        content_layout.addWidget(self.login_button, alignment=Qt.AlignmentFlag.AlignCenter)

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
        self.register_button.setVisible(False)
        content_layout.addWidget(self.register_button, alignment=Qt.AlignmentFlag.AlignCenter)

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
        self.installEventFilter(self)

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

    def switch_mode(self, mode):
        self.current_mode = mode
        if mode == "login":
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
            self.get_verification_code_button.setVisible(False)  # 登录模式下隐藏获取验证码按钮
            self.login_button.setVisible(True)
            self.register_button.setVisible(False)
            self._set_layout_visible(self.username_layout, False)  # 登录模式下隐藏用户名输入框
            self._set_layout_visible(self.verification_code_layout, False)  # 登录模式下隐藏验证码输入框
        elif mode == "register":
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
            self.get_verification_code_button.setVisible(True)  # 注册模式下显示获取验证码按钮
            self.login_button.setVisible(False)
            self.register_button.setVisible(True)
            self._set_layout_visible(self.username_layout, True)  # 注册模式下显示用户名输入框
            self._set_layout_visible(self.verification_code_layout, True)  # 注册模式下显示验证码输入框

    def _set_layout_visible(self, layout, visible):
        """设置布局中所有控件的可见性"""
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item.widget():
                item.widget().setVisible(visible)

if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    login_dialog = LoginDialog()
    login_dialog.show()
    sys.exit(app.exec())    