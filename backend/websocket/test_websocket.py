"""
WebSocket 功能测试脚本

测试 WebSocket 连接、消息推送、心跳检测等功能。
"""

import sys
import os
import time
import logging

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from client.websocket_client import WebSocketClient, ConnectionStatus

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_basic_connection():
    """测试基本连接"""
    logger.info("=" * 50)
    logger.info("测试 1: 基本连接")
    logger.info("=" * 50)
    
    # 创建客户端
    ws_client = WebSocketClient(server_url="http://127.0.0.1:8000")
    
    # 注册回调
    connected = False
    
    def on_connect():
        nonlocal connected
        connected = True
        logger.info("✅ 连接成功")
    
    def on_disconnect():
        logger.info("⚠️  连接断开")
    
    def on_status_change(status: ConnectionStatus):
        logger.info(f"📊 状态变化: {status.value}")
    
    ws_client.on_connect(on_connect)
    ws_client.on_disconnect(on_disconnect)
    ws_client.on_status_change(on_status_change)
    
    try:
        # 连接（需要有效的 user_id 和 token）
        # 这里使用测试数据，实际使用时需要真实的认证信息
        ws_client.connect(
            user_id=1,
            token="test-token",
            device_id="test-device",
            device_info={
                "device_name": "Test Device",
                "device_type": "desktop",
                "platform": "Windows",
                "os_version": "10",
            }
        )
        
        # 等待连接
        timeout = 10
        start_time = time.time()
        while not connected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if connected:
            logger.info("✅ 测试通过：连接成功")
            
            # 保持连接一段时间测试心跳
            logger.info("保持连接 10 秒测试心跳...")
            time.sleep(10)
            
            # 断开连接
            ws_client.disconnect()
            logger.info("✅ 测试通过：断开连接成功")
        else:
            logger.error("❌ 测试失败：连接超时")
        
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}", exc_info=True)


def test_message_sending():
    """测试消息发送"""
    logger.info("=" * 50)
    logger.info("测试 2: 消息发送")
    logger.info("=" * 50)
    
    ws_client = WebSocketClient(server_url="http://127.0.0.1:8000")
    
    connected = False
    message_received = False
    
    def on_connect():
        nonlocal connected
        connected = True
        logger.info("✅ 连接成功")
    
    def on_message(data):
        nonlocal message_received
        message_received = True
        logger.info(f"📨 收到消息: {data.get('text', '')}")
    
    ws_client.on_connect(on_connect)
    ws_client.on_message(on_message)
    
    try:
        # 连接
        ws_client.connect(
            user_id=1,
            token="test-token",
            device_id="test-device"
        )
        
        # 等待连接
        timeout = 10
        start_time = time.time()
        while not connected and time.time() - start_time < timeout:
            time.sleep(0.1)
        
        if connected:
            # 发送消息
            logger.info("发送测试消息...")
            success = ws_client.send_message(
                session_id="test-session",
                message="Hello, WebSocket!",
                role="user",
                message_type="text"
            )
            
            if success:
                logger.info("✅ 测试通过：消息发送成功")
            else:
                logger.warning("⚠️  消息发送失败（可能需要有效的会话）")
            
            # 等待接收消息
            time.sleep(5)
            
            ws_client.disconnect()
        else:
            logger.error("❌ 测试失败：连接超时")
    
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}", exc_info=True)


def test_reconnection():
    """测试自动重连"""
    logger.info("=" * 50)
    logger.info("测试 3: 自动重连")
    logger.info("=" * 50)
    
    ws_client = WebSocketClient(server_url="http://127.0.0.1:8000")
    
    reconnected = False
    
    def on_connect():
        logger.info("✅ 连接成功")
    
    def on_disconnect():
        logger.info("⚠️  连接断开，等待重连...")
    
    def on_status_change(status: ConnectionStatus):
        nonlocal reconnected
        logger.info(f"📊 状态变化: {status.value}")
        if status == ConnectionStatus.RECONNECTING:
            reconnected = True
    
    ws_client.on_connect(on_connect)
    ws_client.on_disconnect(on_disconnect)
    ws_client.on_status_change(on_status_change)
    
    try:
        # 连接
        ws_client.connect(
            user_id=1,
            token="test-token",
            device_id="test-device"
        )
        
        # 等待连接
        time.sleep(5)
        
        if ws_client.is_connected():
            logger.info("手动断开连接以测试重连...")
            ws_client.sio.disconnect()
            
            # 等待重连
            logger.info("等待自动重连...")
            time.sleep(15)
            
            if reconnected:
                logger.info("✅ 测试通过：检测到重连尝试")
            else:
                logger.warning("⚠️  未检测到重连尝试")
            
            ws_client.disconnect()
        else:
            logger.error("❌ 测试失败：初始连接失败")
    
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}", exc_info=True)


def test_message_queue():
    """测试消息队列"""
    logger.info("=" * 50)
    logger.info("测试 4: 消息队列")
    logger.info("=" * 50)
    
    ws_client = WebSocketClient(server_url="http://127.0.0.1:8000")
    
    try:
        # 不连接，直接发送消息（应该加入队列）
        logger.info("在未连接状态下发送消息...")
        success = ws_client.send_message(
            session_id="test-session",
            message="Queued message",
            role="user"
        )
        
        if not success:
            logger.info("✅ 消息发送失败（预期行为）")
            
            # 检查队列
            with ws_client.queue_lock:
                queue_size = len(ws_client.message_queue)
            
            if queue_size > 0:
                logger.info(f"✅ 测试通过：消息已加入队列（队列大小: {queue_size}）")
            else:
                logger.warning("⚠️  消息未加入队列")
        else:
            logger.warning("⚠️  消息发送成功（不符合预期）")
    
    except Exception as e:
        logger.error(f"❌ 测试失败：{e}", exc_info=True)


def main():
    """运行所有测试"""
    logger.info("开始 WebSocket 功能测试")
    logger.info("=" * 50)
    logger.info("注意：这些测试需要后端服务器运行在 http://127.0.0.1:8000")
    logger.info("=" * 50)
    
    try:
        # 测试 1：基本连接
        test_basic_connection()
        time.sleep(2)
        
        # 测试 2：消息发送
        test_message_sending()
        time.sleep(2)
        
        # 测试 3：自动重连
        # test_reconnection()  # 这个测试需要较长时间，可以选择性运行
        # time.sleep(2)
        
        # 测试 4：消息队列
        test_message_queue()
        
        logger.info("=" * 50)
        logger.info("所有测试完成")
        logger.info("=" * 50)
    
    except KeyboardInterrupt:
        logger.info("测试被用户中断")
    except Exception as e:
        logger.error(f"测试异常: {e}", exc_info=True)


if __name__ == "__main__":
    main()

