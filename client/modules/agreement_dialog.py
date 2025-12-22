from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, 
    QApplication, QPushButton, QWidget, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QPainter, QColor, QPen, QKeyEvent, QLinearGradient, QCursor, QBrush
from PyQt6.QtCore import Qt, QEvent

class AgreementCardWidget(QWidget):
    """用户协议对话框的卡片容器，带精美渐变背景和装饰"""
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.rect().adjusted(0, 0, -1, -1)
        
        # 创建更精美的渐变背景（从浅蓝到白色）
        gradient = QLinearGradient(rect.topLeft().toPointF(), rect.bottomLeft().toPointF())
        gradient.setColorAt(0, QColor(249, 250, 251, 255))  # 浅灰白
        gradient.setColorAt(0.5, QColor(255, 255, 255, 255))  # 纯白
        gradient.setColorAt(1, QColor(248, 250, 252, 255))  # 浅灰
        
        # 绘制圆角矩形背景
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawRoundedRect(rect, 24, 24)
        
        # 绘制精美的边框（带渐变效果）
        border_gradient = QLinearGradient(rect.topLeft().toPointF(), rect.topRight().toPointF())
        border_gradient.setColorAt(0, QColor(226, 232, 240, 180))
        border_gradient.setColorAt(0.5, QColor(203, 213, 225, 200))
        border_gradient.setColorAt(1, QColor(226, 232, 240, 180))
        
        border_pen = QPen(QBrush(border_gradient), 1.5)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 24, 24)
        
        painter.end()

class AgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户协议")
        parent_height = parent.height()
        max_height = min(parent_height + 100, 720)
        self.setFixedSize(720, max_height)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # 创建卡片容器（带阴影）
        card_widget = AgreementCardWidget()
        card_widget.setObjectName("agreement_card")
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 60))
        card_widget.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 标题栏容器（带渐变背景）
        header_widget = QWidget()
        header_widget.setFixedHeight(72)
        header_widget.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(239, 246, 255, 0.6),
                    stop:1 rgba(255, 255, 255, 0.3));
                border-top-left-radius: 24px;
                border-top-right-radius: 24px;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(28, 16, 20, 16)
        header_layout.setSpacing(12)

        # 标题图标装饰
        icon_label = QLabel("📋")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                background: transparent;
                padding: 0px;
            }
        """)
        header_layout.addWidget(icon_label)

        # 标题容器（带装饰线）
        title_container = QWidget()
        title_container.setStyleSheet("background: transparent;")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(4)
        
        title_label = QLabel("用户协议")
        title_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 24px; 
                font-weight: 700; 
                color: #1e293b; 
                padding: 0px;
                background: transparent;
            }
        """)
        title_layout.addWidget(title_label)
        
        # 装饰性下划线
        title_underline = QWidget()
        title_underline.setFixedHeight(3)
        title_underline.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6,
                    stop:1 #60a5fa);
                border-radius: 2px;
            }
        """)
        title_layout.addWidget(title_underline)
        
        header_layout.addWidget(title_container)
        header_layout.addStretch()

        # 关闭按钮（更精美）
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, 36)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 20px;
                font-weight: 400;
                color: #64748b;
                background-color: rgba(241, 245, 249, 0.8);
                border: 1px solid rgba(226, 232, 240, 0.6);
                border-radius: 18px;
            }
            QPushButton:hover {
                background-color: rgba(254, 242, 242, 1);
                border-color: rgba(254, 202, 202, 1);
                color: #dc2626;
            }
            QPushButton:pressed {
                background-color: rgba(254, 226, 226, 1);
            }
        """)
        close_btn.clicked.connect(self.close)
        header_layout.addWidget(close_btn)

        card_layout.addWidget(header_widget)

        # 精美的分隔线（带渐变）
        separator = QWidget()
        separator.setFixedHeight(2)
        separator.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 transparent,
                    stop:0.5 rgba(226, 232, 240, 0.6),
                    stop:1 transparent);
            }
        """)
        card_layout.addWidget(separator)

        # 内容区域（带内边距和背景）
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.5);
                border-bottom-left-radius: 24px;
                border-bottom-right-radius: 24px;
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(28, 24, 28, 28)
        content_layout.setSpacing(0)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                border: none;  
                background-color: transparent;  
                line-height: 2.0;
                color: #475569;
                padding: 4px;
            }
            QScrollBar:vertical {
                width: 10px;
                background-color: rgba(241, 245, 249, 0.8);
                border-radius: 5px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(148, 163, 184, 0.5),
                    stop:1 rgba(100, 116, 139, 0.7));
                border-radius: 5px;
                min-height: 40px;
            }
            QScrollBar::handle:vertical:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(100, 116, 139, 0.8),
                    stop:1 rgba(71, 85, 105, 0.9));
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
                    color: #2563eb;
                    font-size: 19px;
                    font-weight: 700;
                    margin-top: 2em;
                    margin-bottom: 0.8em;
                    padding-left: 8px;
                    border-left: 4px solid #3b82f6;
                    background: linear-gradient(to right, rgba(59, 130, 246, 0.1), transparent);
                    padding-top: 4px;
                    padding-bottom: 4px;
                }
                hr {
                    border: none;
                    border-bottom: 2px solid transparent;
                    border-image: linear-gradient(to right, transparent, #e2e8f0, transparent) 1;
                    margin: 14px 0 18px 0;
                }
                p {
                    text-indent: 2em;
                    color: #475569;
                    margin-top: 0.8em;
                    margin-bottom: 0.8em;
                    line-height: 2.0;
                    font-size: 14px;
                }
                h4 {
                    color: #dc2626;
                    font-weight: 700;
                    font-size: 16px;
                    margin-top: 2em;
                    margin-bottom: 0.8em;
                    padding: 16px 18px;
                    background: linear-gradient(135deg, rgba(254, 242, 242, 0.8), rgba(254, 226, 226, 0.6));
                    border-left: 4px solid #dc2626;
                    border-radius: 8px;
                    box-shadow: 0 2px 8px rgba(220, 38, 38, 0.1);
                }
            </style>
            <h3>1. 引言</h3>
            <hr>
            <p>欢迎使用本变声软件！在使用本软件前，请您仔细阅读并理解本用户协议。一旦您下载、安装或使用本软件，即表示您同意遵守本协议的所有条款。</p>
            <h3>2. 软件使用许可</h3>
            <hr>
            <p>2.1 本软件授予您非独占、不可转让的使用许可，仅供个人非商业用途。</p>
            <p>2.2 您不得对软件进行反向工程、反编译或试图以任何方式发现软件的源代码。</p>
            <h3>3. 用户行为规范</h3>
            <hr>
            <p>3.1 用户不得利用本软件进行任何违法或不当行为，包括但不限于传播非法、诈骗、侵犯他人版权或其他知识产权的内容。</p>
            <p>3.2 用户应当遵守所有适用的本地、国家及国际法律法规。对于用户通过软件进行的任何行为及其结果，用户应当独立承担全部责任。</p>
            <h3>4. 免责声明</h3>
            <hr>
            <p>4.1 用户明确同意其使用本软件所存在的风险将完全由其自己承担；因其使用软件而产生的一切后果也由其自己承担。</p>
            <p>4.2 本软件不对用户使用软件的行为及其结果承担责任。若用户的行为导致第三方损害的，用户应当独立承担责任；若因此给软件开发者或其关联方造成损失的，用户还应负责赔偿。</p>
            <h3>5. 修订和终止</h3>
            <hr>
            <p>5.1 本协议的修改和更新由软件开发者自行决定，并通过软件更新或官方公告的方式通知用户。用户继续使用软件将被视为接受修改后的协议。</p>
            <p>5.2 若用户违反本协议的任何条款，开发者有权随时终止用户的使用许可。</p>
            <h3>6. 其他</h3>
            <hr>
            <p>6.1 本协议的解释权和修改权归软件开发者所有。</p>
            <p>6.2 若本协议中的任何一条被视为废止、无效或因任何原因不可执行，该条应视为可从本协议中分离，不影响其余条款的有效性和可执行性。</p>
            <h4>通过安装、复制、下载或以其他方式使用本软件，您确认您已阅读本协议，并同意受其条款的约束。如果您不同意本协议的条款，请不要安装或使用本变声软件。</h4>
        """)
        content_layout.addWidget(text_edit)
        card_layout.addWidget(content_widget)
        main_layout.addWidget(card_widget)

    def showEvent(self, event):
        """对话框显示时安装事件过滤器"""
        super().showEvent(event)
        # 在应用程序级别安装事件过滤器，以便捕获对话框外部的点击事件
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            # 检查点击是否在对话框外部
            if self.isVisible() and not self.geometry().contains(event.globalPosition().toPoint()):
                # 检查点击是否发生在对话框的子控件上（如滚动条）
                widget_under_mouse = QApplication.widgetAt(event.globalPosition().toPoint())
                if widget_under_mouse is None or not self.isAncestorOf(widget_under_mouse):
                    self.close()
                    return True
        return super().eventFilter(obj, event)
    
    def closeEvent(self, event):
        """关闭对话框时移除应用程序级别的事件过滤器"""
        QApplication.instance().removeEventFilter(self)
        super().closeEvent(event)
    
    def hideEvent(self, event):
        """对话框隐藏时也移除事件过滤器（防止内存泄漏）"""
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(event)
    
    def keyPressEvent(self, event: QKeyEvent):
        """支持 ESC 键关闭对话框"""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """绘制透明背景"""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()