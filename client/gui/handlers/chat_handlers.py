import os
import random
from datetime import datetime
from typing import TYPE_CHECKING, List, Tuple, Optional

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QMenu, QWidgetAction, QGridLayout,
    QDialog, QFileDialog, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF
from PyQt6.QtGui import (
    QPixmap, QCursor, QPainter, QPainterPath, QColor
)

from client.resources import get_default_avatar
from gui.components.chat_bubble import ChatBubble
from gui.handlers import dialog_handlers
from gui.handlers.message_utils import show_message

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def open_customer_service_chat(main_window: "MainWindow", event):
    if event.button() != Qt.MouseButton.LeftButton:
        return

    # 未登录时，引导用户先登录，再联系客服
    if not main_window.user_id:
        show_message(
            main_window,
            "登录后即可联系客服为你处理问题。",
            "请先登录",
            variant="warning"
        )
        # 顺便弹出登录框
        dialog_handlers.show_login_dialog(main_window)
        return

    # 清除未读消息计数
    clear_unread_count(main_window)

    # 只初始化一次布局切换
    if getattr(main_window, "_chat_panel_added", False):
        main_window.chat_panel.setVisible(True)
        return

    # 从主布局移除中间和右侧（占原来的 3+1 比例），用一个聊天面板等效占比替换
    if main_window.merged_section2_layout:
        main_window.main_content_layout.removeItem(main_window.merged_section2_layout)
        if main_window.merged_section2:
            main_window.merged_section2.hide()
    if main_window.right_column_widget:
        main_window.main_content_layout.removeWidget(main_window.right_column_widget)
        main_window.right_column_widget.hide()

    # 聊天面板占据原中间+右侧的总宽度（保持左侧宽度不变）
    main_window.main_content_layout.addWidget(main_window.chat_panel, 4)
    main_window.chat_panel.setVisible(True)
    main_window._chat_panel_added = True


def clear_unread_count(main_window: "MainWindow"):
    """清除未读消息计数"""
    main_window.unread_count = 0
    update_unread_badge(main_window)


def update_unread_badge(main_window: "MainWindow"):
    """更新未读消息 badge 显示"""
    if not hasattr(main_window, "unread_badge"):
        return
    if main_window.unread_count <= 0:
        main_window.unread_badge.setVisible(False)
    else:
        main_window.unread_badge.setVisible(True)
        if main_window.unread_count > 10:
            main_window.unread_badge.setText("...")
        else:
            main_window.unread_badge.setText(str(main_window.unread_count))


def add_unread_count(main_window: "MainWindow"):
    """增加未读消息计数（聊天面板隐藏时调用）"""
    if not hasattr(main_window, "unread_count"):
        main_window.unread_count = 0
    main_window.unread_count += 1
    update_unread_badge(main_window)


def minimize_chat_panel(main_window: "MainWindow"):
    """最小化聊天面板（隐藏但保留聊天记录）"""
    if hasattr(main_window, "chat_panel") and main_window.chat_panel:
        main_window.chat_panel.setVisible(False)
        main_window._chat_minimized = True


def close_chat_panel(main_window: "MainWindow"):
    """关闭聊天面板（结束聊天服务，清空聊天记录）"""
    if hasattr(main_window, "chat_panel") and main_window.chat_panel:
        main_window.chat_panel.setVisible(False)
        # 清空聊天记录
        if hasattr(main_window, "chat_layout"):
            while main_window.chat_layout.count():
                item = main_window.chat_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        # 重置状态
        main_window._chat_minimized = False
        clear_unread_count(main_window)
        
        # 恢复原来的布局
        if getattr(main_window, "_chat_panel_added", False):
            main_window.main_content_layout.removeWidget(main_window.chat_panel)
            if main_window.merged_section2_layout:
                main_window.main_content_layout.removeItem(main_window.merged_section2_layout)
            if main_window.right_column_widget:
                main_window.main_content_layout.removeWidget(main_window.right_column_widget)

            if main_window.left_column_widget and main_window.main_content_layout.indexOf(main_window.left_column_widget) == -1:
                main_window.main_content_layout.addWidget(main_window.left_column_widget, 1)

            if main_window.merged_section2_layout:
                main_window.main_content_layout.addLayout(main_window.merged_section2_layout, 3)
                if main_window.merged_section2:
                    main_window.merged_section2.show()

            if main_window.right_column_widget:
                main_window.main_content_layout.addWidget(main_window.right_column_widget, 1)
                main_window.right_column_widget.show()

            main_window._chat_panel_added = False


