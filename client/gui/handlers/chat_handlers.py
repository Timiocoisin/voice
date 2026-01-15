import os
import random
import base64
import logging
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

        # 不再需要停止HTTP轮询（已移除）
        
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
        
        # 断开 WebSocket 连接（因为客服会话已结束）
        try:
            from client.utils.websocket_helper import disconnect_websocket
            disconnect_websocket(main_window)
            logging.info("客服会话结束，已断开 WebSocket 连接")
        except Exception as e:
            logging.warning(f"断开 WebSocket 连接失败: {e}")
            # 断开失败不影响关闭流程
        
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

        token = read_token()
        session_id = getattr(main_window, "_chat_session_id", None)

        if token and session_id and main_window.user_id:
            # 检查是否有引用消息
            reply_to_id = getattr(main_window, "_reply_to_message_id", None)
            reply_to_text = getattr(main_window, "_reply_to_message_text", None)
            reply_to_username = getattr(main_window, "_reply_to_username", None)
            reply_to_message_type = getattr(main_window, "_reply_to_message_type", None)
            
            # 获取当前用户名
            current_username = None
            try:
                from client.login.login_status_manager import check_login_status
                _, _, current_username = check_login_status()
            except Exception:
                pass
            
            # 先乐观展示自己的消息（包含引用信息）
            # 注意：此时没有message_id，发送成功后会通过轮询获取完整消息信息
            # 如果没有设置引用消息类型，则根据内容自动检测
            if reply_to_message_type is None and reply_to_text:
                if reply_to_text.startswith("data:image"):
                    reply_to_message_type = "image"
                else:
                    reply_to_message_type = "text"
            
            append_chat_message(
                main_window, 
                text, 
                from_self=True,
                reply_to_message_id=reply_to_id,
                reply_to_message=reply_to_text,
                reply_to_username=reply_to_username,
                reply_to_message_type=reply_to_message_type,
                from_user_id=main_window.user_id,
                from_username=current_username,
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

            def send_via_websocket():
                try:
                    # 检查是否有引用消息
                    reply_to_id = getattr(main_window, "_reply_to_message_id", None)
                    # 如果之前点击引用时还没有 message_id，这里再尝试从被引用控件读取一次（可能已同步到ID）
                    if reply_to_id is None and hasattr(main_window, "_reply_to_widget"):
                        try:
                            cached_widget = getattr(main_window, "_reply_to_widget", None)
                            if cached_widget:
                                cached_id = cached_widget.property("message_id")
                                if cached_id:
                                    reply_to_id = cached_id
                        except Exception:
                            pass
                    
                    # 验证引用消息ID是否有效（必须是大于0的正整数）
                    if reply_to_id is not None:
                        try:
                            reply_to_id_int = int(reply_to_id)
                            # 数据库ID从1开始，所以允许 >= 1
                            if reply_to_id_int <= 0:
                                logging.warning(f"引用消息ID无效: {reply_to_id}（ID必须大于0），将按普通消息发送")
                                reply_to_id = None
                            else:
                                # 先在本地检查是否存在该消息（自己刚发出的消息可立即引用）
                                local_exists = False
                                try:
                                    if hasattr(main_window, "_message_widgets_map") and reply_to_id_int in getattr(main_window, "_message_widgets_map", {}):
                                        local_exists = True
                                    elif hasattr(main_window, "chat_layout"):
                                        for i in range(main_window.chat_layout.count() - 1, -1, -1):
                                            item = main_window.chat_layout.itemAt(i)
                                            if not item or not item.widget():
                                                continue
                                            widget = item.widget()
                                            existing_id = widget.property("message_id")
                                            if existing_id is None:
                                                continue
                                            try:
                                                if int(existing_id) == reply_to_id_int:
                                                    local_exists = True
                                                    break
                                            except Exception:
                                                continue
                                except Exception:
                                    pass
                                
                                # 如果本地没有该消息，交由服务端在收到 reply_to_message_id 后自行校验，
                                # 这里不再通过已废弃的 HTTP 接口进行验证
                        except (ValueError, TypeError):
                            logging.warning(f"引用消息ID格式错误: {reply_to_id}，将按普通消息发送")
                            reply_to_id = None
                    
                    # 使用 WebSocket 发送消息
                    from client.utils.websocket_helper import send_message_via_websocket
                    resp = send_message_via_websocket(
                        main_window,
                        session_id,
                        text,
                        message_type="text",
                        reply_to_message_id=reply_to_id
                    )
                    
                    # 清除引用状态
                    if hasattr(main_window, "_reply_to_message_id"):
                        main_window._reply_to_message_id = None
                    if hasattr(main_window, "_reply_to_message_text"):
                        main_window._reply_to_message_text = None
                    if hasattr(main_window, "_reply_to_username"):
                        main_window._reply_to_username = None
                    if hasattr(main_window, "_reply_to_widget"):
                        main_window._reply_to_widget = None
                    # 恢复输入框占位符
                    if hasattr(main_window, "chat_input"):
                        main_window.chat_input.setPlaceholderText("输入消息...")
                    return resp
                except Exception as e:
                    logging.error(f"通过 WebSocket 发送消息失败: {e}", exc_info=True)
                    return None

            def handle_response(resp):
                fallback_enable()
                
                if not resp or not resp.get("success"):
                    error_msg = resp.get("message", "消息发送失败，请稍后重试。") if resp else "消息发送失败，请稍后重试。"
                    # 如果是因为 WebSocket 未连接，提供更友好的提示
                    if "WebSocket 未连接" in error_msg or "未初始化" in error_msg:
                        error_msg = "实时通信未连接，请稍等片刻或重新匹配客服。消息将通过备用方式发送。"
                    append_chat_message(
                        main_window,
                        error_msg,
                        from_self=False,
                        is_html=False,
                        streaming=False
                    )
                    return
                
                # WebSocket 发送为异步模式，此处仅表示数据已提交给 Socket.IO。
                # 实际的 message_id、送达/已读状态等全部依赖服务器回推事件，再由 update_ui 同步到界面。
                return

            # 使用QTimer.singleShot在后台执行WebSocket请求，避免阻塞UI
            def do_send():
                resp = send_via_websocket()
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
    reply_to_message_type: Optional[str] = None,  # 引用消息的类型：text, image, file
    from_user_id: Optional[int] = None,
    from_username: Optional[str] = None,
    message_created_time: Optional[str] = None,
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

    # 处理撤回状态 - 如果是撤回消息，先尝试更新现有消息，而不是创建新消息
    if is_recalled and message_id is not None:
        try:
            recalled_id = None
            try:
                recalled_id = int(message_id)
            except (ValueError, TypeError):
                recalled_id = message_id
            
            # 先尝试查找并更新现有消息
            if recalled_id is not None:
                # 优先从 _message_widgets_map 中查找
                # 注意：需要同时尝试整数和字符串键，因为存储时可能类型不一致
                if hasattr(main_window, "_message_widgets_map"):
                    widget_bubble = main_window._message_widgets_map.get(recalled_id)
                    # 如果没找到，尝试字符串键
                    if not widget_bubble and isinstance(recalled_id, int):
                        widget_bubble = main_window._message_widgets_map.get(str(recalled_id))
                    # 如果还没找到，尝试整数键
                    if not widget_bubble and isinstance(recalled_id, str):
                        try:
                            widget_bubble = main_window._message_widgets_map.get(int(recalled_id))
                        except (ValueError, TypeError):
                            pass
                    
                    if widget_bubble:
                        widget, bubble = widget_bubble
                        if widget and not widget.property("is_recalled"):
                            # 找到现有消息，更新为撤回状态
                            # 隐藏整个消息行（包括头像和气泡）以及引用块
                            parent_layout = widget.layout()
                            if parent_layout and bubble:
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
                                
                                # 隐藏包含气泡的row布局中的所有控件（包括头像和气泡）
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
                        
                        # 判断是自己撤回还是对方撤回
                        current_user_id = getattr(main_window, 'user_id', None)
                        if current_user_id is not None and from_user_id is not None:
                            try:
                                is_self_recalled = (int(from_user_id) == int(current_user_id))
                            except (ValueError, TypeError):
                                is_self_recalled = (from_user_id == current_user_id)
                        else:
                            is_self_recalled = (from_user_id == current_user_id)
                        
                        expected_label_texts = set()
                        if is_self_recalled:
                            recall_text = "你撤回了一条消息"
                            expected_label_texts.add(recall_text)
                        else:
                            username = from_username or "用户"
                            if from_user_id and not from_username:
                                if hasattr(main_window, "username"):
                                    username = main_window.username
                                else:
                                    try:
                                        from client.login.login_status_manager import check_login_status
                                        _, _, current_username = check_login_status()
                                        if current_username:
                                            username = current_username
                                    except Exception:
                                        pass
                            recall_text = f"{username}撤回了一条消息"
                            expected_label_texts.add(recall_text)
                        
                        # 检查是否已经有撤回提示标签
                        widget_layout = widget.layout()
                        if widget_layout:
                            # 查找是否已有撤回标签
                            has_recall_label = False
                            for i in range(widget_layout.count()):
                                item = widget_layout.itemAt(i)
                                if item and item.widget():
                                    w = item.widget()
                                    if isinstance(w, QLabel) and w.text() in expected_label_texts:
                                        has_recall_label = True
                                        break
                            
                            # 如果没有撤回标签，创建一个
                            if not has_recall_label:
                                recall_label = QLabel(recall_text)
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
                                widget_layout.insertWidget(0, recall_label)
                        
                        # 标记为已撤回
                        widget.setProperty("is_recalled", True)
                        
                        # 同步更新所有引用了这条消息的引用块文案
                        if hasattr(main_window, "chat_layout"):
                            parent_layout = main_window.chat_layout
                            for i in range(parent_layout.count()):
                                item = parent_layout.itemAt(i)
                                w = item.widget() if item else None
                                if not w:
                                    continue
                                ref_id = w.property("reply_to_message_id")
                                if ref_id is None:
                                    continue
                                try:
                                    ref_id_norm = int(ref_id)
                                except (ValueError, TypeError):
                                    ref_id_norm = ref_id
                                if ref_id_norm == recalled_id:
                                    reply_container = w.property("reply_container")
                                    if reply_container:
                                        sender_name = reply_container.property("reply_sender_name") or ""
                                        reply_label = reply_container.property("reply_label")
                                        new_text = "该引用消息已被撤回"
                                        if sender_name:
                                            new_text = f"{sender_name}: {new_text}"
                                        
                                        # 先找到并删除所有图片相关的控件
                                        thumbnail_label = reply_container.property("reply_thumbnail_label")
                                        thumbnail_layout = reply_container.property("reply_thumbnail_layout")
                                        
                                        # 找到 reply_content_layout
                                        reply_content_layout = None
                                        main_layout = reply_container.layout()
                                        if main_layout and main_layout.count() > 0:
                                            first_item = main_layout.itemAt(0)
                                            if first_item and first_item.layout():
                                                reply_content_layout = first_item.layout()
                                        
                                        # 如果有 thumbnail_layout，完全删除它及其所有子控件
                                        if thumbnail_layout and reply_content_layout:
                                            # 找到 thumbnail_layout 在 reply_content_layout 中的位置
                                            layout_index = -1
                                            for i in range(reply_content_layout.count()):
                                                item = reply_content_layout.itemAt(i)
                                                if item and item.layout() == thumbnail_layout:
                                                    layout_index = i
                                                    break
                                            
                                            if layout_index >= 0:
                                                # 先删除 thumbnail_layout 中的所有控件
                                                while thumbnail_layout.count() > 0:
                                                    item = thumbnail_layout.takeAt(0)
                                                    if item:
                                                        widget = item.widget()
                                                        if widget:
                                                            # 完全删除控件
                                                            widget.hide()
                                                            widget.setVisible(False)
                                                            if isinstance(widget, QLabel):
                                                                widget.setPixmap(QPixmap())
                                                                widget.clear()
                                                            widget.setFixedSize(0, 0)
                                                            widget.setParent(None)
                                                            widget.deleteLater()
                                                        else:
                                                            # 如果是子布局，也删除
                                                            sub_layout = item.layout()
                                                            if sub_layout:
                                                                while sub_layout.count() > 0:
                                                                    sub_item = sub_layout.takeAt(0)
                                                                    if sub_item:
                                                                        sub_widget = sub_item.widget()
                                                                        if sub_widget:
                                                                            sub_widget.hide()
                                                                            sub_widget.setVisible(False)
                                                                            sub_widget.setParent(None)
                                                                            sub_widget.deleteLater()
                                                                sub_layout.deleteLater()
                                                
                                                # 从 reply_content_layout 中移除 thumbnail_layout
                                                reply_content_layout.removeItem(thumbnail_layout)
                                                # 删除 thumbnail_layout 本身
                                                thumbnail_layout.deleteLater()
                                                
                                                # 创建新的文本标签并添加到相同位置
                                                new_reply_label = QLabel(new_text)
                                                new_reply_label.setStyleSheet("""
                                                    QLabel {
                                                        font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                        font-size: 12px;
                                                        color: #4b5563;
                                                        background-color: transparent;
                                                    }
                                                """)
                                                new_reply_label.setWordWrap(True)
                                                new_reply_label.setMaximumWidth(300)  # 限制最大宽度
                                                reply_content_layout.insertWidget(layout_index, new_reply_label)
                                                
                                                # 更新 reply_label 属性
                                                reply_container.setProperty("reply_label", new_reply_label)
                                                reply_label = new_reply_label
                                        else:
                                            # 如果没有 thumbnail_layout，直接更新或创建 reply_label
                                            if reply_label:
                                                reply_label.setText(new_text)
                                            else:
                                                # 如果连 reply_label 都没有，创建一个新的
                                                if reply_content_layout:
                                                    new_reply_label = QLabel(new_text)
                                                    new_reply_label.setStyleSheet("""
                                                        QLabel {
                                                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                            font-size: 12px;
                                                            color: #4b5563;
                                                            background-color: transparent;
                                                        }
                                                    """)
                                                    new_reply_label.setWordWrap(True)
                                                    new_reply_label.setMaximumWidth(300)  # 限制最大宽度
                                                    reply_content_layout.addWidget(new_reply_label)
                                                    reply_container.setProperty("reply_label", new_reply_label)
                                                    reply_label = new_reply_label
                                        
                                        # 删除 thumbnail_label（如果还存在）
                                        if thumbnail_label:
                                            thumbnail_label.hide()
                                            thumbnail_label.setVisible(False)
                                            thumbnail_label.setPixmap(QPixmap())
                                            thumbnail_label.clear()
                                            thumbnail_label.setFixedSize(0, 0)
                                            # 尝试从父布局中移除
                                            parent = thumbnail_label.parent()
                                            if parent:
                                                parent_layout = parent.layout()
                                                if parent_layout:
                                                    parent_layout.removeWidget(thumbnail_label)
                                            thumbnail_label.setParent(None)
                                            thumbnail_label.deleteLater()
                                        
                                        # 清除所有属性
                                        reply_container.setProperty("reply_thumbnail_label", None)
                                        reply_container.setProperty("reply_thumbnail_layout", None)
                                        
                                        # 使用 findChildren 确保找到并删除所有图片标签
                                        all_labels = reply_container.findChildren(QLabel)
                                        for label in all_labels:
                                            # 只处理有图片的标签，且不是新的文本标签
                                            if label.pixmap() and label is not reply_label:
                                                label.hide()
                                                label.setVisible(False)
                                                label.setPixmap(QPixmap())
                                                label.clear()
                                                label.setFixedSize(0, 0)
                                                # 尝试从父布局中移除
                                                parent = label.parent()
                                                if parent:
                                                    parent_layout = parent.layout()
                                                    if parent_layout:
                                                        parent_layout.removeWidget(label)
                                                label.setParent(None)
                                                label.deleteLater()
                                        
                                        # 强制更新整个引用容器和父控件
                                        reply_container.update()
                                        reply_container.repaint()
                                        if w:
                                            w.update()
                                            w.repaint()
                        
                        # 已更新现有消息，直接返回，不创建新消息
                        return
                
                # 如果 _message_widgets_map 中没有找到，尝试从布局中查找
                if hasattr(main_window, "chat_layout"):
                    for i in range(main_window.chat_layout.count() - 1, -1, -1):
                        item = main_window.chat_layout.itemAt(i)
                        if not item or not item.widget():
                            continue
                        widget = item.widget()
                        widget_id = widget.property("message_id")
                        if widget_id is not None:
                            # 尝试将 widget_id 转换为整数进行比较
                            widget_id_matched = False
                            try:
                                widget_id_int = int(widget_id)
                                if isinstance(recalled_id, int):
                                    widget_id_matched = (widget_id_int == recalled_id)
                                else:
                                    try:
                                        recalled_id_int = int(recalled_id)
                                        widget_id_matched = (widget_id_int == recalled_id_int)
                                    except (ValueError, TypeError):
                                        widget_id_matched = (str(widget_id_int) == str(recalled_id))
                            except (ValueError, TypeError):
                                # 如果无法转换为整数，直接进行字符串比较
                                widget_id_matched = (str(widget_id) == str(recalled_id))
                            
                            if widget_id_matched and not widget.property("is_recalled"):
                                # 找到现有消息，更新为撤回状态
                                # 隐藏整个消息行（包括头像和气泡）以及引用块
                                parent_layout = widget.layout()
                                if parent_layout:
                                    # 遍历所有布局项，找到包含头像和气泡的row布局
                                    for i in range(parent_layout.count()):
                                        item = parent_layout.itemAt(i)
                                        if item and item.layout():
                                            row_layout = item.layout()
                                            # 检查这个布局是否包含头像和气泡（通常是QHBoxLayout）
                                            # 隐藏row布局中的所有控件（包括头像和气泡）
                                            for j in range(row_layout.count()):
                                                row_item = row_layout.itemAt(j)
                                                if row_item and row_item.widget():
                                                    w = row_item.widget()
                                                    # 隐藏头像（QLabel with pixmap）和气泡（ChatBubble 或 QLabel without pixmap）
                                                    if isinstance(w, (ChatBubble, QLabel)):
                                                        w.setVisible(False)
                                    
                                    # 隐藏引用块（如果存在），并先隐藏其中的所有缩略图
                                    reply_container = widget.property("reply_container")
                                    if reply_container:
                                        # 先隐藏引用块中的所有缩略图
                                        thumbnail_label = reply_container.property("reply_thumbnail_label")
                                        if thumbnail_label:
                                            thumbnail_label.hide()
                                            thumbnail_label.setVisible(False)
                                        # 使用 findChildren 查找所有图片标签并隐藏
                                        all_labels = reply_container.findChildren(QLabel)
                                        for label in all_labels:
                                            if label.pixmap():
                                                label.hide()
                                                label.setVisible(False)
                                        # 最后隐藏整个引用块
                                        reply_container.setVisible(False)
                                        reply_container.hide()
                                
                                # 隐藏时间标签（如果有）
                                time_label = widget.property("time_label")
                                if time_label:
                                    time_label.setVisible(False)
                                
                                # 判断是自己撤回还是对方撤回
                                current_user_id = getattr(main_window, 'user_id', None)
                                if current_user_id is not None and from_user_id is not None:
                                    try:
                                        is_self_recalled = (int(from_user_id) == int(current_user_id))
                                    except (ValueError, TypeError):
                                        is_self_recalled = (from_user_id == current_user_id)
                                else:
                                    is_self_recalled = (from_user_id == current_user_id)
                                
                                if is_self_recalled:
                                    recall_text = "你撤回了一条消息"
                                else:
                                    username = from_username or "用户"
                                    if from_user_id and not from_username:
                                        if hasattr(main_window, "username"):
                                            username = main_window.username
                                        else:
                                            try:
                                                from client.login.login_status_manager import check_login_status
                                                _, _, current_username = check_login_status()
                                                if current_username:
                                                    username = current_username
                                            except Exception:
                                                pass
                                    recall_text = f"{username}撤回了一条消息"
                                
                                # 检查是否已经有撤回提示标签
                                widget_layout = widget.layout()
                                if widget_layout:
                                    # 查找是否已有撤回标签
                                    has_recall_label = False
                                    for layout_idx in range(widget_layout.count()):
                                        item = widget_layout.itemAt(layout_idx)
                                        if item and item.widget():
                                            w = item.widget()
                                            if isinstance(w, QLabel) and w.text() in ("你撤回了一条消息", f"{username}撤回了一条消息"):
                                                has_recall_label = True
                                                break
                                    
                                    # 如果没有撤回标签，创建一个
                                    if not has_recall_label:
                                        recall_label = QLabel(recall_text)
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
                                        widget_layout.insertWidget(0, recall_label)
                                
                                # 标记为已撤回
                                widget.setProperty("is_recalled", True)
                                
                                # 同步更新所有引用了这条消息的引用块文案
                                if hasattr(main_window, "chat_layout"):
                                    parent_layout = main_window.chat_layout
                                    for layout_idx in range(parent_layout.count()):
                                        item = parent_layout.itemAt(layout_idx)
                                        w = item.widget() if item else None
                                        if not w:
                                            continue
                                        ref_id = w.property("reply_to_message_id")
                                        if ref_id is None:
                                            continue
                                        try:
                                            ref_id_norm = int(ref_id)
                                        except (ValueError, TypeError):
                                            ref_id_norm = ref_id
                                        if ref_id_norm == recalled_id:
                                            reply_container = w.property("reply_container")
                                            if reply_container:
                                                sender_name = reply_container.property("reply_sender_name") or ""
                                                reply_label = reply_container.property("reply_label")
                                                new_text = "该引用消息已被撤回"
                                                if sender_name:
                                                    new_text = f"{sender_name}: {new_text}"
                                                
                                                # 先找到并删除所有图片相关的控件
                                                thumbnail_label = reply_container.property("reply_thumbnail_label")
                                                thumbnail_layout = reply_container.property("reply_thumbnail_layout")
                                                
                                                # 找到 reply_content_layout
                                                reply_content_layout = None
                                                main_layout = reply_container.layout()
                                                if main_layout and main_layout.count() > 0:
                                                    first_item = main_layout.itemAt(0)
                                                    if first_item and first_item.layout():
                                                        reply_content_layout = first_item.layout()
                                                
                                                # 如果有 thumbnail_layout，完全删除它及其所有子控件
                                                if thumbnail_layout and reply_content_layout:
                                                    # 找到 thumbnail_layout 在 reply_content_layout 中的位置
                                                    layout_index = -1
                                                    for i in range(reply_content_layout.count()):
                                                        item = reply_content_layout.itemAt(i)
                                                        if item and item.layout() == thumbnail_layout:
                                                            layout_index = i
                                                            break

                                                    if layout_index >= 0:
                                                        # 先删除 thumbnail_layout 中的所有控件
                                                        while thumbnail_layout.count() > 0:
                                                            item = thumbnail_layout.takeAt(0)
                                                            if not item:
                                                                continue
                                                            widget = item.widget()
                                                            if widget:
                                                                # 完全删除控件
                                                                widget.hide()
                                                                widget.setVisible(False)
                                                                if isinstance(widget, QLabel):
                                                                    widget.setPixmap(QPixmap())
                                                                    widget.clear()
                                                                widget.setFixedSize(0, 0)
                                                                widget.setParent(None)
                                                                widget.deleteLater()
                                                            else:
                                                                # 如果是子布局，也删除
                                                                sub_layout = item.layout()
                                                                if sub_layout:
                                                                    while sub_layout.count() > 0:
                                                                        sub_item = sub_layout.takeAt(0)
                                                                        if sub_item:
                                                                            sub_widget = sub_item.widget()
                                                                            if sub_widget:
                                                                                sub_widget.hide()
                                                                                sub_widget.setVisible(False)
                                                                                sub_widget.setParent(None)
                                                                                sub_widget.deleteLater()
                                                                    sub_layout.deleteLater()
                                                        
                                                        # 从 reply_content_layout 中移除 thumbnail_layout
                                                        reply_content_layout.removeItem(thumbnail_layout)
                                                        # 删除 thumbnail_layout 本身
                                                        thumbnail_layout.deleteLater()
                                                        
                                                        # 创建新的文本标签并添加到相同位置
                                                        new_reply_label = QLabel(new_text)
                                                        new_reply_label.setStyleSheet("""
                                                            QLabel {
                                                                font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                                font-size: 12px;
                                                                color: #4b5563;
                                                                background-color: transparent;
                                                            }
                                                        """)
                                                        new_reply_label.setWordWrap(True)
                                                        new_reply_label.setMaximumWidth(300)
                                                        reply_content_layout.insertWidget(layout_index, new_reply_label)
                                                        
                                                        # 更新 reply_label 属性
                                                        reply_container.setProperty("reply_label", new_reply_label)
                                                        reply_label = new_reply_label
                                                else:
                                                    # 如果没有 thumbnail_layout，直接更新 reply_label
                                                    if reply_label:
                                                        reply_label.setText(new_text)
                                                    else:
                                                        # 如果连 reply_label 都没有，创建一个新的
                                                        if reply_content_layout:
                                                            new_reply_label = QLabel(new_text)
                                                            new_reply_label.setStyleSheet("""
                                                                QLabel {
                                                                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                                    font-size: 12px;
                                                                    color: #4b5563;
                                                                    background-color: transparent;
                                                                }
                                                            """)
                                                            new_reply_label.setWordWrap(True)
                                                            new_reply_label.setMaximumWidth(300)  # 限制最大宽度
                                                            reply_content_layout.addWidget(new_reply_label)
                                                            reply_container.setProperty("reply_label", new_reply_label)
                                                            reply_label = new_reply_label
                                                
                                                # 删除 thumbnail_label（如果还存在）
                                                if thumbnail_label:
                                                    thumbnail_label.hide()
                                                    thumbnail_label.setVisible(False)
                                                    thumbnail_label.setPixmap(QPixmap())
                                                    thumbnail_label.clear()
                                                    thumbnail_label.setFixedSize(0, 0)
                                                    # 尝试从父布局中移除
                                                    parent = thumbnail_label.parent()
                                                    if parent:
                                                        parent_layout = parent.layout()
                                                        if parent_layout:
                                                            parent_layout.removeWidget(thumbnail_label)
                                                    thumbnail_label.setParent(None)
                                                    thumbnail_label.deleteLater()
                                                
                                                # 清除所有属性
                                                reply_container.setProperty("reply_thumbnail_label", None)
                                                reply_container.setProperty("reply_thumbnail_layout", None)
                                                
                                                # 使用 findChildren 确保找到并删除所有图片标签
                                                all_labels = reply_container.findChildren(QLabel)
                                                for label in all_labels:
                                                    # 只处理有图片的标签，且不是新的文本标签
                                                    if label.pixmap() and label is not reply_label:
                                                        label.hide()
                                                        label.setVisible(False)
                                                        label.setPixmap(QPixmap())
                                                        label.clear()
                                                        label.setFixedSize(0, 0)
                                                        # 尝试从父布局中移除
                                                        parent = label.parent()
                                                        if parent:
                                                            parent_layout = parent.layout()
                                                            if parent_layout:
                                                                parent_layout.removeWidget(label)
                                                        label.setParent(None)
                                                        label.deleteLater()
                                                
                                                # 强制更新整个引用容器和父控件
                                                reply_container.update()
                                                reply_container.repaint()
                                                if w:
                                                    w.update()
                                                    w.repaint()
                                
                                # 已更新现有消息，直接返回，不创建新消息
                                return
        except Exception as e:
            logging.error(f"更新撤回消息失败: {e}", exc_info=True)
            # 如果更新失败，继续创建新的撤回提示消息
    
    # 如果没有找到现有消息，或者不是撤回消息，继续正常流程
    # 处理撤回状态 - 如果是撤回消息，只显示居中灰色小字，不显示气泡和头像
    if is_recalled:
        # 隐藏时间标签（如果有）
        if time_label:
            time_label.setVisible(False)
        
        # 判断是自己撤回还是对方撤回
        current_user_id = getattr(main_window, 'user_id', None)
        if current_user_id is not None and from_user_id is not None:
            try:
                is_self_recalled = (int(from_user_id) == int(current_user_id))
            except (ValueError, TypeError):
                is_self_recalled = (from_user_id == current_user_id)
        else:
            is_self_recalled = (from_user_id == current_user_id)
        
        if is_self_recalled:
            recall_text = "你撤回了一条消息"
        else:
            username = from_username or "用户"
            if from_user_id and not from_username:
                if hasattr(main_window, "username"):
                    username = main_window.username
                else:
                    try:
                        from client.login.login_status_manager import check_login_status
                        _, _, current_username = check_login_status()
                        if current_username:
                            username = current_username
                    except Exception:
                        pass
            recall_text = f"{username}撤回了一条消息"
        
        # 创建撤回提示标签（灰色居中）- 一行灰色小字，独立显示，不显示气泡和头像
        recall_label = QLabel(recall_text)
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
        # 直接添加到布局，不显示气泡和头像
        v_layout.addWidget(recall_label)

        # 同步更新所有引用了这条消息的引用块文案
        try:
            recalled_id = None
            if message_id is not None:
                try:
                    recalled_id = int(message_id)
                except (ValueError, TypeError):
                    recalled_id = message_id
            if recalled_id is not None and hasattr(main_window, "chat_layout"):
                parent_layout = main_window.chat_layout
                for i in range(parent_layout.count()):
                    item = parent_layout.itemAt(i)
                    w = item.widget() if item else None
                    if not w:
                        continue
                    ref_id = w.property("reply_to_message_id")
                    if ref_id is None:
                        continue
                    try:
                        ref_id_norm = int(ref_id)
                    except (ValueError, TypeError):
                        ref_id_norm = ref_id
                    if ref_id_norm == recalled_id:
                        reply_container = w.property("reply_container")
                        if reply_container:
                            sender_name = reply_container.property("reply_sender_name") or ""
                            reply_label = reply_container.property("reply_label")
                            new_text = "该引用消息已被撤回"
                            if sender_name:
                                new_text = f"{sender_name}: {new_text}"
                            
                            # 先找到并删除所有图片相关的控件
                            thumbnail_label = reply_container.property("reply_thumbnail_label")
                            thumbnail_layout = reply_container.property("reply_thumbnail_layout")
                            
                            # 找到 reply_content_layout
                            reply_content_layout = None
                            main_layout = reply_container.layout()
                            if main_layout and main_layout.count() > 0:
                                first_item = main_layout.itemAt(0)
                                if first_item and first_item.layout():
                                    reply_content_layout = first_item.layout()
                            
                            # 如果有 thumbnail_layout，完全删除它及其所有子控件
                            if thumbnail_layout and reply_content_layout:
                                # 找到 thumbnail_layout 在 reply_content_layout 中的位置
                                layout_index = -1
                                for i in range(reply_content_layout.count()):
                                    item = reply_content_layout.itemAt(i)
                                    if item and item.layout() == thumbnail_layout:
                                        layout_index = i
                                        break
                                
                                if layout_index >= 0:
                                    # 先删除 thumbnail_layout 中的所有控件
                                    while thumbnail_layout.count() > 0:
                                        item = thumbnail_layout.takeAt(0)
                                        if item:
                                            widget = item.widget()
                                            if widget:
                                                # 完全删除控件
                                                widget.hide()
                                                widget.setVisible(False)
                                                if isinstance(widget, QLabel):
                                                    widget.setPixmap(QPixmap())
                                                    widget.clear()
                                                widget.setFixedSize(0, 0)
                                                widget.setParent(None)
                                                widget.deleteLater()
                                            else:
                                                # 如果是子布局，也删除
                                                sub_layout = item.layout()
                                                if sub_layout:
                                                    while sub_layout.count() > 0:
                                                        sub_item = sub_layout.takeAt(0)
                                                        if sub_item:
                                                            sub_widget = sub_item.widget()
                                                            if sub_widget:
                                                                sub_widget.hide()
                                                                sub_widget.setVisible(False)
                                                                sub_widget.setParent(None)
                                                                sub_widget.deleteLater()
                                                    sub_layout.deleteLater()
                                    
                                    # 从 reply_content_layout 中移除 thumbnail_layout
                                    reply_content_layout.removeItem(thumbnail_layout)
                                    # 删除 thumbnail_layout 本身
                                    thumbnail_layout.deleteLater()
                                    
                                    # 创建新的文本标签并添加到相同位置
                                    new_reply_label = QLabel(new_text)
                                    new_reply_label.setStyleSheet("""
                                        QLabel {
                                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                                            font-size: 12px;
                                            color: #4b5563;
                                            background-color: transparent;
                                        }
                                    """)
                                    new_reply_label.setWordWrap(True)
                                    new_reply_label.setMaximumWidth(300)  # 限制最大宽度
                                    reply_content_layout.insertWidget(layout_index, new_reply_label)
                                    
                                    # 更新 reply_label 属性
                                    reply_container.setProperty("reply_label", new_reply_label)
                                    reply_label = new_reply_label
                            else:
                                # 如果没有 thumbnail_layout，直接更新 reply_label
                                if reply_label:
                                    reply_label.setText(new_text)
                                else:
                                    # 如果连 reply_label 都没有，创建一个新的
                                    if reply_content_layout:
                                        new_reply_label = QLabel(new_text)
                                        new_reply_label.setStyleSheet("""
                                            QLabel {
                                                font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                font-size: 12px;
                                                color: #4b5563;
                                                background-color: transparent;
                                            }
                                        """)
                                        new_reply_label.setWordWrap(True)
                                        new_reply_label.setMaximumWidth(300)  # 限制最大宽度
                                        reply_content_layout.addWidget(new_reply_label)
                                        reply_container.setProperty("reply_label", new_reply_label)
                                        reply_label = new_reply_label
                            
                            # 删除 thumbnail_label（如果还存在）
                            if thumbnail_label:
                                thumbnail_label.hide()
                                thumbnail_label.setVisible(False)
                                thumbnail_label.setPixmap(QPixmap())
                                thumbnail_label.clear()
                                thumbnail_label.setFixedSize(0, 0)
                                # 尝试从父布局中移除
                                parent = thumbnail_label.parent()
                                if parent:
                                    parent_layout = parent.layout()
                                    if parent_layout:
                                        parent_layout.removeWidget(thumbnail_label)
                                thumbnail_label.setParent(None)
                                thumbnail_label.deleteLater()
                            
                            # 清除所有属性
                            reply_container.setProperty("reply_thumbnail_label", None)
                            reply_container.setProperty("reply_thumbnail_layout", None)
                            
                            # 使用 findChildren 确保找到并删除所有图片标签
                            all_labels = reply_container.findChildren(QLabel)
                            for label in all_labels:
                                # 只处理有图片的标签，且不是新的文本标签
                                if label.pixmap() and label is not reply_label:
                                    label.hide()
                                    label.setVisible(False)
                                    label.setPixmap(QPixmap())
                                    label.clear()
                                    label.setFixedSize(0, 0)
                                    # 尝试从父布局中移除
                                    parent = label.parent()
                                    if parent:
                                        parent_layout = parent.layout()
                                        if parent_layout:
                                            parent_layout.removeWidget(label)
                                    label.setParent(None)
                                    label.deleteLater()
                            
                            # 强制更新整个引用容器和父控件
                            reply_container.update()
                            reply_container.repaint()
                            if w:
                                w.update()
                                w.repaint()
        except Exception:
            # 更新引用块失败不影响主流程
            pass

        # 不创建气泡和头像，直接返回
        return
    
    # 气泡 + 头像 行（正常消息才显示）
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
    
    # 处理引用消息显示（引用卡片）：在主布局中单独一行显示引用块，放在正文气泡下方
    if reply_to_message_id and reply_to_message and not is_recalled:
        # 创建引用消息容器（浅灰卡片 + 左侧色条），注意：样式只作用于容器本身，避免子控件“各自被包裹”
        reply_container = QWidget()
        reply_container.setObjectName("reply_container")
        reply_container.setStyleSheet("""
            QWidget#reply_container {
                background-color: #f3f4f6;
                border-radius: 10px;
                margin-top: 6px;
                border: 1px solid #e5e7eb;
            }
        """)
        # 保证整体有一个合理的最小高度，不会被上下压扁（图片引用会在创建缩略图后再抬高）
        reply_container.setMinimumHeight(30)
        reply_layout = QHBoxLayout(reply_container)
        # 给引用卡片留足内边距，避免“字顶到边/溢出”的观感，并让内部内容在气泡内垂直居中
        reply_layout.setContentsMargins(10, 8, 10, 8)
        reply_layout.setSpacing(8)
        reply_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 左侧竖色条，增强层次感
        left_bar = QLabel()
        left_bar.setFixedWidth(3)
        left_bar.setMinimumHeight(26)
        left_bar.setStyleSheet("""
            QLabel {
                background-color: #60a5fa;
                border-radius: 999px;
            }
        """)
        reply_layout.addWidget(left_bar)

        reply_content_layout = QVBoxLayout()
        reply_content_layout.setContentsMargins(0, 0, 0, 0)
        reply_content_layout.setSpacing(2)

        # 获取引用消息的发送者信息
        reply_sender_name = reply_to_username or "用户"
        # 如果是当前用户自己发送的消息，用“我”替代用户名，效果更贴近聊天习惯
        try:
            current_username = getattr(main_window, "username", None)
            if current_username and reply_sender_name == current_username:
                reply_sender_name = "我"
        except Exception:
            pass
        # 检查引用消息是否被撤回
        reply_text = reply_to_message
        if reply_text == "[消息已撤回]":
            reply_text = "该引用消息已被撤回"
        
        # 尝试为图片引用查找原始 base64 内容（data:image/...），用于生成缩略图
        original_image_data: str | None = None
        if reply_to_message_type == "image" and reply_to_message_id is not None:
            try:
                msg_map = getattr(main_window, "_message_widgets_map", None)
                if isinstance(msg_map, dict):
                    # 优先从 _message_widgets_map 中查找
                    # 注意：需要同时尝试整数和字符串键，因为存储时可能类型不一致
                    original_widget = None
                    
                    # 先尝试直接查找（整数或字符串键）
                    if reply_to_message_id in msg_map:
                        original_widget = msg_map[reply_to_message_id][0]
                    # 如果没找到，尝试字符串键
                    elif isinstance(reply_to_message_id, int):
                        str_key = str(reply_to_message_id)
                        if str_key in msg_map:
                            original_widget = msg_map[str_key][0]
                    # 如果还没找到，尝试整数键
                    elif isinstance(reply_to_message_id, str):
                        try:
                            int_key = int(reply_to_message_id)
                            if int_key in msg_map:
                                original_widget = msg_map[int_key][0]
                        except (ValueError, TypeError):
                            pass
                    
                    # 如果找到了原始消息控件，尝试获取原始图片数据
                    if original_widget:
                        raw_image = original_widget.property("raw_image_message")
                        if isinstance(raw_image, str) and raw_image.startswith("data:image"):
                            original_image_data = raw_image
            except Exception:
                original_image_data = None
        
        # 初始化 reply_label，确保在所有分支中都有定义
        reply_label = None
        thumbnail_label = None  # 初始化缩略图标签变量
        
        # 如果是图片消息，显示更美观的“左文右图”缩略图布局
        # 优先使用 original_image_data（从原消息控件里取出的 data:image/...），
        # 如果没有，再尝试使用 reply_text 本身。
        if reply_to_message_type == "image" and (original_image_data or (reply_text and reply_text.startswith("data:image"))):
            try:
                # 解析base64图片
                data_source = original_image_data or reply_text
                b64_part = data_source.split(",", 1)[1] if "," in data_source else ""
                raw = base64.b64decode(b64_part)
                image = QImage.fromData(raw)
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    # 创建 60x60 的缩略图（紧凑且不撑破引用块）
                    thumbnail = pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    
                    # 创建缩略图标签
                    thumbnail_label = QLabel()
                    thumbnail_label.setFixedSize(60, 60)
                    thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    thumbnail_label.setPixmap(thumbnail)
                    thumbnail_label.setStyleSheet("""
                        QLabel {
                            border-radius: 6px;
                            background-color: transparent;
                            border: 1px solid #d1d5db;
                        }
                    """)
                    # 图片引用块高度至少能容纳缩略图
                    reply_container.setMinimumHeight(68)
                    # 立即保存缩略图标签到属性中，方便撤回时隐藏
                    reply_container.setProperty("reply_thumbnail_label", thumbnail_label)
                    
                    # 创建文本标签（显示发送者名称），这个标签也作为 reply_label 用于撤回时更新
                    # 样式参考你给的示例：仅显示 "用户名:"，不再额外加"图片"文字
                    sender_label = QLabel(f"{reply_sender_name}：")
                    sender_label.setStyleSheet("""
                        QLabel {
                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                        font-size: 12px;
                            color: #111827;  /* 深色文字，保证清晰可见 */
                            background-color: transparent;
                        }
                    """)
                    sender_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                    # 限制最大宽度，避免整块引用气泡被用户名拉得太长
                    sender_label.setMaximumWidth(160)
                    reply_label = sender_label  # 使用 sender_label 作为 reply_label
                    
                    # 水平布局：发送者名称 + 缩略图（紧凑排列，中间不要太大空白）
                    thumbnail_layout = QHBoxLayout()
                    thumbnail_layout.setContentsMargins(0, 0, 0, 0)
                    thumbnail_layout.setSpacing(8)
                    thumbnail_layout.addWidget(sender_label)
                    thumbnail_layout.addWidget(thumbnail_label)
                    # 保存 thumbnail_layout 到属性中，方便撤回时处理
                    reply_container.setProperty("reply_thumbnail_layout", thumbnail_layout)
                    
                    reply_content_layout.addLayout(thumbnail_layout)
                else:
                    # 图片解析失败，显示文本
                    reply_label = QLabel(f"{reply_sender_name}: [图片]")
                    reply_label.setStyleSheet("""
                        QLabel {
                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                            font-size: 12px;
                            color: #111827;
                            background-color: transparent;
                        }
                    """)
                    reply_label.setWordWrap(True)
                    reply_content_layout.addWidget(reply_label)
            except Exception as e:
                logging.error(f"解析引用图片失败: {e}", exc_info=True)
                # 解析失败，显示文本
                reply_label = QLabel(f"{reply_sender_name}: [图片]")
                reply_label.setStyleSheet("""
                    QLabel {
                        font-family: "Microsoft YaHei", "SimHei", "Arial";
                        font-size: 12px;
                        color: #111827;
                        background-color: transparent;
                    }
                """)
                reply_label.setWordWrap(True)
                reply_label.setMaximumWidth(300)  # 限制最大宽度
                reply_content_layout.addWidget(reply_label)
        else:
            # 文本消息，单行显示：`用户名: 内容预览`
            if reply_text and len(reply_text) > 80:
                reply_text = reply_text[:80] + "..."

            display_text = f"{reply_sender_name}: {reply_text}"
            reply_label = QLabel(display_text)
            reply_label.setStyleSheet("""
                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 12px;
                    color: #111827;  /* 深色文字 */
                    background-color: transparent;
                }
            """)
            # 文本引用允许换行（更像微信的引用卡片），避免长文本挤出气泡
            reply_label.setWordWrap(True)
            reply_label.setMinimumHeight(20)
            reply_label.setMaximumWidth(320)
            # 在引用气泡内部左对齐、垂直方向居中
            reply_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            reply_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
            reply_content_layout.addWidget(reply_label)

        # 把引用信息存到容器属性里，方便后续在被引用消息撤回时更新文案/缩略图
        reply_container.setProperty("reply_sender_name", reply_sender_name)
        if reply_label:
            reply_container.setProperty("reply_label", reply_label)
        # 缩略图标签已在创建时保存到属性中（如果存在的话）

        reply_layout.addLayout(reply_content_layout)

        # 让引用卡片宽度更“饱满”，但封顶避免横向太长
        reply_container.setMinimumWidth(160)
        reply_container.setMaximumWidth(320)

        # 引用块单独占一行，与消息气泡左对齐（放在正文气泡下方）
        reply_row = QHBoxLayout()
        reply_row.setContentsMargins(0, 0, 0, 0)
        reply_row.setSpacing(6)

        # 引用块始终与消息气泡的左边缘对齐
        # 对于用户消息，消息气泡右对齐，但引用块需要与气泡左边缘对齐
        # 对于客服消息，消息气泡左对齐，引用块也与气泡左边缘对齐
        if from_self:
            # 用户消息：引用块右对齐，与消息气泡左边缘对齐
            reply_row.addStretch()
            reply_row.addWidget(reply_container)
            reply_row.addSpacing(38)  # 32px 头像 + 6px spacing
        else:
            # 客服消息：引用块左对齐，与消息气泡左边缘对齐
            reply_row.addSpacing(38)  # 32px 头像 + 6px spacing
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
    
    # 保存消息创建时间（用于撤回时间检查）
    if message_created_time:
        message_widget.setProperty("message_created_time", message_created_time)
    else:
        # 如果没有提供创建时间，使用当前时间（用于乐观展示的消息）
        message_widget.setProperty("message_created_time", datetime.now().isoformat())
    
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
                
                # 验证消息ID是否有效（必须是正整数）
                valid_msg_id = None
                if current_msg_id is not None:
                    try:
                        msg_id_int = int(current_msg_id)
                        # 数据库ID从1开始，所以允许 >= 1
                        if msg_id_int > 0:
                            # 不再通过 HTTP 接口验证是否存在，由服务端在收到引用 ID 后自行校验
                                valid_msg_id = msg_id_int
                    except (ValueError, TypeError):
                        pass
                
                # 如果 message_id 无效，不再弹出阻塞弹窗，允许用户继续引用
                # 这种情况下仅作为普通回复发送（不携带 reply_to_message_id），前端仍会显示引用提示
                # 这样即使消息刚发送还未绑定 ID，用户也可以顺畅引用自己的消息
                main_window._reply_to_message_id = valid_msg_id  # 可能为 None
                main_window._reply_to_message_text = content
                # 设置引用消息类型为文本（表情也是文本）
                main_window._reply_to_message_type = "text"
                # 记录被引用的控件，发送前可再次读取最新的 message_id（避免乐观消息尚未分配ID）
                main_window._reply_to_widget = message_widget
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
                message_created_time = message_widget.property("message_created_time")
                
                # 检查消息是否超过2分钟
                can_recall = False
                if current_msg_id and message_created_time:
                    try:
                        from datetime import timedelta
                        created_time = datetime.fromisoformat(message_created_time.replace('Z', '+00:00'))
                        time_diff = datetime.now() - created_time.replace(tzinfo=None)
                        can_recall = time_diff <= timedelta(minutes=2)
                    except Exception:
                        # 如果时间解析失败，允许撤回（由后端验证）
                        can_recall = True
                elif current_msg_id:
                    # 如果没有创建时间，允许撤回（由后端验证）
                    can_recall = True
                
                if current_msg_id and can_recall:
                    recall_action.setEnabled(True)
                else:
                    recall_action.setEnabled(False)
                    if not current_msg_id:
                        recall_action.setToolTip("消息ID尚未同步，请稍后再试")
                    else:
                        recall_action.setToolTip("消息已超过2分钟，无法撤回")
                
                def recall_message_action():
                    # 再次检查message_id（确保是最新的）
                    current_msg_id = message_widget.property("message_id")
                    if not current_msg_id:
                        # 不弹窗，直接返回（因为按钮已禁用）
                        return
                    
                    # 再次检查时间（防止在检查后到点击之间超过2分钟）
                    message_created_time = message_widget.property("message_created_time")
                    if message_created_time:
                        try:
                            from datetime import timedelta
                            created_time = datetime.fromisoformat(message_created_time.replace('Z', '+00:00'))
                            time_diff = datetime.now() - created_time.replace(tzinfo=None)
                            if time_diff > timedelta(minutes=2):
                                # 超过2分钟，直接禁用，不弹窗
                                recall_action.setEnabled(False)
                                return
                        except Exception:
                            pass
                    
                    # 使用 WebSocket 撤回消息
                    from client.utils.websocket_helper import recall_message_via_websocket
                    
                    try:
                        resp = recall_message_via_websocket(main_window, current_msg_id)
                        if resp.get("success"):
                            # 判断是自己撤回还是对方撤回
                            # 自己撤回的消息，显示"你撤回了一条消息"
                            recall_text = "你撤回了一条消息"
                            
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
                            
                            # 创建撤回提示标签（灰色居中）- 简化样式，只显示一行灰色小字
                            recall_label = QLabel(recall_text)
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
                            # 撤回失败，但不弹窗（后端会返回具体原因，但用户已经看到按钮被禁用了）
                            error_msg = resp.get("message", "撤回失败")
                            logging.warning(f"撤回消息失败: {error_msg}")
                    except Exception as e:
                        # 不弹窗，只记录日志
                        logging.error(f"撤回消息时发生错误: {e}", exc_info=True)
                
                recall_action.triggered.connect(recall_message_action)
            
            # 将局部坐标转换为全局坐标
            global_pos = message_widget.mapToGlobal(pos)
            menu.exec(global_pos)
        
        message_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        message_widget.customContextMenuRequested.connect(show_context_menu)
        
        # 存储消息ID和控件引用，用于更新撤回状态和消息查找
        # 即使 message_id 是 None（乐观展示），也要注册到 _message_widgets_map，以便后续更新
        if not hasattr(main_window, "_message_widgets_map"):
            main_window._message_widgets_map = {}
        
        # 如果 message_id 不为 None，先检查是否已经存在该 message_id 的消息（避免重复显示）
        if message_id is not None:
            if message_id in main_window._message_widgets_map:
                # 消息已经存在，不重复添加
                return
            main_window._message_widgets_map[message_id] = (message_widget, bubble_label)
            message_widget.setProperty("message_id", message_id)
        else:
            # 乐观展示时，使用 None 作为临时 key，后续收到 message_id 后会更新
            # 但要注意：如果已经有 None 的消息，需要先移除（避免覆盖）
            if None in main_window._message_widgets_map:
                # 如果已经有乐观展示的消息，检查是否是同一条消息（通过内容匹配）
                existing_widget, existing_bubble = main_window._message_widgets_map[None]
                # 如果内容匹配，不重复添加；否则移除旧的（可能是之前的消息）
                try:
                    if hasattr(existing_bubble, 'toPlainText'):
                        existing_text = existing_bubble.toPlainText()
                    elif hasattr(existing_bubble, 'text'):
                        existing_text = existing_bubble.text()
                    else:
                        existing_text = ""
                    import re
                    existing_clean = re.sub(r'<[^>]+>', '', existing_text).strip()
                    content_clean = re.sub(r'<[^>]+>', '', effective_content).strip()
                    if existing_clean == content_clean:
                        # 内容相同，不重复添加
                        return
                except Exception:
                    pass
                # 移除旧的乐观展示消息
                del main_window._message_widgets_map[None]
            main_window._message_widgets_map[None] = (message_widget, bubble_label)
            message_widget.setProperty("message_id", None)
    
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
    
    # 用户点击匹配客服时，立即建立 WebSocket 连接
    # 这样即使匹配失败（加入等待队列），客服接入后也能立即通信
    from client.login.token_storage import read_token
    token = read_token()
    if token:
        try:
            from client.utils.websocket_helper import connect_websocket
            if connect_websocket(main_window, main_window.user_id, token):
                logging.info("用户点击匹配客服，WebSocket 连接成功")
            else:
                logging.warning("用户点击匹配客服，WebSocket 连接失败，将在匹配成功后重试")
        except Exception as e:
            logging.error(f"建立 WebSocket 连接失败: {e}", exc_info=True)
    
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
    """匹配人工客服（通过 WebSocket）"""
    from client.login.token_storage import read_token
    from client.utils.websocket_helper import get_or_create_websocket_client, connect_websocket
    
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
        # 确保 WebSocket 连接
        ws_client = get_or_create_websocket_client(main_window)
        if not ws_client or ws_client.status.value != "connected":
            if not connect_websocket(main_window, main_window.user_id, token):
                raise RuntimeError("WebSocket 连接失败，无法匹配客服")

        response = ws_client.match_agent(session_id) if ws_client else None
        
        # 移除匹配中的消息
        if hasattr(main_window, "_matching_message_widget") and main_window._matching_message_widget:
            widget = main_window._matching_message_widget.pop(0)
            if widget:
                widget.deleteLater()
        
        if response and response.get("success") and response.get("matched"):
            # 一旦匹配到在线客服，用户端立即进入对话模式
            from gui.handlers.chat_handlers import clear_all_chat_messages, add_connected_separator

            # 清空原有聊天内容
            clear_all_chat_messages(main_window)
            
            # 标记为已连接人工客服
            main_window._human_service_connected = True
            main_window._matched_agent_id = response.get("agent_id")
            
            # 添加"已连接客服，可以开始对话"的分隔线
            add_connected_separator(main_window)

            logging.info("已为用户匹配到在线客服，已进入对话模式")
        else:
            # 匹配失败或暂无在线客服，加入等待队列
            safe_response = response or {}
            wait_message = safe_response.get("message", "暂无在线客服，您的请求已加入等待队列，客服接入后会主动联系您。")
            append_chat_message(
                main_window,
                wait_message,
                from_self=False,
                is_html=False,
                streaming=False
            )
    except Exception as e:
        # API调用失败
        logging.error(f"匹配客服时发生错误: {e}", exc_info=True)
        if hasattr(main_window, "_matching_message_widget") and main_window._matching_message_widget:
            widget = main_window._matching_message_widget.pop(0)
            if widget:
                widget.deleteLater()
        
        append_chat_message(
            main_window,
            f"匹配客服时发生错误：{str(e)}，请稍后重试。",
            from_self=False,
            is_html=False,
            streaming=False
        )
    
    # 重置匹配状态
    main_window._matching_human_service = False


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
    # 先在界面上乐观展示图片；raw_message 会在真正发送时设置为 data_url
    # 如果已连接人工客服，使用 WebSocket 发送图片
    if getattr(main_window, "_human_service_connected", False) and getattr(main_window, "_chat_session_id", None):
        from client.login.token_storage import read_token
        from client.utils.websocket_helper import get_or_create_websocket_client
        
        token = read_token()
        session_id = getattr(main_window, "_chat_session_id", None)

        # 将图片转为 data URL 发送给后端（后端 message_type=image）
        try:
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
            data_url = f"data:image/png;base64,{b64}"
        except Exception:
            data_url = "[图片发送失败]"

        # 乐观展示：生成 data_url 后再插入到聊天区，这样引用自己发送的图片时可以读到 raw_image_message
        raw_for_widget = data_url if isinstance(data_url, str) and data_url.startswith("data:image") else None

        # 读取当前的引用信息，用于本地预览时就显示引用气泡
        reply_to_id_preview = getattr(main_window, "_reply_to_message_id", None)
        reply_to_text_preview = getattr(main_window, "_reply_to_message_text", None)
        reply_to_username_preview = getattr(main_window, "_reply_to_username", None)
        reply_to_type_preview = getattr(main_window, "_reply_to_message_type", None)

        append_image_message(
            main_window,
            scaled,
            from_self=True,
            message_id=None,
            message_created_time=None,
            from_user_id=main_window.user_id,
            from_username=getattr(main_window, "username", None),
            reply_to_message_id=reply_to_id_preview,
            reply_to_message=reply_to_text_preview,
            reply_to_username=reply_to_username_preview,
            reply_to_message_type=reply_to_type_preview,
            is_recalled=False,
            raw_message=raw_for_widget,
        )

        def restore():
            main_window.chat_input.setEnabled(True)
            if hasattr(main_window, 'chat_send_button'):
                main_window.chat_send_button.setEnabled(True)
                if original_text:
                    main_window.chat_send_button.setText(original_text)
                main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())

        # 直接在主线程中使用 WebSocket 客户端发送（WebSocket 发送是异步的，不会阻塞UI）
        from client.utils.websocket_helper import get_or_create_websocket_client
        
        ws_client = get_or_create_websocket_client(main_window)
        if not ws_client or not ws_client.is_connected():
            append_chat_message(main_window, "WebSocket 未连接，请稍后重试。", from_self=False)
            restore()
            return
        
        # 检查是否有引用消息
        reply_to_id = getattr(main_window, "_reply_to_message_id", None)
        
        # 验证引用消息ID是否有效（必须是大于0的正整数）
        if reply_to_id is not None:
            try:
                reply_to_id_int = int(reply_to_id)
                # 数据库ID从1开始，所以允许 >= 1
                if reply_to_id_int <= 0:
                    logging.warning(f"引用消息ID无效: {reply_to_id}（ID必须大于0），将按普通消息发送")
                    reply_to_id = None
            except (ValueError, TypeError):
                logging.warning(f"引用消息ID格式错误: {reply_to_id}，将按普通消息发送")
                reply_to_id = None
        
        # 使用 WebSocket 客户端发送消息（异步，不阻塞UI）
        ws_client = get_or_create_websocket_client(main_window)
        success = False
        if ws_client and ws_client.is_connected():
            success = ws_client.send_message(
            session_id=session_id,
            message=data_url,
            role="user",
            message_type="image",
            reply_to_message_id=reply_to_id
        )
        
        # 清除引用状态
        if hasattr(main_window, "_reply_to_message_id"):
            main_window._reply_to_message_id = None
        if hasattr(main_window, "_reply_to_message_text"):
            main_window._reply_to_message_text = None
        if hasattr(main_window, "_reply_to_username"):
            main_window._reply_to_username = None
        # 恢复输入框占位符
        if hasattr(main_window, "chat_input"):
            main_window.chat_input.setPlaceholderText("请输入消息...")
        
        if success:
            # 发送成功，恢复UI状态
            restore()
        else:
            # 发送失败，显示错误并恢复UI状态
            append_chat_message(main_window, "图片发送失败，请稍后重试。", from_self=False)
            restore()
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


