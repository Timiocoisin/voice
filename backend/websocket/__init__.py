"""WebSocket 模块"""

# 只导出异步版本
try:
    from .async_websocket_manager import AsyncWebSocketManager
except ImportError:
    # 如果 python-socketio 未安装，跳过异步版本
    AsyncWebSocketManager = None

__all__ = ['AsyncWebSocketManager']

