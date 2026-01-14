"""
WebSocket 辅助函数

提供简化的 WebSocket 使用接口，方便在客户端代码中集成。
"""

import logging
import platform
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

# 全局 UI 调度器，确保从任意线程切换到主线程执行 UI 更新
class _UIDispatcher(QObject):
    trigger = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        # 使用 QueuedConnection 确保信号槽回调在主线程执行
        self.trigger.connect(self._execute, Qt.ConnectionType.QueuedConnection)

    def _execute(self, fn):
        try:
            fn()
        except Exception as e:
            logger.error(f"[UIDispatcher] 执行 UI 更新失败: {e}", exc_info=True)


_ui_dispatcher: Optional[_UIDispatcher] = None


def _get_ui_dispatcher(main_window) -> Optional[_UIDispatcher]:
    """获取（或创建）UI 调度器，放在主线程（使用 main_window 作为 parent）"""
    global _ui_dispatcher
    if _ui_dispatcher is None:
        app = QApplication.instance()
        if not app:
            logger.warning("[UIDispatcher] QApplication 不存在，无法创建调度器")
            return None
        # 使用 main_window 作为 parent，确保调度器在主线程中
        _ui_dispatcher = _UIDispatcher(parent=main_window)
        logger.info("[UIDispatcher] UI 调度器已创建")
    return _ui_dispatcher


