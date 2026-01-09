# WebSocket 实时通信模块

本模块实现了完整的 WebSocket 实时通信功能，包括消息推送、连接管理、心跳检测、自动重连、离线消息等。

## 功能特性

### ✅ 已实现功能

#### 1. 消息实时推送
- **双向实时推送**：用户 ↔ 客服实时消息推送
- **消息状态回执**：支持已发送、已送达、已读三种状态
- **离线消息推送**：用户上线后自动推送离线期间的消息
- **消息去重**：防止重复接收同一消息

#### 2. 连接管理
- **连接注册**：用户连接时自动注册到服务器
- **心跳检测**：定期发送心跳保持连接活跃
- **连接超时检测**：自动清理超时的连接
- **多设备支持**：同一用户可在多个设备同时在线

#### 3. 自动重连
- **指数退避重连**：连接断开后自动重连，重连间隔逐渐增加
- **无限重试**：默认无限次重连尝试
- **状态管理**：连接状态实时更新（connecting/connected/reconnecting/disconnected）

#### 4. 消息队列与可靠性
- **发送失败重试**：消息发送失败自动加入队列重试
- **消息序列号**：保证消息顺序
- **队列持久化**：支持将未发送消息保存到数据库

#### 5. 设备管理
- **设备注册**：记录用户设备信息
- **设备列表**：查看用户所有设备
- **设备踢出**：支持踢出指定设备

## 数据库表结构

### 1. user_connections（用户连接表）
```sql
CREATE TABLE user_connections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    connection_id VARCHAR(255) NOT NULL UNIQUE,
    socket_id VARCHAR(255),
    device_id VARCHAR(255),
    status ENUM('connected', 'disconnected') DEFAULT 'connected',
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    disconnected_at TIMESTAMP NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    ...
)
```

### 2. offline_messages（离线消息表）
```sql
CREATE TABLE offline_messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    message_id INT NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ...
)
```

### 3. user_devices（用户设备表）
```sql
CREATE TABLE user_devices (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    device_id VARCHAR(255) NOT NULL,
    device_name VARCHAR(255),
    device_type ENUM('desktop', 'mobile', 'web', 'other') DEFAULT 'other',
    platform VARCHAR(100),
    browser VARCHAR(100),
    os_version VARCHAR(100),
    app_version VARCHAR(50),
    push_token VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    ...
)
```

### 4. message_queue（消息队列表）
```sql
CREATE TABLE message_queue (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id INT NOT NULL,
    session_id VARCHAR(255) NOT NULL,
    from_user_id INT NOT NULL,
    to_user_id INT,
    retry_count INT DEFAULT 0,
    max_retries INT DEFAULT 3,
    status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
    error_message TEXT,
    next_retry_at TIMESTAMP NULL,
    ...
)
```

### 5. chat_messages 新增字段
```sql
ALTER TABLE chat_messages 
ADD COLUMN status ENUM('pending', 'sent', 'delivered', 'read', 'failed') DEFAULT 'sent',
ADD COLUMN sent_at TIMESTAMP NULL,
ADD COLUMN delivered_at TIMESTAMP NULL,
ADD COLUMN read_at TIMESTAMP NULL,
ADD COLUMN sequence_number BIGINT NULL;
```

## 服务端 API

### WebSocket 事件

#### 1. connect（连接建立）
客户端连接成功后自动触发。

**响应：**
```json
{
  "success": true,
  "socket_id": "abc123"
}
```

#### 2. register（注册连接）
客户端需要在连接后立即注册。

**请求：**
```json
{
  "user_id": 123,
  "token": "xxx",
  "connection_id": "uuid",
  "device_id": "device-uuid",
  "device_info": {
    "device_name": "iPhone 13",
    "device_type": "mobile",
    "platform": "iOS",
    "browser": "Safari",
    "os_version": "15.0",
    "app_version": "1.0.0"
  }
}
```

**响应：**
```json
{
  "success": true,
  "connection_id": "uuid",
  "socket_id": "abc123",
  "message": "连接注册成功"
}
```

#### 3. heartbeat（心跳）
客户端定期发送心跳保持连接。

**请求：**
```json
{
  "connection_id": "uuid"
}
```

**响应：**
```json
{
  "success": true,
  "timestamp": "2024-01-01T12:00:00"
}
```

#### 4. send_message（发送消息）
发送聊天消息。

**请求：**
```json
{
  "session_id": "session-uuid",
  "from_user_id": 123,
  "message": "Hello",
  "role": "user",
  "token": "xxx",
  "message_type": "text",
  "reply_to_message_id": 456
}
```

**响应：**
```json
{
  "success": true,
  "message_id": 789,
  "time": "12:00"
}
```

#### 5. message_delivered（消息已送达）
客户端收到消息后发送已送达回执。

**请求：**
```json
{
  "message_id": 789,
  "user_id": 123
}
```

**响应：**
```json
{
  "success": true
}
```

#### 6. message_read（消息已读）
用户阅读消息后发送已读回执。

