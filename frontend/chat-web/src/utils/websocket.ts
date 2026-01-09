/**
 * WebSocket 客户端工具
 * 提供 WebSocket 连接、消息发送、消息接收等功能
 */

import { io, Socket } from 'socket.io-client';

const SERVER_URL = 'http://127.0.0.1:8000';

export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

export interface WebSocketMessage {
  id: string;
  session_id: string;
  from: 'user' | 'agent';
  from_user_id: number;
  to_user_id?: number;
  text: string;
  time: string;
  avatar?: string;
  message_type?: 'text' | 'image' | 'file';
  reply_to_message_id?: number;
  status?: 'sent' | 'delivered' | 'read';
  is_recalled?: boolean;
  username?: string;
  is_from_self?: boolean;  // 服务端提供的标记，表示是否是自己发送的消息
}

export interface WebSocketClientCallbacks {
  onConnect?: () => void;
  onDisconnect?: () => void;
  onMessage?: (message: WebSocketMessage) => void;
  onStatusChange?: (status: ConnectionStatus) => void;
  onError?: (error: any) => void;
  onMessageStatus?: (data: { message_id: string; status: string; timestamp: string }) => void;
}

class WebSocketClient {
  private socket: Socket | null = null;
  private status: ConnectionStatus = ConnectionStatus.DISCONNECTED;
  private connectionId: string = '';
  private userId: number | null = null;
  private token: string | null = null;
  private callbacks: WebSocketClientCallbacks = {};
  private heartbeatInterval: number | null = null;
  private receivedMessageIds = new Set<string>();
  private maxReceivedIds = 1000;

  constructor() {
    // 生成连接ID
    this.connectionId = this.generateConnectionId();
  }