def get_or_create_websocket_client(main_window, server_url: str = "http://127.0.0.1:8000"):
    """
    获取或创建 WebSocket 客户端实例
    
    Args:
        main_window: MainWindow 实例
        server_url: 服务器地址
        
    Returns:
        WebSocketClient 实例，如果创建失败则返回 None
    """
    try:
        # 如果已经存在，直接返回
        if hasattr(main_window, '_ws_client') and main_window._ws_client:
            return main_window._ws_client
        
        # 导入 WebSocket 客户端
        try:
            from client.websocket_client import WebSocketClient
        except ImportError:
            logger.error("WebSocket 客户端模块未安装，请运行: pip install python-socketio")
            return None
        
        # 创建新的客户端
        ws_client = WebSocketClient(server_url=server_url)
        
        # 初始化 UI 调度器（确保在主线程中创建）
        _get_ui_dispatcher(main_window)
        
        # 注册回调（所有回调都通过 UI 调度器在主线程中执行）
        def on_connect():
            def _on_connect():
                logger.debug("WebSocket 连接成功")
                # 连接成功后订阅 VIP 信息
                if hasattr(main_window, '_ws_client') and main_window._ws_client:
                    try:
                        main_window._ws_client.subscribe_vip_info()
                    except Exception as e:
                        logger.error(f"订阅 VIP 信息失败: {e}", exc_info=True)
            # 通过 UI 调度器在主线程中执行
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_connect)
            else:
                _on_connect()
        
        def on_disconnect():
            def _on_disconnect():
                logger.warning("WebSocket 连接断开")
            # 通过 UI 调度器在主线程中执行
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_disconnect)
            else:
                _on_disconnect()

        def on_session_accepted_for_user(data):
            """会话已被客服接入（用户侧事件）"""
            def _on_session_accepted_for_user():
                try:
                    session_id = data.get("session_id")
                    agent_id = data.get("agent_id")
                    agent_name = data.get("agent_name")

                    # 仅当当前窗口存在对应的会话时才处理
                    current_session_id = getattr(main_window, "_chat_session_id", None)
                    if not current_session_id or (session_id and current_session_id != session_id):
                        return

                    # 如果已经处于“已连接客服”状态，则不重复处理，避免重复清空界面
                    if getattr(main_window, "_human_service_connected", False):
                        return

                    from gui.handlers.chat_handlers import clear_all_chat_messages, add_connected_separator

                    # 清空原有聊天内容，进入对话模式
                    clear_all_chat_messages(main_window)

                    # 标记为已连接人工客服
                    main_window._human_service_connected = True
                    if agent_id is not None:
                        main_window._matched_agent_id = agent_id

                    # 添加“已连接客服，可以开始对话”的分隔线
                    add_connected_separator(main_window)

                    logger.info(
                        f"会话已被客服接入: session_id={session_id}, agent_id={agent_id}, agent_name={agent_name}"
                    )
                except Exception as e:
                    logger.error(f"处理会话已被客服接入事件失败: {e}", exc_info=True)

            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_session_accepted_for_user)
            else:
                _on_session_accepted_for_user()
        
        def on_message(data):
            # 处理收到的新消息
            # 注意：Socket.IO 的回调可能在后台线程中执行，必须通过 UI 调度器确保在主线程中执行
            try:
                message_id_log = data.get('id') if isinstance(data, dict) else 'unknown'
                
                # 在主线程中执行 UI 更新
                def update_ui():
                    message_id_log = data.get('id') if isinstance(data, dict) else 'unknown'
                    try:
                        message_id = data.get('id')
                        text = data.get('text', '')
                        from_user_id = data.get('from_user_id')
                        from_username = data.get('username')
                        avatar = data.get('avatar')
                        message_type = data.get('message_type', 'text')
                        reply_to_message_id = data.get('reply_to_message_id')
                        # 引用消息摘要信息由服务端随消息一起推送
                        reply_to_message = data.get('reply_to_message')
                        reply_to_username = data.get('reply_to_username')
                        reply_to_message_type = data.get('reply_to_message_type')
                        is_recalled = data.get('is_recalled', False)
                        offline = data.get('offline', False)
                        message_time = data.get('time') or data.get('created_at') or data.get('timestamp')
                        
                        # 初始化 updated 变量，用于标记是否已找到并更新了乐观展示的消息
                        updated = False
                        
                        # 使用服务端提供的 is_from_self 标记（优先使用，更可靠）
                        # 如果没有提供，则回退到通过 user_id 比较判断
                        is_from_self = data.get('is_from_self')
                        current_user_id = getattr(main_window, 'user_id', None)
                        if is_from_self is None:
                            # 回退逻辑：通过 user_id 比较判断
                            if current_user_id is not None and from_user_id is not None:
                                try:
                                    is_from_self = (int(from_user_id) == int(current_user_id))
                                except (ValueError, TypeError):
                                    is_from_self = (from_user_id == current_user_id)
                            else:
                                is_from_self = (from_user_id == current_user_id)
                        
                        # 如果是撤回的消息，先尝试更新现有消息
                        if is_recalled and message_id:
                            try:
                                recalled_id = int(message_id)
                                
                                # 直接调用 append_chat_message，让它自己处理查找和更新逻辑
                                from gui.handlers.chat_handlers import append_chat_message
                                append_chat_message(
                                    main_window,
                                    text or "",
                                    from_self=is_from_self,
                                    is_html=False,
                                    streaming=False,
                                    avatar_base64=avatar,
                                    message_id=recalled_id,
                                    is_recalled=True,
                                    from_user_id=from_user_id,
                                    from_username=from_username,
                                    message_created_time=message_time
                                )
                                # append_chat_message 内部会处理查找和更新，如果找到现有消息会直接返回
                                # 如果没有找到，会创建新的撤回提示消息
                                return
                            except (ValueError, TypeError) as e:
                                logger.error(f"处理撤回消息失败: {e}", exc_info=True)
                        
                        # 如果是自己的消息，且已经通过乐观展示显示过了，则只更新message_id，不重复显示
                        # 注意：只对文本消息和图片消息进行此检查，其他消息类型直接显示
                        if is_from_self and message_id and message_type in ['text', 'image'] and not is_recalled:
                            # 首先检查 _message_widgets_map 中是否已经有该 message_id 的消息
                            # 如果 handle_response 已经更新了 _message_widgets_map，这里应该能找到
                            msg_id_int = None
                            try:
                                msg_id_int = int(message_id)
                            except (ValueError, TypeError):
                                pass
                            
                            if msg_id_int and hasattr(main_window, "_message_widgets_map") and msg_id_int in main_window._message_widgets_map:
                                # 消息已经在 _message_widgets_map 中（可能是 handle_response 已经更新了），跳过
                                return
                            
                            # 检查是否已经显示过（乐观展示的消息可能还没有message_id）
                            # 尝试更新已显示的消息的message_id
                            updated = False
                            if hasattr(main_window, "chat_layout"):
                                # 优先检查 _message_widgets_map 中是否有未设置 message_id 的消息（乐观展示的消息）
                                if hasattr(main_window, "_message_widgets_map") and None in main_window._message_widgets_map:
                                    existing_widget, existing_bubble = main_window._message_widgets_map[None]
                                    # 检查消息类型和内容是否匹配
                                    matched = False
                                    if message_type == 'image':
                                        # 对于图片消息，检查是否是图片
                                        from PyQt6.QtWidgets import QLabel
                                        if isinstance(existing_bubble, QLabel) and existing_bubble.pixmap() is not None:
                                            matched = True
                                    elif message_type == 'text':
                                        # 对于文本消息，检查内容是否匹配
                                        from gui.components.chat_bubble import ChatBubble
                                        if isinstance(existing_bubble, ChatBubble):
                                            try:
                                                bubble_text = existing_bubble.toPlainText() if hasattr(existing_bubble, 'toPlainText') else existing_bubble.text() if hasattr(existing_bubble, 'text') else ""
                                                # 比较文本内容（去除HTML标签和空白字符）
                                                import re
                                                bubble_text_clean = re.sub(r'<[^>]+>', '', bubble_text).strip()
                                                text_clean = re.sub(r'<[^>]+>', '', text).strip()
                                                if bubble_text_clean == text_clean:
                                                    matched = True
                                            except Exception:
                                                pass
                                    
                                    if matched:
                                        # 找到匹配的乐观展示消息，更新message_id
                                        existing_widget.setProperty("message_id", int(message_id))
                                        # 更新 _message_widgets_map
                                        del main_window._message_widgets_map[None]
                                        if not hasattr(main_window, "_message_widgets_map"):
                                            main_window._message_widgets_map = {}
                                        main_window._message_widgets_map[int(message_id)] = (existing_widget, existing_bubble)
                                        updated = True
                                
                                # 如果图片消息没有在 _message_widgets_map 中找到，或者不是图片消息，查找布局中未设置 message_id 的消息
                                if not updated:
                                    # 从最新的消息开始查找（从后往前），找到第一个没有ID且是用户发送的消息
                                    for i in range(main_window.chat_layout.count() - 1, -1, -1):
                                        if updated:
                                            break
                                        item = main_window.chat_layout.itemAt(i)
                                        if item and item.widget():
                                            widget = item.widget()
                                            existing_id = widget.property("message_id")
                                            # 如果消息没有ID或者是0，尝试更新它
                                            if existing_id is None or existing_id == 0 or existing_id == "":
                                                # 检查是否是用户自己的消息（通过布局判断：用户消息在右侧，有stretch）
                                                layout = widget.layout()
                                                if layout:
                                                    for j in range(layout.count()):
                                                        if updated:
                                                            break
                                                        layout_item = layout.itemAt(j)
                                                        if layout_item and layout_item.layout():
                                                            row_layout = layout_item.layout()
                                                            for k in range(row_layout.count()):
                                                                if updated:
                                                                    break
                                                                row_item = row_layout.itemAt(k)
                                                                if row_item and row_item.widget():
                                                                    w = row_item.widget()
                                                                    # 检查是否是文本消息的气泡或图片消息
                                                                    from PyQt6.QtWidgets import QLabel
                                                                    from gui.components.chat_bubble import ChatBubble
                                                                    if isinstance(w, ChatBubble) or (isinstance(w, QLabel) and w.pixmap() is not None):
                                                                        # 检查前面是否有stretch（用户消息在右侧）
                                                                        if k > 0:
                                                                            prev_item = row_layout.itemAt(k - 1)
                                                                            if prev_item and prev_item.spacerItem():
                                                                                # 对于文本消息，还需要检查内容是否匹配（避免匹配到错误的消息）
                                                                                if message_type == 'text' and isinstance(w, ChatBubble):
                                                                                    # 获取气泡的文本内容进行比较
                                                                                    try:
                                                                                        bubble_text = w.toPlainText() if hasattr(w, 'toPlainText') else w.text() if hasattr(w, 'text') else ""
                                                                                        # 比较文本内容（去除HTML标签和空白字符）
                                                                                        import re
                                                                                        bubble_text_clean = re.sub(r'<[^>]+>', '', bubble_text).strip()
                                                                                        text_clean = re.sub(r'<[^>]+>', '', text).strip()
                                                                                        if bubble_text_clean != text_clean:
                                                                                            # 内容不匹配，继续查找
                                                                                            continue
                                                                                    except Exception:
                                                                                        # 如果无法获取文本内容，跳过内容匹配检查
                                                                                        pass
                                                                                
                                                                                # 找到用户发送的消息，更新message_id
                                                                                widget.setProperty("message_id", int(message_id))
                                                                                if not hasattr(main_window, "_message_widgets_map"):
                                                                                    main_window._message_widgets_map = {}
                                                                                # 如果 w 是图片，使用 img_label；否则使用 w
                                                                                if isinstance(w, QLabel) and w.pixmap() is not None:
                                                                                    main_window._message_widgets_map[int(message_id)] = (widget, w)
                                                                                else:
                                                                                    main_window._message_widgets_map[int(message_id)] = (widget, w)
                                                                                updated = True
                                                                                break
                            
                            # 如果成功更新了message_id，直接返回，不重复显示
                            if updated:
                                return
                            
                            # 对于自己的消息，如果 updated=False，说明没有找到乐观展示的消息
                            # 但是，为了安全起见，对于自己的消息，如果 _message_widgets_map 中有 None 键（说明有乐观展示的消息），
                            # 即使内容匹配失败，也应该直接返回，避免重复显示
                            # 因为服务器推送的消息可能是重复的（多设备同步），而乐观展示的消息已经在界面上显示了
                            if not updated:
                                # 再次检查 _message_widgets_map[message_id]，确保不会重复显示
                                if msg_id_int and hasattr(main_window, "_message_widgets_map") and msg_id_int in main_window._message_widgets_map:
                                    return
                                # 如果 _message_widgets_map 中有 None 键，说明有乐观展示的消息，即使内容匹配失败，也应该直接返回
                                # 因为服务器推送的消息可能是重复的
                                if hasattr(main_window, "_message_widgets_map") and None in main_window._message_widgets_map:
                                    # 有乐观展示的消息，直接返回，避免重复显示
                                    return
                                # 检查 _displayed_message_ids，如果 message_id 已经在列表中，说明已经处理过，直接返回
                                if not hasattr(main_window, "_displayed_message_ids"):
                                    main_window._displayed_message_ids = set()
                                msg_id_str = str(message_id)
                                if msg_id_str in main_window._displayed_message_ids:
                                    return
                                # 将 message_id 添加到 _displayed_message_ids，防止后续重复处理
                                main_window._displayed_message_ids.add(msg_id_str)
                            
                            # 对于自己的消息，如果 updated=False 且没有找到乐观展示的消息，直接返回，避免重复显示
                            # 因为服务器推送的消息可能是重复的（多设备同步），而乐观展示的消息已经在界面上显示了
                            # 如果确实没有乐观展示的消息（比如消息发送失败后重试），那么应该显示服务器推送的消息
                            # 但是，为了安全起见，我们假设乐观展示的消息总是存在的，所以直接返回
                            return
                        
                        # 消息去重：检查是否已经显示过
                        # 对于自己的消息，如果已经通过乐观展示显示并更新了message_id，上面的逻辑应该已经返回了
                        # 这里只对未处理的消息进行去重检查
                        # 注意：对于客服消息（is_from_self=False），updated 仍然是 False，所以也会进入这个检查
                        # 但是，对于客服消息，我们只检查 _message_widgets_map，不检查 _displayed_message_ids
                        # 因为客服消息没有乐观展示，所以如果 _message_widgets_map 中没有，就应该显示
                        if not updated:  # 只对未找到乐观展示的消息进行去重
                            if not hasattr(main_window, "_displayed_message_ids"):
                                main_window._displayed_message_ids = set()
                            
                            # 如果有message_id，进行去重检查
                            if message_id:
                                msg_id_str = str(message_id)
                                msg_id_int = None
                                try:
                                    msg_id_int = int(message_id)
                                except (ValueError, TypeError):
                                    pass
                                
                                # 首先检查 _message_widgets_map 中是否已经有该 message_id 的消息
                                if msg_id_int and hasattr(main_window, "_message_widgets_map") and msg_id_int in main_window._message_widgets_map:
                                    # 消息已经在 _message_widgets_map 中，说明已经显示过了，跳过
                                    return
                                
                                # 对于自己的消息，检查 _displayed_message_ids 集合
                                # 对于客服消息（is_from_self=False），不检查 _displayed_message_ids，因为客服消息没有乐观展示
                                if is_from_self:
                                    # 然后检查 _displayed_message_ids 集合
                                    if msg_id_str in main_window._displayed_message_ids:
                                        # 检查消息是否真的已经显示（在_message_widgets_map中）
                                        if hasattr(main_window, "_message_widgets_map"):
                                            if msg_id_int and msg_id_int in main_window._message_widgets_map:
                                                # 消息已显示，跳过
                                                return
                                            else:
                                                # 消息ID在列表中但未显示，可能是HTTP轮询获取失败，继续处理
                                                # 从列表中移除，允许重新处理
                                                main_window._displayed_message_ids.discard(msg_id_str)
                                        else:
                                            main_window._displayed_message_ids.discard(msg_id_str)
                                    
                                    main_window._displayed_message_ids.add(msg_id_str)
                            else:
                                # 如果没有message_id，记录日志但继续处理（可能是系统消息）
                                logger.warning(f"收到没有message_id的消息，继续处理")
                        
                        # 导入消息处理函数
                        from gui.handlers.chat_handlers import append_chat_message, append_image_message
                        from PyQt6.QtGui import QPixmap, QImage
                        import base64
                        
                        # 检查 chat_layout 是否存在
                        if not hasattr(main_window, "chat_layout"):
                            logger.error(f"chat_layout 不存在，无法显示消息: message_id={message_id}")
                            return
                        
                        # 如果是撤回的消息
                        if is_recalled:
                            text = "[消息已撤回]"
                        
                        # 获取消息创建时间（用于撤回时间检查）
                        message_time = data.get('time') or data.get('created_at') or data.get('timestamp')
                        
                        # 根据消息类型显示消息
                        if message_type == 'image' and text and text.startswith('data:image'):
                            # 图片消息
                            # 引用信息直接使用服务端推送的摘要（reply_to_message / reply_to_username / reply_to_message_type），
                            # 不再通过已废弃的 HTTP 接口获取
                            try:
                                b64_part = text.split(",", 1)[1] if "," in text else ""
                                raw = base64.b64decode(b64_part)
                                image = QImage.fromData(raw)
                                if not image.isNull():
                                    pixmap = QPixmap.fromImage(image)
                                    # 为了与用户本地发送图片的大小规格一致，统一使用最大边 160 像素的缩放规则
                                    max_size = 160
                                    w, h = pixmap.width(), pixmap.height()
                                    if w > max_size or h > max_size:
                                        if w >= h:
                                            pixmap = pixmap.scaledToWidth(max_size, Qt.TransformationMode.SmoothTransformation)
                                        else:
                                            pixmap = pixmap.scaledToHeight(max_size, Qt.TransformationMode.SmoothTransformation)
                                    # 图片消息支持引用显示
                                    try:
                                        append_image_message(
                                            main_window,
                                            pixmap,
                                            from_self=is_from_self,
                                            message_id=int(message_id) if message_id else None,
                                            message_created_time=message_time,
                                            from_user_id=from_user_id,
                                            from_username=from_username,
                                            reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
                                            reply_to_message=reply_to_message,
                                            reply_to_username=reply_to_username,
                                            reply_to_message_type=reply_to_message_type,
                                            is_recalled=is_recalled,
                                            raw_message=text,  # 保存原始 data:image/...，用于后续引用生成缩略图
                                        )
                                    except Exception as e:
                                        logger.error(f"显示图片消息失败: message_id={message_id}, error={e}", exc_info=True)
                                    # 确保消息ID已添加到已显示列表（避免轮询重复显示）
                                    if message_id:
                                        if not hasattr(main_window, "_displayed_message_ids"):
                                            main_window._displayed_message_ids = set()
                                        main_window._displayed_message_ids.add(str(message_id))
                                else:
                                    # 图片解析失败，显示文本（带引用信息）
                                    append_chat_message(
                                        main_window,
                                        "[图片] 加载失败",
                                        from_self=is_from_self,
                                        is_html=False,
                                        streaming=False,
                                        avatar_base64=avatar,
                                        message_id=int(message_id) if message_id else None,
                                        is_recalled=is_recalled,
                                        reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
                                        reply_to_message=reply_to_message,
                                        reply_to_username=reply_to_username,
                                        reply_to_message_type=reply_to_message_type,
                                        from_user_id=from_user_id,
                                        from_username=from_username,
                                        message_created_time=message_time
                                    )
                            except Exception as e:
                                logger.error(f"处理图片消息失败: {e}", exc_info=True)
                                append_chat_message(
                                    main_window,
                                    "[图片] 加载失败",
                                    from_self=is_from_self,
                                    is_html=False,
                                    streaming=False,
                                    avatar_base64=avatar,
                                    message_id=int(message_id) if message_id else None,
                                    is_recalled=is_recalled,
                                    reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
                                    reply_to_message=reply_to_message,
                                    reply_to_username=reply_to_username,
                                    reply_to_message_type=reply_to_message_type,
                                    from_user_id=from_user_id,
                                    from_username=from_username,
                                    message_created_time=message_time
                                )
                        else:
                            # 文本消息或表情消息（表情也是文本）
                            # 引用信息同样直接使用服务端推送的数据
                            # 检查是否在主线程中
                            from PyQt6.QtCore import QThread
                            from PyQt6.QtWidgets import QApplication
                            app = QApplication.instance()
                            if app:
                                is_main_thread = QThread.currentThread() == app.thread()
                            
                            try:
                                append_chat_message(
                                    main_window,
                                    text,
                                    from_self=is_from_self,
                                    is_html=False,
                                    streaming=False,
                                    avatar_base64=avatar,
                                    message_id=int(message_id) if message_id else None,
                                    is_recalled=is_recalled,
                                    reply_to_message_id=int(reply_to_message_id) if reply_to_message_id else None,
                                    reply_to_message=reply_to_message,
                                    reply_to_username=reply_to_username,
                                    reply_to_message_type=reply_to_message_type,
                                    from_user_id=from_user_id,
                                    from_username=from_username,
                                    message_created_time=message_time
                                )
                            except Exception as e:
                                logger.error(f"显示消息失败: message_id={message_id}, error={e}", exc_info=True)
                            # 确保消息ID已添加到已显示列表（避免轮询重复显示）
                            if message_id:
                                if not hasattr(main_window, "_displayed_message_ids"):
                                    main_window._displayed_message_ids = set()
                                main_window._displayed_message_ids.add(str(message_id))
                    
                    except Exception as e:
                        logger.error(f"处理 WebSocket 消息失败: {e}", exc_info=True)
                
                # 强制通过 UI 调度器在主线程中执行 update_ui
                # Socket.IO 回调总是在后台线程中执行，必须通过信号机制切换到主线程
                try:
                    from PyQt6.QtCore import QThread, QTimer
                    from PyQt6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        is_main_thread = QThread.currentThread() == app.thread()
                        
                        # 无论是否在主线程，都通过 UI 调度器执行，确保安全
                        dispatcher = _get_ui_dispatcher(main_window)
                        if dispatcher:
                            dispatcher.trigger.emit(update_ui)
                        else:
                            # 如果调度器不存在，使用 QTimer.singleShot（必须在主线程中调用）
                            if is_main_thread:
                                QTimer.singleShot(0, update_ui)
                            else:
                                logger.error(f"无法执行 update_ui: 不在主线程且 UI 调度器不存在, message_id={message_id_log}")
                    else:
                        logger.error(f"QApplication 不存在，无法执行 update_ui: message_id={message_id_log}")
                except Exception as e:
                    logger.error(f"执行 update_ui 失败: {e}, message_id={message_id_log}", exc_info=True)
            
            except Exception as e:
                logger.error(f"on_message 回调外层异常: {e}, message_id={data.get('id') if isinstance(data, dict) else 'unknown'}", exc_info=True)
            
            # 如果存在自定义处理函数，也调用它
            if hasattr(main_window, '_on_websocket_message'):
                try:
                    main_window._on_websocket_message(data)
                except Exception as e:
                    logger.error(f"调用自定义 WebSocket 消息处理函数失败: {e}", exc_info=True)
        
        def on_error(error):
            def _on_error():
                logger.error(f"WebSocket 错误: {error}")
            # 通过 UI 调度器在主线程中执行
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_error)
            else:
                _on_error()
        
        def on_vip_status_updated(data):
            """处理 VIP 状态更新"""
            def _on_vip_status_updated():
                try:
                    user_id = data.get('user_id')
                    vip_info = data.get('vip_info', {})
                    
                    # 更新会员信息显示
                    if hasattr(main_window, 'refresh_membership_from_db'):
                        main_window.refresh_membership_from_db()
                except Exception as e:
                    logger.error(f"处理 VIP 状态更新失败: {e}", exc_info=True)
            
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_vip_status_updated)
            else:
                _on_vip_status_updated()
        
        def on_diamond_balance_updated(data):
            """处理钻石余额更新"""
            def _on_diamond_balance_updated():
                try:
                    user_id = data.get('user_id')
                    balance = data.get('balance', 0)
                    
                    # 更新会员信息显示（包含钻石余额）
                    if hasattr(main_window, 'refresh_membership_from_db'):
                        main_window.refresh_membership_from_db()
                except Exception as e:
                    logger.error(f"处理钻石余额更新失败: {e}", exc_info=True)
            
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_diamond_balance_updated)
            else:
                _on_diamond_balance_updated()
        
        def on_user_profile_updated(data):
            """处理用户资料更新"""
            def _on_user_profile_updated():
                try:
                    user_id = data.get('user_id')
                    profile = data.get('profile', {})
                    
                    # 更新会员信息显示
                    if hasattr(main_window, 'refresh_membership_from_db'):
                        main_window.refresh_membership_from_db()
                except Exception as e:
                    logger.error(f"处理用户资料更新失败: {e}", exc_info=True)
            
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_user_profile_updated)
            else:
                _on_user_profile_updated()
        
        def on_message_edited(data):
            """处理消息编辑"""
            def _on_message_edited():
                try:
                    message_id = data.get('message_id')
                    session_id = data.get('session_id')
                    new_content = data.get('new_content')
                    edited_at = data.get('edited_at')
                    
                    # 更新聊天面板中的消息内容
                    # 这里需要根据实际的消息显示逻辑来更新
                    # 可以通过 main_window 的方法来更新消息显示
                    if hasattr(main_window, 'update_message_content'):
                        main_window.update_message_content(message_id, new_content, edited_at)
                except Exception as e:
                    logger.error(f"处理消息编辑失败: {e}", exc_info=True)
            
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_message_edited)
            else:
                _on_message_edited()
        
        def on_session_status_updated(data):
            """处理会话状态更新"""
            def _on_session_status_updated():
                try:
                    session_id = data.get('session_id')
                    status = data.get('status')
                    
                    # 更新会话列表和状态显示
                    # 这里需要根据实际的会话列表逻辑来更新
                    if hasattr(main_window, 'update_session_status'):
                        main_window.update_session_status(session_id, status)
                except Exception as e:
                    logger.error(f"处理会话状态更新失败: {e}", exc_info=True)
            
            dispatcher = _get_ui_dispatcher(main_window)
            if dispatcher:
                dispatcher.trigger.emit(_on_session_status_updated)
            else:
                _on_session_status_updated()
        
        ws_client.on_connect(on_connect)
        ws_client.on_disconnect(on_disconnect)
        ws_client.on_message(on_message)
        ws_client.on_error(on_error)
        ws_client.on_vip_status_updated(on_vip_status_updated)
        ws_client.on_diamond_balance_updated(on_diamond_balance_updated)
        ws_client.on_user_profile_updated(on_user_profile_updated)
        ws_client.on_message_edited(on_message_edited)
        ws_client.on_session_status_updated(on_session_status_updated)
        ws_client.on_session_accepted_for_user(on_session_accepted_for_user)
        
        # 注册撤回消息事件处理器（通过 WebSocketClient 的 message_recalled 事件）
        # WebSocketClient 会将 message_recalled 事件转换为消息格式并调用 on_message_callback
        # 所以这里不需要单独处理，撤回消息会通过 on_message 回调处理
        
        # 保存到 main_window
        main_window._ws_client = ws_client
        
        return ws_client
    
    except Exception as e:
        logger.error(f"创建 WebSocket 客户端失败: {e}", exc_info=True)
        return None