def handle_chat_send(main_window: "MainWindow"):
    """发送消息并使用关键词匹配生成客服回复"""
    # 首先检查是否正在发送中，防止重复点击
    if hasattr(main_window, 'chat_send_button') and not main_window.chat_send_button.isEnabled():
        return
    if not main_window.chat_input.isEnabled():
        return
    
    # QTextEdit 使用 toPlainText() 方法获取文本内容
    text = main_window.chat_input.toPlainText().strip()
    if not text:
        return
    
    # 立即禁用发送按钮和输入框，防止重复发送
    main_window.chat_input.setEnabled(False)
    original_text = None
    if hasattr(main_window, 'chat_send_button'):
        original_text = main_window.chat_send_button.text()
        main_window.chat_send_button.setEnabled(False)
        main_window.chat_send_button.setText("发送中...")
        main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    append_chat_message(main_window, text, from_self=True)
    main_window.chat_input.clear()
    
    # 使用关键词匹配生成回复
    reply = main_window.keyword_matcher.generate_reply(text, add_greeting=True)
    
    # 模拟客服回复延迟
    delay = random.randint(500, 1500)
    
    def send_reply_and_enable():
        append_support_message(main_window, reply)
        # 恢复按钮和输入框状态
        main_window.chat_input.setEnabled(True)
        if hasattr(main_window, 'chat_send_button'):
            main_window.chat_send_button.setEnabled(True)
            if original_text:
                main_window.chat_send_button.setText(original_text)
            main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 延迟聚焦，确保 UI 更新完成后再聚焦
        QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
    
    QTimer.singleShot(delay, send_reply_and_enable)


