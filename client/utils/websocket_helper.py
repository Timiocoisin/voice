"""
WebSocket 辅助函数

提供简化的 WebSocket 使用接口，方便在客户端代码中集成。
"""

import logging
import platform
from typing import Optional, Dict, Any
from PyQt6.QtCore import Qt

logger = logging.getLogger(__name__)


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
        
        # 注册回调
        def on_connect():
            logger.info("WebSocket 连接成功")
        
        def on_disconnect():
            logger.warning("WebSocket 连接断开")
        
        def on_message(data):
            # 处理收到的新消息
            # 注意：Socket.IO 的回调可能在后台线程中执行，需要使用 QTimer.singleShot 确保 UI 更新在主线程中执行
            try:
                from PyQt6.QtCore import QTimer
                
                # 在主线程中执行 UI 更新
                def update_ui():
                    try:
                        message_id = data.get('id')
                        text = data.get('text', '')
                        from_user_id = data.get('from_user_id')
                        from_username = data.get('username')
                        avatar = data.get('avatar')
                        message_type = data.get('message_type', 'text')
                        reply_to_message_id = data.get('reply_to_message_id')
                        is_recalled = data.get('is_recalled', False)
                        offline = data.get('offline', False)
                        
                        logger.debug(f"收到 WebSocket 消息: message_id={message_id}, from_user_id={from_user_id}, message_type={message_type}, text_length={len(text) if text else 0}")
                        
                        # 使用服务端提供的 is_from_self 标记（优先使用，更可靠）
                        # 如果没有提供，则回退到通过 user_id 比较判断
                        is_from_self = data.get('is_from_self')
                        if is_from_self is None:
                            # 回退逻辑：通过 user_id 比较判断
                            current_user_id = getattr(main_window, 'user_id', None)
                            if current_user_id is not None and from_user_id is not None:
                                try:
                                    is_from_self = (int(from_user_id) == int(current_user_id))
                                except (ValueError, TypeError):
                                    is_from_self = (from_user_id == current_user_id)
                            else:
                                is_from_self = (from_user_id == current_user_id)
                        
                        logger.debug(f"消息判断: is_from_self={is_from_self}, current_user_id={getattr(main_window, 'user_id', None)}, from_user_id={from_user_id}")
                        
                        # 如果是自己的消息，且已经通过乐观展示显示过了，则只更新message_id，不重复显示
                        # 注意：只对文本消息和图片消息进行此检查，其他消息类型直接显示
                        if is_from_self and message_id and message_type in ['text', 'image']:
                            # 检查是否已经显示过（乐观展示的消息可能还没有message_id）
                            # 尝试更新已显示的消息的message_id
                            updated = False
                            if hasattr(main_window, "chat_layout"):
                                # 对于图片消息，优先检查 _message_widgets_map 中是否有未设置 message_id 的图片消息
                                if message_type == 'image' and hasattr(main_window, "_message_widgets_map") and None in main_window._message_widgets_map:
                                    existing_widget, existing_label = main_window._message_widgets_map[None]
                                    # 检查是否是图片消息（通过 label 是否有 pixmap 判断）
                                    from PyQt6.QtWidgets import QLabel
                                    if isinstance(existing_label, QLabel) and existing_label.pixmap() is not None:
                                        # 找到用户发送的图片消息，更新message_id
                                        existing_widget.setProperty("message_id", int(message_id))
                                        # 更新 _message_widgets_map
                                        del main_window._message_widgets_map[None]
                                        if not hasattr(main_window, "_message_widgets_map"):
                                            main_window._message_widgets_map = {}
                                        main_window._message_widgets_map[int(message_id)] = (existing_widget, existing_label)
                                        updated = True
                                        logger.debug(f"已更新图片消息的message_id: None -> {message_id}")
                                
                                # 如果图片消息没有在 _message_widgets_map 中找到，或者不是图片消息，查找布局中未设置 message_id 的消息
                                if not updated:
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
                                
                                # 只有成功更新了现有消息的message_id时，才跳过显示
                                # 如果更新失败（找不到已显示的消息），应该继续显示消息
                                if updated:
                                    logger.debug(f"已更新消息的message_id: {message_id}，跳过重复显示")
                                    return
                                else:
                                    # 更新失败，说明没有找到已显示的消息，需要显示新消息
                                    logger.debug(f"未找到已显示的消息来更新message_id: {message_id}，将显示新消息")
                        
                        # 消息去重：检查是否已经显示过（只对非自己的消息进行去重检查）
                        # 自己的消息已经在上面处理过了
                        # 注意：对于图片和表情消息，即使消息ID已经在_displayed_message_ids中，
                        # 也要检查是否真的已经显示（可能HTTP轮询获取了消息但显示失败）
                        if not is_from_self:
                            if not hasattr(main_window, "_displayed_message_ids"):
                                main_window._displayed_message_ids = set()
                            
                            # 如果有message_id，进行去重检查
                            if message_id:
                                msg_id_str = str(message_id)
                                
                                # 对于图片消息，即使ID在列表中，也要检查是否真的已经显示
                                # 因为HTTP轮询可能获取了消息但显示失败
                                if msg_id_str in main_window._displayed_message_ids:
                                    # 检查消息是否真的已经显示（在_message_widgets_map中）
                                    if hasattr(main_window, "_message_widgets_map"):
                                        msg_id_int = None
                                        try:
                                            msg_id_int = int(message_id)
                                        except (ValueError, TypeError):
                                            pass
                                        
                                        if msg_id_int and msg_id_int in main_window._message_widgets_map:
                                            # 消息已经显示，跳过
                                            logger.debug(f"忽略重复的 WebSocket 消息: {message_id} (已显示)")
                                            return
                                        else:
                                            # 消息ID在列表中但未显示，可能是HTTP轮询获取失败，继续处理
                                            logger.debug(f"消息ID {message_id} 在列表中但未显示，继续处理")
                                            # 从列表中移除，允许重新处理
                                            main_window._displayed_message_ids.discard(msg_id_str)
                                
                                main_window._displayed_message_ids.add(msg_id_str)
                            else:
                                # 如果没有message_id，记录日志但继续处理（可能是系统消息）
                                logger.debug(f"收到没有message_id的消息，继续处理")
                        
                        # 导入消息处理函数
                        from gui.handlers.chat_handlers import append_chat_message, append_image_message
                        from PyQt6.QtGui import QPixmap, QImage
                        import base64
                        
                        # 如果是撤回的消息
                        if is_recalled:
                            text = "[消息已撤回]"
                        
                        # 获取消息创建时间（用于撤回时间检查）
                        message_time = data.get('time') or data.get('created_at') or data.get('timestamp')
                        
                        # 根据消息类型显示消息
                        if message_type == 'image' and text and text.startswith('data:image'):
                            # 图片消息
                            # 获取引用消息信息（如果有）
                            reply_to_message = None
                            reply_to_username = None
                            reply_to_message_type = None
                            if reply_to_message_id:
                                try:
                                    from client.api_client import get_reply_message
                                    from client.login.token_storage import read_token
                                    reply_token = read_token()
                                    reply_resp = get_reply_message(int(reply_to_message_id), reply_token)
                                    if reply_resp.get("success"):
                                        reply_msg = reply_resp.get("message", {})
                                        if reply_msg.get("is_recalled", False) or reply_msg.get("message") == "[消息已撤回]":
                                            reply_to_message = "该引用消息已被撤回"
                                        else:
                                            reply_to_message = reply_msg.get("message", "")
                                            reply_to_message_type = reply_msg.get("message_type", "text")
                                        reply_to_username = reply_msg.get("from_username")
                                except Exception:
                                    pass
                            
                            try:
                                b64_part = text.split(",", 1)[1] if "," in text else ""
                                raw = base64.b64decode(b64_part)
                                image = QImage.fromData(raw)
                                if not image.isNull():
                                    pixmap = QPixmap.fromImage(image)
                                    if pixmap.width() > 360:
                                        pixmap = pixmap.scaledToWidth(360, Qt.TransformationMode.SmoothTransformation)
                                    # 图片消息支持引用显示
                                    logger.info(f"准备显示图片消息: message_id={message_id}, is_from_self={is_from_self}, from_user_id={from_user_id}")
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
                                            is_recalled=is_recalled
                                        )
                                        logger.info(f"图片消息已成功显示: message_id={message_id}, is_from_self={is_from_self}")
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
                            # 获取引用消息信息
                            reply_to_message = None
                            reply_to_username = None
                            reply_to_message_type = None
                            if reply_to_message_id:
                                try:
                                    from client.api_client import get_reply_message
                                    from client.login.token_storage import read_token
                                    reply_token = read_token()
                                    reply_resp = get_reply_message(int(reply_to_message_id), reply_token)
                                    if reply_resp.get("success"):
                                        reply_msg = reply_resp.get("message", {})
                                        if reply_msg.get("is_recalled", False) or reply_msg.get("message") == "[消息已撤回]":
                                            reply_to_message = "该引用消息已被撤回"
                                        else:
                                            reply_to_message = reply_msg.get("message", "")
                                            reply_to_message_type = reply_msg.get("message_type", "text")
                                        reply_to_username = reply_msg.get("from_username")
                                except Exception as e:
                                    logger.debug(f"获取引用消息失败: {e}")
                            
                            logger.info(f"准备显示消息: message_id={message_id}, text={text[:50] if text else None}, is_from_self={is_from_self}, from_user_id={from_user_id}, from_username={from_username}")
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
                                logger.info(f"消息已成功显示: message_id={message_id}, is_from_self={is_from_self}")
                            except Exception as e:
                                logger.error(f"显示消息失败: message_id={message_id}, error={e}", exc_info=True)
                            # 确保消息ID已添加到已显示列表（避免轮询重复显示）
                            if message_id:
                                if not hasattr(main_window, "_displayed_message_ids"):
                                    main_window._displayed_message_ids = set()
                                main_window._displayed_message_ids.add(str(message_id))
                        
                        # 如果是离线消息，记录日志
                        if offline:
                            logger.info(f"收到离线消息: {message_id}")
                    
                    except Exception as e:
                        logger.error(f"处理 WebSocket 消息失败: {e}", exc_info=True)
                
                # 使用 QTimer.singleShot 确保在主线程中执行
                QTimer.singleShot(0, update_ui)
            
            except Exception as e:
                logger.error(f"处理 WebSocket 消息失败: {e}", exc_info=True)
            
            # 如果存在自定义处理函数，也调用它
            if hasattr(main_window, '_on_websocket_message'):
                try:
                    main_window._on_websocket_message(data)
                except Exception as e:
                    logger.error(f"调用自定义 WebSocket 消息处理函数失败: {e}", exc_info=True)
        
        def on_error(error):
            logger.error(f"WebSocket 错误: {error}")
        
        ws_client.on_connect(on_connect)
        ws_client.on_disconnect(on_disconnect)
        ws_client.on_message(on_message)
        ws_client.on_error(on_error)
        
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
        
        # 发送消息（现在返回 message_id）
        message_id = ws_client.send_message(
            session_id=session_id,
            message=message,
            role="user",
            message_type=message_type,
            reply_to_message_id=reply_to_message_id
        )
        
        if message_id:
            return {
                "success": True,
                "message": "消息已发送",
                "message_id": message_id
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
            logger.info("WebSocket 已断开")
    except Exception as e:
        logger.error(f"断开 WebSocket 失败: {e}", exc_info=True)