def connect_websocket(main_window, user_id: int, token: str):
    """
    连接 WebSocket
    
    Args:
        main_window: MainWindow 实例
        user_id: 用户ID
        token: 认证 Token
        
    Returns:
        bool: 是否成功
    """
    try:
        ws_client = get_or_create_websocket_client(main_window)
        if not ws_client:
            return False
        
        # 获取设备信息
        device_info = {
            "device_name": platform.node() or "Unknown",
            "device_type": "desktop",
            "platform": platform.system(),
            "os_version": platform.release(),
        }
        
        # 连接
        ws_client.connect(
            user_id=user_id,
            token=token,
            device_id=None,  # 自动生成
            device_info=device_info
        )
        
        return True
    
    except Exception as e:
        logger.error(f"连接 WebSocket 失败: {e}", exc_info=True)
        return False


def send_message_via_websocket(main_window, session_id: str, message: str, 
                               message_type: str = "text", reply_to_message_id: Optional[int] = None) -> Dict[str, Any]:
    """
    通过 WebSocket 发送消息
    
    Args:
        main_window: MainWindow 实例
        session_id: 会话ID
        message: 消息内容
        message_type: 消息类型 (text/image/file)
        reply_to_message_id: 引用消息ID
        
    Returns:
        dict: 发送结果，格式 {"success": bool, "message": str, "message_id": Optional[int]}
    """
    try:
        ws_client = get_or_create_websocket_client(main_window)
        if not ws_client:
            return {
                "success": False,
                "message": "WebSocket 客户端未初始化，请先连接"
            }
        
        # 检查是否已连接
        if not ws_client.is_connected():
            return {
                "success": False,
                "message": "WebSocket 未连接，请先连接"
            }
        
        # 发送消息（异步 emit，返回值仅表示是否成功提交给 Socket.IO 客户端）
        send_ok = ws_client.send_message(
            session_id=session_id,
            message=message,
            role="user",
            message_type=message_type,
            reply_to_message_id=reply_to_message_id
        )
        
        if send_ok:
            return {
                "success": True,
                "message": "消息已发送"
            }
        else:
            return {
                "success": False,
                "message": "消息发送失败"
            }
    
    except Exception as e:
        logger.error(f"通过 WebSocket 发送消息失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"发送失败: {str(e)}"
        }