def append_chat_message(
    main_window: "MainWindow",
    content: str,
    from_self: bool = True,
    is_html: bool = False,
    streaming: bool = False
):
    """按左右气泡形式追加一条消息，使用真实圆角控件"""
    if not hasattr(main_window, "chat_layout"):
        return

    # 容器：一条完整的消息
    message_widget = QWidget()
    v_layout = QVBoxLayout(message_widget)
    v_layout.setContentsMargins(4, 0, 4, 0)
    v_layout.setSpacing(2)

    # 用户消息：上方一行时间（右对齐）
    if from_self:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #9ca3af;
            }
        """)
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.addStretch()
        time_row.addWidget(time_label)
        v_layout.addLayout(time_row)

    # 气泡 + 头像 行
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    # 头像
    avatar_label = QLabel()
    avatar_label.setFixedSize(32, 32)
    if from_self and main_window.user_avatar_label.pixmap():
        pm = main_window.user_avatar_label.pixmap().scaled(
            32, 32,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        avatar_label.setPixmap(pm)
    else:
        default_bytes = get_default_avatar()
        if default_bytes:
            pm = QPixmap()
            if pm.loadFromData(default_bytes):
                avatar_label.setPixmap(
                    pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
                )

    if from_self:
        bubble_label = ChatBubble(
            content,
            background=QColor("#dcf8c6"),
            text_color=QColor("#0f172a"),
            max_width=420,
            align_right=True,
            rich_text=is_html,
        )
        avatar_label.setStyleSheet("border-radius: 16px;")
        row.addStretch()
        row.addWidget(bubble_label)
        row.addWidget(avatar_label)
    else:
        bubble_label = ChatBubble(
            content,
            background=QColor("#ffffff"),
            text_color=QColor("#111827"),
            border_color=QColor("#e5e7eb"),
            max_width=420,
            align_right=False,
            rich_text=is_html,
        )
        avatar_label.setStyleSheet("border-radius: 16px;")
        row.addWidget(avatar_label)
        row.addWidget(bubble_label)
        row.addStretch()

    v_layout.addLayout(row)
    main_window.chat_layout.addWidget(message_widget)

    # 打字机效果
    if streaming and not from_self and not is_html and isinstance(bubble_label, ChatBubble):
        start_streaming_text(main_window, bubble_label, content)

    # 滚动到底部
    if hasattr(main_window, "chat_scroll_area"):
        bar = main_window.chat_scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())


def start_streaming_text(main_window: "MainWindow", bubble: ChatBubble, full_text: str, interval_ms: int = 30):
    """让气泡中的文本以打字机形式逐字出现"""
    if not full_text:
        return

    bubble.label.setText("")
    state = {"i": 0}
    timer = QTimer(bubble)
    timer.setInterval(interval_ms)

    def on_timeout():
        i = state["i"]
        if i >= len(full_text):
            timer.stop()
            timer.deleteLater()
            return
        i += 1
        state["i"] = i
        bubble.label.setText(full_text[:i])

        if hasattr(main_window, "chat_scroll_area"):
            bar = main_window.chat_scroll_area.verticalScrollBar()
            bar.setValue(bar.maximum())

    timer.timeout.connect(on_timeout)
    timer.start()


def append_support_message(main_window: "MainWindow", content: str, is_html: bool = False):
    """供后续真实客服或机器人使用的接口"""
    streaming = not is_html
    append_chat_message(main_window, content, from_self=False, is_html=is_html, streaming=streaming)
    # 如果聊天面板隐藏，增加未读消息计数
    if hasattr(main_window, "chat_panel") and not main_window.chat_panel.isVisible():
        add_unread_count(main_window)


def show_scrollbar_handle(scroll_area: QScrollArea):
    """鼠标进入时显示滚动条手柄"""
    style = scroll_area.styleSheet()
    style = style.replace(
        "background: rgba(148, 163, 184, 0);",
        "background: rgba(148, 163, 184, 0.6);"
    )
    scroll_area.setStyleSheet(style)


def hide_scrollbar_handle(scroll_area: QScrollArea):
    """鼠标离开时隐藏滚动条手柄"""
    style = scroll_area.styleSheet()
    style = style.replace(
        "background: rgba(148, 163, 184, 0.6);",
        "background: rgba(148, 163, 184, 0);"
    )
    scroll_area.setStyleSheet(style)


def open_emoji_menu(main_window: "MainWindow"):
    """弹出表情选择器"""
    emojis = [
        "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😉", "😊", "😍",
        "😘", "😗", "😙", "😚", "😋", "😜", "🤪", "😝", "🤑", "🤗",
        "🤭", "🤫", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣",
        "😥", "😮", "🤐", "😯", "😪", "😫", "🥱", "😴", "😌", "😛",
        "😓", "😔", "😕", "🙃", "🫠", "😷", "🤒", "🤕", "🤢", "🤮",
        "🤧", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "😎", "🤓",
        "🧐", "😕", "😟", "🙁", "☹️", "😮‍💨", "😢", "😭", "😤", "😠",
        "😡", "🤬", "😈", "👿", "💀", "☠️", "💩", "🤡", "👻", "👽",
    ]

    menu = QMenu(main_window)
    menu.setStyleSheet("""
        QMenu {
            background-color: #ffffff;
            border: 1px solid #e5e7eb;
            padding: 4px;
        }
    """)

    grid_widget = QWidget()
    grid_layout = QGridLayout(grid_widget)
    grid_layout.setContentsMargins(4, 4, 4, 4)
    grid_layout.setHorizontalSpacing(4)
    grid_layout.setVerticalSpacing(4)

    columns = 10
    for idx, e in enumerate(emojis):
        row = idx // columns
        col = idx % columns
        btn = QPushButton(e)
        btn.setFixedSize(28, 28)
        btn.setStyleSheet("""
            QPushButton {
                border: none;
                background: transparent;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
                border-radius: 4px;
            }
        """)
        btn.clicked.connect(lambda _, em=e: insert_emoji(main_window, em))
        grid_layout.addWidget(btn, row, col)

    widget_action = QWidgetAction(menu)
    widget_action.setDefaultWidget(grid_widget)
    menu.addAction(widget_action)

    menu_size = menu.sizeHint()
    button_top_left = main_window.emoji_button.mapToGlobal(main_window.emoji_button.rect().topLeft())
    pos = QPoint(button_top_left.x(), button_top_left.y() - menu_size.height())
    menu.exec(pos)


def insert_emoji(main_window: "MainWindow", emoji: str):
    """插入表情到输入框"""
    if hasattr(main_window, "chat_input") and main_window.chat_input is not None:
        # QTextEdit 使用 insertPlainText 来插入文本
        main_window.chat_input.insertPlainText(emoji)


def create_faq_item(question: str, answer: str) -> QWidget:
    """创建一个无边框的 FAQ 问答条目"""
    item = QWidget()
    item.setStyleSheet("background-color: transparent;")

    item_layout = QVBoxLayout(item)
    item_layout.setContentsMargins(0, 0, 0, 10)
    item_layout.setSpacing(6)

    q_label = QLabel(question)
    q_label.setWordWrap(True)
    q_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 12px;
            font-weight: 700;
            color: #1e293b;
            background-color: rgba(124, 58, 237, 0.08);
            padding: 6px 8px;
            border-radius: 6px;
        }
    """)
    item_layout.addWidget(q_label)

    a_label = QLabel()
    a_label.setWordWrap(True)
    a_label.setTextFormat(Qt.TextFormat.RichText)
    a_label.setText(answer)
    a_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 11px;
            color: #475569;
            padding: 4px 6px;
            line-height: 1.5;
        }
    """)
    item_layout.addWidget(a_label)

    return item


def create_faq_item_with_images(
    main_window: "MainWindow",
    question: str,
    text1: str,
    images1: list,
    text2: str = "",
    images2: Optional[List[Tuple[str, str]]] = None,
    text3: str = ""
) -> QWidget:
    """创建一个带图片的 FAQ 问答条目，图片可点击放大"""
    item = QWidget()
    item.setStyleSheet("background-color: transparent;")

    item_layout = QVBoxLayout(item)
    item_layout.setContentsMargins(0, 0, 0, 10)
    item_layout.setSpacing(6)

    q_label = QLabel(question)
    q_label.setWordWrap(True)
    q_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 12px;
            font-weight: 700;
            color: #1e293b;
            background-color: rgba(124, 58, 237, 0.08);
            padding: 6px 8px;
            border-radius: 6px;
        }
    """)
    item_layout.addWidget(q_label)

    if text1:
        label1 = QLabel()
        label1.setWordWrap(True)
        label1.setTextFormat(Qt.TextFormat.RichText)
        label1.setText(text1)
        label1.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #475569;
                padding: 4px 6px;
            }
        """)
        item_layout.addWidget(label1)

    if images1:
        for img_path, img_title in images1:
            img_widget = create_clickable_image(main_window, img_path, img_title)
            if img_widget:
                item_layout.addWidget(img_widget)

    if text2:
        label2 = QLabel()
        label2.setWordWrap(True)
        label2.setTextFormat(Qt.TextFormat.RichText)
        label2.setText(text2)
        label2.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #475569;
                padding: 4px 6px;
            }
        """)
        item_layout.addWidget(label2)

    if images2:
        for img_path, img_title in images2:
            img_widget = create_clickable_image(main_window, img_path, img_title)
            if img_widget:
                item_layout.addWidget(img_widget)

    if text3:
        label3 = QLabel()
        label3.setWordWrap(True)
        label3.setTextFormat(Qt.TextFormat.RichText)
        label3.setText(text3)
        label3.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #475569;
                padding: 4px 6px;
            }
        """)
        item_layout.addWidget(label3)

    return item


def create_clickable_image(main_window: "MainWindow", img_path: str, title: str) -> Optional[QWidget]:
    """创建一个可点击放大的图片控件"""
    full_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), img_path)
    if not os.path.exists(full_path):
        full_path = img_path
        if not os.path.exists(full_path):
            return None

    pixmap = QPixmap(full_path)
    if pixmap.isNull():
        return None

    container = QWidget()
    container_layout = QVBoxLayout(container)
    container_layout.setContentsMargins(6, 4, 6, 4)
    container_layout.setSpacing(4)

    thumb = pixmap.scaled(
        200, 120,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    img_label = QLabel()
    img_label.setPixmap(thumb)
    img_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    img_label.setStyleSheet("""
        QLabel {
            border: 1px solid #e5e7eb;
            border-radius: 6px;
            padding: 2px;
            background-color: #f8fafc;
        }
        QLabel:hover {
            border-color: #7c3aed;
        }
    """)
    img_label.setToolTip(f"点击查看大图：{title}")
    img_label.mousePressEvent = lambda event, p=full_path, t=title: show_image_popup(main_window, p, t)
    container_layout.addWidget(img_label, alignment=Qt.AlignmentFlag.AlignLeft)

    title_label = QLabel(f"📷 {title}")
    title_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 10px;
            color: #64748b;
            padding-left: 2px;
        }
    """)
    container_layout.addWidget(title_label)

    return container


