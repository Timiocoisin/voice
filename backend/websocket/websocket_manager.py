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
                time_since_heartbeat = now - last_heartbeat
                if time_since_heartbeat > self.heartbeat_timeout:
                    stale_connections.append((conn_id, time_since_heartbeat))
                    logger.debug(f"连接 {conn_id} 心跳超时: 距离上次心跳 {time_since_heartbeat:.1f} 秒 (超时阈值: {self.heartbeat_timeout} 秒)")
        
        # 断开过期连接
        for conn_id, time_since_heartbeat in stale_connections:
            logger.warning(f"连接 {conn_id} 心跳超时（距离上次心跳 {time_since_heartbeat:.1f} 秒），自动断开")
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
                        logger.debug(f"通过 socket_id 查找 connection_id 失败: socket_id={socket_id}")
            
            if not connection_id:
                logger.debug(f"更新心跳失败: connection_id 和 socket_id 都为空")
                return False
            
            with self.lock:
                if connection_id in self.connections:
                    old_heartbeat = self.connections[connection_id].get('last_heartbeat', 0)
                    self.connections[connection_id]['last_heartbeat'] = time.time()
                    time_since_last = time.time() - old_heartbeat if old_heartbeat > 0 else 0
                    logger.debug(f"更新心跳成功: connection_id={connection_id}, 距离上次心跳 {time_since_last:.1f} 秒")
                else:
                    logger.debug(f"更新心跳失败: connection_id={connection_id} 不在连接列表中")
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
    
    def push_session_list_update(self, user_id: int, session_type: str, sessions: list):
        """
        推送会话列表更新给指定用户
        
        Args:
            user_id: 用户ID
            session_type: 会话类型 ('my' 或 'pending')
            sessions: 会话列表
        """
        try:
            data = {
                "type": session_type,
                "sessions": sessions
            }
            self.send_message_to_user(user_id, "session_list_updated", data)
            logger.debug(f"推送会话列表更新给用户 {user_id}: type={session_type}, count={len(sessions)}")
        except Exception as e:
            logger.error(f"推送会话列表更新失败: {e}", exc_info=True)
    
    def push_new_pending_session(self, session_data: dict):
        """
        推送新待接入会话给所有订阅的客服
        
        Args:
            session_data: 会话数据
        """
        try:
            # 获取所有在线的客服
            online_agents = self.db.get_online_agents()
            for agent in online_agents:
                agent_id = agent.get('id')
                if agent_id:
                    self.send_message_to_user(agent_id, "new_pending_session", session_data)
            logger.debug(f"推送新待接入会话给所有客服: session_id={session_data.get('id')}")
        except Exception as e:
            logger.error(f"推送新待接入会话失败: {e}", exc_info=True)
    
    def push_pending_session_accepted(self, session_id: str, agent_id: int):
        """
        推送待接入会话被接入给所有订阅的客服
        
        Args:
            session_id: 会话ID
            agent_id: 接入的客服ID
        """
        try:
            data = {
                "session_id": session_id,
                "agent_id": agent_id
            }
            # 获取所有在线的客服
            online_agents = self.db.get_online_agents()
            for agent in online_agents:
                target_agent_id = agent.get('id')
                if target_agent_id:
                    self.send_message_to_user(target_agent_id, "pending_session_accepted", data)
            logger.debug(f"推送待接入会话被接入: session_id={session_id}, agent_id={agent_id}")
        except Exception as e:
            logger.error(f"推送待接入会话被接入失败: {e}", exc_info=True)

    def push_session_accepted_for_user(self, user_id: int, session_id: str, agent_id: int, agent_name: Optional[str] = None):
        """
        推送“会话已被客服接入”事件给最终用户
        
        Args:
            user_id: 用户ID（最终用户）
            session_id: 会话ID
            agent_id: 接入的客服ID
            agent_name: 客服名称（可选）
        """
        try:
            data = {
                "user_id": user_id,
                "session_id": session_id,
                "agent_id": agent_id,
                "agent_name": agent_name,
            }
            self.send_message_to_user(user_id, "session_accepted_for_user", data)
            logger.debug(f"推送会话已被客服接入给用户 {user_id}: session_id={session_id}, agent_id={agent_id}")
        except Exception as e:
            logger.error(f"推送会话已被客服接入事件失败: {e}", exc_info=True)
    
    def push_agent_status_changed(self, agent_id: int, status: str):
        """
        推送客服状态变化给所有订阅的客服
        
        Args:
            agent_id: 客服ID
            status: 状态
        """
        try:
            data = {
                "agent_id": agent_id,
                "status": status
            }
            # 获取所有在线的客服
            online_agents = self.db.get_online_agents()
            for agent in online_agents:
                target_agent_id = agent.get('id')
                if target_agent_id:
                    self.send_message_to_user(target_agent_id, "agent_status_changed", data)
            logger.debug(f"推送客服状态变化: agent_id={agent_id}, status={status}")
        except Exception as e:
            logger.error(f"推送客服状态变化失败: {e}", exc_info=True)
    
    def push_vip_status_update(self, user_id: int, vip_info: dict):
        """
        推送 VIP 状态更新给指定用户
        
        Args:
            user_id: 用户ID
            vip_info: VIP 信息（包含 is_vip, vip_expiry_date, diamonds）
        """
        try:
            data = {
                "user_id": user_id,
                "vip_info": vip_info
            }
            self.send_message_to_user(user_id, "vip_status_updated", data)
            logger.debug(f"推送 VIP 状态更新给用户 {user_id}: is_vip={vip_info.get('is_vip')}, diamonds={vip_info.get('diamonds')}")
        except Exception as e:
            logger.error(f"推送 VIP 状态更新失败: {e}", exc_info=True)
    
    def push_diamond_balance_update(self, user_id: int, balance: int):
        """
        推送钻石余额更新给指定用户
        
        Args:
            user_id: 用户ID
            balance: 钻石余额
        """
        try:
            data = {
                "user_id": user_id,
                "balance": balance
            }
            self.send_message_to_user(user_id, "diamond_balance_updated", data)
            logger.debug(f"推送钻石余额更新给用户 {user_id}: balance={balance}")
        except Exception as e:
            logger.error(f"推送钻石余额更新失败: {e}", exc_info=True)
    
    def push_user_profile_update(self, user_id: int, profile_data: dict):
        """
        推送用户资料更新给指定用户
        
        Args:
            user_id: 用户ID
            profile_data: 用户资料数据（包含 user 和 vip 信息）
        """
        try:
            data = {
                "user_id": user_id,
                "profile": profile_data
            }
            self.send_message_to_user(user_id, "user_profile_updated", data)
            logger.debug(f"推送用户资料更新给用户 {user_id}")
        except Exception as e:
            logger.error(f"推送用户资料更新失败: {e}", exc_info=True)
    
    def push_message_edited(self, session_id: str, message_id: int, new_content: str, edited_at: str):
        """
        推送消息编辑给会话中的所有用户
        
        Args:
            session_id: 会话ID
            message_id: 消息ID
            new_content: 新内容
            edited_at: 编辑时间
        """
        try:
            # 获取会话信息
            session = self.db.get_chat_session_by_id(session_id)
            if not session:
                logger.warning(f"推送消息编辑失败：会话不存在: session_id={session_id}")
                return
            
            user_id = session.get('user_id')
            agent_id = session.get('agent_id')
            
            data = {
                "message_id": message_id,
                "session_id": session_id,
                "new_content": new_content,
                "edited_at": edited_at
            }
            
            # 推送给用户和客服
            if user_id:
                self.send_message_to_user(user_id, "message_edited", data)
            if agent_id:
                self.send_message_to_user(agent_id, "message_edited", data)
            
            logger.debug(f"推送消息编辑: session_id={session_id}, message_id={message_id}")
        except Exception as e:
            logger.error(f"推送消息编辑失败: {e}", exc_info=True)
    
    def push_session_status_update(self, session_id: str, status: str, user_id: int = None, agent_id: int = None):
        """
        推送会话状态更新给会话相关用户
        
        Args:
            session_id: 会话ID
            status: 会话状态（pending, active, closed）
            user_id: 用户ID（可选，如果不提供则从数据库获取）
            agent_id: 客服ID（可选，如果不提供则从数据库获取）
        """
        try:
            # 如果未提供 user_id 或 agent_id，从数据库获取
            if user_id is None or agent_id is None:
                session = self.db.get_chat_session_by_id(session_id)
                if session:
                    user_id = user_id or session.get('user_id')
                    agent_id = agent_id or session.get('agent_id')
            
            data = {
                "session_id": session_id,
                "status": status,
                "user_id": user_id,
                "agent_id": agent_id
            }
            
            # 推送给用户和客服
            if user_id:
                self.send_message_to_user(user_id, "session_status_updated", data)
            if agent_id:
                self.send_message_to_user(agent_id, "session_status_updated", data)
            
            logger.debug(f"推送会话状态更新: session_id={session_id}, status={status}")
        except Exception as e:
            logger.error(f"推送会话状态更新失败: {e}", exc_info=True)
    
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

