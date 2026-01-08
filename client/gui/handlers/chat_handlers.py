import os
import random
import base64
from datetime import datetime
from typing import TYPE_CHECKING, List, Tuple, Optional

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QPushButton, QMenu, QWidgetAction, QGridLayout,
    QDialog, QFileDialog, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QTimer, QRectF, QUrl
from PyQt6.QtGui import (
    QPixmap, QCursor, QPainter, QPainterPath, QColor, QImage, QDesktopServices
)

from client.resources import get_default_avatar
from gui.components.chat_bubble import ChatBubble
from gui.handlers import dialog_handlers
from gui.handlers.message_utils import show_message
from gui.components.chat_rich_text import format_message_rich_text

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

    # 如果之前是关闭状态（非最小化），确保彻底清空旧记录
    if getattr(main_window, "_chat_closed", False):
        clear_all_chat_messages(main_window)
        clear_unread_count(main_window)
        main_window._chat_closed = False

    # 检查聊天面板是否已经在布局中
    chat_panel_in_layout = main_window.main_content_layout.indexOf(main_window.chat_panel) != -1
    
    # 如果聊天面板已经在布局中，直接显示即可
    if chat_panel_in_layout:
        main_window.chat_panel.setVisible(True)
        main_window._chat_minimized = False
        # 确保中间和右侧是隐藏的
        if main_window.merged_section2:
            main_window.merged_section2.hide()
        if main_window.right_column_widget:
            main_window.right_column_widget.hide()
        # 清除未读消息计数（因为已经打开聊天面板）
        clear_unread_count(main_window)
        # 延迟滚动到底部，确保UI完全渲染后再滚动
        QTimer.singleShot(100, lambda: scroll_to_bottom(main_window))
        return

    # 如果聊天面板不在布局中，需要重新添加到布局
    # 从主布局移除中间和右侧（占原来的 3+1 比例），用一个聊天面板等效占比替换
    if main_window.merged_section2_layout:
        # 尝试移除，如果不存在会失败但不会报错
        try:
            main_window.main_content_layout.removeItem(main_window.merged_section2_layout)
        except:
            pass
        if main_window.merged_section2:
            main_window.merged_section2.hide()
    if main_window.right_column_widget:
        # 尝试移除，如果不存在会失败但不会报错
        try:
            main_window.main_content_layout.removeWidget(main_window.right_column_widget)
        except:
            pass
        main_window.right_column_widget.hide()

    # 聊天面板占据原中间+右侧的总宽度（保持左侧宽度不变）
    main_window.main_content_layout.addWidget(main_window.chat_panel, 4)
    main_window.chat_panel.setVisible(True)
    main_window._chat_minimized = False
    main_window._chat_panel_added = True
    
    # 检查是否是第一次打开聊天面板（聊天记录为空），如果是则显示欢迎消息
    if hasattr(main_window, "chat_layout"):
        # 检查聊天布局中是否已有消息
        has_messages = main_window.chat_layout.count() > 0
        if not has_messages:
            # 延迟一小段时间，等UI渲染完成后再显示欢迎消息
            QTimer.singleShot(200, lambda: _show_welcome_message(main_window))
        else:
            # 如果有消息，滚动到底部
            QTimer.singleShot(100, lambda: scroll_to_bottom(main_window))


def _show_welcome_message(main_window: "MainWindow"):
    """显示欢迎消息（首次进入聊天区域时）"""
    welcome_message = "欢迎来到云汐幻声，请问有什么可以帮到你的嘛？"
    append_support_message(main_window, welcome_message)


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
        
        # 恢复原来的布局（左2中1右2）
        if getattr(main_window, "_chat_panel_added", False):
            # 从布局中移除聊天面板
            main_window.main_content_layout.removeWidget(main_window.chat_panel)
            
            # 检查并移除可能重复的布局项
            if main_window.merged_section2_layout:
                # 先尝试移除，如果不存在会失败但不会报错
                try:
                    main_window.main_content_layout.removeItem(main_window.merged_section2_layout)
                except:
                    pass
            if main_window.right_column_widget:
                try:
                    main_window.main_content_layout.removeWidget(main_window.right_column_widget)
                except:
                    pass
            
            # 恢复左侧列（如果不在布局中）
            if main_window.left_column_widget and main_window.main_content_layout.indexOf(main_window.left_column_widget) == -1:
                main_window.main_content_layout.addWidget(main_window.left_column_widget, 1)
            
            # 恢复中间部分（merged_section2_layout）
            if main_window.merged_section2_layout:
                main_window.main_content_layout.addLayout(main_window.merged_section2_layout, 3)
                if main_window.merged_section2:
                    main_window.merged_section2.show()
            
            # 恢复右侧列
            if main_window.right_column_widget:
                main_window.main_content_layout.addWidget(main_window.right_column_widget, 1)
                main_window.right_column_widget.show()
            
            # 注意：这里不重置 _chat_panel_added 标志，以便后续可以重新显示聊天面板


def close_chat_panel(main_window: "MainWindow"):
    """关闭聊天面板（结束聊天服务，清空聊天记录）"""
    if hasattr(main_window, "chat_panel") and main_window.chat_panel:
        main_window.chat_panel.setVisible(False)
        
        # 停止消息轮询（机器人消息轮询）
        if hasattr(main_window, "_message_poll_timer") and main_window._message_poll_timer:
            try:
                main_window._message_poll_timer.stop()
                main_window._message_poll_timer.deleteLater()
            except RuntimeError:
                # QTimer 已被删除，忽略错误
                pass
            finally:
                main_window._message_poll_timer = None

        # 停止人工客服消息轮询
        if hasattr(main_window, "_agent_poll_timer") and main_window._agent_poll_timer:
            try:
                main_window._agent_poll_timer.stop()
                main_window._agent_poll_timer.deleteLater()
            except RuntimeError:
                pass
            finally:
                main_window._agent_poll_timer = None
        
        # 清空聊天记录（仅清除UI，不清除数据库）
        if hasattr(main_window, "chat_layout"):
            while main_window.chat_layout.count():
                item = main_window.chat_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
        
        # 清除已显示消息ID记录
        if hasattr(main_window, "_displayed_message_ids"):
            main_window._displayed_message_ids.clear()
        
        # 重置状态
        main_window._chat_minimized = False
        main_window._chat_closed = True
        main_window._human_service_connected = False
        main_window._matched_agent_id = None
        if hasattr(main_window, "_chat_session_id"):
            main_window._chat_session_id = None
        clear_unread_count(main_window)
        
        # 恢复原来的布局
        if getattr(main_window, "_chat_panel_added", False):
            # 从布局中移除聊天面板
            try:
                main_window.main_content_layout.removeWidget(main_window.chat_panel)
            except:
                pass
            
            # 检查并移除可能重复的布局项
            if main_window.merged_section2_layout:
                try:
                    main_window.main_content_layout.removeItem(main_window.merged_section2_layout)
                except:
                    pass
            if main_window.right_column_widget:
                try:
                    main_window.main_content_layout.removeWidget(main_window.right_column_widget)
                except:
                    pass

            # 恢复左侧列（如果不在布局中）
            if main_window.left_column_widget and main_window.main_content_layout.indexOf(main_window.left_column_widget) == -1:
                main_window.main_content_layout.addWidget(main_window.left_column_widget, 1)

            # 恢复中间部分（merged_section2_layout）
            if main_window.merged_section2_layout:
                main_window.main_content_layout.addLayout(main_window.merged_section2_layout, 3)
                if main_window.merged_section2:
                    main_window.merged_section2.show()

            # 恢复右侧列
            if main_window.right_column_widget:
                main_window.main_content_layout.addWidget(main_window.right_column_widget, 1)
                main_window.right_column_widget.show()

            main_window._chat_panel_added = False


