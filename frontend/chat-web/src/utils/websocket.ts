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

export interface ReplyMessageInfo {
  id: number;
  message: string;
  message_type: 'text' | 'image' | 'file';
  is_recalled: boolean;
  from_user_id: number;
  from_username?: string;
  created_at?: string;
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
  reply_to_message?: ReplyMessageInfo;  // 引用消息的摘要信息（由服务端自动填充）
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
  onSessionListUpdated?: (data: { sessions: any[]; type: string }) => void;
  onNewPendingSession?: (data: { session: any }) => void;
  onPendingSessionAccepted?: (data: { session_id: string; agent_id: number }) => void;
  onAgentStatusChanged?: (data: { agent_id: number; status: string }) => void;
  onVipStatusUpdated?: (data: { user_id: number; vip_info: any }) => void;
  onDiamondBalanceUpdated?: (data: { user_id: number; balance: number }) => void;
  onUserProfileUpdated?: (data: { user_id: number; profile: any }) => void;
  onMessageEdited?: (data: { message_id: number; session_id: string; new_content: string; edited_at: string }) => void;
  onSessionStatusUpdated?: (data: { session_id: string; status: string; user_id: number; agent_id: number }) => void;
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

        // 判断被撤回的消息是否是自己发送的
        // fromUserId 是被撤回消息的发送者ID
        // 如果 fromUserId === this.userId，说明被撤回的消息是我自己发送的
        // 在客服端，客服发送的消息 from 是 'agent'，用户发送的消息 from 是 'user'
        // 在用户端，用户发送的消息 from 是 'user'，客服发送的消息 from 是 'agent'
        // 这里需要根据 fromUserId 来判断被撤回消息的发送者
        let fromField: 'agent' | 'user' = 'user';
        if (this.userId && fromUserId) {
          // 如果 fromUserId === this.userId，说明被撤回的消息是我自己发送的
          // 在客服端，this.userId 是客服ID，所以 from 应该是 'agent'
          // 在用户端，this.userId 是用户ID，所以 from 应该是 'user'
          // 但是，我们需要知道当前是客服端还是用户端
          // 由于 Web 端是客服端，所以如果 fromUserId === this.userId，from 应该是 'agent'
          if (fromUserId === this.userId) {
            fromField = 'agent';
          } else {
            fromField = 'user';
          }
        }

        // 推送给上层的统一消息结构
        const recalledMessage: WebSocketMessage = {
          id: messageId,
          session_id: data.session_id || '',
          from: fromField,
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

    // 会话列表更新
    this.socket.on('session_list_updated', (data: { sessions: any[]; type: string }) => {
      if (this.callbacks.onSessionListUpdated) {
        this.callbacks.onSessionListUpdated(data);
      }
    });

    // 新待接入会话
    this.socket.on('new_pending_session', (data: { session: any }) => {
      if (this.callbacks.onNewPendingSession) {
        this.callbacks.onNewPendingSession(data);
      }
    });

    // 待接入会话被接入
    this.socket.on('pending_session_accepted', (data: { session_id: string; agent_id: number }) => {
      if (this.callbacks.onPendingSessionAccepted) {
        this.callbacks.onPendingSessionAccepted(data);
      }
    });

    // 客服状态变化
    this.socket.on('agent_status_changed', (data: { agent_id: number; status: string }) => {
      if (this.callbacks.onAgentStatusChanged) {
        this.callbacks.onAgentStatusChanged(data);
      }
    });

    // VIP 状态更新
    this.socket.on('vip_status_updated', (data: { user_id: number; vip_info: any }) => {
      if (this.callbacks.onVipStatusUpdated) {
        this.callbacks.onVipStatusUpdated(data);
      }
    });

    // 钻石余额更新
    this.socket.on('diamond_balance_updated', (data: { user_id: number; balance: number }) => {
      if (this.callbacks.onDiamondBalanceUpdated) {
        this.callbacks.onDiamondBalanceUpdated(data);
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
    }, 20000); // 20秒：略微提高心跳频率，减少因为浏览器降频导致的误判掉线
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
  sendHeartbeat(): void {
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
   * 获取会话历史消息（通过 WebSocket）
   * @param sessionId 会话ID
   * @param limit 返回消息数量限制（默认200）
   */
  getSessionMessages(
    sessionId: string,
    limit: number = 200
  ): Promise<{
    success: boolean;
    messages: WebSocketMessage[];
    message?: string;
  }> {
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
        user_id: this.userId,
        token: this.token,
        limit: limit,
      };

      this.socket.emit('get_session_messages', data, (response: any) => {
        if (response && response.success) {
          resolve({
            success: true,
            messages: response.messages || [],
          });
        } else {
          reject(new Error(response?.message || '获取消息失败'));
        }
      });
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
   * 订阅会话列表
   */
  subscribeSessions(type: 'my' | 'pending'): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('subscribe_sessions', {
        user_id: this.userId,
        token: this.token,
        type: type
      }, (response: any) => {
        if (response && response.success) {
          console.log(`订阅会话列表成功: type=${type}`);
          resolve();
        } else {
          reject(new Error(response?.message || '订阅失败'));
        }
      });
    });
  }

