import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QPushButton, QDialog, QTextEdit)
from PyQt6.QtGui import QPixmap, QFont, QCursor, QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QSize, QPoint, QTimer, QEvent, pyqtSignal


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户协议")
        self.setFixedSize(600, 700)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 创建主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 标题栏
        title_label = QLabel("用户协议")
        title_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 18px; 
            font-weight: bold; 
            color: #333; 
            padding: 5px 0;
            text-align: center;
        """)
        main_layout.addWidget(title_label)

        # 协议内容 - 修改为无边框透明背景
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                border: none;  /* 无边框 */
                background-color: transparent;  /* 透明背景 */
                line-height: 1.5;
            }
            QScrollBar:vertical {
                width: 10px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: #ccc;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                background-color: transparent;
            }
        """)
        text_edit.setHtml("""
            <style>
                h3 {
                    color: #007bff;
                    font-size: 16px;
                    margin-top: 1.5em;  /* 增加标题上方间距 */
                }
                hr {
                    border: none;
                    border-bottom: 3px solid #007bff;  /* 使用border-bottom替代border */
                    margin: 10px 0 15px 0;
                }
                p {
                    text-indent: 2em;
                    color: #666;
                    margin-top: 0.8em;  /* 增加段落间距 */
                    margin-bottom: 0.8em;
                }
                h4 {  /* 最后一段文字 */
                    color: #ff0000;  /* 红色文字 */
                    font-weight: 500;  /* 加粗 */
                    margin-top: 1.5em;  /* 增加上方间距 */
                }
            </style>
            <h3>1. 引言</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;欢迎使用本变声软件！在使用本软件前，请您仔细阅读并理解本用户协议。一旦您下载、安装或使用本软件，即表示您同意遵守本协议的所有条款。</p>
            <h3>2. 软件使用许可</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1 本软件授予您非独占、不可转让的使用许可，仅供个人非商业用途。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2 您不得对软件进行反向工程、反编译或试图以任何方式发现软件的源代码。</p>
            <h3>3. 用户行为规范</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.1 用户不得利用本软件进行任何违法或不当行为，包括但不限于传播非法、诈骗、侵犯他人版权或其他知识产权的内容。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.2 用户应当遵守所有适用的本地、国家及国际法律法规。对于用户通过软件进行的任何行为及其结果，用户应当独立承担全部责任。</p>
            <h3>4. 免责声明</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1 用户明确同意其使用本软件所存在的风险将完全由其自己承担；因其使用软件而产生的一切后果也由其自己承担。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.2 本软件不对用户使用软件的行为及其结果承担责任。若用户的行为导致第三方损害的，用户应当独立承担责任；若因此给软件开发者或其关联方造成损失的，用户还应负责赔偿。</p>
            <h3>5. 修订和终止</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.1 本协议的修改和更新由软件开发者自行决定，并通过软件更新或官方公告的方式通知用户。用户继续使用软件将被视为接受修改后的协议。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2 若用户违反本协议的任何条款，开发者有权随时终止用户的使用许可。</p>
            <h3>6. 其他</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6.1 本协议的解释权和修改权归软件开发者所有。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6.2 若本协议中的任何一条被视为废止、无效或因任何原因不可执行，该条应视为可从本协议中分离，不影响其余条款的有效性和可执行性。</p>
            <h4>通过安装、复制、下载或以其他方式使用本软件，您确认您已阅读本协议，并同意受其条款的约束。如果您不同意本协议的条款，请不要安装或使用本变声软件。</h4>
        """)
        main_layout.addWidget(text_edit)

        # 安装事件过滤器，用于检测点击外部区域
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        # 检测鼠标点击事件
        if event.type() == QEvent.Type.MouseButtonPress:
            # 如果点击发生在窗口外部
            if not self.geometry().contains(event.globalPosition().toPoint()):
                self.close()
                return True
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制半透明圆角背景 (220/255 ≈ 86% 不透明度)
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 220))  # 半透明白色
        painter.drawRoundedRect(rect, 15, 15)

        painter.end()


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        # 根据屏幕宽度动态设置窗口大小
        screen_width = self.screen_size(0.25)
        self.setFixedSize(screen_width, int(screen_width * 1.2))
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 存储用户协议对话框的引用
        self.agreement_dialog = None

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 创建内部容器控件
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)

        # 头部布局
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # 修正：标题应为"用户登录"
        user_login_label = QLabel("用户登录")
        user_login_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 15px; 
            font-weight: bold; 
            color: #222;
            letter-spacing: 1px;
        """)
        user_login_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        header_layout.addWidget(user_login_label)
        header_layout.addStretch()

        content_layout.addLayout(header_layout)

        # QQ文本
        qq_label = QLabel("QQ")
        qq_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 15px; 
            font-weight: bold; 
            color: #222;
            qproperty-alignment: AlignCenter;
            letter-spacing: 2px;
        """)
        content_layout.addWidget(qq_label)

        # 二维码区域用蓝色色块代替
        qr_label = QLabel()
        qr_pixmap_size = int(screen_width * 0.45)
        qr_pixmap = QPixmap(qr_pixmap_size, qr_pixmap_size)

        # 填充为蓝色色块
        qr_pixmap.fill(QColor(0, 160, 233))  # QQ蓝

        # 绘制简单的文本提示
        painter = QPainter(qr_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(255, 255, 255))  # 白色文字

        # 设置字体
        font = painter.font()
        font.setFamily("Microsoft YaHei")
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)

        # 绘制文本
        painter.drawText(qr_pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "扫码登录")

        painter.end()

        qr_label.setPixmap(qr_pixmap)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qr_label.setStyleSheet("background-color: transparent;")

        content_layout.addWidget(qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # QQ登录按钮
        qq_button = QPushButton("使用 QQ 登录")
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

        # 用户协议文本
        agreement_layout = QHBoxLayout()
        text_label = QLabel("登录即代表你已阅读并同意 ")
        text_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 16px; 
            color: #888;
            letter-spacing: 0.5px;
        """)

        # 使用自定义的可点击QLabel
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

        # 设置文本间距
        agreement_layout.setSpacing(3)

        agreement_layout.addWidget(text_label)
        agreement_layout.addWidget(agreement_label)
        agreement_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addLayout(agreement_layout)

        # 将内容控件添加到主布局
        main_layout.addWidget(content_widget)

        # 安装事件过滤器，处理点击外部关闭
        self.installEventFilter(self)

    def screen_size(self, ratio, height=False):
        screen = QApplication.primaryScreen()
        size = screen.size()
        if height:
            return int(size.height() * ratio)
        return int(size.width() * ratio)

    def show_agreement(self):
        # 如果对话框已存在但隐藏，则显示它
        if self.agreement_dialog and not self.agreement_dialog.isVisible():
            self.agreement_dialog.show()
            return

        # 创建新的用户协议对话框
        self.agreement_dialog = AgreementDialog(self)
        self.agreement_dialog.setWindowModality(Qt.WindowModality.NonModal)

        # 居中显示
        center = self.screen().geometry().center()
        self.agreement_dialog.move(center.x() - self.agreement_dialog.width() // 2,
                                  center.y() - self.agreement_dialog.height() // 2)

        self.agreement_dialog.show()

    def eventFilter(self, obj, event):
        # 处理鼠标点击事件
        if event.type() == QEvent.Type.MouseButtonPress:
            # 如果点击发生在登录对话框内，但不在协议对话框内
            if (self.agreement_dialog and self.agreement_dialog.isVisible() and
                not self.agreement_dialog.geometry().contains(event.globalPosition().toPoint())):
                self.agreement_dialog.close()

        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 绘制半透明圆角背景
        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 230))  # 半透明白色
        painter.drawRoundedRect(rect, 25, 25)

        painter.end()


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


if __name__ == "__main__":
    # 修复：在创建QApplication实例之前设置高DPI策略
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())