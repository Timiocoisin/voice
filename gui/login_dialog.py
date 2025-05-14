from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QDialog, QLineEdit)
from PyQt6.QtCore import Qt, QEvent
from PyQt6.QtGui import QCursor, QPainter, QColor
from gui.clickable_label import ClickableLabel
from gui.agreement_dialog import AgreementDialog

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        screen_width = self.screen_size(0.25)
        self.setFixedSize(screen_width, int(screen_width * 1.2))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.agreement_dialog = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        header_layout = QHBoxLayout()
        user_login_label = QLabel("用户登录")
        user_login_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 25px; 
            font-weight: bold; 
            color: #222;
            letter-spacing: 1px;
        """)
        user_login_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(user_login_label)
        header_layout.addStretch()
        content_layout.addLayout(header_layout)

        label_style = """
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 15px; 
            font-weight: bold; 
            color: #222;
            letter-spacing: 1px;
        """
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

        username_layout = QHBoxLayout()
        username_label = QLabel("用户名")
        username_label.setStyleSheet(label_style + " margin-right: 10px;")
        username_layout.addWidget(username_label)
        username_input = QLineEdit()
        username_input.setPlaceholderText("请输入用户名")
        username_input.setStyleSheet(input_style)
        username_layout.addWidget(username_input)
        content_layout.addLayout(username_layout)

        email_layout = QHBoxLayout()
        email_label = QLabel("邮箱")
        email_label.setStyleSheet(label_style + " margin-right: 23px;")
        email_layout.addWidget(email_label)
        email_input = QLineEdit()
        email_input.setPlaceholderText("请输入邮箱")
        email_input.setStyleSheet(input_style)
        email_layout.addWidget(email_input)
        content_layout.addLayout(email_layout)

        password_layout = QHBoxLayout()
        password_label = QLabel("密码")
        password_label.setStyleSheet(label_style + " margin-right: 23px;")
        password_layout.addWidget(password_label)
        password_input = QLineEdit()
        password_input.setPlaceholderText("请输入密码")
        password_input.setEchoMode(QLineEdit.EchoMode.Password)
        password_input.setStyleSheet(input_style)
        password_layout.addWidget(password_input)
        content_layout.addLayout(password_layout)

        qq_button = QPushButton("登录")
        qq_button.setStyleSheet("""
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
        content_layout.addWidget(qq_button, alignment=Qt.AlignmentFlag.AlignCenter)

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