def show_image_popup(main_window: "MainWindow", img_path: str, title: str):
    """显示图片放大弹窗"""
    pixmap = QPixmap(img_path)
    if pixmap.isNull():
        return

    dialog = QDialog(main_window)
    dialog.setWindowTitle(title)
    dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
    dialog.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dialog.setModal(True)

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    bg_widget = QWidget()
    bg_widget.setObjectName("imagePopupBg")
    bg_widget.setStyleSheet("""
        #imagePopupBg {
            background-color: #ffffff;
            border-radius: 12px;
            border: 1px solid #e5e7eb;
        }
    """)
    bg_layout = QVBoxLayout(bg_widget)
    bg_layout.setContentsMargins(12, 12, 12, 12)
    bg_layout.setSpacing(8)

    header = QHBoxLayout()
    header.setContentsMargins(0, 0, 0, 0)

    title_lbl = QLabel(f"📷 {title}")
    title_lbl.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 14px;
            font-weight: 600;
            color: #1e293b;
        }
    """)
    header.addWidget(title_lbl)
    header.addStretch()

    close_btn = QPushButton("✕")
    close_btn.setFixedSize(28, 28)
    close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #f1f5f9;
            border: none;
            border-radius: 14px;
            font-size: 14px;
            color: #64748b;
        }
        QPushButton:hover {
            background-color: #fee2e2;
            color: #dc2626;
        }
    """)
    close_btn.clicked.connect(dialog.close)
    header.addWidget(close_btn)

    bg_layout.addLayout(header)

    screen = QApplication.primaryScreen().size()
    max_w = int(screen.width() * 0.7)
    max_h = int(screen.height() * 0.7)

    scaled = pixmap.scaled(
        max_w, max_h,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )

    img_label = QLabel()
    img_label.setPixmap(scaled)
    img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    img_label.setStyleSheet("border-radius: 8px;")
    bg_layout.addWidget(img_label)

    hint = QLabel("点击任意位置关闭")
    hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
    hint.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 11px;
            color: #94a3b8;
            padding-top: 4px;
        }
    """)
    bg_layout.addWidget(hint)

    layout.addWidget(bg_widget)

    dialog.mousePressEvent = lambda event: dialog.close()

    dialog.adjustSize()
    dialog_rect = dialog.geometry()
    parent_rect = main_window.geometry()
    x = parent_rect.x() + (parent_rect.width() - dialog_rect.width()) // 2
    y = parent_rect.y() + (parent_rect.height() - dialog_rect.height()) // 2
    dialog.move(x, y)

    shadow = QGraphicsDropShadowEffect(bg_widget)
    shadow.setBlurRadius(30)
    shadow.setOffset(0, 8)
    shadow.setColor(QColor(0, 0, 0, 60))
    bg_widget.setGraphicsEffect(shadow)

    dialog.exec()


def send_image(main_window: "MainWindow"):
    """选择并发送图片（内联展示），限制 100MB"""
    # 检查是否正在发送中，防止重复操作
    if hasattr(main_window, 'chat_send_button') and not main_window.chat_send_button.isEnabled():
        return
    if not main_window.chat_input.isEnabled():
        return
    
    file_path, _ = QFileDialog.getOpenFileName(
        main_window, "选择图片", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
    )
    if not file_path:
        return
    
    # 禁用发送相关控件
    main_window.chat_input.setEnabled(False)
    original_text = None
    if hasattr(main_window, 'chat_send_button'):
        original_text = main_window.chat_send_button.text()
        main_window.chat_send_button.setEnabled(False)
        main_window.chat_send_button.setText("发送中...")
        main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
    
    size = os.path.getsize(file_path)
    if size > 100 * 1024 * 1024:
        append_chat_message(main_window, "图片超过 100MB，未发送。", from_self=False)
        # 恢复状态
        main_window.chat_input.setEnabled(True)
        if hasattr(main_window, 'chat_send_button') and original_text:
            main_window.chat_send_button.setEnabled(True)
            main_window.chat_send_button.setText(original_text)
            main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 自动聚焦输入框
        QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
        return

    pix = QPixmap(file_path)
    if pix.isNull():
        append_chat_message(main_window, "图片加载失败。", from_self=False)
        # 恢复状态
        main_window.chat_input.setEnabled(True)
        if hasattr(main_window, 'chat_send_button') and original_text:
            main_window.chat_send_button.setEnabled(True)
            main_window.chat_send_button.setText(original_text)
            main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 自动聚焦输入框
        QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
        return
    
    scaled = pix.scaled(160, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    append_image_message(main_window, scaled, from_self=True)
    
    reply = main_window.keyword_matcher.generate_reply("图片", add_greeting=True)
    delay = random.randint(500, 1500)
    
    def send_reply_and_enable():
        append_support_message(main_window, reply)
        # 恢复按钮和输入框状态
        main_window.chat_input.setEnabled(True)
        if hasattr(main_window, 'chat_send_button'):
            main_window.chat_send_button.setEnabled(True)
            if original_text:
                main_window.chat_send_button.setText(original_text)
            main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 延迟聚焦，确保 UI 更新完成后再聚焦
        QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
    
    QTimer.singleShot(delay, send_reply_and_enable)


def append_image_message(main_window: "MainWindow", pixmap: QPixmap, from_self: bool = True):
    """发送图片消息，不使用气泡，直接显示圆角图片 + 头像"""
    if not hasattr(main_window, "chat_layout"):
        return

    message_widget = QWidget()
    v_layout = QVBoxLayout(message_widget)
    v_layout.setContentsMargins(4, 0, 4, 0)
    v_layout.setSpacing(2)

    if from_self:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #9ca3af;
            }
        """)
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.addStretch()
        time_row.addWidget(time_label)
        v_layout.addLayout(time_row)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    img_label = QLabel()
    img_label.setFixedSize(pixmap.width(), pixmap.height())
    rounded_pix = QPixmap(pixmap.size())
    rounded_pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(rounded_pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, pixmap.width(), pixmap.height()), 12, 12)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, pixmap)
    painter.end()
    img_label.setPixmap(rounded_pix)

    avatar_label = QLabel()
    avatar_label.setFixedSize(32, 32)
    if from_self:
        if main_window.user_avatar_label.pixmap():
            pm = main_window.user_avatar_label.pixmap().scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            avatar_label.setPixmap(pm)
    else:
        default_bytes = get_default_avatar()
        if default_bytes:
            pm = QPixmap()
            pm.loadFromData(default_bytes)
            pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            cropped = QPixmap(32, 32)
            cropped.fill(Qt.GlobalColor.transparent)
            p = QPainter(cropped)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            clip_path = QPainterPath()
            clip_path.addEllipse(0, 0, 32, 32)
            p.setClipPath(clip_path)
            p.drawPixmap(0, 0, pm)
            p.end()
            avatar_label.setPixmap(cropped)

    avatar_label.setStyleSheet("border-radius: 16px;")

    if from_self:
        row.addStretch()
        row.addWidget(img_label)
        row.addWidget(avatar_label)
    else:
        row.addWidget(avatar_label)
        row.addWidget(img_label)
        row.addStretch()

    v_layout.addLayout(row)
    main_window.chat_layout.addWidget(message_widget)

    if hasattr(main_window, "chat_scroll_area"):
        bar = main_window.chat_scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())