def handle_chat_send(main_window: "MainWindow"):
    """发送消息，如果已连接人工客服则发送到后端，否则使用关键词匹配生成回复"""
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
    
    # 如果已连接人工客服，强制走人工通道（禁用关键词机器人）
    if hasattr(main_window, "_human_service_connected") and main_window._human_service_connected:
        from client.login.token_storage import read_token
        from client.api_client import send_chat_message

        token = read_token()
        session_id = getattr(main_window, "_chat_session_id", None)

        if token and session_id and main_window.user_id:
            # 检查是否有引用消息
            reply_to_id = getattr(main_window, "_reply_to_message_id", None)
            reply_to_text = getattr(main_window, "_reply_to_message_text", None)
            reply_to_username = getattr(main_window, "_reply_to_username", None)
            
            # 获取当前用户名
            current_username = None
            try:
                from client.login.login_status_manager import check_login_status
                _, _, current_username = check_login_status()
            except Exception:
                pass
            
            # 先乐观展示自己的消息（包含引用信息）
            # 注意：此时没有message_id，发送成功后会通过轮询获取完整消息信息
            append_chat_message(
                main_window, 
                text, 
                from_self=True,
                reply_to_message_id=reply_to_id,
                reply_to_message=reply_to_text,
                reply_to_username=reply_to_username,
                from_user_id=main_window.user_id,
                from_username=current_username
            )
            main_window.chat_input.clear()

            # 兜底定时器，防止HTTP请求失败时界面一直禁用
            def fallback_enable():
                if not main_window.chat_input.isEnabled():
                    main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                    if original_text:
                        main_window.chat_send_button.setText(original_text)
                    main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                main_window.chat_input.setFocus()

            def send_via_http():
                try:
                    # 检查是否有引用消息
                    reply_to_id = getattr(main_window, "_reply_to_message_id", None)
                    resp = send_chat_message(session_id, main_window.user_id, text, token, reply_to_message_id=reply_to_id)
                    # 清除引用状态
                    if hasattr(main_window, "_reply_to_message_id"):
                        main_window._reply_to_message_id = None
                    if hasattr(main_window, "_reply_to_message_text"):
                        main_window._reply_to_message_text = None
                    if hasattr(main_window, "_reply_to_username"):
                        main_window._reply_to_username = None
                    # 恢复输入框占位符
                    if hasattr(main_window, "chat_input"):
                        main_window.chat_input.setPlaceholderText("输入消息...")
                    return resp
                except Exception:
                    return None

            def handle_response(resp):
                fallback_enable()
                
                if not resp or not resp.get("success"):
                    append_chat_message(
                        main_window,
                        "消息发送失败，请稍后重试。",
                        from_self=False,
                        is_html=False,
                        streaming=False
                    )
                    return
                
                message_id_raw = resp.get("message_id")
                message_id_int = None
                try:
                    message_id_int = int(message_id_raw) if message_id_raw else None
                except (ValueError, TypeError):
                    pass
                
                if message_id_int:
                    if not hasattr(main_window, "_displayed_message_ids"):
                        main_window._displayed_message_ids = set()
                    main_window._displayed_message_ids.add(str(message_id_int))
                    
                    # 发送成功后，立即轮询一次以获取完整的消息信息（包括引用消息）
                    # 这样能确保消息有正确的message_id和引用信息
                    if hasattr(main_window, "_agent_poll_timer") and main_window._agent_poll_timer:
                        # 触发一次轮询
                        QTimer.singleShot(100, lambda: None)  # 延迟100ms后轮询会自动触发

            # 使用QTimer.singleShot在后台执行HTTP请求，避免阻塞UI
            def do_send():
                resp = send_via_http()
                QTimer.singleShot(0, lambda: handle_response(resp))
            
            QTimer.singleShot(0, do_send)
            # 启动 3 秒兜底，避免请求超时导致按钮一直禁用
            QTimer.singleShot(3000, fallback_enable)
        else:
            # 已进入人工客服但通道异常，提示并恢复输入，不再走关键词机器人
            main_window.chat_input.setEnabled(True)
            if hasattr(main_window, 'chat_send_button'):
                main_window.chat_send_button.setEnabled(True)
                if original_text:
                    main_window.chat_send_button.setText(original_text)
                main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            append_chat_message(
                main_window,
                "当前客服通道未就绪，请稍后重试或关闭对话框重新进入。",
                from_self=False,
                is_html=False,
                streaming=False
            )
            QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
    else:
        # 未连接人工客服，使用关键词匹配生成回复
        # 获取当前用户名
        current_username = None
        try:
            from client.login.login_status_manager import check_login_status
            _, _, current_username = check_login_status()
        except Exception:
            pass
        
        append_chat_message(
            main_window, 
            text, 
            from_self=True,
            from_user_id=main_window.user_id if hasattr(main_window, 'user_id') else None,
            from_username=current_username
        )
        main_window.chat_input.clear()

        reply = main_window.keyword_matcher.generate_reply(text, add_greeting=True)
        
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
            QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
        
        QTimer.singleShot(delay, send_reply_and_enable)


def scroll_to_bottom(main_window: "MainWindow"):
    """滚动聊天区域到底部，确保最新消息可见"""
    if not hasattr(main_window, "chat_scroll_area"):
        return
    
    def do_scroll():
        if not hasattr(main_window, "chat_scroll_area"):
            return
        bar = main_window.chat_scroll_area.verticalScrollBar()
        if bar:
            max_value = bar.maximum()
            bar.setValue(max_value)
    
    # 立即尝试滚动一次
    do_scroll()
    # 使用多个延迟确保在不同时机都能滚动到底部（UI更新、布局调整等）
    QTimer.singleShot(10, do_scroll)
    QTimer.singleShot(50, do_scroll)
    QTimer.singleShot(100, do_scroll)


def clear_all_chat_messages(main_window: "MainWindow"):
    """清除聊天区域的所有消息"""
    if not hasattr(main_window, "chat_layout"):
        return
    
    # 清空聊天记录（仅清除UI，不清除数据库）
    while main_window.chat_layout.count():
        item = main_window.chat_layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
    
    # 清除已显示消息ID记录
    if hasattr(main_window, "_displayed_message_ids"):
        main_window._displayed_message_ids.clear()


def add_connected_separator(main_window: "MainWindow"):
    """在聊天区域顶部添加已连接客服的分隔线提示"""
    if not hasattr(main_window, "chat_layout"):
        return
    
    separator_widget = QWidget()
    separator_layout = QVBoxLayout(separator_widget)
    separator_layout.setContentsMargins(0, 12, 0, 12)
    separator_layout.setSpacing(0)
    
    # 创建分隔线和文字
    separator_container = QWidget()
    separator_container_layout = QHBoxLayout(separator_container)
    separator_container_layout.setContentsMargins(0, 0, 0, 0)
    separator_container_layout.setSpacing(8)
    
    # 左侧线条
    left_line = QLabel()
    left_line.setFixedHeight(1)
    left_line.setStyleSheet("background-color: #d1d5db;")
    left_line.setSizePolicy(left_line.sizePolicy().horizontalPolicy(), left_line.sizePolicy().verticalPolicy())
    
    # 中间文字
    text_label = QLabel("已连接客服，可以开始对话")
    text_label.setStyleSheet("""
        QLabel {
            color: #9ca3af;
            font-size: 11px;
            font-family: "Microsoft YaHei", "SimHei", "Arial", sans-serif;
            padding: 0 8px;
            background-color: transparent;
        }
    """)
    text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    # 右侧线条
    right_line = QLabel()
    right_line.setFixedHeight(1)
    right_line.setStyleSheet("background-color: #d1d5db;")
    right_line.setSizePolicy(right_line.sizePolicy().horizontalPolicy(), right_line.sizePolicy().verticalPolicy())
    
    separator_container_layout.addWidget(left_line, stretch=1)
    separator_container_layout.addWidget(text_label, stretch=0)
    separator_container_layout.addWidget(right_line, stretch=1)
    
    separator_layout.addWidget(separator_container)
    
    # 插入到布局顶部（索引0）
    main_window.chat_layout.insertWidget(0, separator_widget)


