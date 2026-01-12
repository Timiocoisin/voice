"""
WebSocket 连接管理器

负责管理 WebSocket 连接、消息推送、心跳检测等功能。
"""

import logging
import threading
import time
from typing import Dict, Optional, Set, Any
from datetime import datetime
from flask_socketio import SocketIO, emit, join_room, leave_room

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器"""
    
    def __init__(self, socketio: SocketIO, db_manager):
        """
        初始化 WebSocket 管理器
        
        Args:
            socketio: Flask-SocketIO 实例
            db_manager: 数据库管理器实例
        """
        self.socketio = socketio
        self.db = db_manager
        
        # 连接映射：{connection_id: {user_id, socket_id, device_id, ...}}
        self.connections: Dict[str, Dict[str, Any]] = {}
        
        # 用户连接映射：{user_id: set(connection_id)}
        self.user_connections: Dict[int, Set[str]] = {}
        
        # Socket ID 到 Connection ID 的映射
        self.socket_to_connection: Dict[str, str] = {}
        
        # 心跳检测线程
        self.heartbeat_thread = None
        self.heartbeat_interval = 30  # 秒
        self.heartbeat_timeout = 120  # 秒，超过此时间未收到心跳则断开
        self.running = False
        
        # 锁
        self.lock = threading.Lock()
        
        logger.info("WebSocket 管理器初始化完成")
    
    def start(self):
        """启动心跳检测线程"""
        if not self.running:
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
            self.heartbeat_thread.start()
            logger.info("WebSocket 心跳检测线程已启动")
    
    def stop(self):
        """停止心跳检测线程"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=5)
        logger.info("WebSocket 心跳检测线程已停止")
    
    def _heartbeat_worker(self):
        """心跳检测工作线程"""
        while self.running:
            try:
                time.sleep(self.heartbeat_interval)
                self._check_connections()
            except Exception as e:
                logger.error(f"心跳检测异常: {e}", exc_info=True)
    
    def _check_connections(self):
        """检查所有连接的心跳状态"""
        now = time.time()
        stale_connections = []
        
        with self.lock:
            for conn_id, conn_info in self.connections.items():
                last_heartbeat = conn_info.get('last_heartbeat', 0)
                if now - last_heartbeat > self.heartbeat_timeout:
                    stale_connections.append(conn_id)
        
        # 断开过期连接
        for conn_id in stale_connections:
            logger.warning(f"连接 {conn_id} 心跳超时，自动断开")
            self.disconnect(conn_id)
        
        # 清理数据库中的过期连接
        if stale_connections:
            self.db.cleanup_stale_connections(timeout_minutes=2)
    
    def connect(self, user_id: int, socket_id: str, connection_id: str, 
                device_id: str = None, ip_address: str = None, user_agent: str = None) -> bool:
        """
        注册新连接
        
        Args:
            user_id: 用户ID
            socket_id: Socket.IO 的 socket ID
            connection_id: 自定义连接ID（通常是 UUID）
            device_id: 设备ID
            ip_address: IP 地址
            user_agent: User-Agent
            
        Returns:
            bool: 是否成功
        """
        try:
            with self.lock:
                # 创建连接信息
                conn_info = {
                    'user_id': user_id,
                    'socket_id': socket_id,
                    'device_id': device_id,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'connected_at': time.time(),
                    'last_heartbeat': time.time(),
                }
                
                # 保存连接映射
                self.connections[connection_id] = conn_info
                self.socket_to_connection[socket_id] = connection_id
                
                # 保存用户连接映射
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
            
            # 保存到数据库
            self.db.create_user_connection(
                user_id=user_id,
                connection_id=connection_id,
                socket_id=socket_id,
                device_id=device_id,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # 加入用户房间（用于广播）
            # 使用 SocketIO.server.enter_room 显式指定 socket_id，避免依赖请求上下文
            try:
                room_name = f"user_{user_id}"
                self.socketio.server.enter_room(socket_id, room_name, namespace="/")
                logger.debug(f"成功将 socket {socket_id} 加入房间 {room_name}")
            except Exception as e:
                logger.error(f"将 socket {socket_id} 加入房间 user_{user_id} 失败: {e}", exc_info=True)
            
            logger.debug(f"用户 {user_id} 建立连接: {connection_id} (socket: {socket_id})")
            
            return True
        except Exception as e:
            logger.error(f"注册连接失败: {e}", exc_info=True)
            return False
    
    def disconnect(self, connection_id: str = None, socket_id: str = None) -> bool:
        """
        断开连接
        
        Args:
            connection_id: 连接ID
            socket_id: Socket ID（二选一）
            
        Returns:
            bool: 是否成功
        """
        try:
            # 如果只提供了 socket_id，查找对应的 connection_id
            if not connection_id and socket_id:
                with self.lock:
                    connection_id = self.socket_to_connection.get(socket_id)
            
            if not connection_id:
                logger.warning("断开连接失败：未找到连接ID")
                return False
            
            with self.lock:
                conn_info = self.connections.get(connection_id)
                if not conn_info:
                    logger.warning(f"连接 {connection_id} 不存在")
                    return False
                
                user_id = conn_info['user_id']
                socket_id = conn_info['socket_id']
                
                # 移除连接映射
                del self.connections[connection_id]
                if socket_id in self.socket_to_connection:
                    del self.socket_to_connection[socket_id]
                
                # 移除用户连接映射
                if user_id in self.user_connections:
                    self.user_connections[user_id].discard(connection_id)
                    if not self.user_connections[user_id]:
                        del self.user_connections[user_id]
            
            # 更新数据库
            self.db.disconnect_user_connection(connection_id)
            
            # 离开用户房间
            # 使用 SocketIO.server.leave_room 显式指定 socket_id，避免依赖请求上下文
            try:
                self.socketio.server.leave_room(socket_id, f"user_{user_id}", namespace="/")
            except Exception as e:
                logger.error(f"将 socket {socket_id} 从房间 user_{user_id} 移除失败: {e}", exc_info=True)
            
            logger.debug(f"用户 {user_id} 断开连接: {connection_id}")
            return True
        except Exception as e:
            logger.error(f"断开连接失败: {e}", exc_info=True)
            return False
    
    def update_heartbeat(self, connection_id: str = None, socket_id: str = None) -> bool:
        """
        更新连接心跳
        
        Args:
            connection_id: 连接ID
            socket_id: Socket ID（二选一）
            
        Returns:
            bool: 是否成功
        """
        try:
            # 如果只提供了 socket_id，查找对应的 connection_id
            if not connection_id and socket_id:
                with self.lock:
                    connection_id = self.socket_to_connection.get(socket_id)
            
            if not connection_id:
                return False
            
            with self.lock:
                if connection_id in self.connections:
                    self.connections[connection_id]['last_heartbeat'] = time.time()
                else:
                    return False
            
            # 更新数据库（异步，不阻塞）
            threading.Thread(
                target=self.db.update_connection_heartbeat,
                args=(connection_id,),
                daemon=True
            ).start()
            
            return True
        except Exception as e:
            logger.error(f"更新心跳失败: {e}", exc_info=True)
            return False
    
    def get_user_connections(self, user_id: int) -> list:
        """
        获取用户的所有活跃连接
        
        Args:
            user_id: 用户ID
            
        Returns:
            list: 连接ID列表
        """
        with self.lock:
            return list(self.user_connections.get(user_id, set()))
    
    def is_user_online(self, user_id: int) -> bool:
        """
        检查用户是否在线
        
        Args:
            user_id: 用户ID
            
        Returns:
            bool: 是否在线
        """
        with self.lock:
            return user_id in self.user_connections and len(self.user_connections[user_id]) > 0
    
    def send_message_to_user(self, user_id: int, event: str, data: dict) -> int:
        """
        向指定用户的所有连接发送消息
        
        Args:
            user_id: 用户ID
            event: 事件名称
            data: 消息数据
            
        Returns:
            int: 成功发送的连接数
        """
        try:
            connections = self.get_user_connections(user_id)
            message_id = data.get("id", "unknown")
            
            # 即使 connections 为空，也尝试发送一次（因为房间可能已经加入了）
            # 使用房间广播（更高效）
            try:
                room_name = f"user_{user_id}"
                logger.debug(f"准备发送消息到房间: {room_name}, event={event}, message_id={message_id}, namespace=/")
                self.socketio.emit(event, data, room=room_name, namespace="/")
                logger.debug(f"消息已发送到房间: {room_name}, event={event}, message_id={message_id}")
                
                if connections:
                    logger.debug(f"向用户 {user_id} 的 {len(connections)} 个连接发送消息: {event}, message_id={message_id}")
                else:
                    logger.debug(f"向用户 {user_id} 发送消息（房间广播，连接记录为空）: {event}, message_id={message_id}")
                
                # 返回连接数，如果没有记录则返回1（假设至少有一个连接在房间中）
                return len(connections) if connections else 1
            except Exception as emit_error:
                logger.error(f"发送消息到房间 user_{user_id} 失败: {emit_error}, message_id={message_id}", exc_info=True)
                return 0
        except Exception as e:
            logger.error(f"发送消息失败: {e}, user_id={user_id}, event={event}", exc_info=True)
            return 0
    
    def send_message_to_connection(self, connection_id: str, event: str, data: dict) -> bool:
        """
        向指定连接发送消息
        
        Args:
            connection_id: 连接ID
            event: 事件名称
            data: 消息数据
            
        Returns:
            bool: 是否成功
        """
        try:
            with self.lock:
                conn_info = self.connections.get(connection_id)
                if not conn_info:
                    logger.warning(f"连接 {connection_id} 不存在")
                    return False
                
                socket_id = conn_info['socket_id']
            
            # 向特定 socket 发送消息
            self.socketio.emit(event, data, room=socket_id, namespace="/")
            
            logger.debug(f"向连接 {connection_id} 发送消息: {event}")
            return True
        except Exception as e:
            logger.error(f"发送消息失败: {e}", exc_info=True)
            return False
    
    def handle_message_status(self, message_id: int, status: str, user_id: int = None):
        """
        处理消息状态更新并推送回执
        
        Args:
            message_id: 消息ID
            status: 消息状态 (sent/delivered/read)
            user_id: 用户ID（可选，用于推送回执）
        """
        try:
            # 检查消息是否存在（最多重试3次，每次间隔100ms）
            message = None
            for retry in range(3):
                message = self.db.get_message_by_id(message_id)
                if message:
                    break
                if retry < 2:  # 不是最后一次重试
                    import time
                    time.sleep(0.1)  # 等待100ms后重试
            
            if not message:
                logger.warning(f"消息 {message_id} 不存在，无法更新状态（已重试3次）")
                return
            
            # 更新数据库中的消息状态
            success = self.db.update_message_status(message_id, status)
            if not success:
                # 如果更新失败，可能是消息不存在或字段不存在，记录调试日志但不中断流程
                logger.debug(f"更新消息 {message_id} 状态失败（可能消息不存在或字段未创建，已忽略）")
                return
            
            # 获取消息详情
            message = self.db.get_message_by_id(message_id)
            if not message:
                logger.warning(f"消息 {message_id} 不存在")
                return
            
            # 推送状态回执给发送者
            from_user_id = message.get('from_user_id')
            if from_user_id:
                status_data = {
                    'message_id': str(message_id),
                    'status': status,
                    'timestamp': datetime.now().isoformat(),
                }
                self.send_message_to_user(from_user_id, 'message_status', status_data)
                logger.debug(f"消息 {message_id} 状态更新为 {status}，已推送回执给用户 {from_user_id}")
        
        except Exception as e:
            logger.error(f"处理消息状态更新失败: {e}", exc_info=True)
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """
        获取连接信息
        
        Args:
            connection_id: 连接ID
            
        Returns:
            dict: 连接信息，如果不存在则返回 None
        """
        with self.lock:
            return self.connections.get(connection_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            dict: 统计信息
        """
        with self.lock:
            return {
                'total_connections': len(self.connections),
                'online_users': len(self.user_connections),
                'connections_by_user': {
                    user_id: len(conns) 
                    for user_id, conns in self.user_connections.items()
                },
            }

