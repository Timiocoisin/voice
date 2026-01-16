"""
Pydantic 请求/响应模型定义

定义所有 API 的请求和响应模型，用于 FastAPI 路由的类型验证和文档生成。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


# ==================== 通用响应模型 ====================

class SuccessResponse(BaseModel):
    """通用成功响应"""
    success: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """通用错误响应"""
    success: bool = False
    message: str


# ==================== 健康检查 ====================

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"


# ==================== 验证码相关 ====================

class SendVerificationCodeRequest(BaseModel):
    """发送验证码请求"""
    email: str = Field(..., description="邮箱地址")
    mode: str = Field(..., description="模式：'login' 或 'register'")
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v


class SendVerificationCodeResponse(BaseModel):
    """发送验证码响应"""
    success: bool


# ==================== 用户注册 ====================

class RegisterRequest(BaseModel):
    """用户注册请求"""
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8, description="密码至少8位，需包含至少一个字母和一个符号")
    username: str = Field(..., min_length=1, description="用户名不能为空")
    code: str = Field(..., description="验证码")
    role: Optional[str] = Field(default="user", description="用户角色：'user', 'admin', 'customer_service'")


class UserInfo(BaseModel):
    """用户信息"""
    id: int
    username: str
    avatar_base64: Optional[str] = None


class VipInfo(BaseModel):
    """VIP 信息"""
    is_vip: bool = False
    vip_expiry_date: Optional[str] = None
    diamonds: int = 0


class RegisterResponse(BaseModel):
    """用户注册响应"""
    success: bool
    message: str
    token: str
    user: UserInfo
    vip: VipInfo


# ==================== 用户登录 ====================

class LoginRequest(BaseModel):
    """用户登录请求"""
    email: str = Field(..., description="邮箱地址")
    password: str
    code: str = Field(..., description="验证码")


class LoginResponse(BaseModel):
    """用户登录响应"""
    success: bool
    message: str
    token: str
    user: UserInfo
    vip: VipInfo


# ==================== 忘记密码 ====================

class ForgotPasswordRequest(BaseModel):
    """忘记密码请求"""
    email: str = Field(..., description="邮箱地址")


class ForgotPasswordResponse(BaseModel):
    """忘记密码响应"""
    success: bool
    message: str


# ==================== 重置密码 ====================

class ResetPasswordRequest(BaseModel):
    """重置密码请求"""
    token: str = Field(..., description="重置token")
    new_password: str = Field(..., min_length=8, description="新密码至少8位，需包含至少一个字母和一个符号")


class ResetPasswordResponse(BaseModel):
    """重置密码响应"""
    success: bool
    message: str


class VerifyResetTokenResponse(BaseModel):
    """验证重置token响应"""
    success: bool
    message: str


# ==================== Token 验证 ====================

class CheckTokenRequest(BaseModel):
    """检查token请求"""
    token: str


class CheckTokenResponse(BaseModel):
    """检查token响应"""
    success: bool
    user: Optional[UserInfo] = None
    vip: Optional[VipInfo] = None
    token: Optional[str] = None


# ==================== 公告 ====================

class AnnouncementResponse(BaseModel):
    """公告响应"""
    success: bool
    content: Optional[str] = None


# ==================== 修改密码 ====================

class ChangePasswordRequest(BaseModel):
    """修改密码请求"""
    token: str
    old_password: str
    new_password: str = Field(..., min_length=8, description="新密码至少8位，需包含至少一个字母和一个符号")


class ChangePasswordResponse(BaseModel):
    """修改密码响应"""
    success: bool
    message: str


# ==================== VIP 购买 ====================

class VipPurchaseRequest(BaseModel):
    """VIP 购买请求"""
    token: str
    package_type: str = Field(..., description="套餐类型：'monthly', 'yearly' 等")
    payment_method: Optional[str] = Field(default=None, description="支付方式")


class VipPurchaseResponse(BaseModel):
    """VIP 购买响应"""
    success: bool
    message: str
    vip_info: Optional[VipInfo] = None


# ==================== 客服相关 ====================

class CustomerServiceRegisterRequest(BaseModel):
    """客服注册请求"""
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=1)
    code: str


class CustomerServiceRegisterResponse(BaseModel):
    """客服注册响应"""
    success: bool
    message: str
    token: str
    user: UserInfo


class CustomerServiceLoginRequest(BaseModel):
    """客服登录请求"""
    email: str = Field(..., description="邮箱地址")
    password: str
    code: str


class CustomerServiceLoginResponse(BaseModel):
    """客服登录响应"""
    success: bool
    message: str
    token: str
    user: UserInfo


class CustomerServiceVerifyTokenRequest(BaseModel):
    """客服验证token请求"""
    token: str


class CustomerServiceVerifyTokenResponse(BaseModel):
    """客服验证token响应"""
    success: bool
    user: Optional[UserInfo] = None


# ==================== 消息相关 ====================

class MessageInfo(BaseModel):
    """消息信息"""
    id: int
    session_id: str
    from_user_id: int
    to_user_id: Optional[int] = None
    message: str
    message_type: str = "text"
    is_read: bool = False
    is_recalled: bool = False
    is_edited: bool = False
    edited_at: Optional[str] = None
    reply_to_message_id: Optional[int] = None
    created_at: str
    status: Optional[str] = None
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None


class SendMessageRequest(BaseModel):
    """发送消息请求（WebSocket 事件）"""
    session_id: str
    message: str
    message_type: str = "text"
    reply_to_message_id: Optional[int] = None


class SendMessageResponse(BaseModel):
    """发送消息响应"""
    success: bool
    message_id: Optional[int] = None
    message: Optional[str] = None


class GetMessagesRequest(BaseModel):
    """获取消息请求"""
    session_id: str
    limit: int = Field(default=100, ge=1, le=1000)


class GetMessagesResponse(BaseModel):
    """获取消息响应"""
    success: bool
    messages: List[MessageInfo]


class EditMessageRequest(BaseModel):
    """编辑消息请求"""
    message_id: int
    new_content: str


class EditMessageResponse(BaseModel):
    """编辑消息响应"""
    success: bool
    message: str


class RecallMessageRequest(BaseModel):
    """撤回消息请求"""
    message_id: int


class RecallMessageResponse(BaseModel):
    """撤回消息响应"""
    success: bool
    message: str


# ==================== 会话相关 ====================

class SessionInfo(BaseModel):
    """会话信息"""
    session_id: str
    user_id: int
    username: str
    email: str
    unread_count: int = 0
    last_message: Optional[str] = None
    last_time: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[str] = None
    created_at: Optional[str] = None


class GetSessionsResponse(BaseModel):
    """获取会话列表响应"""
    success: bool
    sessions: List[SessionInfo]


class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    session_id: Optional[str] = None


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    success: bool
    session_id: str
    message: str


# ==================== 客服会话管理 ====================

class GetPendingSessionsResponse(BaseModel):
    """获取待接入会话列表响应"""
    success: bool
    sessions: List[SessionInfo]


class AssignSessionRequest(BaseModel):
    """分配会话请求"""
    session_id: str
    agent_id: int


class AssignSessionResponse(BaseModel):
    """分配会话响应"""
    success: bool
    message: str


class CloseSessionRequest(BaseModel):
    """关闭会话请求"""
    session_id: str


class CloseSessionResponse(BaseModel):
    """关闭会话响应"""
    success: bool
    message: str


# ==================== 客服状态 ====================

class AgentStatusInfo(BaseModel):
    """客服状态信息"""
    id: int
    username: str
    email: str
    status: str


class GetOnlineAgentsResponse(BaseModel):
    """获取在线客服列表响应"""
    success: bool
    agents: List[AgentStatusInfo]


class UpdateAgentStatusRequest(BaseModel):
    """更新客服状态请求"""
    status: str = Field(..., description="状态：'online', 'offline', 'away', 'busy'")


class UpdateAgentStatusResponse(BaseModel):
    """更新客服状态响应"""
    success: bool
    message: str


# ==================== 用户资料 ====================

class UpdateProfileRequest(BaseModel):
    """更新用户资料请求"""
    token: str
    username: Optional[str] = None
    avatar_base64: Optional[str] = None


class UpdateProfileResponse(BaseModel):
    """更新用户资料响应"""
    success: bool
    message: str
    user: Optional[UserInfo] = None


# ==================== WebSocket 事件 ====================

class WebSocketConnectData(BaseModel):
    """WebSocket 连接数据"""
    user_id: int
    connection_id: str
    device_id: Optional[str] = None


class WebSocketHeartbeatData(BaseModel):
    """WebSocket 心跳数据"""
    connection_id: Optional[str] = None
    socket_id: Optional[str] = None


class WebSocketMessageData(BaseModel):
    """WebSocket 消息数据"""
    id: Optional[str] = None
    session_id: str
    from_user_id: int
    to_user_id: Optional[int] = None
    message: str
    message_type: str = "text"
    reply_to_message_id: Optional[int] = None
    created_at: Optional[str] = None


class WebSocketSessionListData(BaseModel):
    """WebSocket 会话列表数据"""
    type: str = Field(..., description="类型：'my' 或 'pending'")
    sessions: List[SessionInfo]


class WebSocketVipStatusData(BaseModel):
    """WebSocket VIP 状态数据"""
    user_id: int
    vip_info: VipInfo


class WebSocketDiamondBalanceData(BaseModel):
    """WebSocket 钻石余额数据"""
    user_id: int
    balance: int


class WebSocketUserProfileData(BaseModel):
    """WebSocket 用户资料数据"""
    user_id: int
    profile: Dict[str, Any]


class WebSocketMessageEditedData(BaseModel):
    """WebSocket 消息编辑数据"""
    message_id: int
    session_id: str
    new_content: str
    edited_at: str


class WebSocketSessionStatusData(BaseModel):
    """WebSocket 会话状态数据"""
    session_id: str
    status: str
    user_id: Optional[int] = None
    agent_id: Optional[int] = None


class WebSocketMessageStatusData(BaseModel):
    """WebSocket 消息状态数据"""
    message_id: str
    status: str
    timestamp: str


class WebSocketNewPendingSessionData(BaseModel):
    """WebSocket 新待接入会话数据"""
    session_id: str
    user_id: int
    username: str
    email: str
    created_at: str
    last_message: Optional[str] = None


class WebSocketPendingSessionAcceptedData(BaseModel):
    """WebSocket 待接入会话被接入数据"""
    session_id: str
    agent_id: int


class WebSocketSessionAcceptedForUserData(BaseModel):
    """WebSocket 会话已被客服接入数据"""
    user_id: int
    session_id: str
    agent_id: int
    agent_name: Optional[str] = None


class WebSocketAgentStatusChangedData(BaseModel):
    """WebSocket 客服状态变化数据"""
    agent_id: int
    status: str

