from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel)
from PyQt6.QtCore import Qt, QTimer, QEvent
from gui.login_dialog import LoginDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("变声器")
        self.setFixedSize(self.screen_size(0.8), self.screen_size(0.8, height=True))  # 窗口大小为屏幕的80%
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
        """)  # 修正了背景色设置

        # 初始化主窗口UI组件
        self.initUI()

        # 使用QTimer在主窗口显示后延迟3秒(3000毫秒)弹出登录对话框
        QTimer.singleShot(3000, self.show_login_dialog)
        
        # 存储登录对话框的引用
        self.login_dialog = None
        
        # 安装事件过滤器，处理点击主窗口收起协议对话框
        self.installEventFilter(self)

    def screen_size(self, ratio, height=False):
        """根据屏幕大小计算组件大小"""
        screen = QApplication.primaryScreen()
        size = screen.size()
        if height:
            return int(size.height() * ratio)
        return int(size.width() * ratio)

    def initUI(self):
        # 创建中央部件和布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 添加标题标签
        title_label = QLabel("欢迎使用变声器")
        title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #333; margin: 30px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title_label)

        # 添加占位文本，实际使用时替换为你的功能UI
        placeholder_text = QLabel("主界面内容区域 - 这里将显示变声器的主要功能")
        placeholder_text.setStyleSheet("font-size: 20px; color: #666; margin: 30px;")
        placeholder_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(placeholder_text)

    def show_login_dialog(self):
        # 创建并显示登录对话框
        self.login_dialog = LoginDialog(self)
        self.login_dialog.show()

    def eventFilter(self, obj, event):
        # 处理鼠标点击事件
        if event.type() == QEvent.Type.MouseButtonPress:
            # 如果登录对话框和协议对话框都存在且可见
            if (self.login_dialog and self.login_dialog.agreement_dialog 
                and self.login_dialog.agreement_dialog.isVisible()):
                # 检查点击是否发生在主窗口内
                if self.geometry().contains(event.globalPosition().toPoint()):
                    self.login_dialog.agreement_dialog.close()
                    return True  # 拦截事件，不再继续处理
                
                # 检查点击是否发生在登录对话框内
                if self.login_dialog.geometry().contains(event.globalPosition().toPoint()):
                    # 如果点击登录对话框但不在协议对话框内，关闭协议对话框
                    if not self.login_dialog.agreement_dialog.geometry().contains(event.globalPosition().toPoint()):
                        self.login_dialog.agreement_dialog.close()
                        return True  # 拦截事件，不再继续处理
        
        return super().eventFilter(obj, event)