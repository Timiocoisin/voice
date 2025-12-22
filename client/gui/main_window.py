from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QScrollArea,
)
from PyQt6.QtCore import Qt, QPoint, QTimer
from PyQt6.QtGui import QPixmap
from modules.login_dialog import LoginDialog
from backend.customer_service.keyword_matcher import get_matcher
from gui.components.chat_bubble import ChatBubble
from gui.components.chat_panel import create_chat_panel
from gui.components.ui_layout import create_main_layout
from gui.handlers import dialog_handlers, avatar_handlers, chat_handlers
from gui.handlers.membership_handlers import (
    refresh_membership_from_db as refresh_membership_from_db_handler,
    refresh_vip_tooltip as refresh_vip_tooltip_handler,
)
from gui.handlers.window_handlers import (
    on_avatar_hover_enter,
    on_avatar_hover_leave,
    update_logout_popup_position,
    really_hide_logout,
    handle_logout_click,
)
from gui.window_utils import (
    create_svg_widget,
    set_icon_button,
    bytes_to_data_url,
    avatar_bytes_to_data_url,
)


class MainWindow(QMainWindow):
    # 初始化功能模块
    def __init__(self):
        super().__init__()
        self.setWindowTitle("变声器")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.screen_size(
            0.8), self.screen_size(0.7, height=True))

        self.dragging = False
        self.offset = QPoint()
        self.login_dialog_offset = QPoint()
        self.draggable_height = 40

        self.user_id = None

        self._avatar_normal_geometry = None
        self._avatar_anim = None
        self.logout_popup = None
        
        self._logout_timer = QTimer(self)
        self._logout_timer.setSingleShot(True)
        self._logout_timer.timeout.connect(lambda: really_hide_logout(self))
        self.keyword_matcher = get_matcher()

        self.initUI()
        self.login_dialog = LoginDialog(self)

        # 蒙版应该覆盖整个rounded_bg，而不仅仅是main_content_widget
        # 这样才能阻止用户点击主界面的任何部分
        self.mask_widget = QWidget(self.rounded_bg)
        # 设置蒙版为最上层，确保能拦截所有鼠标事件
        self.mask_widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.mask_widget.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 120);
                border-radius: 20px;
            }
        """)
        self.mask_widget.setVisible(False)

        dialog_handlers.check_auto_login(self)
        self._setup_event_handlers()

        self.installEventFilter(self)

    # 事件处理器功能模块
    def _setup_event_handlers(self):
        if hasattr(self, 'headset_container'):
            self.headset_container.mousePressEvent = lambda event: chat_handlers.open_customer_service_chat(self, event)

        if hasattr(self, 'user_avatar_label'):
            self.user_avatar_label.enterEvent = lambda event: on_avatar_hover_enter(self, event)
            self.user_avatar_label.leaveEvent = lambda event: on_avatar_hover_leave(self, event)

    # 会员信息功能模块
    def update_membership_info(self, avatar_data, username, is_vip, diamonds, user_id=None):
        avatar_handlers.update_membership_info(self, avatar_data, username, is_vip, diamonds, user_id=user_id)

    # 遮罩层功能模块
    def _update_mask_geometry(self):
        dialog_handlers._update_mask_geometry(self)

    def refresh_membership_from_db(self):
        return refresh_membership_from_db_handler(self)


    def _refresh_vip_tooltip(self):
        return refresh_vip_tooltip_handler(self)

    # 窗口工具功能模块
    def screen_size(self, ratio, height=False):
        screen = QApplication.primaryScreen()
        size = screen.size()
        if height:
            return int(size.height() * ratio)
        return int(size.width() * ratio)

    # UI初始化功能模块
    def initUI(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        # 收紧整体留白，让内容更紧凑
        main_layout.setContentsMargins(16, 16, 16, 16)

        (self.rounded_bg, self.main_content_widget, self.main_content_layout,
         self.merged_section2, self.merged_section2_layout,
         self.left_column_widget, self.right_column_widget, self.chat_panel) = create_main_layout(self)

        main_layout.addWidget(self.rounded_bg)

    # 聊天面板功能模块
    def create_chat_panel(self, parent=None):
        return create_chat_panel(self, parent)

    # 聊天功能模块
    def open_customer_service_chat(self, event):
        return chat_handlers.open_customer_service_chat(self, event)

    def _minimize_chat_panel(self):
        return chat_handlers.minimize_chat_panel(self)

    def _close_chat_panel(self):
        return chat_handlers.close_chat_panel(self)

    def _add_unread_count(self):
        return chat_handlers.add_unread_count(self)

    def _clear_unread_count(self):
        return chat_handlers.clear_unread_count(self)

    def _update_unread_badge(self):
        return chat_handlers.update_unread_badge(self)

    def _handle_chat_send(self):
        return chat_handlers.handle_chat_send(self)

    def _append_chat_message(self, content: str, from_self: bool = True, is_html: bool = False, streaming: bool = False):
        return chat_handlers.append_chat_message(self, content, from_self, is_html, streaming)

    def append_support_message(self, content: str, is_html: bool = False):
        return chat_handlers.append_support_message(self, content, is_html)

    def send_image(self):
        return chat_handlers.send_image(self)

    def send_file(self):
        return chat_handlers.send_file(self)

    def open_emoji_menu(self):
        return chat_handlers.open_emoji_menu(self)

    def _append_file_message(self, filename: str, size_str: str, from_self: bool = True):
        return chat_handlers.append_file_message(self, filename, size_str, from_self)

    def _start_streaming_text(self, bubble: "ChatBubble", full_text: str, interval_ms: int = 30):
        return chat_handlers.start_streaming_text(self, bubble, full_text, interval_ms)

    def _insert_emoji(self, emoji: str):
        return chat_handlers.insert_emoji(self, emoji)

    def _show_scrollbar_handle(self, scroll_area: QScrollArea):
        return chat_handlers.show_scrollbar_handle(scroll_area)

    def _hide_scrollbar_handle(self, scroll_area: QScrollArea):
        return chat_handlers.hide_scrollbar_handle(scroll_area)

    def _create_faq_item(self, question: str, answer: str) -> QWidget:
        return chat_handlers.create_faq_item(question, answer)

    def _create_faq_item_with_images(
        self, question: str, text1: str, images1: list,
        text2: str = "", images2: list = None, text3: str = ""
    ) -> QWidget:
        return chat_handlers.create_faq_item_with_images(self, question, text1, images1, text2, images2, text3)

    def _create_clickable_image(self, img_path: str, title: str) -> QWidget:
        return chat_handlers.create_clickable_image(self, img_path, title)

    def _show_image_popup(self, img_path: str, title: str):
        return chat_handlers.show_image_popup(self, img_path, title)

    def _append_image_message(self, pixmap: QPixmap, from_self: bool = True):
        return chat_handlers.append_image_message(self, pixmap, from_self)

    # 窗口控制功能模块
    def _on_avatar_hover_enter(self, event):
        return on_avatar_hover_enter(self, event)

    def _on_avatar_hover_leave(self, event):
        return on_avatar_hover_leave(self, event)

    def _really_hide_logout(self):
        return really_hide_logout(self)

    def _update_logout_popup_position(self):
        return update_logout_popup_position(self)

    def _handle_logout_click(self):
        return handle_logout_click(self)

    # 工具功能模块
    def create_svg_widget(self, icon_id, width, height, style):
        return create_svg_widget(self, icon_id, width, height, style)

    def _set_icon_button(self, button: QPushButton, icon_id: int, tooltip: str = ""):
        return set_icon_button(button, icon_id, tooltip)

    def _bytes_to_data_url(self, data: bytes, mime: str = "image/png") -> str:
        return bytes_to_data_url(data, mime)

    def _avatar_bytes_to_data_url(self, data: bytes, size: int = 32, mime: str = "image/png") -> str:
        return avatar_bytes_to_data_url(data, size, mime)
