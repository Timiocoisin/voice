"""
SQLAlchemy ORM 模型定义

定义所有数据表的 SQLAlchemy 模型，用于异步数据库操作。
"""

from datetime import datetime
from typing import Optional, Type
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    Enum, ForeignKey, BigInteger, Index, LargeBinary, TypeDecorator
)
from sqlalchemy.orm import DeclarativeBase, relationship
import enum


class Base(DeclarativeBase):
    """SQLAlchemy 基类"""
    pass


class EnumValueType(TypeDecorator):
    """自定义类型，使用枚举值而不是名称"""
    impl = String
    cache_ok = True
    
    def __init__(self, enum_class: Type[enum.Enum], length: int = 50, *args, **kwargs):
        super().__init__(length, *args, **kwargs)
        self.enum_class = enum_class
    
    def process_bind_param(self, value, dialect):
        """写入数据库时：将枚举对象转换为值字符串"""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value
        if isinstance(value, str):
            # 如果已经是字符串，验证是否是有效的枚举值
            valid_values = [e.value for e in self.enum_class]
            if value in valid_values:
                return value
            # 如果不是有效值，尝试通过名称查找
            try:
                return self.enum_class[value].value
            except KeyError:
                return value
        return str(value)
    
    def process_result_value(self, value, dialect):
        """从数据库读取时：将字符串值转换为枚举对象"""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value
        if isinstance(value, str):
            # 尝试通过值查找枚举
            for enum_item in self.enum_class:
                if enum_item.value == value:
                    return enum_item
            # 如果值不匹配，尝试通过名称查找（向后兼容）
            try:
                return self.enum_class[value.upper()]
            except (KeyError, AttributeError):
                # 如果都失败了，返回第一个枚举值作为默认值
                return list(self.enum_class)[0]
        return value


class UserRole(str, enum.Enum):
    """用户角色枚举"""
    USER = "user"
    ADMIN = "admin"
    CUSTOMER_SERVICE = "customer_service"


class MessageType(str, enum.Enum):
    """消息类型枚举"""
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"


class SessionStatus(str, enum.Enum):
    """会话状态枚举"""
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"


class AgentStatusEnum(str, enum.Enum):
    """客服状态枚举"""
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"


class ConnectionStatus(str, enum.Enum):
    """连接状态枚举"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"


class DeviceType(str, enum.Enum):
    """设备类型枚举"""
    DESKTOP = "desktop"
    MOBILE = "mobile"
    WEB = "web"
    OTHER = "other"


class MessageStatus(str, enum.Enum):
    """消息状态枚举"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class QueueStatus(str, enum.Enum):
    """队列状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class User(Base):
    """用户表模型"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password = Column(String(255), nullable=False)
    avatar = Column(LargeBinary)  # LONGBLOB
    role = Column(
        EnumValueType(UserRole, length=20),
        default=UserRole.USER,
        nullable=False
    )
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 关系
    vip_info = relationship("UserVip", back_populates="user", uselist=False)
    chat_sessions_as_user = relationship("ChatSession", foreign_keys="ChatSession.user_id", back_populates="user")
    chat_sessions_as_agent = relationship("ChatSession", foreign_keys="ChatSession.agent_id", back_populates="agent")
    sent_messages = relationship("ChatMessage", foreign_keys="ChatMessage.from_user_id", back_populates="from_user")
    received_messages = relationship("ChatMessage", foreign_keys="ChatMessage.to_user_id", back_populates="to_user")


class UserVip(Base):
    """用户 VIP 信息表模型"""
    __tablename__ = "user_vip"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    is_vip = Column(Boolean, default=False, nullable=False)
    vip_expiry_date = Column(DateTime, nullable=True)
    diamonds = Column(Integer, default=0, nullable=False)
    
    # 关系
    user = relationship("User", back_populates="vip_info")


class ChatMessage(Base):
    """聊天消息表模型"""
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence_number = Column(BigInteger, nullable=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    message = Column(Text, nullable=False)  # MEDIUMTEXT
    message_type = Column(EnumValueType(MessageType, length=20), default=MessageType.TEXT, nullable=False)
    status = Column(EnumValueType(MessageStatus, length=20), default=MessageStatus.SENT, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)
    is_recalled = Column(Boolean, default=False, nullable=False)
    is_edited = Column(Boolean, default=False, nullable=False)
    edited_at = Column(DateTime, nullable=True)
    reply_to_message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    
    # 关系
    from_user = relationship("User", foreign_keys=[from_user_id], back_populates="sent_messages")
    to_user = relationship("User", foreign_keys=[to_user_id], back_populates="received_messages")
    reply_to_message = relationship("ChatMessage", remote_side=[id], backref="replies")
    session = relationship("ChatSession", foreign_keys=[session_id], primaryjoin="ChatMessage.session_id == ChatSession.session_id", back_populates="messages")
    
    # 索引
    __table_args__ = (
        Index("idx_sequence", "session_id", "sequence_number"),
    )


class ChatSession(Base):
    """聊天会话表模型"""
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(EnumValueType(SessionStatus, length=20), default=SessionStatus.PENDING, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    
    # 关系
    user = relationship("User", foreign_keys=[user_id], back_populates="chat_sessions_as_user")
    agent = relationship("User", foreign_keys=[agent_id], back_populates="chat_sessions_as_agent")
    messages = relationship("ChatMessage", foreign_keys="ChatMessage.session_id", primaryjoin="ChatSession.session_id == ChatMessage.session_id", back_populates="session")


class Announcement(Base):
    """公告表模型"""
    __tablename__ = "announcements"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PasswordResetToken(Base):
    """密码重置token表模型"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), nullable=False, index=True)
    token = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class AgentStatus(Base):
    """客服在线状态表模型"""
    __tablename__ = "agent_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    status = Column(EnumValueType(AgentStatusEnum, length=20), default=AgentStatusEnum.OFFLINE, nullable=False, index=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)


class UserConnection(Base):
    """用户连接管理表模型（WebSocket 连接管理）"""
    __tablename__ = "user_connections"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(String(255), nullable=False, unique=True, index=True)
    socket_id = Column(String(255), nullable=True)
    device_id = Column(String(255), nullable=True, index=True)
    status = Column(EnumValueType(ConnectionStatus, length=20), default=ConnectionStatus.CONNECTED, nullable=False, index=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    disconnected_at = Column(DateTime, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)


class UserDevice(Base):
    """用户设备管理表模型（多设备登录管理）"""
    __tablename__ = "user_devices"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    device_name = Column(String(255), nullable=True)
    device_type = Column(EnumValueType(DeviceType, length=20), default=DeviceType.OTHER, nullable=False)
    platform = Column(String(100), nullable=True)
    browser = Column(String(100), nullable=True)
    os_version = Column(String(100), nullable=True)
    app_version = Column(String(50), nullable=True)
    push_token = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # 唯一约束
    __table_args__ = (
        Index("unique_user_device", "user_id", "device_id", unique=True),
    )


class MessageQueue(Base):
    """消息队列表模型（消息发送失败重试队列）"""
    __tablename__ = "message_queue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(255), nullable=False)
    from_user_id = Column(Integer, nullable=False)
    to_user_id = Column(Integer, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    status = Column(EnumValueType(QueueStatus, length=20), default=QueueStatus.PENDING, nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    next_retry_at = Column(DateTime, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

