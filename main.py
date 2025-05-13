import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QDialog, QTextEdit, QGraphicsDropShadowEffect)
from PySide6.QtGui import QPixmap, QFont, QCursor, QPainter, QColor
from PySide6.QtCore import Qt, QSize, QTimer


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(500, 450)
        # 先清空可能存在的干扰样式，再设置带透明度和圆角的样式
        self.setStyleSheet("") 
        self.setStyleSheet("""
            QDialog {
                background-color: rgba(255, 255, 255, 0.8);  
                border-radius: 30px;
            }
        """)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)  # 去掉标题栏和关闭按钮

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 创建一个水平布局来放置"用户登录"标签，并使其占据整个宽度
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)  # 消除内边距
        
        user_login_label = QLabel("用户登录")
        user_login_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        user_login_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)  # 垂直居中，水平左对齐
        
        header_layout.addWidget(user_login_label)
        header_layout.addStretch()  # 添加伸展项，将标签推到左侧
        
        main_layout.addLayout(header_layout)
        main_layout.addSpacing(20)

        # 显示"QQ"文本，居中显示
        qq_label = QLabel("QQ")
        qq_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin-bottom: 15px;")
        qq_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(qq_label)

        # 显示QQ登录二维码，居中显示
        qr_label = QLabel(self)
        
        # 使用临时占位图片，实际使用时请替换为真实图片路径
        qr_pixmap = QPixmap()
        if not qr_pixmap.load("path_to_your_qq_qr_image.png"):
            # 如果加载失败，创建一个临时的占位图片
            qr_pixmap = QPixmap(200, 200)
            qr_pixmap.fill(Qt.lightGray)
            # 在占位图上绘制提示文字
            painter = QPainter(qr_pixmap)
            painter.setPen(Qt.black)
            painter.drawText(qr_pixmap.rect(), Qt.AlignCenter, "QQ二维码")
            painter.end()
        
        qr_label.setPixmap(qr_pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        qr_label.setAlignment(Qt.AlignCenter)
        qr_label.setStyleSheet("border-radius: 10px;")  # 给二维码区域添加圆角
        
        main_layout.addWidget(qr_label)

        # 只保留QQ登录按钮
        qq_button = QPushButton("使用 QQ 登录")
        qq_button.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 20px;
                padding: 12px 30px;
                font-size: 16px;
                min-width: 220px;
                margin-top: 25px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        # 去除按钮阴影，若后续仍需阴影，可根据实际情况调整相关参数
        # button_shadow = QGraphicsDropShadowEffect()
        # button_shadow.setBlurRadius(10)
        # button_shadow.setColor(QColor(0, 0, 0, 50))
        # button_shadow.setOffset(0, 3)
        # qq_button.setGraphicsEffect(button_shadow)
        
        main_layout.addWidget(qq_button, alignment=Qt.AlignCenter)
        main_layout.addSpacing(25)  # 增加按钮和协议之间的间距

        # 用户协议文本
        agreement_layout = QHBoxLayout()
        text_label = QLabel("登录即代表你已阅读并同意 ")
        text_label.setStyleSheet("font-size: 16px; color: #666;")  # 增大字体

        # 创建可点击的协议文本
        agreement_label = QLabel("《用户协议》")
        agreement_label.setStyleSheet("font-size: 16px; color: #409EFF; text-decoration: none;")  # 增大字体并去掉下划线
        agreement_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard | Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        agreement_label.setOpenExternalLinks(False)
        agreement_label.setCursor(QCursor(Qt.PointingHandCursor))
        agreement_label.linkActivated.connect(self.show_agreement)

        agreement_layout.addWidget(text_label)
        agreement_layout.addWidget(agreement_label)
        agreement_layout.setAlignment(Qt.AlignCenter)
        main_layout.addLayout(agreement_layout)

        self.setLayout(main_layout)

    def show_agreement(self):
        agreement_dialog = AgreementDialog(self)
        agreement_dialog.exec()


class AgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户协议")
        self.setFixedSize(600, 500)
        self.setStyleSheet("background-color: white; border-radius: 10px;")

        layout = QVBoxLayout()

        title_label = QLabel("用户协议")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #333; margin: 15px 0;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 协议内容区域，使用QTextEdit显示可滚动的文本
        agreement_text = QTextEdit()
        agreement_text.setReadOnly(True)
        agreement_text.setStyleSheet("border: 1px solid #ccc; padding: 10px; border-radius: 5px;")
        agreement_text.setHtml("""
            <h3>用户协议</h3>
            <p>欢迎使用我们的变声器产品！在使用本服务之前，请仔细阅读以下条款。</p>
            <h4>1. 服务条款</h4>
            <p>本服务由XXX公司提供，您同意遵守本协议的所有条款和条件。</p>
            <h4>2. 隐私政策</h4>
            <p>我们尊重您的隐私，您的个人信息将按照我们的隐私政策进行处理。</p>
            <h4>3. 知识产权</h4>
            <p>本服务中包含的所有内容，包括但不限于文本、图形、 logos等均受版权保护。</p>
            <h4>4. 责任限制</h4>
            <p>在任何情况下，我们对因使用本服务而导致的任何直接、间接损失不承担责任。</p>
            <h4>5. 变更条款</h4>
            <p>我们保留随时修改本协议的权利，修改后的协议将在发布时生效。</p>
            <p>通过使用本服务，即表示您同意接受本协议的条款和条件的约束。如果您不同意这些条款，请不要使用本服务。</p>
        """)
        layout.addWidget(agreement_text)

        close_button = QPushButton("关闭")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #409EFF;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 10px 20px;
                font-size: 16px;
                width: 100px;
                margin-top: 15px;
            }
            QPushButton:hover {
                background-color: #66b1ff;
            }
        """)
        
        close_button.clicked.connect(self.accept)
        close_button.setAlignment(Qt.AlignCenter)
        layout.addWidget(close_button, alignment=Qt.AlignCenter)
        self.setLayout(layout)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("变声器")
        self.setFixedSize(1970, 1080)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
        """)  # 修正了背景色设置

        # 初始化主窗口UI组件
        self.initUI()

        # 使用QTimer在主窗口显示后延迟3秒(3000毫秒)弹出登录对话框
        QTimer.singleShot(3000, self.show_login_dialog)

    def initUI(self):
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 添加标题标签
        title_label = QLabel("欢迎使用变声器")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #333; margin: 30px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 添加占位文本，实际使用时替换为你的功能UI
        placeholder_text = QLabel("主界面内容区域 - 这里将显示变声器的主要功能")
        placeholder_text.setStyleSheet("font-size: 20px; color: #666; margin: 30px;")
        placeholder_text.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(placeholder_text)

    def show_login_dialog(self):
        # 创建并显示登录对话框
        login_dialog = LoginDialog(self)
        login_dialog.exec()


if __name__ == "__main__":
    # 修复：在创建QApplication实例之前设置高DPI策略
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())