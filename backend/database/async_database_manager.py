"""
异步数据库管理器

基于 SQLAlchemy 2.0 异步 API 实现的数据库管理器，替代同步的 DatabaseManager。
所有方法都是异步的，使用 AsyncSession 进行数据库操作。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

import bcrypt
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.exc import IntegrityError

from backend.config.database_config import get_database_config
from backend.database.models import (
    Base, User, UserVip, ChatMessage, ChatSession, Announcement,
    PasswordResetToken, AgentStatus, UserConnection, UserDevice, MessageQueue,
    UserRole, MessageType, SessionStatus, AgentStatusEnum, ConnectionStatus,
    DeviceType, MessageStatus, QueueStatus
)
from backend.resources import get_default_avatar

logger = logging.getLogger(__name__)


class AsyncDatabaseManager:
    """异步数据库管理器"""
    
    def __init__(self):
        """初始化异步数据库管理器"""
        db_config = get_database_config()
        
        # 构建异步数据库 URL (aiomysql)
        # 格式: mysql+aiomysql://user:password@host:port/database?charset=utf8mb4
        db_url = (
            f"mysql+aiomysql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config.get('port', 3306)}"
            f"/{db_config['database']}?charset={db_config.get('charset', 'utf8mb4')}"
        )
        
        # 创建异步引擎
        self.engine = create_async_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # 连接健康检查
            echo=False,  # 生产环境设为 False
        )
        
        # 创建异步会话工厂
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        self.tables_initialized = False
        logger.info("异步数据库管理器初始化完成")
    
    async def initialize_tables(self):
        """初始化数据库表结构（异步）"""
        if self.tables_initialized:
            return
        
        try:
            async with self.engine.begin() as conn:
                # 创建所有表
                await conn.run_sync(Base.metadata.create_all)
            self.tables_initialized = True
            logger.info("数据库表结构初始化完成")
        except Exception as e:
            logger.error(f"初始化数据库表结构失败: {e}")
            raise
    
    async def get_session(self) -> AsyncSession:
        """获取异步会话"""
        return self.async_session()
    
    # ==================== 用户相关方法 ====================
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱查询用户信息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(User).where(User.email == email)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return None
                
                # 处理 role 字段：可能是枚举对象或字符串
                role_value = None
                try:
                    if isinstance(user.role, UserRole):
                        role_value = user.role.value
                    elif isinstance(user.role, str):
                        role_value = user.role
                    else:
                        # 尝试获取枚举值
                        role_value = str(user.role)
                except Exception:
                    # 如果都失败了，尝试从数据库直接读取字符串
                    role_value = str(user.role) if user.role else 'user'
                
                # 转换为字典格式（保持兼容性）
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "password": user.password,
                    "avatar": user.avatar,
                    "role": role_value or 'user',
                }
        except Exception as e:
            logger.error(f"查询用户信息失败: {e}", exc_info=True)
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户 ID 查询用户基础信息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                if not user:
                    return None
                
                # 处理 role 字段：可能是枚举对象或字符串
                role_value = None
                try:
                    if isinstance(user.role, UserRole):
                        role_value = user.role.value
                    elif isinstance(user.role, str):
                        role_value = user.role
                    else:
                        # 尝试获取枚举值
                        role_value = str(user.role)
                except Exception:
                    # 如果都失败了，尝试从数据库直接读取字符串
                    role_value = str(user.role) if user.role else 'user'
                
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "avatar": user.avatar,
                    "role": role_value or 'user',
                }
        except Exception as e:
            logger.error(f"根据用户ID查询用户信息失败: {e}", exc_info=True)
            return None
    
    async def insert_user_info(
        self, 
        username: str, 
        email: str, 
        password: str, 
        avatar_data: Optional[bytes] = None, 
        role: str = 'user'
    ) -> bool:
        """插入用户信息到数据库（异步）"""
        try:
            # 如果没有提供头像数据，使用默认头像
            if not avatar_data:
                avatar_data = get_default_avatar()
            
            # 加密密码
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            
            # 转换角色
            user_role = UserRole(role) if role in ['user', 'admin', 'customer_service'] else UserRole.USER
            
            async with self.async_session() as session:
                # 创建用户
                new_user = User(
                    username=username,
                    email=email,
                    password=hashed.decode('utf-8'),
                    avatar=avatar_data,  # LONGBLOB 直接存储二进制
                    role=user_role
                )
                session.add(new_user)
                await session.flush()  # 获取 user_id
                user_id = new_user.id
                
                # 只有普通用户才插入默认的 VIP 信息
                if role == 'user':
                    await self.insert_user_vip_info(user_id)
                
                await session.commit()
                logger.info(f"用户 {username} 注册成功，ID: {user_id}, 角色: {role}")
                return True
        except IntegrityError as e:
            logger.error(f"插入用户信息失败（唯一约束冲突）: {e}")
            return False
        except Exception as e:
            logger.error(f"插入用户信息失败: {e}")
            return False
    
    async def insert_user_vip_info(self, user_id: int) -> bool:
        """插入用户 VIP 信息到数据库（异步）"""
        try:
            async with self.async_session() as session:
                new_vip = UserVip(
                    user_id=user_id,
                    is_vip=False,
                    diamonds=0
                )
                session.add(new_vip)
                await session.commit()
                logger.info(f"用户 {user_id} VIP 信息插入成功")
                return True
        except Exception as e:
            logger.error(f"插入用户 VIP 信息失败: {e}")
            return False
    
    async def get_user_vip_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户 ID 查询用户 VIP 信息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(UserVip).where(UserVip.user_id == user_id)
                )
                vip = result.scalar_one_or_none()
                if not vip:
                    return None
                
                return {
                    "is_vip": vip.is_vip,
                    "vip_expiry_date": vip.vip_expiry_date,
                    "diamonds": vip.diamonds,
                }
        except Exception as e:
            logger.error(f"查询用户 VIP 信息失败: {e}")
            return None
    
    async def update_user_password(self, email: str, new_password: str) -> bool:
        """更新用户密码（异步）"""
        try:
            hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
            
            async with self.async_session() as session:
                result = await session.execute(
                    update(User)
                    .where(User.email == email)
                    .values(password=hashed.decode('utf-8'))
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"用户 {email} 密码更新成功")
                    return True
                return False
        except Exception as e:
            logger.error(f"更新用户密码失败: {e}")
            return False
    
    async def update_user_avatar(self, user_id: int, avatar_data: bytes) -> bool:
        """更新用户头像（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(avatar=avatar_data)
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(f"用户 {user_id} 的头像已更新")
                    return True
                return False
        except Exception as e:
            logger.error(f"更新用户头像失败: {e}")
            return False
    
    async def consume_diamonds_and_update_vip(
        self, 
        user_id: int, 
        cost: int, 
        new_expiry: datetime
    ) -> bool:
        """消耗钻石并更新 VIP 有效期（异步）"""
        try:
            async with self.async_session() as session:
                # 使用条件更新，仅当钻石足够时才更新
                result = await session.execute(
                    update(UserVip)
                    .where(
                        and_(
                            UserVip.user_id == user_id,
                            UserVip.diamonds >= cost
                        )
                    )
                    .values(
                        diamonds=UserVip.diamonds - cost,
                        is_vip=True,
                        vip_expiry_date=new_expiry
                    )
                )
                await session.commit()
                
                if result.rowcount > 0:
                    logger.info(
                        f"用户 {user_id} 消耗 {cost} 钻石，VIP 有效期更新为 {new_expiry}"
                    )
                    return True
                return False
        except Exception as e:
            logger.error(f"更新用户 VIP 信息失败: {e}")
            return False
    
    # ==================== 消息相关方法 ====================
    
    async def insert_chat_message(
        self,
        session_id: str,
        from_user_id: int,
        to_user_id: Optional[int],
        message: str,
        message_type: str = 'text',
        reply_to_message_id: Optional[int] = None
    ) -> Optional[int]:
        """插入聊天消息（异步）"""
        try:
            msg_type = MessageType(message_type) if message_type in ['text', 'image', 'file'] else MessageType.TEXT
            
            async with self.async_session() as session:
                # 获取序列号（用于消息顺序保证）
                seq_result = await session.execute(
                    select(func.max(ChatMessage.sequence_number))
                    .where(ChatMessage.session_id == session_id)
                )
                max_seq = seq_result.scalar() or 0
                next_seq = max_seq + 1
                
                new_message = ChatMessage(
                    session_id=session_id,
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    message=message,
                    message_type=msg_type,
                    reply_to_message_id=reply_to_message_id,
                    sequence_number=next_seq,
                    status=MessageStatus.SENT,
                    sent_at=datetime.utcnow()
                )
                session.add(new_message)
                await session.flush()
                message_id = new_message.id
                await session.commit()
                return message_id
        except Exception as e:
            logger.error(f"插入聊天消息失败: {e}")
            return None
    
    async def get_chat_messages(
        self, 
        session_id: str, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取会话的聊天消息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(ChatMessage)
                    .where(ChatMessage.session_id == session_id)
                    .order_by(ChatMessage.created_at.asc())
                    .limit(limit)
                )
                messages = result.scalars().all()
                
                # 转换为字典格式（保持兼容性）
                return [
                    {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "from_user_id": msg.from_user_id,
                        "to_user_id": msg.to_user_id,
                        "message": msg.message,
                        "message_type": msg.message_type.value if isinstance(msg.message_type, MessageType) else msg.message_type,
                        "is_read": msg.is_read,
                        "is_recalled": msg.is_recalled,
                        "is_edited": msg.is_edited,
                        "edited_at": msg.edited_at,
                        "reply_to_message_id": msg.reply_to_message_id,
                        "created_at": msg.created_at,
                        "status": msg.status.value if isinstance(msg.status, MessageStatus) else msg.status,
                        "sent_at": msg.sent_at,
                        "delivered_at": msg.delivered_at,
                        "read_at": msg.read_at,
                    }
                    for msg in messages
                ]
        except Exception as e:
            logger.error(f"获取聊天消息失败: {e}")
            return []
    
    async def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """根据消息ID获取消息详情（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(ChatMessage).where(ChatMessage.id == message_id)
                )
                msg = result.scalar_one_or_none()
                if not msg:
                    return None
                
                return {
                    "id": msg.id,
                    "session_id": msg.session_id,
                    "from_user_id": msg.from_user_id,
                    "to_user_id": msg.to_user_id,
                    "message": msg.message,
                    "message_type": msg.message_type.value if isinstance(msg.message_type, MessageType) else msg.message_type,
                    "is_read": msg.is_read,
                    "is_recalled": msg.is_recalled,
                    "is_edited": msg.is_edited,
                    "edited_at": msg.edited_at,
                    "reply_to_message_id": msg.reply_to_message_id,
                    "created_at": msg.created_at,
                }
        except Exception as e:
            logger.error(f"获取消息详情失败: {e}")
            return None
    
    async def recall_message(self, message_id: int, user_id: int) -> bool:
        """撤回消息（异步，2分钟内可撤回）"""
        try:
            async with self.async_session() as session:
                # 首先检查消息是否存在、是否属于该用户、是否已撤回
                result = await session.execute(
                    select(ChatMessage).where(ChatMessage.id == message_id)
                )
                message = result.scalar_one_or_none()
                
                if not message:
                    logger.debug(f"撤回消息时未找到消息 {message_id}")
                    return False
                
                # 类型转换：确保 user_id 和 from_user_id 都是整数进行比较
                from_user_id = int(message.from_user_id) if message.from_user_id else None
                request_user_id = int(user_id) if user_id else None
                
                logger.debug(f"撤回消息检查: message_id={message_id}, from_user_id={from_user_id}, request_user_id={request_user_id}")
                
                if from_user_id != request_user_id:
                    logger.warning(
                        f"用户 {request_user_id} 无权撤回消息 {message_id} "
                        f"(消息发送者: {from_user_id}, 类型: {type(from_user_id)}, 请求者: {request_user_id}, 类型: {type(request_user_id)})"
                    )
                    return False
                
                if message.is_recalled:
                    logger.warning(f"消息 {message_id} 已被撤回")
                    return False
                
                # 检查是否在2分钟内
                time_diff = datetime.utcnow() - message.created_at
                if time_diff.total_seconds() > 120:  # 2分钟
                    logger.warning(
                        f"消息 {message_id} 超过2分钟，无法撤回 "
                        f"(创建时间: {message.created_at}, 当前时间: {datetime.utcnow()}, 时间差: {time_diff.total_seconds()}秒)"
                    )
                    return False
                
                # 更新消息为已撤回状态
                await session.execute(
                    update(ChatMessage)
                    .where(ChatMessage.id == message_id)
                    .values(is_recalled=True)
                )
                await session.commit()
                logger.info(f"消息 {message_id} 已被用户 {user_id} 撤回")
                return True
        except Exception as e:
            logger.error(f"撤回消息失败: {e}", exc_info=True)
            return False
    
    async def edit_message(
        self, 
        message_id: int, 
        user_id: int, 
        new_content: str
    ) -> bool:
        """编辑消息（异步）"""
        try:
            async with self.async_session() as session:
                # 检查消息是否存在、是否属于该用户
                result = await session.execute(
                    select(ChatMessage).where(ChatMessage.id == message_id)
                )
                message = result.scalar_one_or_none()
                
                if not message:
                    return False
                
                if message.from_user_id != user_id:
                    logger.warning(f"用户 {user_id} 无权编辑消息 {message_id}")
                    return False
                
                if message.is_recalled:
                    logger.warning(f"消息 {message_id} 已撤回，无法编辑")
                    return False
                
                # 更新消息内容
                await session.execute(
                    update(ChatMessage)
                    .where(ChatMessage.id == message_id)
                    .values(
                        message=new_content,
                        is_edited=True,
                        edited_at=datetime.utcnow()
                    )
                )
                await session.commit()
                logger.info(f"消息 {message_id} 已被用户 {user_id} 编辑")
                return True
        except Exception as e:
            logger.error(f"编辑消息失败: {e}")
            return False
    
    async def update_message_status(
        self, 
        message_id: int, 
        status: str
    ) -> bool:
        """更新消息状态（异步）"""
        try:
            msg_status = MessageStatus(status) if status in ['pending', 'sent', 'delivered', 'read', 'failed'] else MessageStatus.SENT
            
            async with self.async_session() as session:
                update_values = {"status": msg_status}
                
                now = datetime.utcnow()
                if status == "delivered":
                    update_values["delivered_at"] = now
                elif status == "read":
                    update_values["read_at"] = now
                    update_values["is_read"] = True
                
                await session.execute(
                    update(ChatMessage)
                    .where(ChatMessage.id == message_id)
                    .values(**update_values)
                )
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"更新消息状态失败: {e}")
            return False
    
    # ==================== 会话相关方法 ====================
    
    async def get_chat_session_by_id(
        self, 
        session_id: str
    ) -> Optional[Dict[str, Any]]:
        """根据 session_id 获取单条会话记录（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(ChatSession).where(ChatSession.session_id == session_id)
                )
                chat_session = result.scalar_one_or_none()
                if not chat_session:
                    return None
                
                return {
                    "id": chat_session.id,
                    "session_id": chat_session.session_id,
                    "user_id": chat_session.user_id,
                    "agent_id": chat_session.agent_id,
                    "status": chat_session.status.value if isinstance(chat_session.status, SessionStatus) else chat_session.status,
                    "created_at": chat_session.created_at,
                    "started_at": chat_session.started_at,
                    "closed_at": chat_session.closed_at,
                }
        except Exception as e:
            logger.error(f"根据 session_id 获取会话失败: {e}")
            return None
    
    async def create_pending_session(
        self, 
        session_id: str, 
        user_id: int
    ) -> bool:
        """创建待接入会话（异步）"""
        try:
            async with self.async_session() as session:
                # 检查会话是否已存在
                existing = await session.execute(
                    select(ChatSession).where(ChatSession.session_id == session_id)
                )
                if existing.scalar_one_or_none():
                    return False  # 会话已存在
                
                new_session = ChatSession(
                    session_id=session_id,
                    user_id=user_id,
                    status=SessionStatus.PENDING
                )
                session.add(new_session)
                await session.commit()
                return True
        except IntegrityError:
            return False  # 会话已存在
        except Exception as e:
            logger.error(f"创建待接入会话失败: {e}")
            return False
    
    async def assign_session_to_agent(
        self, 
        session_id: str, 
        agent_id: int
    ) -> bool:
        """将会话分配给客服（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    update(ChatSession)
                    .where(
                        and_(
                            ChatSession.session_id == session_id,
                            ChatSession.status == SessionStatus.PENDING
                        )
                    )
                    .values(
                        agent_id=agent_id,
                        status=SessionStatus.ACTIVE,
                        started_at=datetime.utcnow()
                    )
                )
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"分配会话给客服失败: {e}")
            return False
    
    async def get_pending_sessions(self) -> List[Dict[str, Any]]:
        """获取所有待接入的会话列表（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(ChatSession, User)
                    .join(User, ChatSession.user_id == User.id)
                    .where(ChatSession.status == SessionStatus.PENDING)
                    .order_by(ChatSession.created_at.asc())
                )
                
                sessions = []
                for chat_session, user in result.all():
                    # 获取最后一条消息
                    last_msg_result = await session.execute(
                        select(ChatMessage.message)
                        .where(ChatMessage.session_id == chat_session.session_id)
                        .order_by(ChatMessage.created_at.desc())
                        .limit(1)
                    )
                    last_message = last_msg_result.scalar_one_or_none()
                    
                    sessions.append({
                        "session_id": chat_session.session_id,
                        "user_id": chat_session.user_id,
                        "username": user.username,
                        "email": user.email,
                        "created_at": chat_session.created_at,
                        "last_message": last_message,
                    })
                
                return sessions
        except Exception as e:
            logger.error(f"获取待接入会话列表失败: {e}")
            return []
    
    async def get_agent_sessions(
        self, 
        agent_id: int, 
        include_pending: bool = False
    ) -> List[Dict[str, Any]]:
        """获取客服的会话列表（异步）"""
        try:
            async with self.async_session() as session:
                if include_pending:
                    # 包含待接入
                    result = await session.execute(
                        select(ChatSession, User)
                        .join(User, ChatSession.user_id == User.id)
                        .where(
                            or_(
                                ChatSession.agent_id == agent_id,
                                and_(
                                    ChatSession.agent_id.is_(None),
                                    ChatSession.status == SessionStatus.PENDING
                                )
                            )
                        )
                        .order_by(ChatSession.created_at.desc())
                    )
                else:
                    # 只包含已分配的会话
                    result = await session.execute(
                        select(ChatSession, User)
                        .join(User, ChatSession.user_id == User.id)
                        .where(
                            and_(
                                ChatSession.agent_id == agent_id,
                                ChatSession.status == SessionStatus.ACTIVE
                            )
                        )
                        .order_by(ChatSession.started_at.desc())
                    )
                
                sessions = []
                for chat_session, user in result.all():
                    # 获取未读消息数
                    unread_result = await session.execute(
                        select(func.count(ChatMessage.id))
                        .where(
                            and_(
                                ChatMessage.session_id == chat_session.session_id,
                                ChatMessage.to_user_id == agent_id,
                                ChatMessage.is_read == False
                            )
                        )
                    )
                    unread_count = unread_result.scalar() or 0
                    
                    # 获取最后一条消息
                    last_msg_result = await session.execute(
                        select(ChatMessage.message, ChatMessage.created_at)
                        .where(ChatMessage.session_id == chat_session.session_id)
                        .order_by(ChatMessage.created_at.desc())
                        .limit(1)
                    )
                    last_msg = last_msg_result.first()
                    
                    sessions.append({
                        "session_id": chat_session.session_id,
                        "user_id": chat_session.user_id,
                        "username": user.username,
                        "email": user.email,
                        "status": chat_session.status.value if isinstance(chat_session.status, SessionStatus) else chat_session.status,
                        "started_at": chat_session.started_at,
                        "created_at": chat_session.created_at,
                        "unread_count": unread_count,
                        "last_message": last_msg[0] if last_msg else None,
                    })
                
                return sessions
        except Exception as e:
            logger.error(f"获取客服会话列表失败: {e}")
            return []
    
    async def close_session(
        self, 
        session_id: str, 
        closed_by_user_id: int
    ) -> bool:
        """关闭会话（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    update(ChatSession)
                    .where(ChatSession.session_id == session_id)
                    .values(
                        status=SessionStatus.CLOSED,
                        closed_at=datetime.utcnow()
                    )
                )
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"关闭会话失败: {e}")
            return False
    
    # ==================== 客服状态相关方法 ====================
    
    async def get_online_agents(self) -> List[Dict[str, Any]]:
        """获取所有在线的客服列表（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(AgentStatus, User)
                    .join(User, AgentStatus.agent_id == User.id)
                    .where(
                        AgentStatus.status.in_([AgentStatusEnum.ONLINE, AgentStatusEnum.AWAY])
                    )
                )
                
                agents = []
                for agent_status, user in result.all():
                    agents.append({
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "status": agent_status.status.value if isinstance(agent_status.status, AgentStatusEnum) else agent_status.status,
                    })
                
                return agents
        except Exception as e:
            logger.error(f"获取在线客服列表失败: {e}")
            return []
    
    async def update_agent_status(
        self, 
        agent_id: int, 
        status: str
    ) -> bool:
        """更新客服在线状态（异步）"""
        try:
            agent_status = AgentStatusEnum(status) if status in ['online', 'offline', 'away', 'busy'] else AgentStatusEnum.OFFLINE
            
            async with self.async_session() as session:
                # 使用 INSERT ... ON DUPLICATE KEY UPDATE
                # SQLAlchemy 2.0 需要使用 merge 或先查询再更新
                existing = await session.execute(
                    select(AgentStatus).where(AgentStatus.agent_id == agent_id)
                )
                agent_status_obj = existing.scalar_one_or_none()
                
                if agent_status_obj:
                    agent_status_obj.status = agent_status
                    agent_status_obj.last_heartbeat = datetime.utcnow()
                else:
                    agent_status_obj = AgentStatus(
                        agent_id=agent_id,
                        status=agent_status
                    )
                    session.add(agent_status_obj)
                
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"更新客服状态失败: {e}")
            return False
    
    # ==================== 公告相关方法 ====================
    
    async def get_latest_announcement(self) -> Optional[str]:
        """获取最新的公告内容（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(Announcement.content)
                    .order_by(Announcement.id.desc())
                    .limit(1)
                )
                content = result.scalar_one_or_none()
                return content
        except Exception as e:
            logger.error(f"查询公告失败: {e}")
            return None
    
    # ==================== 密码重置相关方法 ====================
    
    async def insert_password_reset_token(
        self, 
        email: str, 
        token: str, 
        expires_at: datetime
    ) -> bool:
        """插入密码重置token（异步）"""
        try:
            async with self.async_session() as session:
                # 先删除该邮箱的旧token
                await session.execute(
                    delete(PasswordResetToken).where(PasswordResetToken.email == email)
                )
                
                # 插入新token
                new_token = PasswordResetToken(
                    email=email,
                    token=token,
                    expires_at=expires_at
                )
                session.add(new_token)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"插入密码重置token失败: {e}")
            return False
    
    async def get_password_reset_token(
        self, 
        token: str
    ) -> Optional[Dict[str, Any]]:
        """获取密码重置token信息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(PasswordResetToken).where(PasswordResetToken.token == token)
                )
                token_obj = result.scalar_one_or_none()
                if not token_obj:
                    return None
                
                return {
                    "email": token_obj.email,
                    "token": token_obj.token,
                    "expires_at": token_obj.expires_at,
                    "used": token_obj.used,
                }
        except Exception as e:
            logger.error(f"查询密码重置token失败: {e}")
            return None
    
    async def mark_password_reset_token_as_used(self, token: str) -> bool:
        """标记密码重置token为已使用（异步）"""
        try:
            async with self.async_session() as session:
                await session.execute(
                    update(PasswordResetToken)
                    .where(PasswordResetToken.token == token)
                    .values(used=True)
                )
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"标记密码重置token为已使用失败: {e}")
            return False
    
    # ==================== WebSocket 连接管理方法 ====================
    
    async def create_user_connection(
        self,
        user_id: int,
        connection_id: str,
        socket_id: str = None,
        device_id: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> bool:
        """创建用户连接记录（异步）"""
        try:
            async with self.async_session() as session:
                new_connection = UserConnection(
                    user_id=user_id,
                    connection_id=connection_id,
                    socket_id=socket_id,
                    device_id=device_id,
                    status=ConnectionStatus.CONNECTED,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                session.add(new_connection)
                await session.commit()
                return True
        except IntegrityError:
            # 连接ID已存在，更新现有记录
            return await self.update_connection_heartbeat(connection_id)
        except Exception as e:
            logger.error(f"创建用户连接记录失败: {e}")
            return False
    
    async def update_connection_heartbeat(self, connection_id: str) -> bool:
        """更新连接心跳（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    update(UserConnection)
                    .where(UserConnection.connection_id == connection_id)
                    .values(
                        last_heartbeat=datetime.utcnow(),
                        status=ConnectionStatus.CONNECTED
                    )
                )
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"更新连接心跳失败: {e}")
            return False
    
    async def disconnect_user_connection(self, connection_id: str) -> bool:
        """断开用户连接（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    update(UserConnection)
                    .where(UserConnection.connection_id == connection_id)
                    .values(
                        status=ConnectionStatus.DISCONNECTED,
                        disconnected_at=datetime.utcnow()
                    )
                )
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"断开用户连接失败: {e}")
            return False
    
    async def get_user_connections(
        self, 
        user_id: int, 
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户连接列表（异步）"""
        try:
            async with self.async_session() as session:
                query = select(UserConnection).where(UserConnection.user_id == user_id)
                if active_only:
                    query = query.where(UserConnection.status == ConnectionStatus.CONNECTED)
                
                result = await session.execute(query)
                connections = result.scalars().all()
                
                return [
                    {
                        "id": conn.id,
                        "user_id": conn.user_id,
                        "connection_id": conn.connection_id,
                        "socket_id": conn.socket_id,
                        "device_id": conn.device_id,
                        "status": conn.status.value if isinstance(conn.status, ConnectionStatus) else conn.status,
                        "last_heartbeat": conn.last_heartbeat,
                        "connected_at": conn.connected_at,
                        "disconnected_at": conn.disconnected_at,
                        "ip_address": conn.ip_address,
                        "user_agent": conn.user_agent,
                    }
                    for conn in connections
                ]
        except Exception as e:
            logger.error(f"获取用户连接列表失败: {e}")
            return []
    
    async def cleanup_stale_connections(self, timeout_minutes: int = 5) -> int:
        """清理过期连接（异步）"""
        try:
            timeout_threshold = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            async with self.async_session() as session:
                result = await session.execute(
                    update(UserConnection)
                    .where(
                        and_(
                            UserConnection.status == ConnectionStatus.CONNECTED,
                            UserConnection.last_heartbeat < timeout_threshold
                        )
                    )
                    .values(
                        status=ConnectionStatus.DISCONNECTED,
                        disconnected_at=datetime.utcnow()
                    )
                )
                await session.commit()
                return result.rowcount
        except Exception as e:
            logger.error(f"清理过期连接失败: {e}")
            return 0
    
    # ==================== 设备管理方法 ====================
    
    async def register_user_device(
        self,
        user_id: int,
        device_id: str,
        device_name: str = None,
        device_type: str = 'other',
        platform: str = None,
        browser: str = None,
        os_version: str = None,
        app_version: str = None,
        push_token: str = None
    ) -> bool:
        """注册用户设备（异步）"""
        try:
            dev_type = DeviceType(device_type) if device_type in ['desktop', 'mobile', 'web', 'other'] else DeviceType.OTHER
            
            async with self.async_session() as session:
                # 检查设备是否已存在
                existing = await session.execute(
                    select(UserDevice).where(
                        and_(
                            UserDevice.user_id == user_id,
                            UserDevice.device_id == device_id
                        )
                    )
                )
                device = existing.scalar_one_or_none()
                
                if device:
                    # 更新现有设备
                    device.device_name = device_name
                    device.device_type = dev_type
                    device.platform = platform
                    device.browser = browser
                    device.os_version = os_version
                    device.app_version = app_version
                    device.push_token = push_token
                    device.is_active = True
                    device.last_login = datetime.utcnow()
                else:
                    # 创建新设备
                    device = UserDevice(
                        user_id=user_id,
                        device_id=device_id,
                        device_name=device_name,
                        device_type=dev_type,
                        platform=platform,
                        browser=browser,
                        os_version=os_version,
                        app_version=app_version,
                        push_token=push_token
                    )
                    session.add(device)
                
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"注册用户设备失败: {e}")
            return False
    
    async def get_user_devices(
        self, 
        user_id: int, 
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """获取用户设备列表（异步）"""
        try:
            async with self.async_session() as session:
                query = select(UserDevice).where(UserDevice.user_id == user_id)
                if active_only:
                    query = query.where(UserDevice.is_active == True)
                
                result = await session.execute(query)
                devices = result.scalars().all()
                
                return [
                    {
                        "id": dev.id,
                        "user_id": dev.user_id,
                        "device_id": dev.device_id,
                        "device_name": dev.device_name,
                        "device_type": dev.device_type.value if isinstance(dev.device_type, DeviceType) else dev.device_type,
                        "platform": dev.platform,
                        "browser": dev.browser,
                        "os_version": dev.os_version,
                        "app_version": dev.app_version,
                        "push_token": dev.push_token,
                        "is_active": dev.is_active,
                        "last_login": dev.last_login,
                        "created_at": dev.created_at,
                    }
                    for dev in devices
                ]
        except Exception as e:
            logger.error(f"获取用户设备列表失败: {e}")
            return []
    
    async def deactivate_user_device(
        self, 
        user_id: int, 
        device_id: str
    ) -> bool:
        """停用用户设备（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    update(UserDevice)
                    .where(
                        and_(
                            UserDevice.user_id == user_id,
                            UserDevice.device_id == device_id
                        )
                    )
                    .values(is_active=False)
                )
                await session.commit()
                return result.rowcount > 0
        except Exception as e:
            logger.error(f"停用用户设备失败: {e}")
            return False
    
    # ==================== 消息队列方法 ====================
    
    async def get_undelivered_messages(
        self, 
        user_id: int, 
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取未送达的消息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(ChatMessage)
                    .where(
                        and_(
                            ChatMessage.to_user_id == user_id,
                            ChatMessage.status != MessageStatus.DELIVERED,
                            ChatMessage.is_recalled == False
                        )
                    )
                    .order_by(ChatMessage.created_at.asc())
                    .limit(limit)
                )
                messages = result.scalars().all()
                
                return [
                    {
                        "id": msg.id,
                        "session_id": msg.session_id,
                        "from_user_id": msg.from_user_id,
                        "to_user_id": msg.to_user_id,
                        "message": msg.message,
                        "message_type": msg.message_type.value if isinstance(msg.message_type, MessageType) else msg.message_type,
                        "created_at": msg.created_at,
                    }
                    for msg in messages
                ]
        except Exception as e:
            logger.error(f"获取未送达消息失败: {e}")
            return []
    
    async def add_message_to_queue(
        self,
        message_id: int,
        session_id: str,
        from_user_id: int,
        to_user_id: Optional[int],
        max_retries: int = 3
    ) -> bool:
        """添加消息到队列（异步）"""
        try:
            async with self.async_session() as session:
                queue_item = MessageQueue(
                    message_id=message_id,
                    session_id=session_id,
                    from_user_id=from_user_id,
                    to_user_id=to_user_id,
                    max_retries=max_retries,
                    status=QueueStatus.PENDING
                )
                session.add(queue_item)
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"添加消息到队列失败: {e}")
            return False
    
    async def get_pending_queue_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取待处理队列消息（异步）"""
        try:
            async with self.async_session() as session:
                result = await session.execute(
                    select(MessageQueue)
                    .where(MessageQueue.status == QueueStatus.PENDING)
                    .order_by(MessageQueue.created_at.asc())
                    .limit(limit)
                )
                queue_items = result.scalars().all()
                
                return [
                    {
                        "id": item.id,
                        "message_id": item.message_id,
                        "session_id": item.session_id,
                        "from_user_id": item.from_user_id,
                        "to_user_id": item.to_user_id,
                        "retry_count": item.retry_count,
                        "max_retries": item.max_retries,
                        "status": item.status.value if isinstance(item.status, QueueStatus) else item.status,
                        "error_message": item.error_message,
                        "next_retry_at": item.next_retry_at,
                    }
                    for item in queue_items
                ]
        except Exception as e:
            logger.error(f"获取待处理队列消息失败: {e}")
            return []
    
    async def update_queue_message_status(
        self,
        queue_id: int,
        status: str,
        error_message: str = None
    ) -> bool:
        """更新队列消息状态（异步）"""
        try:
            queue_status = QueueStatus(status) if status in ['pending', 'processing', 'completed', 'failed'] else QueueStatus.PENDING
            
            async with self.async_session() as session:
                update_values = {"status": queue_status}
                if error_message:
                    update_values["error_message"] = error_message
                
                await session.execute(
                    update(MessageQueue)
                    .where(MessageQueue.id == queue_id)
                    .values(**update_values)
                )
                await session.commit()
                return True
        except Exception as e:
            logger.error(f"更新队列消息状态失败: {e}")
            return False
    
    # ==================== 用户会话相关方法 ====================
    
    async def get_user_sessions(self, user_id: int, role: str) -> List[Dict[str, Any]]:
        """获取用户的会话列表（异步）"""
        try:
            async with self.async_session() as session:
                if role == 'customer_service':
                    # 客服：获取所有分配给该客服的会话，或所有用户发起的会话（待分配）
                    result = await session.execute(
                        select(ChatMessage, User)
                        .join(User, or_(
                            ChatMessage.from_user_id == User.id,
                            ChatMessage.to_user_id == User.id
                        ))
                        .where(
                            and_(
                                or_(
                                    ChatMessage.to_user_id == user_id,
                                    ChatMessage.to_user_id.is_(None)
                                ),
                                User.role == UserRole.USER
                            )
                        )
                        .distinct()
                    )
                else:
                    # 普通用户：获取自己发起的会话
                    result = await session.execute(
                        select(ChatMessage, User)
                        .join(User, ChatMessage.from_user_id == User.id)
                        .where(ChatMessage.from_user_id == user_id)
                        .distinct()
                    )
                
                # 按 session_id 分组并构建结果
                sessions_dict = {}
                for msg, user in result.all():
                    if msg.session_id not in sessions_dict:
                        # 获取未读消息数
                        unread_result = await session.execute(
                            select(func.count(ChatMessage.id))
                            .where(
                                and_(
                                    ChatMessage.session_id == msg.session_id,
                                    ChatMessage.to_user_id == user_id,
                                    ChatMessage.is_read == False
                                )
                            )
                        )
                        unread_count = unread_result.scalar() or 0
                        
                        # 获取最后一条消息
                        last_msg_result = await session.execute(
                            select(ChatMessage.message, ChatMessage.created_at)
                            .where(ChatMessage.session_id == msg.session_id)
                            .order_by(ChatMessage.created_at.desc())
                            .limit(1)
                        )
                        last_msg = last_msg_result.first()
                        
                        sessions_dict[msg.session_id] = {
                            "session_id": msg.session_id,
                            "user_id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "unread_count": unread_count,
                            "last_message": last_msg[0] if last_msg else None,
                            "last_time": last_msg[1] if last_msg else None,
                        }
                
                return list(sessions_dict.values())
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            return []
    
    # ==================== 关闭连接 ====================
    
    async def close(self):
        """关闭数据库连接（异步）"""
        await self.engine.dispose()
        logger.info("异步数据库连接已关闭")

