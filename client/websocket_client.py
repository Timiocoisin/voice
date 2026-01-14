"""
WebSocket 客户端

提供 WebSocket 连接、消息发送、自动重连等功能。
"""

import logging
import threading
import uuid
from typing import Callable, Optional, Dict, Any
from enum import Enum
from PyQt6.QtCore import QTimer

try:
    import socketio
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False
    logging.warning("socketio 模块未安装，WebSocket 功能不可用")



class ConnectionStatus(Enum):
    """连接状态枚举"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketClient:
    """WebSocket 客户端"""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8000"):
        """
        初始化 WebSocket 客户端
        
        Args:
            server_url: 服务器地址
        """
        if not SOCKETIO_AVAILABLE:
            raise ImportError("socketio 模块未安装，请运行: pip install python-socketio")
        
        self.server_url = server_url
        # 使用 threading 模式，确保所有对 sio 的操作都在主线程中执行
        # 使用 emit() 而不是 call() 来避免阻塞操作
        self.sio = socketio.Client(
            reconnection=True,
            reconnection_attempts=0,  # 无限重试
            reconnection_delay=1,
            reconnection_delay_max=10,
            randomization_factor=0.5,
        )
        
        # 连接信息
        self.connection_id = str(uuid.uuid4())
        self.user_id: Optional[int] = None
        self.token: Optional[str] = None
        self.device_id: Optional[str] = None
        self.device_info: Optional[Dict[str, Any]] = None
        
        # 连接状态
        self.status = ConnectionStatus.DISCONNECTED
        self.socket_id: Optional[str] = None
        
        # 心跳（使用 QTimer，运行在主线程事件循环）
        self.heartbeat_interval = 30  # 秒
        self.heartbeat_timer: Optional[QTimer] = None
        
        # 消息队列（发送失败时重试）
        self.message_queue = []
        self.queue_lock = threading.Lock()
        self.max_queue_size = 100
        self.retry_interval = 5  # 秒
        self.retry_timer: Optional[QTimer] = None
        
        # 回调函数
        self.on_connect_callback: Optional[Callable] = None
        self.on_disconnect_callback: Optional[Callable] = None
        self.on_message_callback: Optional[Callable] = None
        self.on_message_status_callback: Optional[Callable] = None
        self.on_status_change_callback: Optional[Callable] = None
        self.on_error_callback: Optional[Callable] = None
        self.on_vip_status_updated_callback: Optional[Callable] = None
        self.on_diamond_balance_updated_callback: Optional[Callable] = None
        self.on_user_profile_updated_callback: Optional[Callable] = None
        self.on_message_edited_callback: Optional[Callable] = None
        self.on_session_status_updated_callback: Optional[Callable] = None
        
        # 消息去重
        self.received_message_ids = set()
        self.max_received_ids = 1000
        
        # 注册事件处理器
        self._register_event_handlers()
        
        logging.info(f"WebSocket 客户端初始化完成: {self.connection_id}")
    
    def _register_event_handlers(self):
        """注册 Socket.IO 事件处理器"""
        
        # 添加通用事件监听器，用于调试
        @self.sio.on('*')
        def catch_all(event, *args):
            """捕获所有事件，用于调试"""
            if event not in ['connect', 'disconnect', 'connect_error', 'heartbeat']:
                logging.info(f"WebSocketClient 收到事件: {event}, args_count={len(args)}, args={args[:1] if args else None}")
        
        @self.sio.event
        def connect():
            """连接成功"""
            logging.info("WebSocket 连接成功")
            self._update_status(ConnectionStatus.CONNECTED)
            
            # 注册连接
            if self.user_id and self.token:
                self._register_connection()
            
            # 启动心跳
            self._start_heartbeat()
            
            # 启动重试线程
            self._start_retry_worker()
            
            # 调用回调
            if self.on_connect_callback:
                try:
                    self.on_connect_callback()
                except Exception as e:
                    logging.error(f"连接回调异常: {e}", exc_info=True)
        
        @self.sio.event
        def disconnect():
            """连接断开"""
            logging.warning("WebSocket 连接断开")
            self._update_status(ConnectionStatus.DISCONNECTED)
            
            # 停止心跳
            self._stop_heartbeat()
            
            # 调用回调
            if self.on_disconnect_callback:
                try:
                    self.on_disconnect_callback()
                except Exception as e:
                    logging.error(f"断开回调异常: {e}", exc_info=True)
        
        @self.sio.event
        def connect_error(data):
            """连接错误"""
            logging.error(f"WebSocket 连接错误: {data}")
            self._update_status(ConnectionStatus.ERROR)
            
            if self.on_error_callback:
                try:
                    self.on_error_callback(data)
                except Exception as e:
                    logging.error(f"错误回调异常: {e}", exc_info=True)
        
        @self.sio.on("new_message")
        def on_new_message(data):
            """收到新消息"""
            try:
                message_id = data.get("id") if isinstance(data, dict) else (data.id if hasattr(data, 'id') else None)
                from_user_id = data.get("from_user_id") if isinstance(data, dict) else (data.from_user_id if hasattr(data, 'from_user_id') else None)
                to_user_id = data.get("to_user_id") if isinstance(data, dict) else (data.to_user_id if hasattr(data, 'to_user_id') else None)
                
                # 消息去重
                if message_id and message_id in self.received_message_ids:
                    return
                
                if message_id:
                    self.received_message_ids.add(message_id)
                    # 限制集合大小
                    if len(self.received_message_ids) > self.max_received_ids:
                        # 移除最旧的一半
                        self.received_message_ids = set(list(self.received_message_ids)[self.max_received_ids // 2:])
                
                # 发送已送达回执
                if message_id and self.user_id:
                    try:
                        self.send_message_delivered(int(message_id), self.user_id)
                    except Exception as e:
                        logging.error(f"发送已送达回执失败: {e}", exc_info=True)
                
                # 调用回调
                if self.on_message_callback:
                    try:
                        self.on_message_callback(data)
                    except Exception as e:
                        logging.error(f"消息回调异常: {e}, message_id={message_id}", exc_info=True)
                else:
                    logging.warning(f"消息回调未设置: message_id={message_id}, on_message_callback=None")
            
            except Exception as e:
                logging.error(f"处理新消息失败: {e}, data={data}", exc_info=True)
        
        @self.sio.on("message_status")
        def on_message_status(data):
            """消息状态更新"""
            try:
                message_id = data.get("message_id")
                status = data.get("status")
                
                # 调用回调以更新 UI
                if self.on_message_status_callback:
                    try:
                        self.on_message_status_callback(data)
                    except Exception as e:
                        logging.error(f"消息状态回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理消息状态更新失败: {e}", exc_info=True)
        
        @self.sio.on("vip_status_updated")
        def on_vip_status_updated(data):
            """VIP 状态更新"""
            try:
                # 调用回调以更新 UI
                if hasattr(self, 'on_vip_status_updated_callback') and self.on_vip_status_updated_callback:
                    try:
                        self.on_vip_status_updated_callback(data)
                    except Exception as e:
                        logging.error(f"VIP 状态更新回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理 VIP 状态更新失败: {e}", exc_info=True)
        
        @self.sio.on("diamond_balance_updated")
        def on_diamond_balance_updated(data):
            """钻石余额更新"""
            try:
                # 调用回调以更新 UI
                if hasattr(self, 'on_diamond_balance_updated_callback') and self.on_diamond_balance_updated_callback:
                    try:
                        self.on_diamond_balance_updated_callback(data)
                    except Exception as e:
                        logging.error(f"钻石余额更新回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理钻石余额更新失败: {e}", exc_info=True)
        
        @self.sio.on("user_profile_updated")
        def on_user_profile_updated(data):
            """用户资料更新"""
            try:
                if hasattr(self, 'on_user_profile_updated_callback') and self.on_user_profile_updated_callback:
                    try:
                        self.on_user_profile_updated_callback(data)
                    except Exception as e:
                        logging.error(f"用户资料更新回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理用户资料更新失败: {e}", exc_info=True)
        
        @self.sio.on("message_edited")
        def on_message_edited(data):
            """消息编辑"""
            try:
                if hasattr(self, 'on_message_edited_callback') and self.on_message_edited_callback:
                    try:
                        self.on_message_edited_callback(data)
                    except Exception as e:
                        logging.error(f"消息编辑回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理消息编辑失败: {e}", exc_info=True)
        
        @self.sio.on("session_status_updated")
        def on_session_status_updated(data):
            """会话状态更新"""
            try:
                if hasattr(self, 'on_session_status_updated_callback') and self.on_session_status_updated_callback:
                    try:
                        self.on_session_status_updated_callback(data)
                    except Exception as e:
                        logging.error(f"会话状态更新回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理会话状态更新失败: {e}", exc_info=True)

        @self.sio.on("session_accepted_for_user")
        def on_session_accepted_for_user(data):
            """会话已被客服接入（用户侧事件）"""
            try:
                if hasattr(self, 'on_session_accepted_for_user_callback') and self.on_session_accepted_for_user_callback:
                    try:
                        self.on_session_accepted_for_user_callback(data)
                    except Exception as e:
                        logging.error(f"会话已被接入回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理会话已被接入事件失败: {e}", exc_info=True)
        
        @self.sio.on("message_recalled")
        def on_message_recalled(data):
            """收到撤回消息事件（后端通过 message_recalled 推送）"""
            try:
                message_id = data.get("message_id")
                
                if not message_id:
                    logging.warning(f"撤回消息事件缺少 message_id: {data}")
                    return
                
                # 将撤回事件转换为与 new_message 接近的结构，统一通过 on_message_callback 分发
                payload = {
                    "id": str(message_id),
                    "session_id": data.get("session_id"),
                    "from_user_id": data.get("from_user_id"),
                    "to_user_id": None,
                    "text": "",
                    "time": data.get("time"),
                    "avatar": None,
                    "message_type": "text",
                    "reply_to_message_id": None,
                    "is_recalled": True,
                    # 可选用户名字段，供前端判断"谁撤回了消息"
                    "username": data.get("username"),
                }
                
                if self.on_message_callback:
                    try:
                        self.on_message_callback(payload)
                    except Exception as e:
                        logging.error(f"撤回消息回调异常: {e}", exc_info=True)
            except Exception as e:
                logging.error(f"处理撤回消息事件失败: {e}", exc_info=True)
    
    def _update_status(self, status: ConnectionStatus):
        """更新连接状态"""
        if self.status != status:
            old_status = self.status
            self.status = status
            logging.info(f"连接状态变化: {old_status.value} -> {status.value}")
            
            # 调用回调
            if self.on_status_change_callback:
                try:
                    self.on_status_change_callback(status)
                except Exception as e:
                    logging.error(f"状态变化回调异常: {e}", exc_info=True)
    
    def _register_connection(self):
        """向服务器注册连接"""
        try:
            data = {
                "user_id": self.user_id,
                "token": self.token,
                "connection_id": self.connection_id,
                "device_id": self.device_id,
                "device_info": self.device_info or {},
            }
            
            # 使用 emit 而不是 call，避免阻塞和跨线程问题
            # 注册结果将通过 new_message 或其他事件返回
            self.sio.emit("register", data)
            logging.info(f"连接注册请求已发送: {self.connection_id}")
        
        except Exception as e:
            logging.error(f"注册连接异常: {e}", exc_info=True)
    
    def _start_heartbeat(self):
        """启动心跳定时器（主线程 QTimer）"""
        from PyQt6.QtCore import QThread, QTimer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            logging.warning("QApplication 不存在，无法启动心跳定时器")
            return
        
        # 检查是否在主线程
        is_main_thread = QThread.currentThread() == app.thread()
        
        if not is_main_thread:
            # 不在主线程，通过 QTimer.singleShot 切换到主线程执行
            logging.info("心跳定时器启动请求在非主线程，切换到主线程执行")
            QTimer.singleShot(0, self._start_heartbeat)
            return
        
        # 在主线程中执行
        if self.heartbeat_timer and self.heartbeat_timer.isActive():
            logging.debug("心跳定时器已在运行")
            return
        
        try:
            self.heartbeat_timer = QTimer()
            self.heartbeat_timer.setInterval(int(self.heartbeat_interval * 1000))
            self.heartbeat_timer.setSingleShot(False)
            self.heartbeat_timer.timeout.connect(self._send_heartbeat)
            self.heartbeat_timer.start()
            logging.debug("心跳定时器已启动")
        except Exception as e:
            logging.error(f"启动心跳定时器失败: {e}", exc_info=True)
    
    def _stop_heartbeat(self):
        """停止心跳定时器（必须在主线程中执行）"""
        from PyQt6.QtCore import QThread, QTimer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            return
        
        # 检查是否在主线程
        is_main_thread = QThread.currentThread() == app.thread()
        
        if not is_main_thread:
            # 不在主线程，通过 QTimer.singleShot 切换到主线程执行
            QTimer.singleShot(0, self._stop_heartbeat)
            return
        
        # 在主线程中执行
        if self.heartbeat_timer:
            try:
                self.heartbeat_timer.stop()
                self.heartbeat_timer.deleteLater()
                self.heartbeat_timer = None
                logging.debug("心跳定时器已停止")
            except Exception as e:
                logging.error(f"停止心跳定时器失败: {e}", exc_info=True)
    
    
    def _send_heartbeat(self):
        """发送心跳（使用 emit 而不是 call）"""
        try:
            data = {"connection_id": self.connection_id}
            # 使用 emit 而不是 call，避免阻塞和跨线程问题
            self.sio.emit("heartbeat", data)
        
        except Exception as e:
            logging.error(f"发送心跳异常: {e}", exc_info=True)
    
    def _start_retry_worker(self):
        """启动重试定时器（主线程 QTimer）"""
        from PyQt6.QtCore import QThread, QTimer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            logging.warning("QApplication 不存在，无法启动重试定时器")
            return
        
        # 检查是否在主线程
        is_main_thread = QThread.currentThread() == app.thread()
        
        if not is_main_thread:
            # 不在主线程，通过 QTimer.singleShot 切换到主线程执行
            QTimer.singleShot(0, self._start_retry_worker)
            return
        
        # 在主线程中执行
        if self.retry_timer and self.retry_timer.isActive():
            logging.debug("重试定时器已在运行")
            return
        
        try:
            self.retry_timer = QTimer()
            self.retry_timer.setInterval(int(self.retry_interval * 1000))
            self.retry_timer.setSingleShot(False)
            self.retry_timer.timeout.connect(self._process_message_queue)
            self.retry_timer.start()
            logging.debug("重试定时器已启动")
        except Exception as e:
            logging.error(f"启动重试定时器失败: {e}", exc_info=True)
    
    def _stop_retry_worker(self):
        """停止重试定时器（必须在主线程中执行）"""
        from PyQt6.QtCore import QThread, QTimer
        from PyQt6.QtWidgets import QApplication
        
        app = QApplication.instance()
        if not app:
            return
        
        # 检查是否在主线程
        is_main_thread = QThread.currentThread() == app.thread()
        
        if not is_main_thread:
            # 不在主线程，通过 QTimer.singleShot 切换到主线程执行
            QTimer.singleShot(0, self._stop_retry_worker)
            return
        
        # 在主线程中执行
        if self.retry_timer:
            try:
                self.retry_timer.stop()
                self.retry_timer.deleteLater()
                self.retry_timer = None
                logging.info("重试定时器已停止")
            except Exception as e:
                logging.error(f"停止重试定时器失败: {e}", exc_info=True)
    
    def _process_message_queue(self):
        """处理消息队列"""
        with self.queue_lock:
            if not self.message_queue:
                return
            
            # 复制队列，避免在处理时被修改
            queue_copy = self.message_queue.copy()
            self.message_queue.clear()
        
        for item in queue_copy:
            try:
                event = item.get("event")
                data = item.get("data")
                retry_count = item.get("retry_count", 0)
                
                # 重试次数限制
                if retry_count >= 3:
                    logging.warning(f"消息重试次数超限，丢弃: {event}")
                    continue
                
                # 重新发送
                logging.info(f"重试发送消息: {event} (第 {retry_count + 1} 次)")
                success = self._send_event(event, data)
                
                if not success:
                    # 失败，重新加入队列
                    item["retry_count"] = retry_count + 1
                    with self.queue_lock:
                        if len(self.message_queue) < self.max_queue_size:
                            self.message_queue.append(item)
            
            except Exception as e:
                logging.error(f"处理队列消息异常: {e}", exc_info=True)
    
    def _send_event(self, event: str, data: dict) -> bool:
        """
        发送事件（使用 emit 而不是 call，避免阻塞和跨线程问题）
        
        Args:
            event: 事件名称
            data: 数据
            
        Returns:
            bool: 是否成功（emit 总是返回 None，这里假设成功）
        """
        try:
            if self.status != ConnectionStatus.CONNECTED:
                return False
            
            # 使用 emit 而不是 call，避免阻塞和跨线程问题
            # emit 是异步的，不会在后台线程中等待响应
            self.sio.emit(event, data)
            return True
        
        except Exception as e:
            logging.error(f"发送事件失败: {e}", exc_info=True)
            return False
    
    def _add_to_queue(self, event: str, data: dict):
        """
        添加到消息队列
        
        Args:
            event: 事件名称
            data: 数据
        """
        with self.queue_lock:
            if len(self.message_queue) >= self.max_queue_size:
                logging.warning("消息队列已满，丢弃最旧的消息")
                self.message_queue.pop(0)
            
            self.message_queue.append({
                "event": event,
                "data": data,
                "retry_count": 0,
            })
    
    def connect(self, user_id: int, token: str, device_id: str = None, device_info: Dict[str, Any] = None):
        """
        连接到服务器
        
        Args:
            user_id: 用户ID
            token: 认证 Token
            device_id: 设备ID
            device_info: 设备信息
        """
        try:
            self.user_id = user_id
            self.token = token
            self.device_id = device_id or str(uuid.uuid4())
            self.device_info = device_info
            
            if self.status in [ConnectionStatus.CONNECTED, ConnectionStatus.CONNECTING]:
                logging.warning("已经连接或正在连接中")
                return
            
            self._update_status(ConnectionStatus.CONNECTING)
            logging.info(f"正在连接到 {self.server_url}...")
            
            self.sio.connect(self.server_url, namespaces=["/"])
        
        except Exception as e:
            logging.error(f"连接失败: {e}", exc_info=True)
            self._update_status(ConnectionStatus.ERROR)
            raise
    
    def disconnect(self):
        """断开连接"""
        try:
            logging.info("正在断开连接...")
            
            # 停止心跳和重试线程（确保在主线程执行）
            try:
                from PyQt6.QtCore import QMetaObject, Qt, QThread
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app and QThread.currentThread() != app.thread():
                    QMetaObject.invokeMethod(app, self._stop_heartbeat, Qt.ConnectionType.QueuedConnection)
                    QMetaObject.invokeMethod(app, self._stop_retry_worker, Qt.ConnectionType.QueuedConnection)
                else:
                    self._stop_heartbeat()
                    self._stop_retry_worker()
            except Exception:
                self._stop_heartbeat()
                self._stop_retry_worker()
            
            # 断开连接
            if self.sio.connected:
                self.sio.disconnect()
            
            self._update_status(ConnectionStatus.DISCONNECTED)
            logging.info("已断开连接")
        
        except Exception as e:
            logging.error(f"断开连接失败: {e}", exc_info=True)
    
    def send_message(self, session_id: str, message: str, role: str = "user", 
                    message_type: str = "text", reply_to_message_id: int = None) -> bool:
        """
        发送消息（异步，使用 emit，避免阻塞导致超时和断线）
        
        Args:
            session_id: 会话ID
            message: 消息内容
            role: 角色 (user/agent)
            message_type: 消息类型 (text/image/file)
            reply_to_message_id: 引用消息ID
            
        Returns:
            bool: 是否成功发送到 Socket.IO 客户端（不代表服务端处理成功）
        """
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法发送消息")
                return False
            
            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法发送消息")
                return False
            
            data = {
                "session_id": session_id,
                "from_user_id": self.user_id,
                "message": message,
                "role": role,
                "token": self.token,
                "message_type": message_type,
            }
            
            if reply_to_message_id:
                data["reply_to_message_id"] = reply_to_message_id
            
            # 使用内部 _send_event（emit），不会阻塞当前线程，也不会因为超时导致断线
            success = self._send_event("send_message", data)
            
            if not success:
                # 发送失败时加入重试队列
                logging.warning("消息发送失败，加入重试队列")
                self._add_to_queue("send_message", data)
            
            return success
        
        except Exception as e:
            logging.error(f"发送消息异常: {e}", exc_info=True)
            return False
    
    def get_session_messages(self, session_id: str, limit: int = 200) -> Optional[Dict[str, Any]]:
        """
        获取会话历史消息（通过 WebSocket）

        Args:
            session_id: 会话ID
            limit: 拉取条数（默认 200，上限由服务端限制）

        Returns:
            dict: {success, messages, message?}，失败返回 None
        """
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法获取历史消息")
                return None

            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法获取历史消息")
                return None

            data = {
                "session_id": session_id,
                "user_id": self.user_id,
                "token": self.token,
                "limit": limit,
            }

            # 使用 call-like 回调方式：_send_event 无回调，这里直接 sio.emit 并等待回调
            event = threading.Event()
            result: Dict[str, Any] = {}

            def callback(response):
                nonlocal result
                result = response or {}
                event.set()

            try:
                self.sio.emit("get_session_messages", data, callback=callback)
            except Exception as e:
                logging.error(f"发送 get_session_messages 事件失败: {e}", exc_info=True)
                return None

            # 等待回调，超时 5 秒
            if not event.wait(timeout=5.0):
                logging.error("获取历史消息超时")
                return None

            return result

        except Exception as e:
            logging.error(f"获取历史消息异常: {e}", exc_info=True)
            return None
    
    def send_message_delivered(self, message_id: int, user_id: int) -> bool:
        """
        发送消息已送达回执
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            data = {
                "message_id": message_id,
                "user_id": user_id,
            }
            
            return self._send_event("message_delivered", data)
        
        except Exception as e:
            logging.error(f"发送已送达回执异常: {e}", exc_info=True)
            return False
    
    def send_message_read(self, message_id: int, user_id: int) -> bool:
        """
        发送消息已读回执
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            data = {
                "message_id": message_id,
                "user_id": user_id,
            }
            
            return self._send_event("message_read", data)
        
        except Exception as e:
            logging.error(f"发送已读回执异常: {e}", exc_info=True)
            return False
    
    def recall_message(self, message_id: int, user_id: int) -> bool:
        """
        撤回消息
        
        Args:
            message_id: 消息ID
            user_id: 用户ID
            
        Returns:
            bool: 是否成功
        """
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法撤回消息")
                return False
            
            data = {
                "message_id": message_id,
                "user_id": user_id,
                "token": self.token,
            }
            
            success = self._send_event("recall_message", data)
            
            if not success:
                # 失败，加入队列重试
                logging.warning("撤回消息失败，加入重试队列")
                self._add_to_queue("recall_message", data)
            
            return success
        
        except Exception as e:
            logging.error(f"撤回消息异常: {e}", exc_info=True)
            return False

    def match_agent(self, session_id: str) -> Optional[Dict[str, Any]]:
        """匹配在线客服（用户侧）"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法匹配客服")
                return None

            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法匹配客服")
                return None

            data = {
                "session_id": session_id,
                "user_id": self.user_id,
                "token": self.token,
            }

            event = threading.Event()
            result: Dict[str, Any] = {}

            def callback(response):
                nonlocal result
                result = response or {}
                event.set()

            self.sio.emit("match_agent", data, callback=callback)

            if not event.wait(timeout=5.0):
                logging.error("匹配客服超时")
                return None

            return result
        except Exception as e:
            logging.error(f"匹配客服异常: {e}", exc_info=True)
            return None

    def accept_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """客服接入待接入会话"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法接入会话")
                return None

            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法接入会话")
                return None

            data = {
                "session_id": session_id,
                "user_id": self.user_id,
                "token": self.token,
            }

            event = threading.Event()
            result: Dict[str, Any] = {}

            def callback(response):
                nonlocal result
                result = response or {}
                event.set()

            self.sio.emit("accept_session", data, callback=callback)

            if not event.wait(timeout=5.0):
                logging.error("接入会话超时")
                return None

            return result
        except Exception as e:
            logging.error(f"接入会话异常: {e}", exc_info=True)
            return None

    def get_link_preview(self, url: str) -> Optional[Dict[str, Any]]:
        """通过 WebSocket 获取链接预览"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法获取链接预览")
                return None

            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法获取链接预览")
                return None

            data = {"url": url, "token": self.token}

            event = threading.Event()
            result: Dict[str, Any] = {}

            def callback(response):
                nonlocal result
                result = response or {}
                event.set()

            self.sio.emit("link_preview", data, callback=callback)

            if not event.wait(timeout=5.0):
                logging.error("获取链接预览超时")
                return None

            return result
        except Exception as e:
            logging.error(f"获取链接预览异常: {e}", exc_info=True)
            return None

    def process_rich_text(self, content: str) -> Optional[Dict[str, Any]]:
        """通过 WebSocket 处理富文本"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法处理富文本")
                return None

            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法处理富文本")
                return None

            data = {
                "content": content,
                "user_id": self.user_id,
                "token": self.token,
            }

            event = threading.Event()
            result: Dict[str, Any] = {}

            def callback(response):
                nonlocal result
                result = response or {}
                event.set()

            self.sio.emit("process_rich_text", data, callback=callback)

            if not event.wait(timeout=5.0):
                logging.error("处理富文本超时")
                return None

            return result
        except Exception as e:
            logging.error(f"处理富文本异常: {e}", exc_info=True)
            return None
    
    def on_connect(self, callback: Callable):
        """注册连接成功回调"""
        self.on_connect_callback = callback
    
    def on_disconnect(self, callback: Callable):
        """注册断开连接回调"""
        self.on_disconnect_callback = callback
    
    def on_message(self, callback: Callable):
        """注册收到消息回调"""
        self.on_message_callback = callback
    
    def on_message_status(self, callback: Callable):
        """注册消息状态更新回调"""
        self.on_message_status_callback = callback
    
    def on_vip_status_updated(self, callback: Callable):
        """注册 VIP 状态更新回调"""
        self.on_vip_status_updated_callback = callback
    
    def on_diamond_balance_updated(self, callback: Callable):
        """注册钻石余额更新回调"""
        self.on_diamond_balance_updated_callback = callback

    def on_session_accepted_for_user(self, callback: Callable):
        """注册会话被客服接入（用户侧）回调"""
        self.on_session_accepted_for_user_callback = callback
    
    def subscribe_vip_info(self) -> bool:
        """
        订阅 VIP 信息
        
        Returns:
            bool: 是否成功
        """
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法订阅 VIP 信息")
                return False
            
            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法订阅 VIP 信息")
                return False
            
            data = {
                "user_id": self.user_id,
                "token": self.token,
            }
            
            return self._send_event("subscribe_vip_info", data)
        
        except Exception as e:
            logging.error(f"订阅 VIP 信息异常: {e}", exc_info=True)
            return False
    
    def subscribe_user_profile(self) -> bool:
        """订阅用户资料更新"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法订阅用户资料")
                return False
            
            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法订阅用户资料")
                return False
            
            data = {"user_id": self.user_id, "token": self.token}
            return self._send_event("subscribe_user_profile", data)
        except Exception as e:
            logging.error(f"订阅用户资料异常: {e}", exc_info=True)
            return False
    
    def edit_message(self, message_id: int, session_id: str, new_content: str) -> bool:
        """编辑消息"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法编辑消息")
                return False
            
            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法编辑消息")
                return False
            
            data = {
                "message_id": message_id,
                "user_id": self.user_id,
                "session_id": session_id,
                "new_content": new_content,
                "token": self.token,
            }
            return self._send_event("edit_message", data)
        except Exception as e:
            logging.error(f"编辑消息异常: {e}", exc_info=True)
            return False
    
    def close_session(self, session_id: str) -> bool:
        """关闭会话"""
        try:
            if not self.user_id or not self.token:
                logging.error("未登录，无法关闭会话")
                return False
            
            if self.status != ConnectionStatus.CONNECTED:
                logging.error("WebSocket 未连接，无法关闭会话")
                return False
            
            data = {
                "session_id": session_id,
                "user_id": self.user_id,
                "token": self.token,
            }
            return self._send_event("close_session", data)
        except Exception as e:
            logging.error(f"关闭会话异常: {e}", exc_info=True)
            return False
    
    def on_user_profile_updated(self, callback: Callable):
        """注册用户资料更新回调"""
        self.on_user_profile_updated_callback = callback
    
    def on_message_edited(self, callback: Callable):
        """注册消息编辑回调"""
        self.on_message_edited_callback = callback
    
    def on_session_status_updated(self, callback: Callable):
        """注册会话状态更新回调"""
        self.on_session_status_updated_callback = callback
    
    def on_status_change(self, callback: Callable):
        """注册状态变化回调"""
        self.on_status_change_callback = callback
    
    def on_error(self, callback: Callable):
        """注册错误回调"""
        self.on_error_callback = callback
    
    def is_connected(self) -> bool:
        """是否已连接"""
        return self.status == ConnectionStatus.CONNECTED
    
    def get_status(self) -> ConnectionStatus:
        """获取连接状态"""
        return self.status