def append_chat_message(
    main_window: "MainWindow",
    content: str,
    from_self: bool = True,
    is_html: bool = False,
    streaming: bool = False,
    avatar_base64: Optional[str] = None,
    message_id: Optional[int] = None,
    is_recalled: bool = False,
    reply_to_message_id: Optional[int] = None,
    reply_to_message: Optional[str] = None,
    reply_to_username: Optional[str] = None,
    from_user_id: Optional[int] = None,
    from_username: Optional[str] = None
):
    """按左右气泡形式追加一条消息，使用真实圆角控件"""
    if not hasattr(main_window, "chat_layout"):
        return

    # 先根据需要将纯文本转换为富文本（Markdown / @提及 / 链接）
    effective_content = content
    rich_flag = is_html
    link_urls: List[str] = []

    # 仅在原始消息非 HTML 时尝试自动解析富文本，避免破坏已有 HTML 文本
    if not is_html and content:
        try:
            html, is_rich, urls = format_message_rich_text(content)
            if is_rich:
                effective_content = html
                rich_flag = True
                link_urls = urls or []
        except Exception:
            # 如果富文本处理出错，使用原始内容
            effective_content = content
            rich_flag = False
            link_urls = []

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
        # 记录时间标签，便于撤回时隐藏
        message_widget.setProperty("time_label", time_label)

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
        pm = None
        # 优先使用服务器下发的 avatar_base64
        if avatar_base64:
            try:
                b64 = avatar_base64
                if b64.startswith("data:image"):
                    b64 = b64.split(",", 1)[1]
                pm = QPixmap()
                if pm.loadFromData(base64.b64decode(b64)):
                    pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)
            except Exception:
                pm = None
        if pm is None:
            default_bytes = get_default_avatar()
            if default_bytes:
                pm = QPixmap()
                if pm.loadFromData(default_bytes):
                    pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                                   Qt.TransformationMode.SmoothTransformation)

        if pm:
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

    if from_self:
        bubble_label = ChatBubble(
            effective_content,
            background=QColor("#dcf8c6"),
            text_color=QColor("#0f172a"),
            max_width=420,
            align_right=True,
            rich_text=rich_flag,
        )
        avatar_label.setStyleSheet("border-radius: 16px;")
        row.addStretch()
        row.addWidget(bubble_label)
        row.addWidget(avatar_label)
    else:
        bubble_label = ChatBubble(
            effective_content,
            background=QColor("#ffffff"),
            text_color=QColor("#111827"),
            border_color=QColor("#e5e7eb"),
            max_width=420,
            align_right=False,
            rich_text=rich_flag,
        )
        avatar_label.setStyleSheet("border-radius: 16px;")
        row.addWidget(avatar_label)
        row.addWidget(bubble_label)
        row.addStretch()

    v_layout.addLayout(row)

    # 处理撤回状态 - 显示"xxx撤回了一条消息"（灰色居中）
    if is_recalled:
        # 获取用户名
        username = from_username or "用户"
        if from_user_id and not from_username:
            # 尝试从main_window获取用户名
            if hasattr(main_window, "username"):
                username = main_window.username
            elif from_user_id == main_window.user_id:
                # 如果是当前用户，尝试获取用户名
                try:
                    from client.login.login_status_manager import check_login_status
                    _, _, current_username = check_login_status()
                    if current_username:
                        username = current_username
                except Exception:
                    pass
        
        # 创建撤回提示标签（灰色居中）
        recall_label = QLabel(f"{username}撤回了一条消息")
        recall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recall_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                color: #9ca3af;
                padding: 4px 0px;
                background-color: transparent;
            }
        """)
        # 在气泡之前插入撤回提示
        v_layout.insertWidget(v_layout.count() - 1, recall_label)
        
        # 隐藏气泡，只显示撤回提示
        if isinstance(bubble_label, ChatBubble):
            bubble_label.setVisible(False)
    
    # 处理引用消息显示（微信风格）：在主布局中单独一行显示引用块，放在正文气泡下方
    if reply_to_message_id and reply_to_message and not is_recalled:
        # 创建引用消息容器（微信风格，灰底）
        reply_container = QWidget()
        reply_container.setStyleSheet("""
            QWidget {
                background-color: #e5e5e5;
                border-left: 3px solid #8dcf7d;
                border-radius: 4px;
                padding: 6px 10px;
                margin-top: 6px;
            }
        """)
        reply_layout = QHBoxLayout(reply_container)
        reply_layout.setContentsMargins(0, 0, 0, 0)
        reply_layout.setSpacing(0)

        reply_content_layout = QVBoxLayout()
        reply_content_layout.setContentsMargins(0, 0, 0, 0)
        reply_content_layout.setSpacing(2)

        # 获取引用消息的发送者信息
        reply_sender_name = reply_to_username or "用户"
        # 检查引用消息是否被撤回
        reply_text = reply_to_message
        if reply_text == "[消息已撤回]":
            reply_text = "该引用消息已被撤回"
        else:
            if len(reply_text) > 50:
                reply_text = reply_text[:50] + "..."

        reply_label = QLabel(f"{reply_sender_name}: {reply_text}")
        reply_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #4b5563;
                background-color: transparent;
            }
        """)
        reply_label.setWordWrap(True)
        reply_content_layout.addWidget(reply_label)

        reply_layout.addLayout(reply_content_layout)

        # 引用块单独占一行，与消息气泡左对齐（放在正文气泡下方）
        reply_row = QHBoxLayout()
        reply_row.setContentsMargins(0, 0, 0, 0)
        reply_row.setSpacing(6)

        # 引用块始终与消息气泡的左边缘对齐
        # 对于用户消息，消息气泡右对齐，但引用块需要与气泡左边缘对齐
        # 对于客服消息，消息气泡左对齐，引用块也与气泡左边缘对齐
        if from_self:
            # 用户消息：引用块右对齐，与消息气泡左边缘对齐
            # 需要添加与头像宽度相同的偏移（32px + 6px spacing），使引用块与消息气泡左边缘对齐
            reply_row.addStretch()
            # 设置引用块的最大宽度，与消息气泡一致
            reply_container.setMaximumWidth(420)
            reply_row.addWidget(reply_container)
            # 添加与头像宽度相同的占位，使引用块与消息气泡左边缘对齐
            reply_row.addSpacing(38)  # 32px 头像 + 6px spacing
        else:
            # 客服消息：引用块左对齐，与消息气泡左边缘对齐
            # 添加与头像宽度相同的偏移（32px + 6px spacing），使引用块与消息气泡左边缘对齐
            reply_row.addSpacing(38)  # 32px 头像 + 6px spacing
            reply_container.setMaximumWidth(420)
            reply_row.addWidget(reply_container)
            reply_row.addStretch()

        # 插入到气泡行之后（正文下方）
        v_layout.addLayout(reply_row)
        
        # 存储引用块的引用，以便撤回时能够找到并隐藏
        message_widget.setProperty("reply_container", reply_container)
        # 存储引用消息ID，以便在引用消息被撤回时更新
        message_widget.setProperty("reply_to_message_id", reply_to_message_id)
    
    # 若识别到 URL，则在当前消息下方追加简单的链接预览卡片
    if link_urls:
        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setContentsMargins(40 if not from_self else 0, 4, 0 if from_self else 40, 0)
        preview_layout.setSpacing(0)

        # 只展示第一个链接的预览，避免过于臃肿
        url = link_urls[0]
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.netloc or parsed.path
        display_host = host if len(host) <= 32 else host[:29] + "..."

        card = QWidget()
        card.setObjectName("linkPreviewCard")
        card.setStyleSheet("""
            #linkPreviewCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #ffffff, stop:1 #f8fafc);
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                max-width: 320px;
            }
            #linkPreviewCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
                    stop:0 #f8fafc, stop:1 #f1f5f9);
                border: 1px solid #cbd5e1;
                transform: translateY(-1px);
            }
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 10, 14, 10)
        card_layout.setSpacing(6)

        # 添加图标和标题行
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)
        
        icon_label = QLabel("🔗")
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
            }
        """)

        title_label = QLabel("链接预览")
        title_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 11px;
                font-weight: 600;
                color: #64748b;
                letter-spacing: 0.5px;
            }
        """)
        
        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        url_label = QLabel(display_host)
        url_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #2563eb;
                font-weight: 500;
                padding: 2px 0px;
            }
        """)
        url_label.setWordWrap(True)

        card_layout.addLayout(header_layout)
        card_layout.addWidget(url_label)

        # 点击整个卡片在系统浏览器中打开链接
        def open_in_browser(*_):
            QDesktopServices.openUrl(QUrl(url))

        card.mousePressEvent = lambda event: open_in_browser(event)

        if from_self:
            preview_layout.addStretch()
            preview_layout.addWidget(card)
        else:
            preview_layout.addWidget(card)
            preview_layout.addStretch()

        v_layout.addLayout(preview_layout)

    # 存储消息ID到消息控件中（用于撤回和引用），统一转换为整数（若可）
    normalized_msg_id = None
    if message_id is not None:
        try:
            normalized_msg_id = int(message_id)
        except (ValueError, TypeError):
            normalized_msg_id = message_id
    message_widget.setProperty("message_id", normalized_msg_id)
    
    # 为消息控件添加右键菜单
    # 用户端：用户自己的消息可以撤回+引用，客服消息只能引用
    # 注意：即使用户消息暂时没有message_id（乐观展示），也要显示右键菜单，但撤回功能需要等待message_id
    if not is_recalled:
        def show_context_menu(pos: QPoint):
            # customContextMenuRequested 信号传递的是 QPoint，不是事件对象
            menu = QMenu(message_widget)
            # 美化右键菜单样式
            menu.setStyleSheet("""
                QMenu {
                    background-color: #ffffff;
                    border: 1px solid #e5e7eb;
                    border-radius: 8px;
                    padding: 4px;
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 13px;
                }
                QMenu::item {
                    padding: 8px 20px;
                    border-radius: 4px;
                    color: #1f2937;
                    min-width: 120px;
                }
                QMenu::item:selected {
                    background-color: #f3f4f6;
                    color: #111827;
                }
                QMenu::item:disabled {
                    color: #9ca3af;
                }
            """)
            
            # 引用回复（所有消息都可以引用）
            reply_action = menu.addAction("引用回复")
            reply_action.setEnabled(True)
            
            def reply_message_action():
                # 设置引用消息ID和内容
                # 从message_widget获取message_id（可能为None，但引用功能不需要message_id）
                current_msg_id = message_widget.property("message_id")
                main_window._reply_to_message_id = current_msg_id if current_msg_id else None
                main_window._reply_to_message_text = content
                # 获取被引用消息的发送者用户名
                main_window._reply_to_username = from_username or (from_self and "我" or "用户")
                # 在输入框显示引用提示
                if hasattr(main_window, "chat_input"):
                    sender_name = main_window._reply_to_username
                    preview = content[:30] + ('...' if len(content) > 30 else '')
                    placeholder = f"回复 {sender_name}：{preview}"
                    main_window.chat_input.setPlaceholderText(placeholder)
                    main_window.chat_input.setFocus()
            
            reply_action.triggered.connect(reply_message_action)
            
            # 撤回消息（只有自己发送的消息才能撤回）
            if from_self:
                recall_action = menu.addAction("撤回消息")
                # 动态检查message_id（从widget属性获取，可能已经被轮询更新）
                current_msg_id = message_widget.property("message_id")
                if current_msg_id:
                    recall_action.setEnabled(True)
                else:
                    recall_action.setEnabled(False)
                    recall_action.setToolTip("消息ID尚未同步，请稍后再试")
                
                def recall_message_action():
                    # 再次检查message_id（确保是最新的）
                    current_msg_id = message_widget.property("message_id")
                    if not current_msg_id:
                        show_message(main_window, "提示", "消息ID尚未同步，请稍后再试")
                        return
                    
                    from client.login.token_storage import read_token
                    from client.api_client import recall_message
                    
                    token = read_token()
                    if not token or not main_window.user_id:
                        show_message(main_window, "错误", "未登录，无法撤回消息")
                        return
                    
                    try:
                        resp = recall_message(current_msg_id, main_window.user_id, token)
                        if resp.get("success"):
                            # 获取用户名
                            username = from_username or "用户"
                            if not username:
                                try:
                                    from client.login.login_status_manager import check_login_status
                                    _, _, current_username = check_login_status()
                                    if current_username:
                                        username = current_username
                                except Exception:
                                    pass
                            
                            # 隐藏整个消息行（包括头像和气泡）以及引用块，显示撤回提示
                            parent_layout = message_widget.layout()
                            if parent_layout:
                                # 找到包含bubble的row布局
                                row_layout = None
                                row_index = -1
                                for i in range(parent_layout.count()):
                                    item = parent_layout.itemAt(i)
                                    if item and item.layout():
                                        # 检查这个布局中是否包含bubble
                                        layout = item.layout()
                                        for j in range(layout.count()):
                                            layout_item = layout.itemAt(j)
                                            if layout_item and layout_item.widget() == bubble_label:
                                                row_layout = layout
                                                row_index = i
                                                break
                                        if row_layout:
                                            break
                                
                                # 隐藏包含气泡的row布局中的所有控件（包括头像和气泡）
                                if row_layout:
                                    for i in range(row_layout.count()):
                                        item = row_layout.itemAt(i)
                                        if item and item.widget():
                                            item.widget().setVisible(False)
                                
                                # 隐藏引用块（如果存在）
                                reply_container = message_widget.property("reply_container")
                                if reply_container:
                                    reply_container.setVisible(False)
                            
                            # 隐藏时间标签（如果有）
                            time_label = message_widget.property("time_label")
                            if time_label:
                                time_label.setVisible(False)
                                
                            # 创建撤回提示标签（灰色居中）
                                recall_label = QLabel(f"{username}撤回了一条消息")
                                recall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                recall_label.setStyleSheet("""
                                    QLabel {
                                        font-family: "Microsoft YaHei", "SimHei", "Arial";
                                        font-size: 11px;
                                        color: #9ca3af;
                                        padding: 4px 0px;
                                        background-color: transparent;
                                    }
                                """)
                                
                                # 在row布局位置插入撤回提示
                                if row_index >= 0:
                                    parent_layout.insertWidget(row_index, recall_label)
                                else:
                                    # 如果找不到row，直接添加到末尾
                                    parent_layout.addWidget(recall_label)
                            
                            message_widget.setProperty("message_id", None)  # 标记为已撤回
                            message_widget.setProperty("is_recalled", True)  # 标记为已撤回
                        else:
                            error_msg = resp.get("message", "撤回失败")
                            show_message(main_window, "撤回失败", error_msg)
                    except Exception as e:
                        show_message(main_window, "撤回失败", f"撤回消息时发生错误：{str(e)}")
                
                recall_action.triggered.connect(recall_message_action)
            
            # 将局部坐标转换为全局坐标
            global_pos = message_widget.mapToGlobal(pos)
            menu.exec(global_pos)
        
        message_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        message_widget.customContextMenuRequested.connect(show_context_menu)
        
        # 存储消息ID和控件引用，用于更新撤回状态
        if not hasattr(main_window, "_message_widgets_map"):
            main_window._message_widgets_map = {}
        main_window._message_widgets_map[message_id] = (message_widget, bubble_label)
    
    main_window.chat_layout.addWidget(message_widget)

    # 打字机效果
    if streaming and not from_self and not is_html and isinstance(bubble_label, ChatBubble):
        start_streaming_text(main_window, bubble_label, content)

    # 如果是客服消息且聊天面板隐藏/最小化，增加未读消息计数
    if not from_self:
        if (hasattr(main_window, "chat_panel") and not main_window.chat_panel.isVisible()) or \
           getattr(main_window, "_chat_minimized", False):
            add_unread_count(main_window)

    # 滚动到底部
    scroll_to_bottom(main_window)