def recall_message_via_websocket(main_window, message_id: int) -> Dict[str, Any]:
    """
    通过 WebSocket 撤回消息
    
    Args:
        main_window: MainWindow 实例
        message_id: 消息ID
        
    Returns:
        dict: 撤回结果，格式 {"success": bool, "message": str}
    """
    try:
        ws_client = get_or_create_websocket_client(main_window)
        if not ws_client:
            return {
                "success": False,
                "message": "WebSocket 客户端未初始化，请先连接"
            }
        
        # 检查是否已连接
        if not ws_client.is_connected():
            return {
                "success": False,
                "message": "WebSocket 未连接，请先连接"
            }
        
        # 获取用户ID
        user_id = getattr(main_window, 'user_id', None)
        if not user_id:
            return {
                "success": False,
                "message": "未登录，无法撤回消息"
            }
        
        # 撤回消息
        success = ws_client.recall_message(message_id, user_id)
        
        if success:
            return {
                "success": True,
                "message": "消息已撤回"
            }
        else:
            return {
                "success": False,
                "message": "撤回失败（已加入重试队列）"
            }
    
    except Exception as e:
        logger.error(f"通过 WebSocket 撤回消息失败: {e}", exc_info=True)
        return {
            "success": False,
            "message": f"撤回失败: {str(e)}"
        }


def disconnect_websocket(main_window):
    """
    断开 WebSocket 连接
    
    Args:
        main_window: MainWindow 实例
    """
    try:
        if hasattr(main_window, '_ws_client') and main_window._ws_client:
            main_window._ws_client.disconnect()
            main_window._ws_client = None
            logger.debug("WebSocket 已断开")
    except Exception as e:
        logger.error(f"断开 WebSocket 失败: {e}", exc_info=True)