def _handle_file_upload_result(main_window: "MainWindow", success: bool, filename: str, size: int, error: str = ""):
    """处理文件上传结果"""
    if success:
        # 格式化文件大小
        if size < 1024 * 1024:
            size_kb = size / 1024
            size_str = f"{size_kb:.1f} KB"
        else:
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB"
        append_file_message(main_window, filename, size_str)
        
        reply = main_window.keyword_matcher.generate_reply("文件", add_greeting=True)
        delay = random.randint(500, 1500)
        
        def send_reply_and_enable():
            append_support_message(main_window, reply)
            main_window.chat_input.setEnabled(True)
            if hasattr(main_window, 'chat_send_button'):
                main_window.chat_send_button.setEnabled(True)
            QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
        
        QTimer.singleShot(delay, send_reply_and_enable)
    else:
        error_msg = error if error else "未知错误"
        append_chat_message(main_window, f"文件 {filename} 上传失败：{error_msg}", from_self=False)
        main_window.chat_input.setEnabled(True)
        if hasattr(main_window, 'chat_send_button'):
            main_window.chat_send_button.setEnabled(True)
        QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())


def send_file(main_window: "MainWindow"):
    """发送文件，限制 100MB；展示文件名和大小，显示上传进度"""
    # 检查是否正在发送中，防止重复操作
    if hasattr(main_window, 'chat_send_button') and not main_window.chat_send_button.isEnabled():
        return
    if not main_window.chat_input.isEnabled():
        return
    
    file_path, _ = QFileDialog.getOpenFileName(
        main_window, "选择文件", "", "All Files (*.*)"
    )
    if not file_path:
        return
    
    size = os.path.getsize(file_path)
    if size > 100 * 1024 * 1024:
        # 显示错误提示框给用户，而不是在聊天框中显示
        show_message(
            main_window,
            f"文件大小超过 100MB 限制，无法发送。\n\n请选择小于 100MB 的文件。",
            "文件过大",
            variant="error"
        )
        return

    # 显示上传进度对话框（仅对大于1MB的文件显示）
    filename = os.path.basename(file_path)
    if size > 1024 * 1024:  # 大于1MB的文件显示进度
        from gui.components.file_upload_progress import FileUploadProgressDialog
        progress_dialog = FileUploadProgressDialog(main_window, filename, size)
        # 居中显示
        dialog_size = progress_dialog.size()
        center_x = main_window.x() + (main_window.width() - dialog_size.width()) // 2
        center_y = main_window.y() + (main_window.height() - dialog_size.height()) // 2
        progress_dialog.move(center_x, center_y)
        
        # 保存原始完成处理方法
        original_on_finished = progress_dialog.on_upload_finished
        
        def custom_on_finished(success: bool, error: str = ""):
            # 调用原始处理（更新UI状态、关闭对话框）
            original_on_finished(success, error)
            
            # 延迟处理文件发送逻辑，等待对话框关闭动画
            QTimer.singleShot(350, lambda: _handle_file_upload_result(
                main_window, success, filename, size, error
            ))
        
        # 启动上传
        progress_dialog.start_upload(file_path)
        # 替换完成处理信号（断开原有连接，连接自定义处理）
        if progress_dialog.upload_thread:
            try:
                progress_dialog.upload_thread.finished.disconnect(progress_dialog.on_upload_finished)
            except TypeError:
                pass  # 如果未连接，忽略错误
            progress_dialog.upload_thread.finished.connect(custom_on_finished)
        
        progress_dialog.show()
        
        # 禁用发送相关控件
        main_window.chat_input.setEnabled(False)
        if hasattr(main_window, 'chat_send_button'):
            main_window.chat_send_button.setEnabled(False)
    else:
        # 小于1MB的文件直接发送，不显示进度
        # 禁用发送相关控件
        main_window.chat_input.setEnabled(False)
        original_text = None
        if hasattr(main_window, 'chat_send_button'):
            original_text = main_window.chat_send_button.text()
            main_window.chat_send_button.setEnabled(False)
            main_window.chat_send_button.setText("发送中...")
            main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        
        size_kb = size / 1024
        size_str = f"{size_kb:.1f} KB"
        append_file_message(main_window, filename, size_str)

        reply = main_window.keyword_matcher.generate_reply("文件", add_greeting=True)
        delay = random.randint(500, 1500)
        
        def send_reply_and_enable():
            append_support_message(main_window, reply)
            # 恢复按钮和输入框状态
            main_window.chat_input.setEnabled(True)
            if hasattr(main_window, 'chat_send_button'):
                main_window.chat_send_button.setEnabled(True)
                if original_text:
                    main_window.chat_send_button.setText(original_text)
                main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            # 延迟聚焦，确保 UI 更新完成后再聚焦
            QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
        
        QTimer.singleShot(delay, send_reply_and_enable)