  private generateConnectionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 连接到服务器
   */
  connect(userId: number, token: string, deviceInfo?: any): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.status === ConnectionStatus.CONNECTED || this.status === ConnectionStatus.CONNECTING) {
        console.warn('WebSocket 已经连接或正在连接中');
        resolve();
        return;
      }

      this.userId = userId;
      this.token = token;

      this.updateStatus(ConnectionStatus.CONNECTING);
      console.log('正在连接到 WebSocket 服务器...');

      // 创建 Socket.IO 客户端
      this.socket = io(SERVER_URL, {
        transports: ['websocket', 'polling'],
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 10000,
      });

      // 连接成功
      this.socket.on('connect', () => {
        console.log('WebSocket 连接成功');
        this.updateStatus(ConnectionStatus.CONNECTED);
        
        // 注册连接
        this.registerConnection(deviceInfo)
          .then(() => {
            this.startHeartbeat();
            if (this.callbacks.onConnect) {
              this.callbacks.onConnect();
            }
            resolve();
          })
          .catch((error) => {
            console.error('注册连接失败:', error);
            reject(error);
          });
      });

      // 连接断开
      this.socket.on('disconnect', () => {
        console.warn('WebSocket 连接断开');
        this.updateStatus(ConnectionStatus.DISCONNECTED);
        this.stopHeartbeat();
        if (this.callbacks.onDisconnect) {
          this.callbacks.onDisconnect();
        }
      });

      // 连接错误
      this.socket.on('connect_error', (error: any) => {
        console.error('WebSocket 连接错误:', error);
        this.updateStatus(ConnectionStatus.ERROR);
        if (this.callbacks.onError) {
          this.callbacks.onError(error);
        }
        reject(error);
      });

      // 重连中
      this.socket.io.on('reconnect_attempt', () => {
        console.log('WebSocket 重连中...');
        this.updateStatus(ConnectionStatus.RECONNECTING);
      });

      // 注册消息事件
      this.registerMessageEvents();
    });
  }

  /**
   * 注册 WebSocket 连接
   */
  private registerConnection(deviceInfo?: any): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或缺少必要参数'));
        return;
      }

      const data = {
        user_id: this.userId,
        token: this.token,
        connection_id: this.connectionId,
        device_id: this.getDeviceId(),
        device_info: deviceInfo || this.getDefaultDeviceInfo(),
      };

      this.socket.emit('register', data, (response: any) => {
        if (response && response.success) {
          console.log('WebSocket 连接注册成功');
          resolve();
        } else {
          reject(new Error(response?.message || '注册失败'));
        }
      });
    });
  }

  /**
   * 注册消息事件
   */
  private registerMessageEvents(): void {
    if (!this.socket) return;

    // 收到新消息
    this.socket.on('new_message', (data: WebSocketMessage) => {
      const messageId = data.id;
      
      // 消息去重
      if (messageId && this.receivedMessageIds.has(messageId)) {
        console.debug(`忽略重复消息: ${messageId}`);
        return;
      }

      if (messageId) {
        this.receivedMessageIds.add(messageId);
        // 限制集合大小
        if (this.receivedMessageIds.size > this.maxReceivedIds) {
          const idsArray = Array.from(this.receivedMessageIds);
          this.receivedMessageIds = new Set(idsArray.slice(this.maxReceivedIds / 2));
        }
      }

      console.log('收到新消息:', data);

      // 调用回调
      if (this.callbacks.onMessage) {
        this.callbacks.onMessage(data);
      }
    });

    // 消息状态更新（当前不在前端 UI 中展示，仅记录日志）
    this.socket.on('message_status', (data: { message_id: string; status: string; timestamp: string }) => {
      console.debug(`消息 ${data.message_id} 状态更新: ${data.status}`);
    });

    // 撤回消息事件：后端通过 message_recalled 推送
    this.socket.on('message_recalled', (data: any) => {
      try {
        const rawId = data.message_id ?? data.id;
        if (!rawId) {
          return;
        }

        const messageId = String(rawId);
        const fromUserId: number | undefined = data.from_user_id;

        // 推送给上层的统一消息结构
        const recalledMessage: WebSocketMessage = {
          id: messageId,
          session_id: data.session_id || '',
          from: this.userId && fromUserId === this.userId ? 'agent' : 'user',
          from_user_id: fromUserId || 0,
          to_user_id: undefined,
          text: '',
          time: data.time || '',
          avatar: undefined,
          message_type: 'text',
          reply_to_message_id: undefined,
          status: undefined,
          is_recalled: true,
          username: data.username,
        };

        // 直接复用 onMessage 回调，让上层根据 is_recalled 更新 UI（包括引用块）
        if (this.callbacks.onMessage) {
          this.callbacks.onMessage(recalledMessage);
        }
      } catch (e) {
        console.error('处理撤回消息事件失败:', e);
      }
    });
  }

  /**
   * 启动心跳
   */
  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatInterval = window.setInterval(() => {
      if (this.status === ConnectionStatus.CONNECTED) {
        this.sendHeartbeat();
      }
    }, 30000); // 30秒
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 发送心跳
   */
  private sendHeartbeat(): void {
    if (!this.socket) return;

    this.socket.emit('heartbeat', { connection_id: this.connectionId }, (response: any) => {
      if (!response || !response.success) {
        console.warn('心跳失败:', response?.message);
      }
    });
  }

  /**
   * 发送消息
   */
  sendMessage(
    sessionId: string,
    message: string,
    role: 'user' | 'agent' = 'agent',
    messageType: 'text' | 'image' | 'file' = 'text',
    replyToMessageId?: number
  ): Promise<{ success: boolean; message_id?: number; time?: string; message?: string }> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      if (this.status !== ConnectionStatus.CONNECTED) {
        reject(new Error('WebSocket 未连接'));
        return;
      }

      const data = {
        session_id: sessionId,
        from_user_id: this.userId,
        message: message,
        role: role,
        token: this.token,
        message_type: messageType,
      };

      if (replyToMessageId) {
        data.reply_to_message_id = replyToMessageId;
      }

      this.socket.emit('send_message', data, (response: any) => {
        if (response && response.success) {
          resolve({
            success: true,
            message_id: response.message_id,
            time: response.time,
          });
        } else {
          reject(new Error(response?.message || '发送失败'));
        }
      });
    });
  }

  /**
   * 发送消息已送达回执
   */
  sendMessageDelivered(messageId: number, userId: number): void {
    if (!this.socket) return;

    this.socket.emit('message_delivered', {
      message_id: messageId,
      user_id: userId,
    });
  }

  /**
   * 发送消息已读回执
   */
  sendMessageRead(messageId: number, userId: number): void {
    if (!this.socket) return;

    this.socket.emit('message_read', {
      message_id: messageId,
      user_id: userId,
    });
  }

  /**
   * 断开连接
   */
  disconnect(): void {
    console.log('正在断开 WebSocket 连接...');
    
    this.stopHeartbeat();
    
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    
    this.updateStatus(ConnectionStatus.DISCONNECTED);
    console.log('WebSocket 已断开');
  }

  /**
   * 注册回调函数
   */
  on(event: keyof WebSocketClientCallbacks, callback: any): void {
    this.callbacks[event] = callback;
  }

  /**
   * 更新连接状态
   */
  private updateStatus(status: ConnectionStatus): void {
    if (this.status !== status) {
      const oldStatus = this.status;
      this.status = status;
      console.log(`连接状态变化: ${oldStatus} -> ${status}`);
      
      if (this.callbacks.onStatusChange) {
        this.callbacks.onStatusChange(status);
      }
    }
  }

  /**
   * 获取连接状态
   */
  getStatus(): ConnectionStatus {
    return this.status;
  }

  /**
   * 是否已连接
   */
  isConnected(): boolean {
    return this.status === ConnectionStatus.CONNECTED;
  }

  /**
   * 获取设备ID
   */
  private getDeviceId(): string {
    let deviceId = localStorage.getItem('device_id');
    if (!deviceId) {
      deviceId = `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('device_id', deviceId);
    }
    return deviceId;
  }

  /**
   * 获取默认设备信息
   */
  private getDefaultDeviceInfo(): any {
    return {
      device_name: navigator.userAgent,
      device_type: 'web',
      platform: navigator.platform,
      browser: this.getBrowserInfo(),
      os_version: navigator.platform,
    };
  }

  /**
   * 获取浏览器信息
   */
  private getBrowserInfo(): string {
    const ua = navigator.userAgent;
    if (ua.includes('Chrome')) return 'Chrome';
    if (ua.includes('Firefox')) return 'Firefox';
    if (ua.includes('Safari')) return 'Safari';
    if (ua.includes('Edge')) return 'Edge';
    return 'Unknown';
  }
}

// 导出单例实例
export const websocketClient = new WebSocketClient();

