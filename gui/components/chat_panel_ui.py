from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton, QLineEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QKeySequence, QShortcut
from backend.resources import get_default_avatar
from gui.window_utils import set_icon_button
from gui.handlers import chat_handlers

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def create_chat_panel_ui(main_window: "MainWindow", parent=None):
    chat_panel = QWidget(parent)
    chat_panel.setObjectName("chatPanel")
    chat_panel.setStyleSheet("""
        #chatPanel {
            background-color: transparent;
        }
    """)

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

    header = _create_chat_header(main_window)
    container_layout.addWidget(header)

    body = _create_chat_body(main_window)
    container_layout.addWidget(body)

    root_layout.addWidget(container)
    return chat_panel


def _create_chat_header(main_window: "MainWindow") -> QWidget:
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

    title_label = QLabel("声音序章")
    title_label.setStyleSheet("""
        QLabel {
            color: #ffffff;
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 16px;
            font-weight: 700;
        }
    """)
    header_layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
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
    minimize_chat_btn.clicked.connect(lambda: chat_handlers.minimize_chat_panel(main_window))
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
    close_chat_btn.clicked.connect(lambda: chat_handlers.close_chat_panel(main_window))
    header_layout.addWidget(close_chat_btn)

    return header


def _create_chat_body(main_window: "MainWindow") -> QWidget:
    from gui.components.faq_widgets import create_faq_container
    
    body = QWidget()
    body_layout = QHBoxLayout(body)
    body_layout.setContentsMargins(0, 0, 0, 0)
    body_layout.setSpacing(0)

    # 左侧聊天区
    left_chat = _create_chat_area(main_window)
    body_layout.addLayout(left_chat, stretch=4)

    # 右侧FAQ区
    right_faq = create_faq_container(main_window)
    body_layout.addWidget(right_faq, stretch=1)

    return body


def _create_chat_area(main_window: "MainWindow") -> QVBoxLayout:
    left_layout = QVBoxLayout()
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(0)

    # 滚动区域
    main_window.chat_scroll_area = QScrollArea()
    main_window.chat_scroll_area.setWidgetResizable(True)
    main_window.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    main_window.chat_scroll_area.setStyleSheet("""
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
    main_window.chat_scroll_area.enterEvent = lambda e: chat_handlers.show_scrollbar_handle(main_window.chat_scroll_area)
    main_window.chat_scroll_area.leaveEvent = lambda e: chat_handlers.hide_scrollbar_handle(main_window.chat_scroll_area)

    main_window.chat_scroll_widget = QWidget()
    main_window.chat_layout = QVBoxLayout(main_window.chat_scroll_widget)
    main_window.chat_layout.setContentsMargins(10, 10, 10, 10)
    main_window.chat_layout.setSpacing(8)
    main_window.chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    main_window.chat_scroll_area.setWidget(main_window.chat_scroll_widget)
    left_layout.addWidget(main_window.chat_scroll_area, stretch=1)

    # 初始化头像URL
    main_window._support_avatar_url = ""
    main_window._user_avatar_url = ""
    default_bytes = get_default_avatar()
    if default_bytes:
        from gui.window_utils import avatar_bytes_to_data_url
        main_window._support_avatar_url = avatar_bytes_to_data_url(default_bytes)
        main_window._user_avatar_url = main_window._support_avatar_url

    # 底部输入栏
    input_bar = _create_chat_input_bar(main_window)
    left_layout.addWidget(input_bar)

    return left_layout


def _create_chat_input_bar(main_window: "MainWindow") -> QWidget:
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

    # 工具栏：表情、图片、文件
    tools_row = QHBoxLayout()
    tools_row.setContentsMargins(0, 0, 0, 0)
    tools_row.setSpacing(10)

    main_window.emoji_button = QPushButton()
    set_icon_button(main_window.emoji_button, 15, "表情")
    main_window.emoji_button.clicked.connect(lambda: chat_handlers.open_emoji_menu(main_window))
    tools_row.addWidget(main_window.emoji_button, alignment=Qt.AlignmentFlag.AlignLeft)

    main_window.pic_button = QPushButton()
    set_icon_button(main_window.pic_button, 17, "发送图片")
    main_window.pic_button.clicked.connect(lambda: chat_handlers.send_image(main_window))
    tools_row.addWidget(main_window.pic_button, alignment=Qt.AlignmentFlag.AlignLeft)

    main_window.file_button = QPushButton()
    set_icon_button(main_window.file_button, 16, "发送文件（≤100MB）")
    main_window.file_button.clicked.connect(lambda: chat_handlers.send_file(main_window))
    tools_row.addWidget(main_window.file_button, alignment=Qt.AlignmentFlag.AlignLeft)

    tools_row.addStretch()
    input_layout.addLayout(tools_row)

    # 输入行
    input_row = QHBoxLayout()
    input_row.setContentsMargins(0, 0, 0, 0)
    input_row.setSpacing(10)

    main_window.chat_input = QLineEdit()
    main_window.chat_input.setPlaceholderText("输入消息，回车或点击发送")
    main_window.chat_input.setFixedHeight(40)
    main_window.chat_input.setStyleSheet("""
        QLineEdit {
            border-radius: 20px;
            border: 1px solid rgba(203, 213, 225, 200);
            padding: 8px 14px;
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px;
            background-color: #ffffff;
        }
        QLineEdit:focus {
            border-color: #7c3aed;
        }
        QLineEdit:disabled {
            background-color: #f1f5f9;
            color: #94a3b8;
        }
    """)
    main_window.chat_input.returnPressed.connect(lambda: chat_handlers.handle_chat_send(main_window))
    
    # 快捷键：Ctrl+Enter 发送消息
    ctrl_enter_shortcut = QShortcut(QKeySequence("Ctrl+Return"), main_window.chat_input)
    ctrl_enter_shortcut.activated.connect(lambda: chat_handlers.handle_chat_send(main_window))

    main_window.chat_send_button = QPushButton("发送")
    main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    main_window.chat_send_button.setFixedHeight(40)
    main_window.chat_send_button.setStyleSheet("""
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
        QPushButton:disabled {
            background-color: #c4b5fd;
            color: #f3f4f6;
        }
    """)
    main_window.chat_send_button.clicked.connect(lambda: chat_handlers.handle_chat_send(main_window))

    input_row.addWidget(main_window.chat_input, stretch=1)
    input_row.addWidget(main_window.chat_send_button, stretch=0)
    input_layout.addLayout(input_row)

    return input_bar