def append_file_message(main_window: "MainWindow", filename: str, size_str: str, from_self: bool = True):
    """以卡片形式追加一条文件消息（用户或客服）"""
    if not hasattr(main_window, "chat_layout"):
        return

    message_widget = QWidget()
    v_layout = QVBoxLayout(message_widget)
    v_layout.setContentsMargins(4, 0, 4, 0)
    v_layout.setSpacing(2)

    if from_self:
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #9ca3af;
            }
        """)
        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)
        time_row.addStretch()
        time_row.addWidget(time_label)
        v_layout.addLayout(time_row)

    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)

    card = QWidget()
    card.setObjectName("fileCard")
    card.setStyleSheet("""
        #fileCard {
            background-color: #ffffff;
            border-radius: 14px;
            border: 1px solid #e5e7eb;
        }
    """)
    card.setMinimumWidth(200)
    card.setMaximumWidth(260)
    card_layout = QHBoxLayout(card)
    card_layout.setContentsMargins(10, 8, 10, 8)
    card_layout.setSpacing(8)

    text_col = QVBoxLayout()
    text_col.setContentsMargins(0, 0, 0, 0)
    text_col.setSpacing(4)

    name_label = QLabel(filename)
    name_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 14px;
            font-weight: 600;
            color: #111827;
        }
    """)
    name_label.setMinimumWidth(120)
    name_label.setMaximumWidth(200)

    size_label = QLabel(size_str)
    size_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 12px;
            color: #6b7280;
        }
    """)

    text_col.addWidget(name_label)
    text_col.addWidget(size_label)
    card_layout.addLayout(text_col, stretch=1)

    ext = os.path.splitext(filename)[1].lstrip(".").upper() or "FILE"
    ext = ext[:3]
    icon_bg = QWidget()
    icon_bg.setObjectName("fileIcon")
    icon_bg.setFixedSize(34, 42)
    icon_bg.setStyleSheet("""
        #fileIcon {
            background-color: #2563eb;
            border-radius: 8px;
        }
    """)
    icon_layout = QVBoxLayout(icon_bg)
    icon_layout.setContentsMargins(0, 0, 0, 0)
    icon_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

    icon_label = QLabel(ext)
    icon_label.setStyleSheet("""
        QLabel {
            color: #ffffff;
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 12px;
            font-weight: 700;
        }
    """)
    icon_layout.addWidget(icon_label)

    card_layout.addWidget(icon_bg, alignment=Qt.AlignmentFlag.AlignVCenter)

    avatar_label = QLabel()
    avatar_label.setFixedSize(32, 32)
    if from_self:
        if main_window.user_avatar_label.pixmap():
            pm = main_window.user_avatar_label.pixmap().scaled(
                32, 32,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            avatar_label.setPixmap(pm)
    else:
        default_bytes = get_default_avatar()
        if default_bytes:
            pm = QPixmap()
            pm.loadFromData(default_bytes)
            pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            cropped = QPixmap(32, 32)
            cropped.fill(Qt.GlobalColor.transparent)
            p = QPainter(cropped)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            clip_path = QPainterPath()
            clip_path.addEllipse(0, 0, 32, 32)
            p.setClipPath(clip_path)
            p.drawPixmap(0, 0, pm)
            p.end()
            avatar_label.setPixmap(cropped)

    avatar_label.setStyleSheet("border-radius:16px;")

    if from_self:
        row.addStretch()
        row.addWidget(card)
        row.addWidget(avatar_label)
    else:
        row.addWidget(avatar_label)
        row.addWidget(card)
        row.addStretch()

    v_layout.addLayout(row)
    main_window.chat_layout.addWidget(message_widget)

    if hasattr(main_window, "chat_scroll_area"):
        bar = main_window.chat_scroll_area.verticalScrollBar()
        bar.setValue(bar.maximum())