def start_streaming_text(main_window: "MainWindow", bubble: ChatBubble, full_text: str, interval_ms: int = 30, on_finished=None):
    """让气泡中的文本以打字机形式逐字出现"""
    if not full_text:
        if on_finished:
            on_finished()
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
            if on_finished:
                on_finished()
            return
        i += 1
        state["i"] = i
        # 使用 ChatBubble 的格式化方法来处理换行
        partial_text = full_text[:i]
        formatted_text = bubble._format_text_with_line_breaks(partial_text)
        bubble.label.setText(formatted_text)

        scroll_to_bottom(main_window)

    timer.timeout.connect(on_timeout)
    timer.start()


def append_support_message(main_window: "MainWindow", content: str, is_html: bool = False):
    """供后续真实客服或机器人使用的接口"""
    # 检测是否需要人工客服
    if content == "NEED_HUMAN_SERVICE":
        append_human_service_request(main_window)
        return
    
    streaming = not is_html
    append_chat_message(main_window, content, from_self=False, is_html=is_html, streaming=streaming)
    # 如果聊天面板隐藏，增加未读消息计数
    if hasattr(main_window, "chat_panel") and not main_window.chat_panel.isVisible():
        add_unread_count(main_window)


def append_human_service_request(main_window: "MainWindow"):
    """显示需要人工客服的消息和按钮"""
    if not hasattr(main_window, "chat_layout"):
        return
    
    # 显示提示消息（使用打字机效果）
    message_text = "这个问题我这边暂时没有查到详细说明呢，建议您直接联系人工客服处理哈～"
    
    # 先添加消息气泡（使用streaming=True实现打字机效果）
    message_widget = QWidget()
    v_layout = QVBoxLayout(message_widget)
    v_layout.setContentsMargins(4, 0, 4, 0)
    v_layout.setSpacing(2)
    
    # 气泡 + 头像 行
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    
    # 头像
    avatar_label = QLabel()
    avatar_label.setFixedSize(32, 32)
    default_bytes = get_default_avatar()
    if default_bytes:
        pm = QPixmap()
        if pm.loadFromData(default_bytes):
            pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
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
    
    bubble_label = ChatBubble(
        message_text,
        background=QColor("#ffffff"),
        text_color=QColor("#111827"),
        border_color=QColor("#e5e7eb"),
        max_width=420,
        align_right=False,
        rich_text=False,
    )
    row.addWidget(avatar_label)
    row.addWidget(bubble_label)
    row.addStretch()
    
    v_layout.addLayout(row)
    main_window.chat_layout.addWidget(message_widget)
    
    # 延迟显示按钮（等文字显示完成后再显示按钮，更有层次感）
    def show_button():
        # 创建包含按钮的消息组件
        button_widget = QWidget()
        button_v_layout = QVBoxLayout(button_widget)
        button_v_layout.setContentsMargins(4, 12, 4, 8)
        button_v_layout.setSpacing(0)
        
        # 按钮容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(0)
        
        # 创建"联系人工客服"按钮（更美观的版本）
        connect_btn = QPushButton("💬 联系人工客服")
        connect_btn.setFixedHeight(52)
        connect_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 使用更现代、更美观的样式（带阴影效果和更柔和的渐变色）
        connect_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:0.5 #8b5cf6, stop:1 #a855f7);
                color: #ffffff;
                border: none;
                border-radius: 26px;
                font-family: "Microsoft YaHei", "SimHei", "Arial", sans-serif;
                font-size: 15px;
                font-weight: 600;
                padding: 0 40px;
                min-width: 220px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #7c3aed, stop:0.5 #9333ea, stop:1 #a855f7);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4f46e5, stop:0.5 #7c3aed, stop:1 #9333ea);
            }
        """)
        
        # 添加阴影效果（通过GraphicsDropShadowEffect）
        shadow = QGraphicsDropShadowEffect(connect_btn)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(99, 102, 241, 120))  # 半透明紫色阴影
        connect_btn.setGraphicsEffect(shadow)
        
        # 连接按钮点击事件
        connect_btn.clicked.connect(lambda: request_human_service(main_window))
        
        button_layout.addStretch()
        button_layout.addWidget(connect_btn)
        button_layout.addStretch()
        
        button_v_layout.addWidget(button_container)
        
        # 添加消息到聊天布局
        main_window.chat_layout.addWidget(button_widget)
        
        # 滚动到底部
        scroll_to_bottom(main_window)
    
    # 启动打字机效果，完成后显示按钮
    # 计算文字显示完成的时间（每个字符约30ms延迟，interval_ms=30）
    def on_streaming_finished():
        # 延迟200ms再显示按钮，让用户看到完整的文字
        QTimer.singleShot(200, show_button)
    
    start_streaming_text(main_window, bubble_label, message_text, interval_ms=30, on_finished=on_streaming_finished)
    
    # 滚动到底部
    scroll_to_bottom(main_window)


def set_chat_mode_indicator(main_window: "MainWindow", human: bool):
    """更新顶部模式指示（呼吸灯 + 文案）"""
    label = getattr(main_window, "chat_mode_label", None)
    if human:
        if label:
            label.setText("人工客服模式")
            label.setStyleSheet("""
                QLabel#modeIndicator {
                    color: #d1fae5;
                    font-size: 13px;
                }
            """)
    else:
        if label:
            label.setText("智能机器人模式")
            label.setStyleSheet("""
                QLabel#modeIndicator {
                    color: #e5e7eb;
                    font-size: 13px;
                }
            """)


def request_human_service(main_window: "MainWindow"):
    """请求人工客服匹配"""
    if not main_window.user_id:
        show_message(
            main_window,
            "请先登录后再联系人工客服。",
            "未登录",
            variant="warning"
        )
        return
    
    # 检查是否已经在匹配中
    if getattr(main_window, "_matching_human_service", False):
        show_message(
            main_window,
            "正在匹配中，请稍候...",
            "匹配中",
            variant="info"
        )
        return
    
    # 显示匹配中的消息
    append_matching_message(main_window)
    
    # 设置匹配状态
    main_window._matching_human_service = True
    
    # 模拟匹配过程（实际应该调用后端API）
    # 这里使用定时器模拟匹配延迟
    QTimer.singleShot(2000, lambda: match_human_service(main_window))


def append_matching_message(main_window: "MainWindow"):
    """显示正在匹配的消息（简化版）"""
    if not hasattr(main_window, "chat_layout"):
        return
    
    message_widget = QWidget()
    v_layout = QVBoxLayout(message_widget)
    v_layout.setContentsMargins(4, 0, 4, 0)
    v_layout.setSpacing(0)
    
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(6)
    
    # 头像
    avatar_label = QLabel()
    avatar_label.setFixedSize(32, 32)
    default_bytes = get_default_avatar()
    if default_bytes:
        pm = QPixmap()
        if pm.loadFromData(default_bytes):
            pm = pm.scaled(32, 32, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
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
    
    # 简化的匹配消息 - 更短更简洁
    matching_text = "🔍 正在匹配客服"
    bubble_label = ChatBubble(
        matching_text,
        background=QColor("#eff6ff"),  # 非常浅的蓝色背景
        text_color=QColor("#1e40af"),  # 深蓝色文字
        border_color=QColor("#93c5fd"),  # 浅蓝色边框
        max_width=280,  # 减小最大宽度，让气泡更短
        align_right=False,
        rich_text=False,
    )
    
    row.addWidget(avatar_label)
    row.addWidget(bubble_label)
    row.addStretch()
    
    v_layout.addLayout(row)
    
    main_window.chat_layout.addWidget(message_widget)
    
    # 滚动到底部
    scroll_to_bottom(main_window)
    
    # 保存消息组件引用，以便后续更新
    if not hasattr(main_window, "_matching_message_widget"):
        main_window._matching_message_widget = []
    main_window._matching_message_widget.append(message_widget)


def match_human_service(main_window: "MainWindow"):
    """匹配人工客服（调用后端API）"""
    from client.api_client import match_human_service as api_match_human_service
    from client.login.token_storage import read_token
    
    # 获取session_id（如果不存在则生成）
    if not hasattr(main_window, "_chat_session_id") or not main_window._chat_session_id:
        import uuid
        main_window._chat_session_id = f"chat_{main_window.user_id}_{uuid.uuid4().hex[:8]}"
    
    session_id = main_window._chat_session_id
    
    # 获取token
    token = read_token()
    if not token:
        append_chat_message(
            main_window,
            "请先登录后再联系人工客服。",
            from_self=False,
            is_html=False,
            streaming=False
        )
        main_window._matching_human_service = False
        return
    
    try:
        # 调用后端API匹配客服
        response = api_match_human_service(main_window.user_id, session_id, token)
        
        # 移除匹配中的消息
        if hasattr(main_window, "_matching_message_widget") and main_window._matching_message_widget:
            widget = main_window._matching_message_widget.pop(0)
            if widget:
                widget.deleteLater()
        
        if response.get("success") and response.get("matched"):
            # 匹配成功 - 清除所有对话
            clear_all_chat_messages(main_window)
            
            # 添加已连接客服的分隔线提示
            add_connected_separator(main_window)
            
            # 设置已连接状态
            main_window._human_service_connected = True
            main_window._matched_agent_id = response.get("agent_id")
            
            # 启动轮询检查客服消息
            start_polling_agent_messages(main_window, session_id, token)
        else:
            # 匹配失败，加入等待队列
            wait_message = response.get("message", "暂无在线客服，您的请求已加入等待队列，客服接入后会主动联系您。")
            append_chat_message(
                main_window,
                wait_message,
                from_self=False,
                is_html=False,
                streaming=False
            )
    except Exception as e:
        # API调用失败
        if hasattr(main_window, "_matching_message_widget") and main_window._matching_message_widget:
            widget = main_window._matching_message_widget.pop(0)
            if widget:
                widget.deleteLater()
        
        append_chat_message(
            main_window,
            "匹配客服时发生错误，请稍后重试。",
            from_self=False,
            is_html=False,
            streaming=False
        )
    
    # 重置匹配状态
    main_window._matching_human_service = False


def start_polling_agent_messages(main_window: "MainWindow", session_id: str, token: str):
    """启动HTTP轮询，定时获取客服消息"""
    # 记录已显示的消息ID，避免重复显示
    if not hasattr(main_window, "_displayed_message_ids"):
        main_window._displayed_message_ids = set()
    # 进入人工客服通道，提前标记，避免文件/图片误走机器人
    main_window._human_service_connected = True
    set_chat_mode_indicator(main_window, human=True)

    # 停止之前的轮询定时器（如果存在）
    try:
        if hasattr(main_window, "_agent_poll_timer") and main_window._agent_poll_timer:
            main_window._agent_poll_timer.stop()
            main_window._agent_poll_timer.deleteLater()
    except Exception:
        pass

    def poll_http_messages():
        """轮询HTTP接口获取新消息"""
        try:
            from client.api_client import get_chat_messages
            resp = get_chat_messages(session_id, main_window.user_id, token)
            if not resp.get("success"):
                return
            
            # 检查已显示的消息是否被撤回（包括用户和客服的消息）
            # 这个检查需要在处理新消息之前执行，确保已显示的消息状态能及时更新
            # 同时，收集所有被撤回的消息ID，用于更新引用这些消息的其他消息
            recalled_message_ids = set()
            if hasattr(main_window, "_message_widgets_map") and main_window._message_widgets_map:
                for msg in resp.get("messages", []):
                    # 统一转换为整数进行比较
                    msg_id_raw = msg.get("id")
                    msg_id_int = None
                    try:
                        msg_id_int = int(msg_id_raw) if msg_id_raw else None
                    except (ValueError, TypeError):
                        continue
                    
                    if not msg_id_int:
                        continue
                    
                    msg_is_recalled = msg.get("is_recalled", False)
                    msg_from_user_id = msg.get("userId") or msg.get("from_user_id")
                    
                    # 记录被撤回的消息ID
                    if msg_is_recalled:
                        recalled_message_ids.add(msg_id_int)
                    
                    # 检查消息是否在映射表中且已被撤回
                    if msg_is_recalled and msg_id_int in main_window._message_widgets_map:
                        widget_bubble = main_window._message_widgets_map.get(msg_id_int)
                        if widget_bubble:
                            widget, bubble = widget_bubble
                            if widget and bubble and not widget.property("is_recalled"):
                                # 获取用户名
                                username = "用户"
                                if msg_from_user_id:
                                    try:
                                        from client.api_client import get_user_profile
                                        profile = get_user_profile(msg_from_user_id)
                                        if profile and profile.get("user"):
                                            username = profile.get("user").get("username", "用户")
                                    except Exception:
                                        # 如果获取失败，尝试从main_window获取
                                        if msg_from_user_id == main_window.user_id:
                                            try:
                                                from client.login.login_status_manager import check_login_status
                                                _, _, current_username = check_login_status()
                                                if current_username:
                                                    username = current_username
                                            except Exception:
                                                pass
                                
                                # 隐藏整个消息行（包括头像和气泡）以及引用块
                                # 找到包含气泡的row布局
                                parent_layout = widget.layout()
                                if parent_layout:
                                    # 找到包含bubble的row布局
                                    row_layout = None
                                    row_index = -1
                                    for i in range(parent_layout.count()):
                                        item = parent_layout.itemAt(i)
                                        if item and item.layout():
                                            # 检查这个布局中是否包含bubble
                                            layout = item.layout()
                                            for j in range(layout.count()):
                                                layout_item = layout.itemAt(j)
                                                if layout_item and layout_item.widget() == bubble:
                                                    row_layout = layout
                                                    row_index = i
                                                    break
                                            if row_layout:
                                                break
                                    
                                    # 隐藏包含气泡的row布局中的所有控件
                                    if row_layout:
                                        for i in range(row_layout.count()):
                                            item = row_layout.itemAt(i)
                                            if item and item.widget():
                                                item.widget().setVisible(False)
                                    
                                    # 隐藏引用块（如果存在）
                                    reply_container = widget.property("reply_container")
                                    if reply_container:
                                        reply_container.setVisible(False)
                                    
                                    # 隐藏时间标签（如果有）
                                    time_label = widget.property("time_label")
                                    if time_label:
                                        time_label.setVisible(False)
                                    
                                    # 创建撤回提示标签（灰色居中）
                                    recall_label = QLabel(f"{username}撤回了一条消息")
                                    recall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                    recall_label.setStyleSheet("""
                                        QLabel {
                                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                                            font-size: 11px;
                                            color: #9ca3af;
                                            padding: 4px 0px;
                                            background-color: transparent;
                                        }
                                    """)
                                    
                                    # 在row布局位置插入撤回提示
                                    if row_index >= 0:
                                        parent_layout.insertWidget(row_index, recall_label)
                                    else:
                                        # 如果找不到row，直接添加到末尾
                                        parent_layout.addWidget(recall_label)
                                
                                widget.setProperty("is_recalled", True)
                                widget.setProperty("message_id", None)
                                
                                # 当消息被撤回时，更新所有引用这条消息的其他消息的引用内容
                                # 遍历所有消息widget，检查它们的reply_to_message_id
                                if hasattr(main_window, "_message_widgets_map"):
                                    for other_msg_id, (other_widget, other_bubble) in main_window._message_widgets_map.items():
                                        if other_widget and other_widget != widget:
                                            other_reply_to_id = other_widget.property("reply_to_message_id")
                                            if other_reply_to_id and other_reply_to_id == msg_id_int:
                                                # 找到引用这条被撤回消息的消息，更新引用内容
                                                other_reply_container = other_widget.property("reply_container")
                                                if other_reply_container:
                                                    # 找到引用容器中的标签并更新文本
                                                    reply_layout = other_reply_container.layout()
                                                    if reply_layout:
                                                        for i in range(reply_layout.count()):
                                                            item = reply_layout.itemAt(i)
                                                            if item and item.layout():
                                                                content_layout = item.layout()
                                                                for j in range(content_layout.count()):
                                                                    layout_item = content_layout.itemAt(j)
                                                                    if layout_item and layout_item.widget():
                                                                        label = layout_item.widget()
                                                                        if isinstance(label, QLabel):
                                                                            # 获取原来的文本，提取发送者名称
                                                                            original_text = label.text()
                                                                            if ":" in original_text:
                                                                                sender_name = original_text.split(":", 1)[0]
                                                                                label.setText(f"{sender_name}: 该引用消息已被撤回")
                                                                                break
            
            # 主动检查所有已存在的消息，如果它们引用的消息被撤回了，更新引用内容
            if hasattr(main_window, "_message_widgets_map") and main_window._message_widgets_map and recalled_message_ids:
                for other_msg_id, (other_widget, other_bubble) in main_window._message_widgets_map.items():
                    if other_widget:
                        other_reply_to_id = other_widget.property("reply_to_message_id")
                        if other_reply_to_id and other_reply_to_id in recalled_message_ids:
                            # 找到引用被撤回消息的消息，更新引用内容
                            other_reply_container = other_widget.property("reply_container")
                            if other_reply_container:
                                # 找到引用容器中的标签并更新文本
                                reply_layout = other_reply_container.layout()
                                if reply_layout:
                                    for i in range(reply_layout.count()):
                                        item = reply_layout.itemAt(i)
                                        if item and item.layout():
                                            content_layout = item.layout()
                                            for j in range(content_layout.count()):
                                                layout_item = content_layout.itemAt(j)
                                                if layout_item and layout_item.widget():
                                                    label = layout_item.widget()
                                                    if isinstance(label, QLabel):
                                                        # 获取原来的文本，提取发送者名称
                                                        original_text = label.text()
                                                        if ":" in original_text:
                                                            sender_name = original_text.split(":", 1)[0]
                                                            new_text = f"{sender_name}: 该引用消息已被撤回"
                                                            if original_text != new_text:
                                                                label.setText(new_text)
                                                                break
            
            for msg in resp.get("messages", []):
                msg_id = str(msg.get("id", "") or "")
                msg_from = msg.get("from", "user")
                msg_text = msg.get("text", "")
                msg_type = msg.get("message_type", "text")
                msg_is_recalled = msg.get("is_recalled", False)
                msg_reply_to_id = msg.get("reply_to_message_id")
                msg_user_id = msg.get("userId") or msg.get("from_user_id")

                # 先处理用户自己的消息：更新已显示但还没有 message_id 的消息，并检查撤回状态
                if msg_from == "user" and msg_user_id == main_window.user_id:
                    msg_id_int = None
                    try:
                        msg_id_int = int(msg.get("id", 0) or 0)
                    except (ValueError, TypeError):
                        pass

                    if msg_id_int:
                        # 确保映射表存在
                        if not hasattr(main_window, "_message_widgets_map"):
                            main_window._message_widgets_map = {}

                        # 检查是否已经在映射表中
                        if msg_id_int in main_window._message_widgets_map:
                            widget_bubble = main_window._message_widgets_map.get(msg_id_int)
                            if widget_bubble:
                                widget, bubble = widget_bubble
                                
                                # 检查引用消息的状态（即使消息本身没有被撤回）
                                if widget and msg_reply_to_id:
                                    # 检查引用的消息是否被撤回了
                                    if msg_reply_to_id in recalled_message_ids:
                                        # 更新引用内容
                                        reply_container = widget.property("reply_container")
                                        if reply_container:
                                            reply_layout = reply_container.layout()
                                            if reply_layout:
                                                for i in range(reply_layout.count()):
                                                    item = reply_layout.itemAt(i)
                                                    if item and item.layout():
                                                        content_layout = item.layout()
                                                        for j in range(content_layout.count()):
                                                            layout_item = content_layout.itemAt(j)
                                                            if layout_item and layout_item.widget():
                                                                label = layout_item.widget()
                                                                if isinstance(label, QLabel):
                                                                    original_text = label.text()
                                                                    if ":" in original_text:
                                                                        sender_name = original_text.split(":", 1)[0]
                                                                        new_text = f"{sender_name}: 该引用消息已被撤回"
                                                                        if original_text != new_text:
                                                                            label.setText(new_text)
                                                                            break
                                
                                # 如果消息已经存在，检查是否需要更新撤回状态
                                if msg_is_recalled:
                                    if widget and bubble and not widget.property("is_recalled"):
                                        # 获取用户名
                                        username = "用户"
                                        if msg_user_id == main_window.user_id:
                                            try:
                                                from client.login.login_status_manager import check_login_status
                                                _, _, current_username = check_login_status()
                                                if current_username:
                                                    username = current_username
                                            except Exception:
                                                pass
                                        
                                        # 隐藏整个消息行（包括头像和气泡）以及引用块
                                        parent_layout = widget.layout()
                                        if parent_layout:
                                            # 找到包含bubble的row布局
                                            row_layout = None
                                            row_index = -1
                                            for i in range(parent_layout.count()):
                                                item = parent_layout.itemAt(i)
                                                if item and item.layout():
                                                    layout = item.layout()
                                                    for j in range(layout.count()):
                                                        layout_item = layout.itemAt(j)
                                                        if layout_item and layout_item.widget() == bubble:
                                                            row_layout = layout
                                                            row_index = i
                                                            break
                                                    if row_layout:
                                                        break
                                            
                                            # 隐藏包含气泡的row布局中的所有控件
                                            if row_layout:
                                                for i in range(row_layout.count()):
                                                    item = row_layout.itemAt(i)
                                                    if item and item.widget():
                                                        item.widget().setVisible(False)
                                            
                                            # 隐藏引用块（如果存在）
                                            reply_container = widget.property("reply_container")
                                            if reply_container:
                                                reply_container.setVisible(False)
                                            
                                            # 创建撤回提示标签（灰色居中）
                                            recall_label = QLabel(f"{username}撤回了一条消息")
                                            recall_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                                            recall_label.setStyleSheet("""
                                                QLabel {
                                                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                    font-size: 11px;
                                                    color: #9ca3af;
                                                    padding: 4px 0px;
                                                    background-color: transparent;
                                                }
                                            """)
                                            
                                            # 在row布局位置插入撤回提示
                                            if row_index >= 0:
                                                parent_layout.insertWidget(row_index, recall_label)
                                            else:
                                                parent_layout.addWidget(recall_label)
                                        
                                        widget.setProperty("is_recalled", True)
                                        widget.setProperty("message_id", None)
                            
                            # 已经存在，跳过后续处理
                            if msg_id:
                                if not hasattr(main_window, "_displayed_message_ids"):
                                    main_window._displayed_message_ids = set()
                                main_window._displayed_message_ids.add(msg_id)
                            continue

                        if hasattr(main_window, "chat_layout"):
                            # 从后往前查找最后一条没有message_id的用户消息
                            # 用户消息的特征：气泡在右侧（row布局中，气泡前面有stretch）
                            found = False
                            for i in range(main_window.chat_layout.count() - 1, -1, -1):
                                item = main_window.chat_layout.itemAt(i)
                                if item and item.widget():
                                    widget = item.widget()
                                    existing_id = widget.property("message_id")
                                    # 如果消息没有ID或者是0，尝试更新它
                                    if existing_id is None or existing_id == 0:
                                        # 检查是否是用户自己的消息：气泡在右侧
                                        layout = widget.layout()
                                        is_user_msg = False
                                        bubble = None
                                        
                                        if layout:
                                            for j in range(layout.count()):
                                                layout_item = layout.itemAt(j)
                                                if layout_item and layout_item.layout():
                                                    row_layout = layout_item.layout()
                                                    # 检查是否有气泡，且气泡前面有stretch（用户消息特征）
                                                    for k in range(row_layout.count()):
                                                        row_item = row_layout.itemAt(k)
                                                        if row_item and row_item.widget():
                                                            w = row_item.widget()
                                                            if isinstance(w, ChatBubble):
                                                                # 检查前面是否有stretch（用户消息在右侧）
                                                                if k > 0:
                                                                    prev_item = row_layout.itemAt(k - 1)
                                                                    if prev_item and prev_item.spacerItem():
                                                                        is_user_msg = True
                                                                        bubble = w
                                                                        break
                                                        elif row_item and row_item.spacerItem():
                                                            # 如果stretch在气泡之后，不是用户消息
                                                            pass
                                        
                                        # 如果确认是用户消息，更新message_id
                                        if is_user_msg and bubble:
                                            widget.setProperty("message_id", msg_id_int)
                                            main_window._message_widgets_map[msg_id_int] = (widget, bubble)
                                            found = True
                                            break
                            
                            # 如果没找到匹配的消息，记录到displayed_ids（避免重复处理）
                            if not found and msg_id:
                                if not hasattr(main_window, "_displayed_message_ids"):
                                    main_window._displayed_message_ids = set()
                                main_window._displayed_message_ids.add(msg_id)
                    # 用户自己的消息不在这里重复展示（已经在发送时乐观展示了）
                    if msg_id:
                        if not hasattr(main_window, "_displayed_message_ids"):
                            main_window._displayed_message_ids = set()
                        main_window._displayed_message_ids.add(msg_id)
                    continue

                # 对于其他消息，再做去重判断
                if msg_id and msg_id in main_window._displayed_message_ids:
                    continue
                if msg_id:
                    main_window._displayed_message_ids.add(msg_id)

                # 只处理来自客服的消息（不是自己发的）
                if msg_from == "user":
                    continue
                
                # 获取用户名
                msg_username = None
                if msg_user_id:
                    try:
                        from client.api_client import get_user_profile
                        profile = get_user_profile(msg_user_id)
                        if profile and profile.get("user"):
                            msg_username = profile.get("user").get("username")
                    except Exception:
                        pass
                
                # 获取引用消息内容（如果有）
                reply_to_message_text = None
                reply_to_username = None
                if msg_reply_to_id:
                    try:
                        from client.api_client import get_reply_message
                        from client.login.token_storage import read_token
                        reply_token = read_token()
                        reply_resp = get_reply_message(msg_reply_to_id, reply_token)
                        if reply_resp.get("success"):
                            reply_msg = reply_resp.get("message", {})
                            # 检查引用消息是否被撤回
                            if reply_msg.get("is_recalled", False) or reply_msg.get("message") == "[消息已撤回]":
                                reply_to_message_text = "该引用消息已被撤回"
                            else:
                                reply_to_message_text = reply_msg.get("message", "")
                            reply_to_username = reply_msg.get("from_username")  # 获取引用消息的发送者用户名
                    except Exception:
                        pass

                def append_main():
                    # 标记已连接人工客服
                    main_window._human_service_connected = True
                    set_chat_mode_indicator(main_window, human=True)

                    # 如果是欢迎/接入提示语，额外给一条"已连接客服"提示
                    if "您好，我是客服" in msg_text or "已连接" in msg_text:
                        append_chat_message(
                            main_window,
                            "✅ 已连接客服，可以开始对话了！",
                            from_self=False,
                            is_html=False,
                            streaming=False
                        )

                    # 获取头像信息
                    avatar_base64 = msg.get("avatar")
                    
                    # 提取消息ID
                    msg_id_int = None
                    try:
                        msg_id_int = int(msg.get("id", 0) or 0)
                    except (ValueError, TypeError):
                        pass

                    # 按消息类型展示
                    if msg_type == "image":
                        pixmap = None
                        try:
                            if isinstance(msg_text, str) and msg_text.startswith("data:image"):
                                b64_part = msg_text.split(",", 1)[1] if "," in msg_text else ""
                                raw = base64.b64decode(b64_part)
                                image = QImage.fromData(raw)
                                if not image.isNull():
                                    pixmap = QPixmap.fromImage(image)
                                    if pixmap.width() > 360:
                                        pixmap = pixmap.scaledToWidth(
                                            360, Qt.TransformationMode.SmoothTransformation
                                        )
                        except Exception:
                            pixmap = None

                        if pixmap:
                            append_image_message(main_window, pixmap, from_self=False)
                        else:
                            append_chat_message(
                                main_window,
                                "[图片] 加载失败",
                                from_self=False,
                                is_html=False,
                                streaming=False,
                                avatar_base64=avatar_base64,
                                message_id=msg_id_int,
                                is_recalled=msg_is_recalled,
                                reply_to_message_id=msg_reply_to_id,
                                reply_to_message=reply_to_message_text,
                                reply_to_username=reply_to_username,
                                from_user_id=msg_user_id,
                                from_username=msg_username
                            )
                    elif msg_type == "file":
                        placeholder = msg_text or "[文件]"
                        append_chat_message(
                            main_window,
                            placeholder,
                            from_self=False,
                            is_html=False,
                            streaming=False,
                            avatar_base64=avatar_base64,
                            message_id=msg_id_int,
                            is_recalled=msg_is_recalled,
                            reply_to_message_id=msg_reply_to_id,
                            reply_to_message=reply_to_message_text,
                            reply_to_username=reply_to_username,
                            from_user_id=msg_user_id,
                            from_username=msg_username
                        )
                    else:
                        append_chat_message(
                            main_window,
                            msg_text,
                            from_self=False,
                            is_html=False,
                            streaming=False,
                            avatar_base64=avatar_base64,
                            message_id=msg_id_int,
                            is_recalled=msg_is_recalled,
                            reply_to_message_id=msg_reply_to_id,
                            reply_to_message=reply_to_message_text,
                            reply_to_username=reply_to_username,
                            from_user_id=msg_user_id,
                            from_username=msg_username
                        )
                
                QTimer.singleShot(0, append_main)
        except Exception:
            # 避免轮询异常影响其他功能
            pass

    # 立即执行一次轮询，获取历史消息
    poll_http_messages()
    
    # 启动定时轮询（每1秒轮询一次）
    poll_timer = QTimer(main_window)
    poll_timer.timeout.connect(poll_http_messages)
    poll_timer.start(1000)  # 1秒一次
    main_window._agent_poll_timer = poll_timer


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

    # 如果已连接人工客服，走HTTP接口发送图片
    if getattr(main_window, "_human_service_connected", False) and getattr(main_window, "_chat_session_id", None):
        from client.login.token_storage import read_token
        from client.api_client import send_chat_message
        
        token = read_token()
        session_id = getattr(main_window, "_chat_session_id", None)

        # 将图片转为 data URL 发送给后端（后端 message_type=image）
        try:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            data_url = f"data:image/png;base64,{b64}"
        except Exception:
            data_url = "[图片发送失败]"

        def restore():
            main_window.chat_input.setEnabled(True)
            if hasattr(main_window, 'chat_send_button'):
                main_window.chat_send_button.setEnabled(True)
                if original_text:
                    main_window.chat_send_button.setText(original_text)
                main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())

        # 使用QThread在后台线程执行HTTP请求，避免阻塞UI
        from PyQt6.QtCore import QThread, pyqtSignal
        
        class SendImageThread(QThread):
            finished = pyqtSignal(object)  # 发送完成信号，参数是响应结果
            
            def __init__(self, session_id, user_id, data_url, token):
                super().__init__()
                self.session_id = session_id
                self.user_id = user_id
                self.data_url = data_url
                self.token = token
                
            def run(self):
                try:
                    resp = send_chat_message(self.session_id, self.user_id, self.data_url, self.token, message_type="image")
                    self.finished.emit(resp)
                except Exception as e:
                    self.finished.emit(None)
        
        def handle_response(resp):
            if not resp or not resp.get("success"):
                append_chat_message(main_window, "图片发送失败，请稍后重试。", from_self=False)
            restore()
        
        thread = SendImageThread(session_id, main_window.user_id, data_url, token)
        thread.setParent(main_window)  # 设置父对象，确保生命周期管理
        thread.finished.connect(handle_response)
        thread.finished.connect(thread.deleteLater)  # 完成后自动删除
        thread.start()
        QTimer.singleShot(3000, restore)  # 3秒兜底
    else:
        # 未进入人工客服，仍使用机器人回复
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
    
    # 如果是客服消息且聊天面板隐藏/最小化，增加未读消息计数
    if not from_self:
        if (hasattr(main_window, "chat_panel") and not main_window.chat_panel.isVisible()) or \
           getattr(main_window, "_chat_minimized", False):
            add_unread_count(main_window)
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

    scroll_to_bottom(main_window)


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

        # 如已有人工客服会话，发送占位到客服，不触发机器人
        if getattr(main_window, "_human_service_connected", False) and getattr(main_window, "_chat_session_id", None):
            from client.login.token_storage import read_token
            from client.api_client import send_chat_message
            
            token = read_token()
            session_id = getattr(main_window, "_chat_session_id", None)
            placeholder = f"[文件] {filename} ({size_str})"

            def restore():
                main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())

            # 使用QThread在后台线程执行HTTP请求，避免阻塞UI
            from PyQt6.QtCore import QThread, pyqtSignal
            
            class SendFileThread(QThread):
                finished = pyqtSignal(object)  # 发送完成信号，参数是响应结果
                
                def __init__(self, session_id, user_id, placeholder, token):
                    super().__init__()
                    self.session_id = session_id
                    self.user_id = user_id
                    self.placeholder = placeholder
                    self.token = token
                    
                def run(self):
                    try:
                        resp = send_chat_message(self.session_id, self.user_id, self.placeholder, self.token, message_type="file")
                        self.finished.emit(resp)
                    except Exception as e:
                        self.finished.emit(None)

            def handle_response(resp):
                if not resp or not resp.get("success"):
                    append_chat_message(main_window, "文件发送提示失败，请稍后重试。", from_self=False)
                restore()

            thread = SendFileThread(session_id, main_window.user_id, placeholder, token)
            thread.setParent(main_window)  # 设置父对象，确保生命周期管理
            thread.finished.connect(handle_response)
            thread.finished.connect(thread.deleteLater)  # 完成后自动删除
            thread.start()
            QTimer.singleShot(3000, restore)  # 3秒兜底
            return

        # 无人工客服时仍使用机器人
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

        # 如果已进入人工客服，发送占位文本给客服，不触发机器人
        if getattr(main_window, "_human_service_connected", False) and getattr(main_window, "_chat_session_id", None):
            from client.login.token_storage import read_token
            from client.api_client import send_chat_message
            
            token = read_token()
            session_id = getattr(main_window, "_chat_session_id", None)

            placeholder = f"[文件] {filename} ({size_str})"

            def restore():
                main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                    if original_text:
                        main_window.chat_send_button.setText(original_text)
                    main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())

            # 使用QThread在后台线程执行HTTP请求，避免阻塞UI
            from PyQt6.QtCore import QThread, pyqtSignal
            
            class SendFileThread(QThread):
                finished = pyqtSignal(object)  # 发送完成信号，参数是响应结果
                
                def __init__(self, session_id, user_id, placeholder, token):
                    super().__init__()
                    self.session_id = session_id
                    self.user_id = user_id
                    self.placeholder = placeholder
                    self.token = token
                    
                def run(self):
                    try:
                        resp = send_chat_message(self.session_id, self.user_id, self.placeholder, self.token, message_type="file")
                        self.finished.emit(resp)
                    except Exception as e:
                        self.finished.emit(None)

            def handle_response(resp):
                if not resp or not resp.get("success"):
                    append_chat_message(main_window, "文件发送提示失败，请稍后重试。", from_self=False)
                restore()

            thread = SendFileThread(session_id, main_window.user_id, placeholder, token)
            thread.setParent(main_window)  # 设置父对象，确保生命周期管理
            thread.finished.connect(handle_response)
            thread.finished.connect(thread.deleteLater)  # 完成后自动删除
            thread.start()
            QTimer.singleShot(3000, restore)  # 3秒兜底
        else:
            # 未进入人工客服，使用机器人回复
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

    scroll_to_bottom(main_window)