def append_image_message(
    main_window: "MainWindow",
    pixmap: QPixmap,
    from_self: bool = True,
    message_id: Optional[int] = None,
    message_created_time: Optional[str] = None,
    from_user_id: Optional[int] = None,
    from_username: Optional[str] = None,
    reply_to_message_id: Optional[int] = None,
    reply_to_message: Optional[str] = None,
    reply_to_username: Optional[str] = None,
    reply_to_message_type: Optional[str] = None,
    is_recalled: bool = False,
    raw_message: Optional[str] = None,
):
    """发送图片消息，不使用气泡，直接显示圆角图片 + 头像。

    raw_message: 原始消息内容（例如 data:image/... 的 base64 串），用于后续“引用图片”时生成 40x40 缩略图。
    """
    if not hasattr(main_window, "chat_layout"):
        return

    # 处理撤回消息：查找现有消息并更新为撤回状态，同时更新所有引用块
    if is_recalled and message_id is not None:
        try:
            recalled_id = None
            try:
                recalled_id = int(message_id)
            except (ValueError, TypeError):
                recalled_id = message_id
            
            # 先尝试查找并更新现有消息
            if recalled_id is not None:
                # 优先从 _message_widgets_map 中查找
                if hasattr(main_window, "_message_widgets_map"):
                    widget_img = main_window._message_widgets_map.get(recalled_id)
                    # 如果没找到，尝试字符串键
                    if not widget_img and isinstance(recalled_id, int):
                        widget_img = main_window._message_widgets_map.get(str(recalled_id))
                    # 如果还没找到，尝试整数键
                    if not widget_img and isinstance(recalled_id, str):
                        try:
                            widget_img = main_window._message_widgets_map.get(int(recalled_id))
                        except (ValueError, TypeError):
                            pass
                    
                    if widget_img:
                        widget, img_label = widget_img
                        if widget and not widget.property("is_recalled"):
                            # 找到现有消息，更新为撤回状态
                            # 隐藏图片和头像
                            if img_label:
                                img_label.setVisible(False)
                            parent_layout = widget.layout()
                            if parent_layout:
                                # 隐藏头像
                                for i in range(parent_layout.count()):
                                    item = parent_layout.itemAt(i)
                                    if item and item.layout():
                                        row_layout = item.layout()
                                        for j in range(row_layout.count()):
                                            row_item = row_layout.itemAt(j)
                                            if row_item and row_item.widget():
                                                w = row_item.widget()
                                                if isinstance(w, QLabel) and w.pixmap():
                                                    # 检查是否是头像（固定大小32x32）
                                                    if w.size().width() == 32 and w.size().height() == 32:
                                                        w.setVisible(False)
                            
                            # 隐藏时间标签（如果有）
                            time_label = widget.property("time_label")
                            if time_label:
                                time_label.setVisible(False)
                            
                            # 隐藏引用块（如果存在），并先隐藏其中的所有缩略图
                            reply_container = widget.property("reply_container")
                            if reply_container:
                                # 先隐藏引用块中的所有缩略图
                                thumbnail_label = reply_container.property("reply_thumbnail_label")
                                if thumbnail_label:
                                    thumbnail_label.hide()
                                    thumbnail_label.setVisible(False)
                                # 使用 findChildren 查找所有图片标签并隐藏
                                all_labels = reply_container.findChildren(QLabel)
                                for label in all_labels:
                                    if label.pixmap():
                                        label.hide()
                                        label.setVisible(False)
                                # 最后隐藏整个引用块
                                reply_container.setVisible(False)
                                reply_container.hide()
                            
                            # 判断是自己撤回还是对方撤回
                            current_user_id = getattr(main_window, 'user_id', None)
                            if current_user_id is not None and from_user_id is not None:
                                try:
                                    is_self_recalled = (int(from_user_id) == int(current_user_id))
                                except (ValueError, TypeError):
                                    is_self_recalled = (from_user_id == current_user_id)
                            else:
                                is_self_recalled = (from_user_id == current_user_id)
                            
                            if is_self_recalled:
                                recall_text = "你撤回了一条消息"
                            else:
                                username = from_username or "用户"
                                if from_user_id and not from_username:
                                    if hasattr(main_window, "username"):
                                        username = main_window.username
                                    else:
                                        try:
                                            from client.login.login_status_manager import check_login_status
                                            _, _, current_username = check_login_status()
                                            if current_username:
                                                username = current_username
                                        except Exception:
                                            pass
                                recall_text = f"{username}撤回了一条消息"
                            
                            # 检查是否已经有撤回提示标签
                            widget_layout = widget.layout()
                            if widget_layout:
                                # 查找是否已有撤回标签
                                has_recall_label = False
                                for layout_idx in range(widget_layout.count()):
                                    item = widget_layout.itemAt(layout_idx)
                                    if item and item.widget():
                                        w = item.widget()
                                        if isinstance(w, QLabel) and w.text() in ("你撤回了一条消息", f"{username}撤回了一条消息"):
                                            has_recall_label = True
                                            break
                                
                                # 如果没有撤回标签，创建一个
                                if not has_recall_label:
                                    recall_label = QLabel(recall_text)
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
                                    widget_layout.insertWidget(0, recall_label)
                            
                            # 标记为已撤回
                            widget.setProperty("is_recalled", True)
                            
                            # 同步更新所有引用了这条消息的引用块文案和缩略图
                            if hasattr(main_window, "chat_layout"):
                                parent_layout = main_window.chat_layout
                                for layout_idx in range(parent_layout.count()):
                                    item = parent_layout.itemAt(layout_idx)
                                    w = item.widget() if item else None
                                    if not w:
                                        continue
                                    ref_id = w.property("reply_to_message_id")
                                    if ref_id is None:
                                        continue
                                    try:
                                        ref_id_norm = int(ref_id)
                                    except (ValueError, TypeError):
                                        ref_id_norm = ref_id
                                    if ref_id_norm == recalled_id:
                                        reply_container = w.property("reply_container")
                                        if reply_container:
                                            sender_name = reply_container.property("reply_sender_name") or ""
                                            reply_label = reply_container.property("reply_label")
                                            new_text = "该引用消息已被撤回"
                                            if sender_name:
                                                new_text = f"{sender_name}: {new_text}"
                                            
                                            # 先找到并删除所有图片相关的控件
                                            thumbnail_label = reply_container.property("reply_thumbnail_label")
                                            thumbnail_layout = reply_container.property("reply_thumbnail_layout")
                                            
                                            # 找到 reply_content_layout
                                            reply_content_layout = None
                                            main_layout = reply_container.layout()
                                            if main_layout and main_layout.count() > 0:
                                                first_item = main_layout.itemAt(0)
                                                if first_item and first_item.layout():
                                                    reply_content_layout = first_item.layout()
                                            
                                            # 如果有 thumbnail_layout，完全删除它及其所有子控件
                                            if thumbnail_layout and reply_content_layout:
                                                # 找到 thumbnail_layout 在 reply_content_layout 中的位置
                                                layout_index = -1
                                                for i in range(reply_content_layout.count()):
                                                    item = reply_content_layout.itemAt(i)
                                                    if item and item.layout() == thumbnail_layout:
                                                        layout_index = i
                                                        break

                                                if layout_index >= 0:
                                                    # 先删除 thumbnail_layout 中的所有控件
                                                    while thumbnail_layout.count() > 0:
                                                        item = thumbnail_layout.takeAt(0)
                                                        if not item:
                                                            continue
                                                        widget = item.widget()
                                                        if widget:
                                                            # 完全删除控件
                                                            widget.hide()
                                                            widget.setVisible(False)
                                                            if isinstance(widget, QLabel):
                                                                widget.setPixmap(QPixmap())
                                                                widget.clear()
                                                            widget.setFixedSize(0, 0)
                                                            widget.setParent(None)
                                                            widget.deleteLater()
                                                        else:
                                                            # 如果是子布局，也删除
                                                            sub_layout = item.layout()
                                                            if sub_layout:
                                                                while sub_layout.count() > 0:
                                                                    sub_item = sub_layout.takeAt(0)
                                                                    if sub_item:
                                                                        sub_widget = sub_item.widget()
                                                                        if sub_widget:
                                                                            sub_widget.hide()
                                                                            sub_widget.setVisible(False)
                                                                            sub_widget.setParent(None)
                                                                            sub_widget.deleteLater()
                                                                sub_layout.deleteLater()
                                                    
                                                    # 从 reply_content_layout 中移除 thumbnail_layout
                                                    reply_content_layout.removeItem(thumbnail_layout)
                                                    # 删除 thumbnail_layout 本身
                                                    thumbnail_layout.deleteLater()
                                                    
                                                    # 创建新的文本标签并添加到相同位置
                                                    new_reply_label = QLabel(new_text)
                                                    new_reply_label.setStyleSheet("""
                                                        QLabel {
                                                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                            font-size: 12px;
                                                            color: #4b5563;
                                                            background-color: transparent;
                                                        }
                                                    """)
                                                    new_reply_label.setWordWrap(True)
                                                    new_reply_label.setMaximumWidth(300)
                                                    reply_content_layout.insertWidget(layout_index, new_reply_label)
                                                    
                                                    # 更新 reply_label 属性
                                                    reply_container.setProperty("reply_label", new_reply_label)
                                                    reply_label = new_reply_label
                                            else:
                                                # 如果没有 thumbnail_layout，直接更新 reply_label
                                                if reply_label:
                                                    reply_label.setText(new_text)
                                                else:
                                                    # 如果连 reply_label 都没有，创建一个新的
                                                    if reply_content_layout:
                                                        new_reply_label = QLabel(new_text)
                                                        new_reply_label.setStyleSheet("""
                                                            QLabel {
                                                                font-family: "Microsoft YaHei", "SimHei", "Arial";
                                                                font-size: 12px;
                                                                color: #4b5563;
                                                                background-color: transparent;
                                                            }
                                                        """)
                                                        new_reply_label.setWordWrap(True)
                                                        new_reply_label.setMaximumWidth(300)  # 限制最大宽度
                                                        reply_content_layout.addWidget(new_reply_label)
                                                        reply_container.setProperty("reply_label", new_reply_label)
                                                        reply_label = new_reply_label
                                            
                                            # 删除 thumbnail_label（如果还存在）
                                            if thumbnail_label:
                                                thumbnail_label.hide()
                                                thumbnail_label.setVisible(False)
                                                thumbnail_label.setPixmap(QPixmap())
                                                thumbnail_label.clear()
                                                thumbnail_label.setFixedSize(0, 0)
                                                # 尝试从父布局中移除
                                                parent = thumbnail_label.parent()
                                                if parent:
                                                    parent_layout = parent.layout()
                                                    if parent_layout:
                                                        parent_layout.removeWidget(thumbnail_label)
                                                thumbnail_label.setParent(None)
                                                thumbnail_label.deleteLater()
                                            
                                            # 清除所有属性
                                            reply_container.setProperty("reply_thumbnail_label", None)
                                            reply_container.setProperty("reply_thumbnail_layout", None)
                                            
                                            # 使用 findChildren 确保找到并删除所有图片标签
                                            all_labels = reply_container.findChildren(QLabel)
                                            for label in all_labels:
                                                # 只处理有图片的标签，且不是新的文本标签
                                                if label.pixmap() and label is not reply_label:
                                                    label.hide()
                                                    label.setVisible(False)
                                                    label.setPixmap(QPixmap())
                                                    label.clear()
                                                    label.setFixedSize(0, 0)
                                                    # 尝试从父布局中移除
                                                    parent = label.parent()
                                                    if parent:
                                                        parent_layout = parent.layout()
                                                        if parent_layout:
                                                            parent_layout.removeWidget(label)
                                                    label.setParent(None)
                                                    label.deleteLater()
                                            
                                            # 强制更新整个引用容器和父控件
                                            reply_container.update()
                                            reply_container.repaint()
                                            if w:
                                                w.update()
                                                w.repaint()
                            
                            # 已更新现有消息，直接返回，不创建新消息
                            return
        except Exception as e:
            logging.error(f"处理图片撤回消息失败: {e}", exc_info=True)

    message_widget = QWidget()
    v_layout = QVBoxLayout(message_widget)
    v_layout.setContentsMargins(4, 0, 4, 0)
    v_layout.setSpacing(2)

    time_label = None
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

    # 处理引用消息显示（如果有）：放在图片下方，让整体更自然，样式与文本消息的引用气泡保持一致
    if reply_to_message_id and reply_to_message and not is_recalled:
        # 创建引用消息容器（浅灰卡片 + 左侧色条），与文本消息的引用样式保持一致
        reply_container = QWidget()
        reply_container.setObjectName("reply_container")
        reply_container.setStyleSheet("""
            QWidget#reply_container {
                background-color: #f3f4f6;
                border-radius: 10px;
                margin-top: 6px;
                border: 1px solid #e5e7eb;
            }
        """)
        # 宽度自适应但不铺满整行，避免像输入框一样太长
        from PyQt6.QtWidgets import QSizePolicy
        reply_container.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        reply_layout = QHBoxLayout(reply_container)
        # 给引用卡片留足内边距，避免“字顶到边/溢出”的观感，并让内部内容在气泡内垂直居中
        reply_layout.setContentsMargins(10, 8, 10, 8)
        reply_layout.setSpacing(8)
        reply_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # 左侧竖色条，增强层次感（与文本引用统一）
        left_bar = QLabel()
        left_bar.setFixedWidth(3)
        left_bar.setMinimumHeight(26)
        left_bar.setStyleSheet("""
            QLabel {
                background-color: #60a5fa;
                border-radius: 999px;
            }
        """)
        reply_layout.addWidget(left_bar)

        reply_content_layout = QVBoxLayout()
        reply_content_layout.setContentsMargins(0, 0, 0, 0)
        reply_content_layout.setSpacing(2)

        # 获取引用消息的发送者信息
        reply_sender_name = reply_to_username or "用户"
        reply_text = reply_to_message
        if reply_text == "[消息已撤回]":
            reply_text = "该引用消息已被撤回"

        # 尝试为图片引用查找原始 base64 内容（data:image/...），用于生成缩略图
        original_image_data: str | None = None
        if reply_to_message_type == "image" and reply_to_message_id is not None:
            try:
                msg_map = getattr(main_window, "_message_widgets_map", None)
                if isinstance(msg_map, dict) and reply_to_message_id in msg_map:
                    original_widget = msg_map[reply_to_message_id][0]
                    raw_image = original_widget.property("raw_image_message")
                    if isinstance(raw_image, str) and raw_image.startswith("data:image"):
                        original_image_data = raw_image
                # 如果没找到，尝试字符串键
                if not original_image_data and isinstance(reply_to_message_id, int):
                    if isinstance(msg_map, dict) and str(reply_to_message_id) in msg_map:
                        original_widget = msg_map[str(reply_to_message_id)][0]
                        raw_image = original_widget.property("raw_image_message")
                        if isinstance(raw_image, str) and raw_image.startswith("data:image"):
                            original_image_data = raw_image
                # 如果还没找到，尝试整数键
                if not original_image_data and isinstance(reply_to_message_id, str):
                    try:
                        msg_id_int = int(reply_to_message_id)
                        if isinstance(msg_map, dict) and msg_id_int in msg_map:
                            original_widget = msg_map[msg_id_int][0]
                            raw_image = original_widget.property("raw_image_message")
                            if isinstance(raw_image, str) and raw_image.startswith("data:image"):
                                original_image_data = raw_image
                    except (ValueError, TypeError):
                        pass
            except Exception:
                original_image_data = None

        # 如果是图片消息，显示缩略图
        # 优先使用 original_image_data（从原消息控件里取出的 data:image/...），
        # 如果没有，再尝试使用 reply_text 本身。
        if reply_to_message_type == "image" and (original_image_data or (reply_text and reply_text.startswith("data:image"))):
            try:
                # 解析base64图片
                import base64
                from PyQt6.QtGui import QImage
                data_source = original_image_data or reply_text
                b64_part = data_source.split(",", 1)[1] if "," in data_source else ""
                raw = base64.b64decode(b64_part)
                image = QImage.fromData(raw)
                if not image.isNull():
                    thumb_pixmap = QPixmap.fromImage(image)
                    # 创建 60x60 的缩略图
                    thumbnail = thumb_pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

                    # 创建缩略图标签
                    thumbnail_label = QLabel()
                    thumbnail_label.setFixedSize(60, 60)
                    thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    thumbnail_label.setPixmap(thumbnail)
                    thumbnail_label.setStyleSheet("""
                        QLabel {
                            border-radius: 6px;
                            background-color: transparent;
                            border: 1px solid #d1d5db;
                        }
                    """)
                    # 立即保存缩略图标签到属性中，方便撤回时隐藏
                    reply_container.setProperty("reply_thumbnail_label", thumbnail_label)

                    # 创建文本标签（只显示发送者名称，后面直接跟缩略图）
                    sender_label = QLabel(f"{reply_sender_name}：")
                    sender_label.setStyleSheet("""
                        QLabel {
                            font-family: "Microsoft YaHei", "SimHei", "Arial";
                            font-size: 12px;
                            color: #4b5563;
                            background-color: transparent;
                        }
                    """)
                    reply_label = sender_label  # 使用 sender_label 作为 reply_label

                    # 水平布局：发送者名称 + 缩略图
                    thumbnail_layout = QHBoxLayout()
                    thumbnail_layout.setContentsMargins(0, 0, 0, 0)
                    thumbnail_layout.setSpacing(6)
                    thumbnail_layout.addWidget(sender_label)
                    thumbnail_layout.addWidget(thumbnail_label)
                    thumbnail_layout.addStretch()
                    # 保存 thumbnail_layout 到属性中，方便撤回时处理
                    reply_container.setProperty("reply_thumbnail_layout", thumbnail_layout)

                    reply_content_layout.addLayout(thumbnail_layout)
                else:
                    # 图片解析失败，显示文本
                    reply_label = QLabel(f"{reply_sender_name}: [图片]")
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
            except Exception as e:
                logging.error(f"解析引用图片失败: {e}", exc_info=True)
                # 解析失败，显示文本
                reply_label = QLabel(f"{reply_sender_name}: [图片]")
                reply_label.setStyleSheet("""
                    QLabel {
                        font-family: "Microsoft YaHei", "SimHei", "Arial";
                        font-size: 12px;
                        color: #4b5563;
                        background-color: transparent;
                    }
                """)
                reply_label.setWordWrap(True)
                reply_label.setMaximumWidth(300)  # 限制最大宽度
                reply_content_layout.addWidget(reply_label)
        else:
            # 文本消息，显示文本内容
            if reply_text and len(reply_text) > 50:
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

        # 使用单独一行的水平布局控制引用块对齐方式，
        # 让引用气泡的边缘与图片边缘对齐（用户侧右对齐，客服侧左对齐）
        reply_row = QHBoxLayout()
        reply_row.setContentsMargins(0, 0, 0, 0)
        reply_row.setSpacing(6)

        if from_self:
            # 用户消息：引用气泡的右边缘应该与图片的右边缘对齐
            # 图片行的布局是：[stretch] + img_label + avatar_label
            # 所以引用行应该是：[stretch] + reply_container + [spacer for avatar]
            reply_row.addStretch()
            reply_row.addWidget(reply_container)
            # 添加一个固定宽度的 spacer，宽度等于头像宽度（32px）+ 间距（6px）
            avatar_spacer = QWidget()
            avatar_spacer.setFixedWidth(38)  # 32px 头像 + 6px 间距
            reply_row.addWidget(avatar_spacer)
        else:
            # 客服消息：引用气泡的左边缘应该与图片的左边缘对齐
            # 图片行的布局是：avatar_label + img_label + [stretch]
            # 所以引用行应该是：[spacer for avatar] + reply_container + [stretch]
            # 添加一个固定宽度的 spacer，宽度等于头像宽度（32px）+ 间距（6px）
            avatar_spacer = QWidget()
            avatar_spacer.setFixedWidth(38)  # 32px 头像 + 6px 间距
            reply_row.addWidget(avatar_spacer)
            reply_row.addWidget(reply_container)
            reply_row.addStretch()

        v_layout.addLayout(reply_row)

        # 保存引用块相关属性到 message_widget，便于撤回时更新
        message_widget.setProperty("reply_container", reply_container)
        # 查找 reply_label（可能是 sender_label 或文本 reply_label）
        reply_label_to_save = None
        # 首先尝试从 reply_content_layout 中查找文字标签（没有 pixmap 的 QLabel）
        for i in range(reply_content_layout.count()):
            item = reply_content_layout.itemAt(i)
            if item:
                layout = item.layout()
                if layout:
                    # 如果是布局（如 thumbnail_layout），查找其中的文字 QLabel
                    for j in range(layout.count()):
                        sub_item = layout.itemAt(j)
                        if sub_item and sub_item.widget():
                            w = sub_item.widget()
                            if isinstance(w, QLabel) and not w.pixmap():
                                reply_label_to_save = w
                                break
                    if reply_label_to_save:
                        break
                else:
                    widget = item.widget()
                    if widget and isinstance(widget, QLabel) and not widget.pixmap():
                        reply_label_to_save = widget
                        break
        # 如果还没找到，使用 findChildren 查找所有没有图片的 QLabel
        if not reply_label_to_save:
            all_labels = reply_container.findChildren(QLabel)
            for label in all_labels:
                if not label.pixmap():
                    reply_label_to_save = label
                    break
        if reply_label_to_save:
            reply_container.setProperty("reply_label", reply_label_to_save)
        reply_container.setProperty("reply_sender_name", reply_sender_name)
        message_widget.setProperty("reply_to_message_id", reply_to_message_id)
    
    # 存储消息ID和控件引用，用于更新撤回状态和引用功能
    # 即使 message_id 是 None（乐观展示），也要注册到 _message_widgets_map，以便后续更新
    if not hasattr(main_window, "_message_widgets_map"):
        main_window._message_widgets_map = {}
    
    if message_id is not None:
        main_window._message_widgets_map[message_id] = (message_widget, img_label)
        message_widget.setProperty("message_id", message_id)
    else:
        # 乐观展示时，使用 None 作为临时 key，后续收到 message_id 后会更新
        main_window._message_widgets_map[None] = (message_widget, img_label)
        # 设置一个标记，表示这是乐观展示的消息
        message_widget.setProperty("message_id", None)

    # 保存原始消息内容，方便后续“引用图片”时生成缩略图
    if raw_message and isinstance(raw_message, str):
        message_widget.setProperty("raw_image_message", raw_message)
    
    # 保存消息创建时间（用于撤回时间检查）
    if message_created_time:
        message_widget.setProperty("message_created_time", message_created_time)
    else:
        # 如果没有提供创建时间，使用当前时间
        message_widget.setProperty("message_created_time", datetime.now().isoformat())
    
    # 为图片消息添加右键菜单（引用 + 撤回）
    def show_context_menu(pos: QPoint):
        menu = QMenu(message_widget)
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
        """)
        
        # 引用回复
        reply_action = menu.addAction("引用回复")
        reply_action.setEnabled(True)
        
        def reply_message_action():
            # 允许在 message_id 尚未同步时也进行引用，发送时按普通消息处理
            current_msg_id = message_widget.property("message_id")
            valid_msg_id = None
            if current_msg_id is not None:
                try:
                    msg_id_int = int(current_msg_id)
                    # 数据库ID从1开始，所以允许 >= 1
                    if msg_id_int > 0:
                        valid_msg_id = msg_id_int
                except (ValueError, TypeError):
                    pass
            
            main_window._reply_to_message_id = valid_msg_id  # 可能为 None
            # 直接使用本地信息设置引用内容，不再通过 HTTP 获取详情。
            # 优先从当前图片消息控件中读取原始 data:image/... 内容，方便引用时生成缩略图
            raw_image_message = message_widget.property("raw_image_message")
            if isinstance(raw_image_message, str) and raw_image_message.startswith("data:image"):
                main_window._reply_to_message_text = raw_image_message
                main_window._reply_to_message_type = "image"
            else:
                # 回退：如果没有保存原始内容，则仍然使用占位文本
                main_window._reply_to_message_text = "[图片]"
                main_window._reply_to_message_type = "image"
            
            # 记录被引用的控件，便于后续在拿到 message_id 后自动补齐引用ID
            main_window._reply_to_widget = message_widget
            
            main_window._reply_to_username = from_username or (from_self and "我" or "用户")
            # 在输入框显示引用提示
            if hasattr(main_window, "chat_input"):
                sender_name = main_window._reply_to_username
                placeholder = f"回复 {sender_name}：[图片]"
                main_window.chat_input.setPlaceholderText(placeholder)
                main_window.chat_input.setFocus()
        
        reply_action.triggered.connect(reply_message_action)
        
        # 撤回图片消息（仅自己发送的图片可以撤回）
        if from_self:
            recall_action = menu.addAction("撤回消息")
            current_msg_id = message_widget.property("message_id")
            message_created_time = message_widget.property("message_created_time")
            
            # 检查是否超过2分钟
            can_recall = False
            if current_msg_id and message_created_time:
                try:
                    from datetime import timedelta
                    created_time = datetime.fromisoformat(str(message_created_time).replace('Z', '+00:00'))
                    time_diff = datetime.now() - created_time.replace(tzinfo=None)
                    can_recall = time_diff <= timedelta(minutes=2)
                except Exception:
                    # 解析失败则交给后端再校验
                    can_recall = True
            elif current_msg_id:
                can_recall = True
            
            if current_msg_id and can_recall:
                recall_action.setEnabled(True)
            else:
                recall_action.setEnabled(False)
                if not current_msg_id:
                    recall_action.setToolTip("消息ID尚未同步，请稍后再试")
                else:
                    recall_action.setToolTip("消息已超过2分钟，无法撤回")
            
            def recall_image_message_action():
                # 再次读取最新 message_id 与时间，防止状态变化
                current_msg_id = message_widget.property("message_id")
                if not current_msg_id:
                    return
                
                message_created_time = message_widget.property("message_created_time")
                if message_created_time:
                    try:
                        from datetime import timedelta
                        created_time = datetime.fromisoformat(str(message_created_time).replace('Z', '+00:00'))
                        time_diff = datetime.now() - created_time.replace(tzinfo=None)
                        if time_diff > timedelta(minutes=2):
                            recall_action.setEnabled(False)
                            return
                    except Exception:
                        pass
                
                from client.utils.websocket_helper import recall_message_via_websocket
                try:
                    resp = recall_message_via_websocket(main_window, current_msg_id)
                    if resp.get("success"):
                        # 本地立即更新 UI，隐藏图片并显示撤回提示，后续服务器广播时会自动跳过
                        try:
                            from gui.handlers.chat_handlers import append_chat_message
                            append_chat_message(
                                main_window,
                                "",
                                from_self=True,
                                is_html=False,
                                streaming=False,
                                avatar_base64=None,
                                message_id=current_msg_id,
                                is_recalled=True,
                                from_user_id=getattr(main_window, "user_id", None),
                                from_username=getattr(main_window, "username", None),
                                message_created_time=message_created_time,
                            )
                        except Exception as e:
                            logging.error(f"更新图片撤回消息UI失败: {e}", exc_info=True)
                except Exception as e:
                    logging.error(f"撤回图片消息失败: {e}", exc_info=True)
            
            recall_action.triggered.connect(recall_image_message_action)
        
        global_pos = message_widget.mapToGlobal(pos)
        menu.exec(global_pos)
    
    message_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    message_widget.customContextMenuRequested.connect(show_context_menu)
    
    main_window.chat_layout.addWidget(message_widget)

    scroll_to_bottom(main_window)


def _handle_file_upload_result(main_window: "MainWindow", success: bool, filename: str, size: int, error: str = "", file_path: str = ""):
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

        # 如已有人工客服会话，发送文件内容到客服
        if getattr(main_window, "_human_service_connected", False) and getattr(main_window, "_chat_session_id", None):
            from client.login.token_storage import read_token
            from client.api_client import send_chat_message
            
            token = read_token()
            session_id = getattr(main_window, "_chat_session_id", None)
            
            # 读取文件内容并转换为base64 data URL
            file_data_url = None
            if file_path and os.path.exists(file_path):
                try:
                    import base64
                    import mimetypes
                    # 获取MIME类型
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if not mime_type:
                        mime_type = 'application/octet-stream'
                    
                    # 读取文件并编码为base64
                    with open(file_path, "rb") as f:
                        file_content = f.read()
                    b64_content = base64.b64encode(file_content).decode("utf-8")
                    # 格式: data:{mime_type};base64,{content};filename="{filename}"
                    file_data_url = f"data:{mime_type};base64,{b64_content};filename=\"{filename}\""
                except Exception as e:
                    logging.error(f"读取文件失败: {e}", exc_info=True)
                    append_chat_message(main_window, f"文件读取失败：{str(e)}", from_self=False)
            
            # 如果文件读取失败，使用占位符
            if not file_data_url:
                file_data_url = f"[文件] {filename} ({size_str})"

            def restore():
                main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())

            # 直接在主线程中使用 WebSocket 客户端发送（WebSocket 发送是异步的，不会阻塞UI）
            from client.utils.websocket_helper import get_or_create_websocket_client
            
            ws_client = get_or_create_websocket_client(main_window)
            if not ws_client or not ws_client.is_connected():
                append_chat_message(main_window, "WebSocket 未连接，请稍后重试。", from_self=False)
                restore()
                return
            
            # 使用 WebSocket 客户端发送消息（异步，不阻塞UI）
            success = ws_client.send_message(
                session_id=session_id,
                message=file_data_url,
                role="user",
                message_type="file"
            )
            
            if success:
                # 发送成功，恢复UI状态
                restore()
            else:
                # 发送失败，显示错误并恢复UI状态
                append_chat_message(main_window, "文件发送失败，请稍后重试。", from_self=False)
                restore()
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
    """发送文件，限制 10MB；展示文件名和大小，显示上传进度
    
    为避免通过 WebSocket 发送超大 Base64 数据导致连接异常，这里在客户端
    先做严格的体积限制和错误处理，只在文件成功读取且体积在安全范围内时发送。
    """
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
    # 客户端侧限制：最大 10MB，避免 WebSocket 发送超大 Base64 消息导致断线
    max_size_mb = 10
    if size > max_size_mb * 1024 * 1024:
        # 显示错误提示框给用户，而不是在聊天框中显示
        show_message(
            main_window,
            f"文件大小超过 {max_size_mb} MB 限制，无法通过实时通道发送。\n\n"
            f"请选择小于 {max_size_mb} MB 的文件，或通过其他方式发送该文件。",
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
                main_window, success, filename, size, error, file_path
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

            # 读取文件内容并转换为 base64 data URL
            file_data_url = None
            try:
                import base64
                import mimetypes
                # 获取MIME类型
                mime_type, _ = mimetypes.guess_type(file_path)
                if not mime_type:
                    mime_type = 'application/octet-stream'
                
                # 读取文件并编码为 base64
                with open(file_path, "rb") as f:
                    file_content = f.read()
                b64_content = base64.b64encode(file_content).decode("utf-8")
                # 格式: data:{mime_type};base64,{content};filename="{filename}"
                file_data_url = f"data:{mime_type};base64,{b64_content};filename=\"{filename}\""
            except Exception as e:
                logging.error(f"读取文件失败: {e}", exc_info=True)
                append_chat_message(main_window, f"文件读取失败：{str(e)}", from_self=False)
                # 读取失败时直接恢复 UI，不再发送占位符，避免客服端收到错误文件
                main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                    if original_text:
                        main_window.chat_send_button.setText(original_text)
                    main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
                return

            # 双重保险：如果 file_data_url 仍然为空，则不发送，避免发送错误占位内容
            if not file_data_url:
                append_chat_message(main_window, "文件处理失败，未发送。", from_self=False)
                main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                    if original_text:
                        main_window.chat_send_button.setText(original_text)
                    main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())
                return

            def restore():
                main_window.chat_input.setEnabled(True)
                if hasattr(main_window, 'chat_send_button'):
                    main_window.chat_send_button.setEnabled(True)
                    if original_text:
                        main_window.chat_send_button.setText(original_text)
                    main_window.chat_send_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
                QTimer.singleShot(50, lambda: main_window.chat_input.setFocus())

            # 直接在主线程中使用 WebSocket 客户端发送（WebSocket 发送是异步的，不会阻塞UI）
            from client.utils.websocket_helper import get_or_create_websocket_client
            
            ws_client = get_or_create_websocket_client(main_window)
            if not ws_client or not ws_client.is_connected():
                append_chat_message(main_window, "WebSocket 未连接，请稍后重试。", from_self=False)
                restore()
                return
            
            # 使用 WebSocket 客户端发送消息（异步，不阻塞UI）
            success = ws_client.send_message(
                session_id=session_id,
                message=file_data_url,
                role="user",
                message_type="file"
            )
            
            if success:
                # 发送成功，恢复UI状态
                restore()
            else:
                # 发送失败，显示错误并恢复UI状态
                append_chat_message(main_window, "文件发送失败，请稍后重试。", from_self=False)
                restore()
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