**请求：**
```json
{
  "message_id": 789,
  "user_id": 123
}
```

**响应：**
```json
{
  "success": true
}
```

### WebSocket 事件（服务端推送）

#### 1. new_message（新消息）
服务端推送新消息给客户端。

**数据：**
```json
{
  "id": "789",
  "session_id": "session-uuid",
  "from": "agent",
  "from_user_id": 456,
  "to_user_id": 123,
  "text": "Hello",
  "time": "12:00",
  "avatar": "data:image/png;base64,...",
  "message_type": "text",
  "reply_to_message_id": null,
  "status": "sent",
  "offline": false
}
```

#### 2. message_status（消息状态更新）
服务端推送消息状态更新。

**数据：**
```json
{
  "message_id": "789",
  "status": "delivered",
  "timestamp": "2024-01-01T12:00:00"
}
```

## 客户端使用

### 1. 安装依赖
```bash
pip install python-socketio
```

### 2. 基本使用
```python
from client.websocket_client import WebSocketClient, ConnectionStatus

# 创建客户端
ws_client = WebSocketClient(server_url="http://127.0.0.1:8000")

# 注册回调
def on_connect():
    print("连接成功")

def on_disconnect():
    print("连接断开")

def on_message(data):
    print(f"收到消息: {data}")

def on_status_change(status: ConnectionStatus):
    print(f"状态变化: {status.value}")

ws_client.on_connect(on_connect)
ws_client.on_disconnect(on_disconnect)
ws_client.on_message(on_message)
ws_client.on_status_change(on_status_change)

# 连接
ws_client.connect(
    user_id=123,
    token="your-token",
    device_id="device-uuid",
    device_info={
        "device_name": "My Computer",
        "device_type": "desktop",
        "platform": "Windows",
        "os_version": "10",
    }
)

# 发送消息
ws_client.send_message(
    session_id="session-uuid",
    message="Hello",
    role="user",
    message_type="text"
)

# 断开连接
ws_client.disconnect()
```

### 3. 状态管理
```python
# 检查连接状态
if ws_client.is_connected():
    print("已连接")

# 获取当前状态
status = ws_client.get_status()
print(f"当前状态: {status.value}")
```

### 4. 消息回执
```python
# 发送已送达回执
ws_client.send_message_delivered(message_id=789, user_id=123)

# 发送已读回执
ws_client.send_message_read(message_id=789, user_id=123)
```

## 配置说明

### 服务端配置

在 `backend/api_server.py` 中：

```python
# WebSocket 管理器配置
ws_manager = WebSocketManager(socketio, db)
ws_manager.heartbeat_interval = 30  # 心跳间隔（秒）
ws_manager.heartbeat_timeout = 120  # 心跳超时（秒）
```

### 客户端配置

在创建 `WebSocketClient` 时：

```python
ws_client = WebSocketClient(server_url="http://127.0.0.1:8000")
ws_client.heartbeat_interval = 30  # 心跳间隔（秒）
ws_client.retry_interval = 5  # 重试间隔（秒）
ws_client.max_queue_size = 100  # 消息队列最大大小
```

## 性能优化建议

### 1. 使用 eventlet
```bash
pip install eventlet
```

在 `backend/api_server.py` 开头添加：
```python
import eventlet
eventlet.monkey_patch()
```

### 2. 调整心跳间隔
根据实际需求调整心跳间隔，减少不必要的网络开销：
- 稳定网络：30-60秒
- 不稳定网络：10-20秒
- 移动网络：20-30秒

### 3. 消息批量处理
对于高频消息场景，可以考虑批量推送：
```python
# 批量推送离线消息
messages = db.get_offline_messages(user_id, limit=100)
for msg in messages:
    ws_manager.send_message_to_user(user_id, 'new_message', msg)
```

### 4. 连接池管理
定期清理过期连接：
```python
# 每小时清理一次
db.cleanup_stale_connections(timeout_minutes=60)
```

## 故障排查

### 1. 连接失败
- 检查服务器是否启动
- 检查防火墙设置
- 检查 Token 是否有效

### 2. 消息未送达
- 检查接收方是否在线
- 检查离线消息表
- 检查消息队列

### 3. 心跳超时
- 检查网络连接
- 调整心跳间隔
- 检查服务器负载

### 4. 自动重连失败
- 检查重连配置
- 检查服务器可用性
- 查看客户端日志

## 最佳实践

1. **及时发送回执**：收到消息后立即发送已送达回执
2. **合理设置心跳**：根据网络环境调整心跳间隔
3. **处理离线消息**：用户上线后及时处理离线消息
4. **监控连接状态**：实时监控连接状态，及时处理异常
5. **日志记录**：记录关键操作日志，便于排查问题

## 后续优化方向

1. **消息加密**：对敏感消息进行端到端加密
2. **消息压缩**：对大消息进行压缩传输
3. **负载均衡**：支持多服务器负载均衡
4. **集群支持**：支持 Redis 等消息队列实现集群
5. **推送通知**：集成 APNs/FCM 实现离线推送