  /**
   * 订阅待接入会话
   */
  subscribePendingSessions(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('subscribe_pending_sessions', {
        user_id: this.userId,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log('订阅待接入会话成功');
          resolve();
        } else {
          reject(new Error(response?.message || '订阅失败'));
        }
      });
    });
  }

  /**
   * 更新客服状态
   */
  updateAgentStatus(status: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('update_agent_status', {
        user_id: this.userId,
        status: status,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log(`更新客服状态成功: ${status}`);
          resolve();
        } else {
          reject(new Error(response?.message || '更新状态失败'));
        }
      });
    });
  }

  /**
   * 订阅 VIP 信息
   */
  subscribeVipInfo(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('subscribe_vip_info', {
        user_id: this.userId,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log('订阅 VIP 信息成功');
          resolve();
        } else {
          reject(new Error(response?.message || '订阅失败'));
        }
      });
    });
  }

  /**
   * 订阅用户资料更新
   */
  subscribeUserProfile(): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('subscribe_user_profile', {
        user_id: this.userId,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log('订阅用户资料成功');
          resolve();
        } else {
          reject(new Error(response?.message || '订阅失败'));
        }
      });
    });
  }

  /**
   * 编辑消息
   */
  editMessage(messageId: number, sessionId: string, newContent: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('edit_message', {
        message_id: messageId,
        user_id: this.userId,
        session_id: sessionId,
        new_content: newContent,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log('消息编辑成功');
          resolve();
        } else {
          reject(new Error(response?.message || '编辑失败'));
        }
      });
    });
  }

  /**
   * 关闭会话
   */
  closeSession(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit('close_session', {
        session_id: sessionId,
        user_id: this.userId,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log('会话关闭成功');
          resolve();
        } else {
          reject(new Error(response?.message || '关闭失败'));
        }
      });
    });
  }

  /**
   * 匹配在线客服（用户侧）
   */
  matchAgent(sessionId: string): Promise<{
    success: boolean;
    matched: boolean;
    agent_id?: number;
    agent_name?: string;
    message?: string;
  }> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit(
        'match_agent',
        {
          session_id: sessionId,
          user_id: this.userId,
          token: this.token,
        },
        (response: any) => {
          if (response && response.success !== undefined) {
            resolve(response);
          } else {
            reject(new Error(response?.message || '匹配失败'));
          }
        }
      );
    });
  }

  /**
   * 接入待接入会话（客服侧）
   */
  acceptSession(sessionId: string): Promise<{
    success: boolean;
    message?: string;
  }> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit(
        'accept_session',
        {
          session_id: sessionId,
          user_id: this.userId,
          token: this.token,
        },
        (response: any) => {
          if (response && response.success) {
            resolve(response);
          } else {
            reject(new Error(response?.message || '接入失败'));
          }
        }
      );
    });
  }

  /**
   * 获取链接预览（富文本相关）
   */
  getLinkPreview(url: string): Promise<{
    success: boolean;
    preview?: any;
    message?: string;
  }> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit(
        'link_preview',
        {
          url,
          token: this.token,
        },
        (response: any) => {
          if (response && response.success) {
            resolve(response);
          } else {
            reject(new Error(response?.message || '获取链接预览失败'));
          }
        }
      );
    });
  }

  /**
   * 处理富文本（交给服务端，便于一致化处理）
   */
  processRichText(
    content: string
  ): Promise<{
    success: boolean;
    html: string;
    is_rich: boolean;
    urls: string[];
    mentions: any[];
    message?: string;
  }> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      this.socket.emit(
        'process_rich_text',
        {
          content,
          user_id: this.userId,
          token: this.token,
        },
        (response: any) => {
          if (response && response.success) {
            resolve(response);
          } else {
            reject(new Error(response?.message || '处理富文本失败'));
          }
        }
      );
    });
  }

  /**
   * 撤回消息
   */
  recallMessage(messageId: number): Promise<void> {
    return new Promise((resolve, reject) => {
      if (!this.socket || !this.userId || !this.token) {
        reject(new Error('未连接或未登录'));
        return;
      }

      if (this.status !== ConnectionStatus.CONNECTED) {
        reject(new Error('WebSocket 未连接'));
        return;
      }

      this.socket.emit('recall_message', {
        message_id: messageId,
        user_id: this.userId,
        token: this.token
      }, (response: any) => {
        if (response && response.success) {
          console.log('撤回消息成功');
          resolve();
        } else {
          reject(new Error(response?.message || '撤回失败'));
        }
      });
    });
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

