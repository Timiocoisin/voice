"""
聊天面板视图组件。

包含聊天消息显示、输入框、FAQ 等功能的完整聊天面板。
"""
from typing import TYPE_CHECKING, Optional
from datetime import datetime
import os
import base64
import random
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QTextEdit,
    QPushButton,
    QMenu,
    QWidgetAction,
    QGridLayout,
    QFileDialog,
    QDialog,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, QTimer, QPoint
from PyQt6.QtGui import QPixmap, QCursor, QPainter, QPainterPath, QBrush, QColor, QIcon, QKeyEvent, QKeySequence
from PyQt6.QtWidgets import QShortcut
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import QByteArray, QBuffer, QIODevice

from client.resources import get_default_avatar, load_icon_path
from gui.components.chat_bubble import ChatBubble
from gui.config import FAQ_CONTAINER_WIDTH, CHAT_INPUT_HEIGHT

if TYPE_CHECKING:
    from gui.main_window import MainWindow


class ChatPanel:
    """聊天面板组件构建器。"""

    def __init__(self, main_window: "MainWindow"):
        """
        初始化聊天面板。

        Args:
            main_window: 主窗口实例
        """
        self.main_window = main_window

    def create(self, parent: Optional[QWidget] = None) -> QWidget:
        """
        创建聊天面板组件。

        Args:
            parent: 父控件

        Returns:
            配置好的聊天面板 QWidget
        """
        chat_panel = QWidget(parent)
        chat_panel.setObjectName("chatPanel")
        chat_panel.setStyleSheet("""
            #chatPanel {
                background-color: transparent;
            }
        """)

        # 根容器：整体包裹聊天+FAQ，右侧栏目嵌在同一个白色框内
        root_layout = QHBoxLayout(chat_panel)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        container = QWidget()
        container.setObjectName("chatContainer")
        container.setStyleSheet("""
            #chatContainer {
                background-color: #ffffff;
                border-radius: 16px;
                border: 1px solid rgba(226, 232, 240, 200);
            }
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # 顶部标题栏
        header = self._create_header()
        container_layout.addWidget(header)

        # 中部主体：左聊天区 + 右 FAQ
        body = self._create_body()
        container_layout.addWidget(body)

        root_layout.addWidget(container)
        
        # 为聊天面板添加ESC键关闭功能
        def chat_panel_key_press_event(event: QKeyEvent):
            if event.key() == Qt.Key.Key_Escape:
                self.main_window._close_chat_panel()
            else:
                # 调用父类的keyPressEvent
                QWidget.keyPressEvent(chat_panel, event)
        
        chat_panel.keyPressEvent = chat_panel_key_press_event
        # 确保聊天面板可以接收键盘事件
        chat_panel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        return chat_panel

    def _create_header(self) -> QWidget:
        """创建聊天面板顶部标题栏。"""
        header = QWidget()
        header.setObjectName("chatHeader")
        header.setStyleSheet("""
            #chatHeader {
                background-color: #7c3aed;
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        header_layout.setSpacing(10)

        title_label = QLabel("云汐幻声")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;
                font-weight: 700;
            }
        """)
        header_layout.addWidget(
            title_label,
            alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )

        # 模式指示：仅文字（取消呼吸灯）
        mode_label = QLabel("智能机器人模式")
        mode_label.setObjectName("modeIndicator")
        mode_label.setStyleSheet("""
            QLabel#modeIndicator {
                color: #e5e7eb;
                font-size: 13px;
            }
        """)
        self.main_window.chat_mode_label = mode_label
        header_layout.addWidget(mode_label, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        header_layout.addStretch()

        # 最小化按钮
        minimize_chat_btn = QPushButton("—")
        minimize_chat_btn.setFixedSize(28, 28)
        minimize_chat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        minimize_chat_btn.setToolTip("最小化聊天")
        minimize_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 14px;
                font-size: 14px;
                font-weight: 700;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.3);
            }
        """)
        minimize_chat_btn.clicked.connect(self.main_window._minimize_chat_panel)
        header_layout.addWidget(minimize_chat_btn)

        # 关闭按钮
        close_chat_btn = QPushButton("✕")
        close_chat_btn.setFixedSize(28, 28)
        close_chat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_chat_btn.setToolTip("结束聊天")
        close_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.2);
                border: none;
                border-radius: 14px;
                font-size: 14px;
                color: #ffffff;
            }
            QPushButton:hover {
                background-color: rgba(239, 68, 68, 0.8);
            }
        """)
        close_chat_btn.clicked.connect(self.main_window._close_chat_panel)
        header_layout.addWidget(close_chat_btn)

        return header

    def _create_body(self) -> QWidget:
        """创建聊天面板主体（聊天区 + FAQ）。"""
        body = QWidget()
        body_layout = QHBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 左侧聊天区
        left_layout = self._create_chat_area()
        body_layout.addLayout(left_layout, stretch=4)

        # 右侧 FAQ
        faq_container = self._create_faq_area()
        body_layout.addWidget(faq_container, stretch=1)

        return body

    def _create_chat_area(self) -> QVBoxLayout:
        """创建左侧聊天区域。"""
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 滚动区域
        self.main_window.chat_scroll_area = QScrollArea()
        self.main_window.chat_scroll_area.setWidgetResizable(True)
        self.main_window.chat_scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.main_window.chat_scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f4f5f7;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #f4f5f7;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(148, 163, 184, 0);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        self.main_window.chat_scroll_area.enterEvent = (
            lambda e: self.main_window._show_scrollbar_handle(
                self.main_window.chat_scroll_area
            )
        )
        self.main_window.chat_scroll_area.leaveEvent = (
            lambda e: self.main_window._hide_scrollbar_handle(
                self.main_window.chat_scroll_area
            )
        )

        self.main_window.chat_scroll_widget = QWidget()
        self.main_window.chat_layout = QVBoxLayout(self.main_window.chat_scroll_widget)
        self.main_window.chat_layout.setContentsMargins(10, 10, 10, 10)
        self.main_window.chat_layout.setSpacing(8)
        self.main_window.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.main_window.chat_scroll_area.setWidget(self.main_window.chat_scroll_widget)
        left_layout.addWidget(self.main_window.chat_scroll_area, stretch=1)

        # 预生成默认头像 Data URL
        self.main_window._support_avatar_url = ""
        self.main_window._user_avatar_url = ""
        default_bytes = get_default_avatar()
        if default_bytes:
            self.main_window._support_avatar_url = (
                self.main_window._avatar_bytes_to_data_url(default_bytes)
            )
            self.main_window._user_avatar_url = self.main_window._support_avatar_url

        # 底部输入栏
        input_bar = self._create_input_bar()
        left_layout.addWidget(input_bar)

        return left_layout

    def _create_input_bar(self) -> QWidget:
        """创建聊天输入栏。"""
        input_bar = QWidget()
        input_bar.setObjectName("chatInputBar")
        input_bar.setStyleSheet("""
            #chatInputBar {
                background-color: #f8fafc;
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
                border-top: 1px solid rgba(226, 232, 240, 180);
            }
        """)
        input_layout = QVBoxLayout(input_bar)
        input_layout.setContentsMargins(12, 10, 12, 12)
        input_layout.setSpacing(8)

        # 工具栏
        tools_row = QHBoxLayout()
        tools_row.setContentsMargins(0, 0, 0, 0)
        tools_row.setSpacing(10)

        self.main_window.emoji_button = QPushButton()
        self.main_window._set_icon_button(self.main_window.emoji_button, 15, "表情")
        self.main_window.emoji_button.clicked.connect(self.main_window.open_emoji_menu)
        tools_row.addWidget(
            self.main_window.emoji_button,
            alignment=Qt.AlignmentFlag.AlignLeft
        )

        self.main_window.pic_button = QPushButton()
        self.main_window._set_icon_button(self.main_window.pic_button, 17, "发送图片")
        self.main_window.pic_button.clicked.connect(self.main_window.send_image)
        tools_row.addWidget(
            self.main_window.pic_button,
            alignment=Qt.AlignmentFlag.AlignLeft
        )

        tools_row.addStretch()
        input_layout.addLayout(tools_row)

        # 输入行
        input_row = QHBoxLayout()
        input_row.setContentsMargins(0, 0, 0, 0)
        input_row.setSpacing(10)

        self.main_window.chat_input = QTextEdit()
        self.main_window.chat_input.setPlaceholderText("输入消息，回车发送，Ctrl+Enter换行")
        self.main_window.chat_input.setFixedHeight(max(60, CHAT_INPUT_HEIGHT + 20))
        self.main_window.chat_input.setStyleSheet("""
            QTextEdit {
                border-radius: 20px;
                border: 1px solid rgba(203, 213, 225, 200);
                padding: 8px 14px;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                background-color: #ffffff;
            }
            QTextEdit:focus {
                border-color: #7c3aed;
            }
            QTextEdit:disabled {
                background-color: #f1f5f9;
                color: #94a3b8;
            }
        """)
        self.main_window.chat_input.setAcceptRichText(False)

        # 自定义按键行为：Enter 发送，Ctrl+Enter 换行
        def chat_input_key_press_event(event: QKeyEvent):
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    cursor = self.main_window.chat_input.textCursor()
                    cursor.insertText("\n")
                    self.main_window.chat_input.setTextCursor(cursor)
                    event.accept()
                    return
                else:
                    self.main_window._handle_chat_send()
                    event.accept()
                    return
            QTextEdit.keyPressEvent(self.main_window.chat_input, event)

        self.main_window.chat_input.keyPressEvent = chat_input_key_press_event

        send_button = QPushButton("发送")
        send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        send_button.setFixedHeight(CHAT_INPUT_HEIGHT)
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: #ffffff;
                border-radius: 20px;
                padding: 8px 20px;
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #6d28d9;
            }
            QPushButton:pressed {
                background-color: #5b21b6;
            }
        """)
        send_button.clicked.connect(self.main_window._handle_chat_send)

        input_row.addWidget(self.main_window.chat_input, stretch=1)
        input_row.addWidget(send_button, stretch=0)
        input_layout.addLayout(input_row)

        return input_bar

    def _create_faq_area(self) -> QWidget:
        """创建右侧 FAQ 区域。"""
        faq_container = QWidget()
        faq_container.setObjectName("faqContainer")
        faq_container.setFixedWidth(FAQ_CONTAINER_WIDTH)
        faq_container.setStyleSheet("""
            #faqContainer {
                background-color: #ffffff;
                border-left: 1px solid rgba(226, 232, 240, 0.5);
            }
        """)
        faq_layout = QVBoxLayout(faq_container)
        faq_layout.setContentsMargins(14, 14, 14, 14)
        faq_layout.setSpacing(8)

        faq_title = QLabel("💡 常见问题")
        faq_title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 700;
                color: #7c3aed;
                padding-bottom: 8px;
            }
        """)
        faq_layout.addWidget(faq_title)

        # 可滚动的 FAQ 内容区域
        faq_scroll = QScrollArea()
        faq_scroll.setWidgetResizable(True)
        faq_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
                margin: 0px;
                padding: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(148, 163, 184, 0);
                border-radius: 3px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: transparent;
            }
        """)
        faq_scroll.enterEvent = (
            lambda e: self.main_window._show_scrollbar_handle(faq_scroll)
        )
        faq_scroll.leaveEvent = (
            lambda e: self.main_window._hide_scrollbar_handle(faq_scroll)
        )

        faq_content = QWidget()
        faq_content_layout = QVBoxLayout(faq_content)
        faq_content_layout.setContentsMargins(0, 0, 0, 0)
        faq_content_layout.setSpacing(10)

        # FAQ 问题 1
        faq1 = self.main_window._create_faq_item(
            "📱 手机能不能使用变声器？",
            """<p style="color:#374151; margin:0 0 8px 0;">软件需要电脑运行，可转接到手机：</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>方法一</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
买转接器（如 <span style="color:#7c3aed;">直播一号</span> / <span style="color:#7c3aed;">ds7pro</span>），把声音转到手机。
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>方法二</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
用支持 OTG 的声卡（如 <span style="color:#7c3aed;">艾肯micu</span> / <span style="color:#7c3aed;">midi r2</span>），直接插上即可。
</p>"""
        )
        faq_content_layout.addWidget(faq1)

        # FAQ 问题 2
        faq2 = self.main_window._create_faq_item(
            "🎛️ 变声参数怎么设置？",
            """<p style="color:#374151; margin:0 0 8px 0;">参数：<b>音调、音量、延迟、阈值</b></p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>音调</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
男→女：<span style="color:#7c3aed;">10~14</span><br/>
女→男：<span style="color:#7c3aed;">-14~-10</span><br/>
同性：<span style="color:#7c3aed;">0 左右</span>
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>音量</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
不要太高，易爆音失真<br/>
建议 <span style="color:#7c3aed;">0.5 左右</span>
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>延迟</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
一般 <span style="color:#7c3aed;">0.5~0.7</span><br/>
配置好可压低到 <span style="color:#7c3aed;">0.3</span><br/>
打游戏时适当调高
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>阈值</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
默认 <span style="color:#7c3aed;">-60</span><br/>
环境吵选 <span style="color:#7c3aed;">-57</span> 减少噪音
</p>"""
        )
        faq_content_layout.addWidget(faq2)

        # FAQ 问题 3
        faq3 = self.main_window._create_faq_item_with_images(
            "🔊 如何安装虚拟声卡？",
            """<p style="color:#374151; margin:0 0 8px 0;"><b>步骤：</b></p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>打开设置中心，安装虚拟声卡</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
点击虚拟声卡，一键安装后，打开声音设置。<br/>
确保系统声音中：<br/>
• 默认播放：<span style="color:#7c3aed;">耳机</span><br/>
• 默认录制：<span style="color:#7c3aed;">幻音麦克风</span>
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>设置幻音麦克风</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
需要设置采样和监听：<br/>
• 不设置采样 → 无法变声<br/>
• 不设置监听 → 听不到效果
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>对齐采样 48000</b>（点击图片放大）</p>""",
            [("resources/images/play.png", "采样设置")],
            """<p style="margin:8px 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>监听设置</b>（不想听可去掉）</p>""",
            [("resources/images/monitor.png", "监听设置")],
            """<p style="margin:8px 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>无法直接安装？</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
找到安装目录：<br/>
<span style="color:#7c3aed;">\\resources\\server\\driver</span><br/>
右键管理员运行 <span style="color:#7c3aed;">Setup.exe</span>
</p>"""
        )
        faq_content_layout.addWidget(faq3)

        faq_content_layout.addStretch()
        faq_scroll.setWidget(faq_content)
        faq_layout.addWidget(faq_scroll, stretch=1)

        return faq_container





