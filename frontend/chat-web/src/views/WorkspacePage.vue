<template>
  <div class="workspace">
    <header class="workspace-header">
      <div class="brand">
        <span class="brand-logo">VC</span>
        <span class="brand-name">变声器客服工作台</span>
      </div>
      <div class="header-actions">
        <span class="agent-name">客服：{{ currentUser?.username || '未登录' }}</span>
        <div class="status-container" @click.stop="toggleStatusMenu">
          <div class="status-indicator">
            <span 
              class="status-dot breathing" 
              :class="currentStatus.type"
              :style="getStatusStyle(currentStatus)"
            ></span>
            <span class="status-text">{{ currentStatus.label }}</span>
            <svg class="status-arrow" :class="{ open: showStatusMenu }" width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M3 4.5L6 7.5L9 4.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div v-if="showStatusMenu" class="status-menu">
            <div
              v-for="status in statusOptions"
              :key="status.type"
              class="status-menu-item"
              :class="{ active: currentStatus.type === status.type }"
              @click.stop="changeStatus(status)"
            >
              <span class="status-menu-dot" :class="status.type"></span>
              <span>{{ status.label }}</span>
            </div>
          </div>
        </div>
        <button class="logout-btn" @click="handleLogout">退出</button>
      </div>
    </header>

    <div class="workspace-body">
      <!-- 左侧：会话列表 -->
      <aside class="sidebar sessions">
        <div class="sidebar-header">
          <h2>会话队列</h2>
          <div class="tabs">
            <button 
              class="tab" 
              :class="{ active: activeTab === 'my' }"
              @click="switchTab('my')"
            >
              我的会话
            </button>
            <button 
              class="tab" 
              :class="{ active: activeTab === 'pending' }"
              @click="switchTab('pending')"
            >
              待接入
              <span v-if="pendingCount > 0" class="tab-badge">{{ pendingCount }}</span>
            </button>
          </div>
        </div>
        <ul class="session-list">
          <li
            v-for="session in filteredSessions"
            :key="session.id"
            :class="['session-item', { active: session.id === activeSessionId }]"
            @click="selectSession(session.id)"
          >
            <div class="session-top">
              <span class="session-user">
                {{ session.userName }}
                <span v-if="session.isVip" class="vip-tag">VIP</span>
              </span>
              <span class="session-time">{{ session.lastTime }}</span>
            </div>
            <div class="session-middle">
              <span class="session-tag">{{ session.category }}</span>
            </div>
            <div class="session-bottom">
              <span class="session-preview">{{ session.lastMessage }}</span>
              <span v-if="session.unread > 0" class="unread-badge">
                {{ session.unread }}
              </span>
            </div>
          </li>
        </ul>
      </aside>

      <!-- 中间：聊天面板 -->
      <main class="chat-main" v-if="activeSession">
        <header class="chat-header">
          <div>
            <div class="chat-user">
              {{ activeSession.userName }}
              <span v-if="activeSession.isVip" class="vip-tag">VIP</span>
            </div>
            <div class="chat-meta">
              问题类型：{{ activeSession.category }} · 会话时长：{{ activeSession.duration }}
            </div>
          </div>
          <button 
            v-if="activeSession.status !== 'closed'"
            class="close-session-btn"
            @click="handleCloseSession"
            title="关闭会话"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 4L4 12M4 4L12 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            关闭会话
          </button>
        </header>

        <div class="chat-messages" ref="messagesRef">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['msg-row', msg.from === 'agent' ? 'from-agent' : 'from-user', msg.isRecalled ? 'recalled-row' : '']"
            @contextmenu.prevent="showMessageContextMenu($event, msg)"
          >
            <!-- 撤回消息：只显示居中灰色小字，不显示气泡和头像 -->
            <template v-if="msg.isRecalled">
              <div class="recalled-message" style="text-align: center; color: #9ca3af; font-size: 11px; padding: 4px 0; width: 100%;">
                {{ msg.userId === currentUser?.id ? '你' : (msg.fromUsername || '用户') }}撤回了一条消息
              </div>
            </template>
            <!-- 正常消息：显示头像和气泡 -->
            <template v-else>
              <div class="msg-avatar">
                <img 
                  v-if="msg.avatar" 
                  :src="msg.avatar" 
                  :alt="msg.from === 'agent' ? '客服' : '用户'"
                  @error="handleAvatarError"
                />
                <span v-else>{{ msg.from === 'agent' ? '客' : '用' }}</span>
              </div>
              <div 
                class="msg-bubble" 
                :class="{ 'editable': msg.userId === currentUser?.id && msg.messageType === 'text' && !msg.isRecalled && !msg.isEdited && canEditMessage(msg) }"
              >
                <div class="msg-text">
                  <template v-if="msg.messageType === 'image'">
                    <img 
                      class="msg-image" 
                      :src="msg.text" 
                      alt="图片" 
                      @click="openImagePreview(msg.text)"
                      style="cursor: pointer;"
                    />
                  </template>
                  <template v-else-if="msg.messageType === 'file'">
                    <div class="file-message-card" @click="downloadFile(msg)">
                      <div class="file-icon">
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M14 2H6C5.46957 2 4.96086 2.21071 4.58579 2.58579C4.21071 2.96086 4 3.46957 4 4V20C4 20.5304 4.21071 21.0391 4.58579 21.4142C4.96086 21.7893 5.46957 22 6 22H18C18.5304 22 19.0391 21.7893 19.4142 21.4142C19.7893 21.0391 20 20.5304 20 20V8L14 2Z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                          <path d="M14 2V8H20" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </div>
                      <div class="file-info">
                        <div class="file-name">{{ extractFileName(msg.text, msg.id) }}</div>
                        <div class="file-size">{{ extractFileSize(msg.text) }}</div>
                      </div>
                      <div class="file-download-icon">
                        <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                          <path d="M8 11V1M8 11L4 7M8 11L12 7M2 14H14" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                        </svg>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    <!-- 引用消息显示（毛玻璃风格） -->
                    <div 
                      v-if="msg.replyToMessage" 
                      class="reply-message-preview"
                    >
                      <!-- 如果是图片消息，显示缩略图 -->
                      <div v-if="msg.replyToMessageType === 'image' && msg.replyToMessage && msg.replyToMessage.startsWith('data:image')" class="reply-image-container">
                        <span class="reply-sender-name">{{ (msg.replyToUsername || '用户') }}:</span>
                        <img 
                          :src="msg.replyToMessage" 
                          alt="引用图片"
                          class="reply-image-thumbnail"
                          @error="(e) => { e.target.style.display = 'none'; }"
                        />
                      </div>
                      <!-- 文本消息或其他类型 -->
                      <div v-else class="reply-text">
                        <span class="reply-sender-name">{{ (msg.replyToUsername || '用户') }}:</span>
                        <span class="reply-content">{{ msg.replyToMessage === '该引用消息已被撤回' ? '该引用消息已被撤回' : (msg.replyToMessage.length > 50 ? msg.replyToMessage.substring(0, 50) + '...' : msg.replyToMessage) }}</span>
                      </div>
                    </div>
                    <!-- 消息内容 -->
                    <div>
                      <div 
                        v-if="msg.isRich && msg.richText" 
                        class="rich-text-content" 
                        v-html="msg.richText"
                      ></div>
                      <span v-else>{{ msg.text }}</span>
                      <span v-if="msg.isEdited" class="edited-badge">已编辑</span>
                    </div>
                    <!-- 链接预览卡片 -->
                    <div v-if="msg.linkUrls && msg.linkUrls.length > 0" class="link-preview-container">
                      <div 
                        v-for="(url, index) in msg.linkUrls.slice(0, 1)" 
                        :key="index"
                        class="link-preview-card"
                        @click="openLink(url)"
                      >
                        <div class="link-preview-title">链接预览</div>
                        <div class="link-preview-url">{{ getUrlDisplay(url) }}</div>
                      </div>
                    </div>
                  </template>
                </div>
                <div class="msg-time">{{ msg.time }}</div>
              </div>
            </template>
          </div>
        </div>

        <!-- 编辑消息模态框 -->
        <div v-if="editingMessage" class="edit-message-modal">
          <div class="edit-message-dialog">
            <div class="edit-message-header">
              <h3>编辑消息</h3>
              <button @click="cancelEditMessage" class="close-btn">×</button>
            </div>
            <div class="edit-message-body">
              <textarea
                v-model="editingContent"
                class="edit-message-input"
                placeholder="编辑消息内容"
                rows="4"
                ref="editMessageInputRef"
              ></textarea>
            </div>
            <div class="edit-message-footer">
              <button @click="cancelEditMessage" class="cancel-btn">取消</button>
              <button @click="saveEditedMessage" class="save-btn">保存</button>
            </div>
          </div>
        </div>

        <form class="chat-input-area" @submit.prevent="handleSend">
          <textarea
            v-model="inputText"
            class="chat-input"
            placeholder="请输入回复内容，Enter 发送，Shift+Enter 换行"
            @keydown.enter.exact.prevent="handleSend"
            @keydown.shift.enter.stop
          />
          <div class="chat-input-toolbar">
            <div class="toolbar-left">
              <button
                type="button"
                class="toolbar-icon-btn"
                title="表情"
                @click="toggleEmojiPanel"
              >
                😊
              </button>
              <button
                type="button"
                class="toolbar-icon-btn"
                title="发送图片"
                @click="triggerImageSelect"
              >
                🖼
              </button>
              <button type="button" class="toolbar-btn">
                常用回复
              </button>
            </div>
            <div class="toolbar-spacer" />
            <button type="submit" class="primary-button" :disabled="!inputText.trim()">
              发送
            </button>
          </div>
        </form>
        <div v-if="emojiPanelVisible" class="emoji-panel">
          <button
            v-for="emoji in emojis"
            :key="emoji"
            type="button"
            class="emoji-item"
            @click="insertEmoji(emoji)"
          >
            {{ emoji }}
          </button>
        </div>
        <input
          ref="imageInputRef"
          type="file"
          accept="image/*"
          style="display: none"
          @change="handleImageChange"
        />
      </main>

      <!-- 右侧：用户信息 / 快捷回复 -->
      <aside class="sidebar detail" v-if="activeSession">
        <div class="sidebar-header">
          <h2>用户信息</h2>
        </div>
        <div class="detail-section">
          <div class="detail-row">
            <span class="label">账号</span>
            <span class="value">{{ activeSession.userName }}</span>
          </div>
          <div class="detail-row">
            <span class="label">VIP 状态</span>
            <span class="value">{{ activeSession.isVip ? '已开通' : '未开通' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">系统</span>
            <span class="value">Windows 11</span>
          </div>
          <div class="detail-row">
            <span class="label">变声器版本</span>
            <span class="value">v1.2.3</span>
          </div>
          <div class="detail-row">
            <span class="label">虚拟声卡</span>
            <span class="value success">已安装</span>
          </div>
        </div>

        <div class="sidebar-header mt">
          <h2>快捷回复</h2>
        </div>
        <ul class="quick-reply-list">
          <li
            v-for="item in quickReplies"
            :key="item.id"
            class="quick-reply-item"
            @click="appendQuickReply(item.content)"
          >
            <div class="qr-title">{{ item.title }}</div>
            <div class="qr-preview">{{ item.preview }}</div>
            <div class="qr-tag">{{ item.tag }}</div>
          </li>
        </ul>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { customerServiceApi } from '@/api/client';
import { processRichText, extractUrlsFromText } from '@/utils/richText';
import { websocketClient, ConnectionStatus, WebSocketMessage } from '@/utils/websocket';

const router = useRouter();

interface Session {
  id: string;
  userName: string;
  userId?: number;
  isVip: boolean;
  category: string;
  lastMessage: string;
  lastTime: string;
  duration: string;
  unread: number;
  avatar?: string;
  status?: string; // 会话状态：pending, active, closed
}

interface ChatMessage {
  id: string;
  from: 'user' | 'agent';
  text: string;
  time: string;
  userId?: number;
  avatar?: string;
  messageType?: 'text' | 'image' | 'file';
  richText?: string; // 富文本HTML
  isRich?: boolean; // 是否为富文本
  linkUrls?: string[]; // 链接URL列表（用于预览）
  isRecalled?: boolean; // 是否已撤回
  isEdited?: boolean; // 是否已编辑
  editedAt?: string; // 编辑时间
  reply_to_message_id?: number | null; // 引用消息ID
  replyToMessage?: string; // 引用消息内容（用于显示）
  replyToMessageType?: 'text' | 'image' | 'file'; // 引用消息类型
  created_at?: string; // 创建时间（用于判断撤回时限）
  fromUsername?: string; // 发送者用户名（用于撤回提示）
}

interface QuickReply {
  id: string;
  title: string;
  preview: string;
  tag: string;
  content: string;
}

const currentUser = ref<any>(null);
const token = ref<string>('');
const sessions = ref<Session[]>([]);
const messages = ref<ChatMessage[]>([]);
const loading = ref(false);
const pendingCount = ref<number>(0);
const replyToMessageId = ref<number | null>(null); // 引用消息ID
const replyToMessageText = ref<string | null>(null); // 引用消息内容
const replyToMessageUsername = ref<string | null>(null); // 引用消息的发送者用户名

// WebSocket：已接收消息ID集合（用于去重）
const receivedMessageIds = new Set<string>();

// 状态管理
type StatusType = 'online' | 'offline' | 'away' | 'busy';

interface StatusOption {
  type: StatusType;
  label: string;
  color: string;
  shadowColor: string;
  animationDuration: string;
}

const statusOptions: StatusOption[] = [
  {
    type: 'online',
    label: '在线',
    color: '#27c346',
    shadowColor: 'rgba(39, 195, 70, 0.4)',
    animationDuration: '2s'
  },
  {
    type: 'offline',
    label: '离线',
    color: '#9ca3af',
    shadowColor: 'rgba(156, 163, 175, 0.3)',
    animationDuration: '3s'
  },
  {
    type: 'away',
    label: '有事',
    color: '#f59e0b',
    shadowColor: 'rgba(245, 158, 11, 0.4)',
    animationDuration: '2.5s'
  },
  {
    type: 'busy',
    label: '繁忙',
    color: '#ef4444',
    shadowColor: 'rgba(239, 68, 68, 0.4)',
    animationDuration: '1.5s'
  }
];

const currentStatus = ref<StatusOption>(statusOptions[0]);
const showStatusMenu = ref(false);

// 从 localStorage 加载保存的状态
const loadSavedStatus = () => {
  const saved = localStorage.getItem('agent_status');
  if (saved) {
    const status = statusOptions.find(s => s.type === saved);
    if (status) {
      currentStatus.value = status;
    }
  }
};

// 保存状态到 localStorage
const saveStatus = (status: StatusType) => {
  localStorage.setItem('agent_status', status);
};

// 切换状态菜单
const toggleStatusMenu = () => {
  showStatusMenu.value = !showStatusMenu.value;
};

// 切换状态
const changeStatus = async (status: StatusOption) => {
  currentStatus.value = status;
  saveStatus(status.type);
  showStatusMenu.value = false;
  
  // 通过 WebSocket 更新后端状态
  if (websocketClient.isConnected() && currentUser.value && token.value) {
    try {
      await websocketClient.updateAgentStatus(status.type);
    } catch (error) {
      console.error('更新状态失败:', error);
    }
  }
};

// 获取状态样式
const getStatusStyle = (status: StatusOption) => {
  return {
    '--status-color': status.color,
    '--status-shadow': status.shadowColor,
    '--animation-duration': status.animationDuration
  } as any;
};

// 点击外部关闭菜单 / 面板
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  // 关闭状态菜单
  if (!target.closest('.status-container')) {
    showStatusMenu.value = false;
  }
  // 关闭表情面板：点击表情面板内部或表情按钮本身不关闭，其它区域点击关闭
  if (
    emojiPanelVisible.value &&
    !target.closest('.emoji-panel') &&
    !target.closest('.toolbar-icon-btn')
  ) {
    emojiPanelVisible.value = false;
  }
};

const quickReplies = ref<QuickReply[]>([
  {
    id: 'q1',
    title: '游戏里没声音排查',
    preview: '请先确认系统里播放音乐是否有声音...',
    tag: '声音问题',
    content:
      '请先确认：\n1）系统里播放音乐是否有声音；\n2）游戏设置中输入/输出设备是否选择为虚拟声卡；\n3）变声器主界面是否已经开启；\n如果仍然无声，请发送一张游戏内音频设置截图给我～'
  },
  {
    id: 'q2',
    title: '虚拟声卡安装失败',
    preview: '请先退出所有语音软件，然后以管理员身份重新安装...',
    tag: '安装问题',
    content:
      '请先退出 QQ/微信/YY/各类语音与直播软件，然后右键以“管理员身份运行”安装包重新安装虚拟声卡。如果仍然失败，请发送完整报错截图给我。'
  }
]);

const activeSessionId = ref<string>('');
// 编辑消息相关状态
const editingMessage = ref<ChatMessage | null>(null);
const editingContent = ref<string>('');
const editMessageInputRef = ref<HTMLTextAreaElement | null>(null);

// 是否可以编辑某条消息（例如只允许在一定时间内编辑自己的文本消息）
const canEditMessage = (msg: ChatMessage): boolean => {
  // 只允许编辑自己发送的、未撤回的文本消息
  if (!currentUser.value || msg.from !== 'agent' || msg.messageType !== 'text' || msg.isRecalled) {
    return false;
  }
  // 可选：限制时间窗口，例如 10 分钟内
  if (msg.created_at) {
    try {
      const createdTime = new Date(msg.created_at);
      const now = new Date();
      const diffMs = now.getTime() - createdTime.getTime();
      const diffMinutes = diffMs / (1000 * 60);
      if (diffMinutes > 10) {
        return false;
      }
    } catch (e) {
      console.warn('解析消息创建时间失败，禁止编辑:', e, msg.created_at);
      return false;
    }
  }
  return true;
};
const inputText = ref('');
const messagesRef = ref<HTMLDivElement | null>(null);
const emojiPanelVisible = ref(false);
const emojis = ref<string[]>([
  '😀','😁','😂','🤣','😃','😄','😅','😆','😉','😊',
  '😍','😘','🥰','😗','😙','😚','😋','😛','😜','🤪',
  '🤨','🧐','🤓','😎','🥳','🤩','😏','😒','🙄','😬',
  '😢','😭','😤','😡','🤯','😳','😱','😨','😰','😥',
  '😴','🤤','🤒','🤕','🤢','🤮','🤧','🥵','🥶','🥴',
  '👍','👎','👌','🤌','🤏','✌️','🤞','🤟','🤘','🤙',
  '👏','🙌','🙏','👐','🤝','💪','✍️','💅','👋','🤗',
  '❤️','🧡','💛','💚','💙','💜','🖤','🤍','💔','❣️',
  '💥','💫','✨','⭐','🌟','🔥','🌈','⚡','🎉','🎊',
  '🍉','🍎','🍔','🍟','🍕','🍣','🍰','🍺','☕','🧋',
  '📷','🎥','🎧','🎮','💻','📱','🖼','📎','📝','💬'
]);
const imageInputRef = ref<HTMLInputElement | null>(null);
const activeTab = ref<'my' | 'pending'>('my');

// 我的会话列表 / 待接入会话列表分开维护
const mySessions = ref<any[]>([]);
const pendingSessions = ref<any[]>([]);

const activeSession = computed(() =>
  (activeTab.value === 'my' ? mySessions.value : pendingSessions.value).find((s) => s.id === activeSessionId.value)
);

// 根据当前标签过滤会话列表
const filteredSessions = computed(() => {
  return activeTab.value === 'my' ? mySessions.value : pendingSessions.value;
});

// 切换标签
const switchTab = async (tab: 'my' | 'pending') => {
  activeTab.value = tab;
  // 切换标签时，重新订阅对应的会话列表（通过 WebSocket）
  if (websocketClient.isConnected() && currentUser.value && token.value) {
    try {
      await websocketClient.subscribeSessions(tab);
    } catch (error) {
      console.error('订阅会话列表失败:', error);
    }
  }
};

// 检查登录状态并验证 token
onMounted(async () => {
  const storedUser = sessionStorage.getItem('user');
  const storedToken = sessionStorage.getItem('token');
  
  if (!storedUser || !storedToken) {
    router.push('/login');
    return;
  }

  try {
    currentUser.value = JSON.parse(storedUser);
    token.value = storedToken;

    // 加载保存的状态
    loadSavedStatus();

    // 添加点击外部关闭菜单的事件监听
    document.addEventListener('click', handleClickOutside);

    // 验证 token 是否有效
    try {
      const verifyResponse = await customerServiceApi.verifyToken(token.value);
      if (!verifyResponse.success) {
        // Token 无效，清除并跳转登录
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        router.push('/login');
        return;
      }
      // 更新用户信息（以防后端有更新）
      if (verifyResponse.user) {
        currentUser.value = verifyResponse.user;
        sessionStorage.setItem('user', JSON.stringify(verifyResponse.user));
      }
      
        // 登录成功后自动设置为在线状态（通过 WebSocket）
        // 注意：需要在 WebSocket 连接成功后设置
        const onlineStatus = statusOptions.find(s => s.type === 'online');
        if (onlineStatus) {
          currentStatus.value = onlineStatus;
          saveStatus('online');
        }
    } catch (error) {
      console.error('Token 验证失败:', error);
      // Token 验证失败，清除并跳转登录
      sessionStorage.removeItem('token');
      sessionStorage.removeItem('user');
      router.push('/login');
      return;
    }

    // 连接 WebSocket 并订阅会话列表
    connectWebSocket().then(() => {
      // WebSocket 连接成功后，订阅会话列表和待接入会话
      subscribeToSessions();
    }).catch((error) => {
      console.error('WebSocket 连接失败:', error);
    });
    
    // 启动心跳机制（仅发送心跳，不更新状态）
    startHeartbeat();
    
    // 监听浏览器关闭/刷新事件：
    const handleBeforeUnload = () => {
      // 仅断开 WebSocket 连接，不清除 sessionStorage，
      // 这样刷新页面仍然保持登录状态，关闭浏览器由 sessionStorage 自动清空
      disconnectWebSocket();
    };
    
    // 监听页面卸载前事件
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    // 组件卸载时清除定时器和断开 WebSocket
    onUnmounted(() => {
      document.removeEventListener('click', handleClickOutside);
      stopHeartbeat();
      // 断开 WebSocket 连接
      disconnectWebSocket();
      // 移除 beforeunload 事件监听
      window.removeEventListener('beforeunload', handleBeforeUnload);
    });
  } catch (error) {
    console.error('解析用户信息失败:', error);
    // 清除无效数据
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('user');
    router.push('/login');
  }
});

// 心跳机制
let heartbeatInterval: number | null = null;

const startHeartbeat = () => {
  // 清除旧的定时器
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
  }
  
  // 每30秒发送一次心跳（仅发送心跳，状态更新通过 WebSocket）
  heartbeatInterval = window.setInterval(() => {
    if (websocketClient.isConnected() && currentUser.value && token.value) {
      websocketClient.sendHeartbeat();
    }
  }, 30000); // 30秒
};

const stopHeartbeat = () => {
  if (heartbeatInterval) {
    clearInterval(heartbeatInterval);
    heartbeatInterval = null;
  }
};

// 订阅会话列表（通过 WebSocket）
const subscribeToSessions = async () => {
  if (!websocketClient.isConnected() || !currentUser.value || !token.value) {
    return;
  }

  try {
    // 订阅我的会话列表
    await websocketClient.subscribeSessions('my');
    // 订阅待接入会话列表
    await websocketClient.subscribePendingSessions();
  } catch (error) {
    console.error('订阅会话列表失败:', error);
  }
};

// 选择会话
const selectSession = async (id: string) => {
  // 如果是待接入tab，执行接入操作
  if (activeTab.value === 'pending') {
    await acceptSession(id);
    return;
  }
  
  activeSessionId.value = id;
  await loadMessages(id);
};

// 接入会话（从待接入移到我的会话）
const acceptSession = async (sessionId: string) => {
  if (!currentUser.value || !token.value) return;

  try {
    // 确保 WebSocket 连接
    if (!websocketClient.isConnected()) {
      await connectWebSocket();
    }

    const response = await websocketClient.acceptSession(sessionId);
    if (response.success === false) {
      throw new Error(response.message || '接入失败');
    }

    if (pendingCount.value > 0) {
      pendingCount.value -= 1;
    }

    activeTab.value = 'my';
    activeSessionId.value = sessionId;
    await loadMessages(sessionId);
  } catch (error: any) {
    console.error('接入会话失败:', error);
    alert(error?.message || error.response?.data?.message || '接入失败，请稍后重试');
  }
};

// 处理消息富文本
const processMessageRichText = (text: string): { richText: string; isRich: boolean; linkUrls: string[] } => {
  if (!text) {
    return { richText: '', isRich: false, linkUrls: [] };
  }
  
  try {
    const result = processRichText(text);
    return {
      richText: result.html,
      isRich: result.isRich,
      linkUrls: result.urls || []
    };
  } catch (error) {
    console.error('处理富文本失败:', error);
    return { richText: text, isRich: false, linkUrls: [] };
  }
};

// 获取URL显示文本
const getUrlDisplay = (url: string): string => {
  try {
    const urlObj = new URL(url);
    let host = urlObj.hostname;
    if (host.startsWith('www.')) {
      host = host.substring(4);
    }
    return host.length > 32 ? host.substring(0, 29) + '...' : host;
  } catch {
    return url.length > 32 ? url.substring(0, 29) + '...' : url;
  }
};

// 打开链接
const openLink = (url: string) => {
  window.open(url, '_blank', 'noopener,noreferrer');
};

// 表情面板
const toggleEmojiPanel = () => {
  // 始终以“打开”为主，关闭交给点击外部的逻辑处理
  if (!emojiPanelVisible.value) {
    emojiPanelVisible.value = true;
  }
};

const insertEmoji = async (emoji: string) => {
  const textarea = document.querySelector('.chat-input') as HTMLTextAreaElement | null;
  const current = inputText.value || '';

  if (textarea && typeof textarea.selectionStart === 'number') {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd ?? start;
    inputText.value = current.slice(0, start) + emoji + current.slice(end);
    await nextTick();
    const pos = start + emoji.length;
    textarea.focus();
    textarea.setSelectionRange(pos, pos);
  } else {
    inputText.value = current + emoji;
  }
};

// 选择图片并发送
const triggerImageSelect = () => {
  if (!activeSessionId.value) {
    alert('请先选择一个会话再发送图片');
    return;
  }
  if (!currentUser.value || !token.value) {
    alert('未登录，无法发送图片');
    return;
  }
  if (imageInputRef.value) {
    imageInputRef.value.click();
  }
};

const handleImageChange = async (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files && input.files[0];
  // 重置 input，避免同一张图片无法重复选择
  input.value = '';
  if (!file) return;

  await sendImageMessage(file);
};

const sendImageMessage = async (file: File) => {
  if (!activeSessionId.value || !currentUser.value || !token.value) {
    alert('未登录或未选择会话，无法发送图片');
    return;
  }

  if (!file.type.startsWith('image/')) {
    alert('只能发送图片文件');
    return;
  }

  const maxSizeMb = 5;
  if (file.size > maxSizeMb * 1024 * 1024) {
    alert(`图片大小不能超过 ${maxSizeMb} MB，请压缩后再发送`);
    return;
  }

  // 确保 WebSocket 已连接
  if (!websocketClient.isConnected()) {
    try {
      await connectWebSocket();
    } catch (error) {
      alert('实时通信未连接，请稍等片刻或刷新页面后重试。');
      return;
    }
  }

  const toDataUrl = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === 'string') {
          resolve(reader.result);
        } else {
          reject(new Error('图片读取失败'));
        }
      };
      reader.onerror = () => reject(new Error('图片读取失败'));
      reader.readAsDataURL(file);
    });
  };

  try {
    const dataUrl = await toDataUrl(file);
    const response = await websocketClient.sendMessage(
      activeSessionId.value,
      dataUrl,
      'agent',
      'image',
      replyToMessageId.value || undefined
    );

    // 发送图片后清除引用状态（如果有）
    replyToMessageId.value = null;
    replyToMessageText.value = null;
    replyToMessageUsername.value = null;

    if (!response || !response.success) {
      alert(response?.message || '图片发送失败，请稍后重试');
    } else {
      console.log('图片发送成功');
    }
  } catch (error: any) {
    console.error('发送图片失败:', error);
    alert(error?.message || '图片发送失败，请稍后重试');
  }
};

// 全局变量，用于存储当前打开的右键菜单
let currentContextMenu: HTMLElement | null = null;

// 关闭当前打开的右键菜单
const closeContextMenu = () => {
  if (currentContextMenu && currentContextMenu.parentNode) {
    currentContextMenu.parentNode.removeChild(currentContextMenu);
    currentContextMenu = null;
  }
};

// 显示消息右键菜单（撤回、引用回复）
// 客服端：客服发送的消息可以撤回+引用，用户发送的消息只能引用
const showMessageContextMenu = async (event: MouseEvent, msg: ChatMessage) => {
  // 阻止默认右键菜单
  event.preventDefault();
  event.stopPropagation();
  
  // 已撤回的消息不显示菜单
  if (msg.isRecalled) {
    return;
  }

  // 先关闭之前打开的菜单
  closeContextMenu();

  const menu = document.createElement('div');
  menu.className = 'context-menu';
  menu.style.cssText = `
    position: fixed;
    top: ${event.clientY}px;
    left: ${event.clientX}px;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    padding: 4px 0;
    z-index: 1000;
    min-width: 120px;
  `;

  // 撤回消息（只有客服发送的消息才能撤回）
  if (msg.from === 'agent') {
    // 检查消息是否超过2分钟
    let canRecall = false; // 默认不允许撤回，必须有有效时间才能撤回
    let recallTooltip = '';
    
    if (msg.created_at) {
      try {
        // 处理不同的时间格式
        let createdTime: Date;
        if (typeof msg.created_at === 'string') {
          // 如果是 ISO 格式字符串，直接解析
          createdTime = new Date(msg.created_at);
        } else {
          // 如果是其他格式，尝试转换
          createdTime = new Date(msg.created_at);
        }
        
        // 检查日期是否有效
        if (isNaN(createdTime.getTime())) {
          // 如果日期无效，不允许撤回
          canRecall = false;
          recallTooltip = '消息时间无效，无法撤回';
        } else {
          const now = new Date();
          const diffMs = now.getTime() - createdTime.getTime();
          const diffMinutes = diffMs / (1000 * 60);
          canRecall = diffMinutes <= 2;
          if (!canRecall) {
            recallTooltip = '消息已超过2分钟，无法撤回';
          }
        }
      } catch (e) {
        console.error('解析消息创建时间失败:', e, msg.created_at);
        // 如果解析失败，不允许撤回
        canRecall = false;
        recallTooltip = '无法解析消息时间，无法撤回';
      }
    } else {
      // 如果没有 created_at 字段，不允许撤回
      canRecall = false;
      recallTooltip = '消息时间信息缺失，无法撤回';
      console.warn('消息缺少 created_at 字段:', msg.id, msg);
    }
    
    const recallItem = document.createElement('div');
    recallItem.textContent = '撤回消息';
    recallItem.style.cssText = `
      padding: 8px 16px;
      cursor: ${canRecall ? 'pointer' : 'not-allowed'};
      font-size: 14px;
      color: ${canRecall ? '#1f2937' : '#9ca3af'};
      ${!canRecall ? 'opacity: 0.5;' : ''}
      ${!canRecall ? 'pointer-events: none;' : ''}
    `;
    
    if (canRecall) {
      recallItem.onmouseenter = () => {
        recallItem.style.backgroundColor = '#f3f4f6';
      };
      recallItem.onmouseleave = () => {
        recallItem.style.backgroundColor = 'transparent';
      };
      recallItem.onclick = async () => {
        closeContextMenu();
        await recallMessage(msg);
      };
    } else {
      // 禁用点击，并显示提示
      recallItem.title = recallTooltip || '消息已超过2分钟，无法撤回';
      recallItem.onclick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        // 不执行任何操作
      };
    }
    
    menu.appendChild(recallItem);
  }

  // 引用回复（所有消息都可以引用）
  const replyItem = document.createElement('div');
  replyItem.textContent = '引用回复';
  replyItem.style.cssText = `
    padding: 8px 16px;
    cursor: pointer;
    font-size: 14px;
    color: #1f2937;
    ${msg.from === 'agent' ? 'border-top: 1px solid #e5e7eb;' : ''}
  `;
  replyItem.onmouseenter = () => {
    replyItem.style.backgroundColor = '#f3f4f6';
  };
  replyItem.onmouseleave = () => {
    replyItem.style.backgroundColor = 'transparent';
  };
  replyItem.onclick = () => {
    closeContextMenu();
    const msgId = parseInt(msg.id);
    if (!isNaN(msgId)) {
      replyToMessageId.value = msgId;
      // 使用原始消息文本，如果已撤回则显示提示
      replyToMessageText.value = msg.isRecalled ? '[消息已撤回]' : msg.text;
      // 保存引用消息的发送者用户名
      replyToMessageUsername.value = msg.fromUsername || (msg.from === 'agent' ? '客服' : '用户');
      // 更新输入框占位符（显示发送者名称）
      const input = document.querySelector('.chat-input') as HTMLTextAreaElement;
      if (input) {
        const senderName = replyToMessageUsername.value;
        const displayText = msg.isRecalled ? '[消息已撤回]' : msg.text;
        const preview = displayText.length > 30 ? displayText.substring(0, 30) + '...' : displayText;
        input.placeholder = `回复 ${senderName}：${preview}`;
        input.focus();
      }
    }
  };
  menu.appendChild(replyItem);

  document.body.appendChild(menu);
  
  // 保存当前菜单引用
  currentContextMenu = menu;

  // 点击其他地方关闭菜单
  const closeMenuOnClick = (e: MouseEvent) => {
    if (!menu.contains(e.target as Node)) {
      closeContextMenu();
      document.removeEventListener('click', closeMenuOnClick);
      document.removeEventListener('contextmenu', closeMenuOnContextMenu);
      window.removeEventListener('scroll', closeMenuOnScroll, true);
    }
  };
  
  // 右键点击其他地方也关闭菜单
  const closeMenuOnContextMenu = (e: MouseEvent) => {
    if (!menu.contains(e.target as Node)) {
      closeContextMenu();
      document.removeEventListener('click', closeMenuOnClick);
      document.removeEventListener('contextmenu', closeMenuOnContextMenu);
      window.removeEventListener('scroll', closeMenuOnScroll, true);
    }
  };
  
  // 滚动时关闭菜单
  const closeMenuOnScroll = () => {
    closeContextMenu();
    document.removeEventListener('click', closeMenuOnClick);
    document.removeEventListener('contextmenu', closeMenuOnContextMenu);
    window.removeEventListener('scroll', closeMenuOnScroll, true);
  };
  
  // 延迟添加事件监听器，避免立即触发
  setTimeout(() => {
    document.addEventListener('click', closeMenuOnClick);
    document.addEventListener('contextmenu', closeMenuOnContextMenu);
    window.addEventListener('scroll', closeMenuOnScroll, true);
  }, 0);
};

// 撤回消息（使用WebSocket）
const recallMessage = async (msg: ChatMessage) => {
  if (!currentUser.value || !token.value) {
    // 不弹窗，静默处理
    console.warn('未登录，无法撤回消息');
    return;
  }

  // 检查WebSocket连接状态
  if (!websocketClient.isConnected()) {
    console.warn('WebSocket 未连接，无法撤回消息');
    return;
  }

  // 再次检查时间（防止在检查后到点击之间超过2分钟）
  if (msg.created_at) {
    try {
      const createdTime = new Date(msg.created_at);
      const now = new Date();
      const diffMs = now.getTime() - createdTime.getTime();
      const diffMinutes = diffMs / (1000 * 60);
      if (diffMinutes > 2) {
        // 超过2分钟，静默处理，不弹窗
        console.warn('消息已超过2分钟，无法撤回');
        return;
      }
    } catch (e) {
      console.error('解析消息创建时间失败:', e);
    }
  }

  try {
    const msgId = parseInt(msg.id);
    if (isNaN(msgId)) {
      // 不弹窗，静默处理
      console.warn('消息ID无效');
      return;
    }

    // 使用WebSocket撤回消息
    await websocketClient.recallMessage(msgId);
    
    // 注意：消息撤回状态会通过WebSocket的message_recalled事件自动更新
    // 这里不需要手动更新UI，因为WebSocket会推送撤回事件
  } catch (error: any) {
    // 不弹窗，只记录日志
    console.error('撤回消息失败:', error);
  }
};

// 加载消息（通过 WebSocket 获取历史消息）
const loadMessages = async (sessionId: string) => {
  if (!currentUser.value || !token.value) return;

  // 确保 WebSocket 已连接
  if (!websocketClient.isConnected()) {
    try {
      await connectWebSocket();
    } catch (error) {
      console.error('WebSocket 连接失败，无法加载历史消息:', error);
      alert('实时通信未连接，无法加载会话历史消息，请稍后重试或刷新页面。');
      return;
    }
  }

  try {
    const response = await websocketClient.getSessionMessages(sessionId, 200);
    if (response.success) {
      const mapped = (response.messages || []).map((m: any) => {
        const text = m.text || '';
        const richTextResult = processMessageRichText(text);

        // 使用后端返回的引用消息摘要信息（如果存在）
        let replyToMessage = null;
        let replyToUsername = null;
        let replyToMessageType: 'text' | 'image' | 'file' | undefined = undefined;
        if (m.reply_to_message) {
          const replyInfo = m.reply_to_message;
          if (replyInfo.is_recalled) {
            const senderName = replyInfo.from_username || '用户';
            replyToMessage = `${senderName}: 该引用消息已被撤回`;
          } else {
            replyToMessage = replyInfo.message || '';
            replyToUsername = replyInfo.from_username || null;
            replyToMessageType = replyInfo.message_type || 'text';
          }
        } else if (m.reply_to_message_id) {
          // 兼容旧数据：如果没有 reply_to_message，但有 reply_to_message_id，显示占位符
          replyToMessage = '引用消息加载中...';
        }

        return {
          id: m.id,
          from: m.from || 'user',
          text: m.is_recalled ? '' : text,
          time: m.time || '刚刚',
          created_at: m.created_at,
          userId: m.userId,
          avatar: m.avatar,
          messageType: (m.message_type || 'text') as ChatMessage['messageType'],
          richText: richTextResult.richText,
          isRich: richTextResult.isRich,
          linkUrls: richTextResult.linkUrls,
          isRecalled: m.is_recalled || false,
          isEdited: m.is_edited || false,
          editedAt: m.edited_at || undefined,
          reply_to_message_id: m.reply_to_message_id,
          replyToMessage: replyToMessage,
          replyToUsername: replyToUsername,
          replyToMessageType: replyToMessageType,
          fromUsername: m.username || (m.from === 'agent' ? '客服' : '用户'),
        } as ChatMessage;
      });

      messages.value = mapped;

      // 同步已接收消息ID，避免重复追加
      receivedMessageIds.clear();
      for (const m of mapped) {
        if (m.id) {
          receivedMessageIds.add(String(m.id));
        }
      }
      scrollToBottom();
    } else {
      console.error('加载消息失败:', response.message);
    }
  } catch (error: any) {
    console.error('加载消息失败:', error);
  }
};

const scrollToBottom = () => {
  const el = messagesRef.value;
  if (!el) return;
  requestAnimationFrame(() => {
    el.scrollTop = el.scrollHeight;
  });
};

watch(
  () => messages.value.length,
  () => scrollToBottom()
);

// 连接 WebSocket
const connectWebSocket = async (): Promise<void> => {
  if (!currentUser.value || !token.value) {
    throw new Error('未登录');
  }

  // 注册消息回调
  websocketClient.on('onMessage', (message: WebSocketMessage) => {
    handleWebSocketMessage(message);
  });

  websocketClient.on('onConnect', async () => {
    console.log('WebSocket 连接成功');
    // 连接成功后订阅会话列表
    await subscribeToSessions();
    // 设置在线状态
    if (currentUser.value && token.value) {
      try {
        await websocketClient.updateAgentStatus('online');
      } catch (error) {
        console.error('设置在线状态失败:', error);
      }
    }
  });

  websocketClient.on('onDisconnect', () => {
    console.warn('WebSocket 连接断开');
  });

  websocketClient.on('onError', (error: any) => {
    console.error('WebSocket 错误:', error);
  });

  // 会话列表更新
  websocketClient.on('onSessionListUpdated', (data: { sessions: any[]; type: string }) => {
    if (data.type === 'my') {
      mySessions.value = data.sessions.map((s: any) => ({
        id: s.id,
        userName: s.userName,
        userId: s.userId,
        isVip: s.isVip,
        category: s.category || '待分类',
        lastMessage: s.lastMessage || '',
        lastTime: s.lastTime || '刚刚',
        duration: s.duration || '00:00',
        unread: s.unread || 0,
        avatar: s.avatar,
        status: s.status || 'active'
      }));

      // 自动选择第一个会话（仅在我的会话tab且当前没有选中会话）
      if (activeTab.value === 'my' && mySessions.value.length > 0 && !activeSessionId.value) {
        selectSession(mySessions.value[0].id);
      }
    } else if (data.type === 'pending') {
      // 更新待接入会话列表与数量
      pendingSessions.value = data.sessions.map((s: any) => ({
        id: s.id,
        userName: s.userName,
        userId: s.userId,
        isVip: s.isVip,
        category: s.category || '待分类',
        lastMessage: s.lastMessage || '',
        lastTime: s.lastTime || '刚刚',
        duration: s.duration || '00:00',
        unread: s.unread || 0,
        avatar: s.avatar,
        status: s.status || 'pending',
      }));
      pendingCount.value = pendingSessions.value.length;
    }
  });

  // 新待接入会话
  websocketClient.on('onNewPendingSession', (data: { session: any }) => {
    pendingCount.value++;
    // 如果当前在待接入tab，可以添加到列表（但通常通过 session_list_updated 更新）
  if (data?.session) {
    // 尽量避免重复插入，最终以 session_list_updated 为准
    const exists = pendingSessions.value.some((s: any) => s.id === data.session.id);
    if (!exists) {
      pendingSessions.value.unshift({
        id: data.session.id,
        userName: data.session.userName,
        userId: data.session.userId,
        isVip: data.session.isVip,
        category: data.session.category || '待分类',
        lastMessage: data.session.lastMessage || '',
        lastTime: data.session.lastTime || '刚刚',
        duration: data.session.duration || '00:00',
        unread: data.session.unread || 0,
        avatar: data.session.avatar,
        status: data.session.status || 'pending',
      });
    }
  }
  });

  // 待接入会话被接入
  websocketClient.on('onPendingSessionAccepted', (data: { session_id: string; agent_id: number }) => {
    if (pendingCount.value > 0) {
      pendingCount.value--;
    }
  // 从待接入列表移除该会话（最终也会被 session_list_updated 覆盖）
  if (data?.session_id) {
    pendingSessions.value = pendingSessions.value.filter((s: any) => s.id !== data.session_id);
  }
    // 如果当前用户是接入的客服，切换到我的会话tab
    if (data.agent_id === currentUser.value?.id) {
      activeTab.value = 'my';
      // 会话列表会通过 session_list_updated 更新
    }
  });

  // 客服状态变化
  websocketClient.on('onAgentStatusChanged', (data: { agent_id: number; status: string }) => {
    // 可以在这里更新其他客服的状态显示（如果有相关UI）
    console.log(`客服 ${data.agent_id} 状态变化: ${data.status}`);
  });

  // 用户资料更新
  websocketClient.on('onUserProfileUpdated', (data: { user_id: number; profile: any }) => {
    if (data.user_id === currentUser.value?.id) {
      // 更新当前用户信息
      if (data.profile?.user) {
        const storedUser = localStorage.getItem('user');
        if (storedUser) {
          try {
            const user = JSON.parse(storedUser);
            Object.assign(user, data.profile.user);
            localStorage.setItem('user', JSON.stringify(user));
            currentUser.value = user;
          } catch (e) {
            console.error('更新用户资料失败:', e);
          }
        }
      }
    }
  });

  // 消息编辑
  websocketClient.on('onMessageEdited', (data: { message_id: number; session_id: string; new_content: string; edited_at: string }) => {
    if (data.session_id === activeSessionId.value) {
      // 更新消息内容
      const messageIndex = messages.value.findIndex(m => m.id === data.message_id);
      if (messageIndex !== -1) {
        messages.value[messageIndex].text = data.new_content;
        messages.value[messageIndex].isEdited = true;
        messages.value[messageIndex].editedAt = data.edited_at;
      }
    }
  });

  // 会话状态更新
  websocketClient.on('onSessionStatusUpdated', (data: { session_id: string; status: string; user_id: number; agent_id: number }) => {
    if (data.session_id === activeSessionId.value) {
      // 更新当前会话状态
      const sessionIndex = sessions.value.findIndex(s => s.id === data.session_id);
      if (sessionIndex !== -1) {
        sessions.value[sessionIndex].status = data.status;
        if (data.status === 'closed') {
          // 会话已关闭，可以选择提示用户或切换到其他会话
          alert('会话已关闭');
          if (sessions.value.length > 1) {
            // 切换到其他会话
            const nextSession = sessions.value.find(s => s.id !== data.session_id);
            if (nextSession) {
              selectSession(nextSession.id);
            }
          }
        }
      }
    }
  });

  // 获取设备信息
  const deviceInfo = {
    device_name: navigator.userAgent,
    device_type: 'web',
    platform: navigator.platform,
    browser: getBrowserInfo(),
    os_version: navigator.platform,
  };

  // 连接 WebSocket
  await websocketClient.connect(currentUser.value.id, token.value, deviceInfo);
};

// 断开 WebSocket
const disconnectWebSocket = (): void => {
  websocketClient.disconnect();
};

// 图片预览（点击放大）
const openImagePreview = (imageSrc: string) => {
  // 创建预览模态框
  const modal = document.createElement('div');
  modal.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.9);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10000;
    cursor: pointer;
  `;
  
  const img = document.createElement('img');
  img.src = imageSrc;
  img.style.cssText = `
    max-width: 90%;
    max-height: 90%;
    object-fit: contain;
    border-radius: 8px;
  `;
  
  modal.appendChild(img);
  document.body.appendChild(modal);
  
  // 点击关闭
  modal.onclick = () => {
    document.body.removeChild(modal);
  };
  
  // ESC键关闭
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      document.body.removeChild(modal);
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);
};

// 从消息文本中提取文件名
const extractFileName = (text: string, messageId?: number): string => {
  if (!text) return '[文件]';
  
  // 如果是base64 data URL，优先提取文件名
  if (text.startsWith('data:')) {
    const filenameMatch = text.match(/filename="([^"]+)"/);
    if (filenameMatch && filenameMatch[1]) {
      return filenameMatch[1];
    }
    // 如果没有文件名，根据MIME类型推断
    const mimeMatch = text.match(/data:([^;]+)/);
    if (mimeMatch) {
      const mimeType = mimeMatch[1];
      const ext = mimeType.split('/')[1] || 'bin';
      return `file_${messageId || Date.now()}.${ext}`;
    }
  }
  
  // 格式: [文件] filename.ext (size)
  const match = text.match(/\[文件\]\s+(.+?)\s+\(/);
  if (match && match[1]) {
    return match[1].trim();
  }
  
  // 如果是URL路径，提取文件名
  if (text.includes('/')) {
    const parts = text.split('/');
    const lastPart = parts[parts.length - 1];
    if (lastPart && lastPart !== text) {
      return lastPart.split('?')[0]; // 移除查询参数
    }
  }
  
  return '[文件]';
};

// 从消息文本中提取文件大小
const extractFileSize = (text: string): string => {
  if (!text) return '';
  
  // 格式: [文件] filename.ext (size)
  const match = text.match(/\(([^)]+)\)$/);
  if (match && match[1]) {
    return match[1].trim();
  }
  
  return '';
};

// 文件下载
const downloadFile = async (msg: ChatMessage) => {
  if (!msg.text) {
    alert('文件内容为空');
    return;
  }
  
  try {
    // 提取文件名
    const fileName = extractFileName(msg.text, msg.id);
    
    // 如果消息文本是base64编码的文件，直接下载
    if (msg.text.startsWith('data:')) {
      // 提取base64内容
      const base64Match = msg.text.match(/base64,(.+?)(?:;filename=|$)/);
      if (base64Match && base64Match[1]) {
        // 提取MIME类型
        const mimeMatch = msg.text.match(/data:([^;]+)/);
        const mimeType = mimeMatch ? mimeMatch[1] : 'application/octet-stream';
        
        // 将base64转换为Blob
        const byteCharacters = atob(base64Match[1]);
        const byteNumbers = new Array(byteCharacters.length);
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        const byteArray = new Uint8Array(byteNumbers);
        const blob = new Blob([byteArray], { type: mimeType });
        
        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // 释放URL对象
        setTimeout(() => URL.revokeObjectURL(url), 100);
      } else {
        // 如果没有base64内容，尝试直接使用data URL
        const link = document.createElement('a');
        link.href = msg.text;
        link.download = fileName;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } else {
      // 如果是文件路径或URL，尝试下载
      const link = document.createElement('a');
      link.href = msg.text;
      link.download = fileName;
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  } catch (error) {
    console.error('下载文件失败:', error);
    alert('下载文件失败，请稍后重试');
  }
};

// 获取浏览器信息
const getBrowserInfo = (): string => {
  const ua = navigator.userAgent;
  if (ua.includes('Chrome')) return 'Chrome';
  if (ua.includes('Firefox')) return 'Firefox';
  if (ua.includes('Safari')) return 'Safari';
  if (ua.includes('Edge')) return 'Edge';
  return 'Unknown';
};

// 处理收到的 WebSocket 消息
const handleWebSocketMessage = (message: WebSocketMessage): void => {
  // 检查消息是否属于当前活动会话
  if (message.session_id !== activeSessionId.value) {
    // 如果不是当前会话的消息，更新会话列表的未读数量
    const session = sessions.value.find(s => s.id === message.session_id);
    if (session) {
      session.unread = (session.unread || 0) + 1;
      // 更新最后一条消息
      session.lastMessage = (message.text || '').substring(0, 50);
      session.lastTime = formatTime(message.time || new Date().toISOString());
    }
    return;
  }

  // 检查消息是否已显示（去重）
  if (receivedMessageIds.has(message.id)) {
    return;
  }
  receivedMessageIds.add(message.id);

  // 限制集合大小
  if (receivedMessageIds.size > 1000) {
    const idsArray = Array.from(receivedMessageIds);
    receivedMessageIds.clear();
    idsArray.slice(500).forEach(id => receivedMessageIds.add(id));
  }

  // 判断是否是自己的消息（多设备同步）
  // 优先使用服务端提供的 is_from_self 标记（更可靠），如果没有则回退到通过 user_id 比较
  const isFromSelf = message.is_from_self !== undefined 
    ? message.is_from_self 
    : (message.from_user_id === currentUser.value?.id);

  // 处理富文本
  let processedMessage = message.text;
  let isRich = false;
  let linkUrls: string[] = [];

  if (message.text) {
    try {
      const result = processRichText(message.text);
      if (result.isRich) {
        processedMessage = result.html;
        isRich = true;
        linkUrls = result.urls || [];
      }
    } catch (error) {
      console.error('处理富文本失败:', error);
    }
  }

  // 添加消息到列表
  const isRecalled = (message as any).is_recalled || false;
  
  // 如果是撤回消息，更新现有消息而不是添加新消息
  if (isRecalled) {
    // 注意：历史消息里 m.id 可能是 number，WebSocket 推送的 message.id 一般是 string
    // 这里统一转成字符串再比较，避免因为类型不同导致找不到原消息
    const existingIndex = messages.value.findIndex(m => String(m.id) === String(message.id));
    if (existingIndex !== -1) {
      // 更新现有消息为撤回状态
      messages.value[existingIndex].isRecalled = true;
      messages.value[existingIndex].text = '';
      messages.value[existingIndex].richText = undefined;
      messages.value[existingIndex].fromUsername = message.username || messages.value[existingIndex].fromUsername;
      messages.value[existingIndex].userId = message.from_user_id || messages.value[existingIndex].userId;
      
      // 更新所有引用这条被撤回消息的其他消息
      const recalledMessageId = parseInt(message.id);
      if (!isNaN(recalledMessageId)) {
        messages.value.forEach((msg, index) => {
          if (msg.reply_to_message_id === recalledMessageId && msg.replyToMessage) {
            // 更新引用消息显示为"该引用消息已被撤回"
            const senderName = messages.value[existingIndex].fromUsername || '用户';
            messages.value[index].replyToMessage = `${senderName}: 该引用消息已被撤回`;
          }
        });
      }
      
      return; // 撤回消息不需要添加新消息
    }
    // 如果消息不存在，可能是新收到的撤回消息，仍然需要显示撤回提示
  }
  
  // 处理引用消息信息（使用后端提供的引用消息摘要）
  let replyToMessage = null;
  let replyToUsername = null;
  let replyToMessageType: 'text' | 'image' | 'file' | undefined = undefined;
  if ((message as any).reply_to_message) {
    // 后端已包含引用消息摘要
    const replyInfo = (message as any).reply_to_message;
    if (replyInfo.is_recalled) {
      const senderName = replyInfo.from_username || '用户';
      replyToMessage = `${senderName}: 该引用消息已被撤回`;
    } else {
      replyToMessage = replyInfo.message || '';
      replyToUsername = replyInfo.from_username || null;
      replyToMessageType = replyInfo.message_type || 'text';
    }
  } else if (message.reply_to_message_id) {
    // 兼容旧数据：如果没有 reply_to_message，但有 reply_to_message_id，显示占位符
    replyToMessage = '引用消息加载中...';
  }
  
  const chatMessage: ChatMessage = {
    id: message.id,
    from: isFromSelf ? 'agent' : 'user',
    text: isRecalled ? '[消息已撤回]' : processedMessage,
    time: formatTime(message.time),
    created_at: message.created_at || message.time, // 添加创建时间（用于判断撤回时限）
    userId: message.from_user_id,
    avatar: message.avatar,
    messageType: message.message_type || 'text',
    richText: isRich ? processedMessage : undefined,
    isRich: isRich,
    linkUrls: linkUrls,
    isRecalled: isRecalled,
    isEdited: message.is_edited || false,
    editedAt: message.edited_at || undefined,
    reply_to_message_id: message.reply_to_message_id || null,
    replyToMessage: replyToMessage, // 使用后端提供的引用消息摘要
    replyToUsername: replyToUsername, // 使用后端提供的引用消息摘要
    replyToMessageType: replyToMessageType, // 引用消息类型
    fromUsername: message.username || (message.from === 'agent' ? '客服' : '用户'),
  };

  // 引用消息信息已由后端自动包含在 reply_to_message 字段中，无需额外请求
  messages.value.push(chatMessage);
  scrollToBottom();
};

// 注意：loadReplyMessage 函数已删除，引用消息信息现在由后端自动包含在消息的 reply_to_message 字段中

// 格式化时间
const formatTime = (timeStr: string): string => {
  try {
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 7) return `${days} 天前`;
    
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) + 
           ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return timeStr;
  }
};

// 发送消息（使用 WebSocket）
const handleSend = async () => {
  const text = inputText.value.trim();
  if (!text || !activeSessionId.value || !currentUser.value || !token.value) return;

  if (text.length > 5000) {
    alert('消息内容过长，不能超过5000个字符');
    return;
  }

  // 检查 WebSocket 是否连接
  if (!websocketClient.isConnected()) {
    // 如果未连接，尝试连接（可能是因为刚接入会话，连接还未建立）
    try {
      await connectWebSocket();
      // 连接成功后继续发送
    } catch (error) {
      // 连接失败，提示用户并恢复输入框
      alert('实时通信未连接，请稍等片刻或刷新页面后重试。');
      return;
    }
  }

  const originalText = inputText.value;
  inputText.value = '';

  try {
    // 使用 WebSocket 发送消息
    const response = await websocketClient.sendMessage(
      activeSessionId.value,
      text,
      'agent', // 客服角色
      'text',
      replyToMessageId.value || undefined
    );
    
    // 清除引用状态
    replyToMessageId.value = null;
    replyToMessageText.value = null;
    replyToMessageUsername.value = null;

    // 恢复输入框占位符
    const input = document.querySelector('.chat-input') as HTMLTextAreaElement;
    if (input) {
      input.placeholder = '请输入回复内容，Enter 发送，Shift+Enter 换行';
    }

    if (!response || !response.success) {
      // 失败时恢复输入框
      inputText.value = originalText;
      const msg = response?.message || '发送失败，请稍后重试';
      alert(msg);
    } else {
      // WebSocket 发送成功，消息会通过 new_message 事件接收
      // 不需要手动轮询，消息会自动显示
      console.log('消息发送成功');
    }
  } catch (error: any) {
    // 失败时恢复输入框
    inputText.value = originalText;
    console.error('发送消息失败:', error);
    alert(error.message || '发送失败，请稍后重试');
  }
};

// 处理头像加载错误
const handleAvatarError = (event: Event) => {
  const img = event.target as HTMLImageElement;
  if (img && img.parentElement) {
    img.style.display = 'none';
    // 显示默认文字
    const span = document.createElement('span');
    span.textContent = img.alt === '客服' ? '客' : '用';
    img.parentElement.appendChild(span);
  }
};

const appendQuickReply = (content: string) => {
  if (!content) return;
  if (!inputText.value) {
    inputText.value = content;
  } else {
    inputText.value = `${inputText.value}\n${content}`;
  }
};

const handleLogout = async () => {
  // 退出前设置为离线状态（通过 WebSocket）
  if (websocketClient.isConnected() && currentUser.value && token.value) {
    try {
      await websocketClient.updateAgentStatus('offline');
    } catch (error) {
      console.error('设置离线状态失败:', error);
    }
  }
  
  // 停止心跳
  stopHeartbeat();
  
  // 断开 WebSocket 连接
  disconnectWebSocket();
  
  // 清除所有 localStorage 数据（包括 token、user、device_id、agent_status 等）
  localStorage.clear();
  
  router.push('/login');
};

</script>

<style scoped>
.workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-width: 1320px;
  margin: 0 auto;
  border-radius: 20px;
  backdrop-filter: blur(22px);
  background: rgba(255, 255, 255, 0.02);
  box-shadow: 0 22px 48px rgba(15, 23, 42, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.38);
  overflow: hidden;
  position: relative;
}

.workspace-header {
  height: 66px;
  padding: 0 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.25);
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.16), rgba(255, 255, 255, 0.08));
  backdrop-filter: blur(18px);
  position: relative;
  z-index: 100;
  overflow: visible;
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #4f8bff, #5ac8fa);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 700;
  color: #ffffff;
  box-shadow: 0 12px 26px rgba(79, 139, 255, 0.4);
}

.brand-name {
  font-size: 15px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: var(--text-secondary);
}

.agent-name {
  color: var(--text-primary);
}

.status-container {
  position: relative;
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  z-index: 1000;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}

.status-indicator:hover {
  background: rgba(255, 255, 255, 0.1);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  position: relative;
  flex-shrink: 0;
}

.status-dot.breathing {
  background: var(--status-color, #27c346);
  animation: breathe var(--animation-duration, 2s) ease-in-out infinite;
}

.status-dot.breathing::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--status-color, #27c346);
  opacity: 0.6;
  animation: pulse var(--animation-duration, 2s) ease-in-out infinite;
}

.status-dot.breathing::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: var(--status-color, #27c346);
  opacity: 0.3;
  animation: pulse2 var(--animation-duration, 2s) ease-in-out infinite;
}

/* 呼吸灯动画 */
@keyframes breathe {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.7;
    transform: scale(0.95);
  }
}

@keyframes pulse {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.6;
  }
  50% {
    transform: translate(-50%, -50%) scale(1.8);
    opacity: 0.2;
  }
  100% {
    transform: translate(-50%, -50%) scale(2.2);
    opacity: 0;
  }
}

@keyframes pulse2 {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0.3;
  }
  50% {
    transform: translate(-50%, -50%) scale(2);
    opacity: 0.1;
  }
  100% {
    transform: translate(-50%, -50%) scale(2.5);
    opacity: 0;
  }
}

.status-arrow {
  width: 12px;
  height: 12px;
  color: var(--text-secondary);
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.status-arrow.open {
  transform: rotate(180deg);
}

.status-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 120px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.15);
  padding: 6px;
  z-index: 9999;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.status-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 13px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.status-menu-item:hover {
  background: rgba(51, 112, 255, 0.1);
}

.status-menu-item.active {
  background: rgba(51, 112, 255, 0.15);
  color: var(--accent);
  font-weight: 500;
}

.status-menu-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-menu-dot.online {
  background: #27c346;
}

.status-menu-dot.offline {
  background: #9ca3af;
}

.status-menu-dot.away {
  background: #f59e0b;
}

.status-menu-dot.busy {
  background: #ef4444;
}

.workspace-body {
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 280px;
  background: rgba(255, 255, 255, 0.01);
  backdrop-filter: blur(20px);
  overflow: hidden; /* 防止整个页面滚动 */
  min-height: 0; /* 允许flex子元素缩小 */
}

.sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  overflow: hidden; /* 防止侧边栏本身滚动 */
  min-height: 0; /* 允许flex子元素缩小 */
}

.sidebar.detail {
  border-right: none;
  border-left: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
  overflow: hidden; /* 防止侧边栏本身滚动 */
  min-height: 0; /* 允许flex子元素缩小 */
}

.sidebar-header {
  padding: 14px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.03);
  backdrop-filter: blur(16px);
}

.sidebar-header h2 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.sidebar-header.mt {
  margin-top: 10px;
}

.tabs {
  display: inline-flex;
  padding: 3px;
  border-radius: 10px;
  background: rgba(243, 244, 246, 0.8);
  border: 1px solid rgba(229, 231, 235, 0.6);
  box-shadow: 
    0 1px 3px rgba(15, 23, 42, 0.06),
    inset 0 1px 1px rgba(255, 255, 255, 0.8);
  position: relative;
  overflow: hidden;
  width: 100%;
  max-width: 240px;
}

.tab {
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 12px;
  font-weight: 500;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1;
  white-space: nowrap;
  flex: 1;
  text-align: center;
  user-select: none;
}

.tab:hover:not(.active) {
  color: #374151;
  background: rgba(255, 255, 255, 0.4);
}

.tab.active {
  background: #ffffff;
  color: #3370ff;
  font-weight: 600;
  box-shadow: 
    0 2px 6px rgba(15, 23, 42, 0.1),
    0 1px 2px rgba(15, 23, 42, 0.06);
  transform: translateY(0);
}

.tab-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  background: #ef4444;
  color: #ffffff;
  border-radius: 9px;
  font-size: 11px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #ffffff;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
}

.session-list {
  list-style: none;
  margin: 0;
  padding: 10px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  min-height: 0; /* 允许flex子元素缩小，使overflow生效 */
  /* 无感滚动条样式 - Firefox */
  scrollbar-width: thin;
  scrollbar-color: transparent transparent; /* 默认透明 */
}

/* 鼠标悬停时显示滚动条 */
.session-list:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

/* WebKit浏览器（Chrome/Safari/Edge）滚动条样式 */
.session-list::-webkit-scrollbar {
  width: 4px;
}

.session-list::-webkit-scrollbar-track {
  background: transparent;
}

.session-list::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 2px;
  transition: background 0.3s ease;
}

.session-list:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.session-list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.session-item {
  padding: 10px 11px;
  border-radius: 14px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 8px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.8);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
  transition: all 0.16s ease;
}

.session-item:hover {
  background: #ffffff;
  border-color: rgba(51, 112, 255, 0.4);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.12);
}

.session-item.active {
  background: #ffffff;
  border-color: #3370ff;
  box-shadow: 0 4px 16px rgba(51, 112, 255, 0.2);
}

.session-top,
.session-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
}

.session-user {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
}

.session-time {
  font-size: 11px;
  color: #64748b;
}

.session-middle {
  display: flex;
  justify-content: flex-start;
}

.session-tag {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(51, 112, 255, 0.12);
  color: #386bf3;
}

.session-preview {
  flex: 1;
  font-size: 11px;
  color: #64748b;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.unread-badge {
  min-width: 18px;
  height: 18px;
  border-radius: 999px;
  background: #ff7d00;
  color: #ffffff;
  font-size: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.vip-tag {
  margin-left: 4px;
  padding: 2px 7px;
  border-radius: 999px;
  background: rgba(255, 193, 7, 0.16);
  color: #b78103;
  font-size: 10px;
  font-weight: 700;
}

.chat-main {
  display: flex;
  flex-direction: column;
  border-inline: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(255, 255, 255, 0.006);
  backdrop-filter: blur(24px);
  overflow: hidden; /* 防止聊天主区域本身滚动 */
  min-height: 0; /* 允许flex子元素缩小 */
}

.chat-header {
  height: 62px;
  padding: 12px 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(255, 255, 255, 0.028);
  backdrop-filter: blur(20px);
}

.chat-user {
  font-size: 15px;
  font-weight: 700;
}

.chat-meta {
  font-size: 11px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.chat-messages {
  flex: 1;
  padding: 16px 20px 12px;
  overflow-y: auto;
  overflow-x: hidden;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(255, 255, 255, 0.0035);
  backdrop-filter: blur(22px);
  min-height: 0; /* 允许flex子元素缩小，使overflow生效 */
  /* 无感滚动条样式 - Firefox */
  scrollbar-width: thin;
  scrollbar-color: transparent transparent; /* 默认透明 */
}

/* 鼠标悬停时显示滚动条 */
.chat-messages:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

/* WebKit浏览器（Chrome/Safari/Edge）滚动条样式 */
.chat-messages::-webkit-scrollbar {
  width: 4px;
}

.chat-messages::-webkit-scrollbar-track {
  background: transparent;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 2px;
  transition: background 0.3s ease;
}

.chat-messages:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.msg-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}

.from-agent {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.62);
  border: 1px solid rgba(255, 255, 255, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: var(--text-secondary);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.12);
  overflow: hidden;
  flex-shrink: 0;
}

.msg-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.msg-avatar span {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.msg-bubble {
  max-width: 72%;
  padding: 10px 12px 8px;
  border-radius: 16px;
  box-shadow: var(--shadow-subtle);
  color: #0f172a;
}

/* 用户消息：毛玻璃效果 */
.from-user .msg-bubble {
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
}

/* 客服消息：毛玻璃效果 */
.from-agent .msg-bubble {
  background: rgba(229, 239, 255, 0.12);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(51, 112, 255, 0.15);
}

.msg-text {
  font-size: 13px;
  line-height: 1.55;
  color: #0f172a;
}
.msg-image {
  max-width: 220px;
  border-radius: 8px;
  display: block;
}
.file-message-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  max-width: 340px;
  min-width: 220px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.file-message-card:hover {
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-color: #3b82f6;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15);
  transform: translateY(-1px);
}

.file-icon {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 10px;
  color: #ffffff;
  box-shadow: 0 2px 6px rgba(59, 130, 246, 0.2);
}

.file-icon svg {
  width: 24px;
  height: 24px;
}

.file-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  letter-spacing: -0.01em;
}

.file-size {
  font-size: 12px;
  color: #64748b;
  font-weight: 500;
}

.file-download-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: color 0.2s ease;
}

.file-message-card:hover .file-download-icon {
  color: #3b82f6;
}

/* 用户消息文字颜色稍深 */
.from-user .msg-text {
  color: #1e293b;
}

.msg-time {
  margin-top: 4px;
  font-size: 10px;
  color: rgba(15, 23, 42, 0.55);
  text-align: right;
  display: flex;
  align-items: center;
  gap: 6px;
  justify-content: flex-end;
}

.edited-badge {
  font-size: 10px;
  color: #9ca3af;
  font-style: italic;
}

.msg-bubble.editable {
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    opacity: 0.9;
  }
}

/* 编辑消息模态框 */
.edit-message-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.edit-message-dialog {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 0;
  width: 90%;
  max-width: 500px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.edit-message-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);

  h3 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #0f172a;
  }

  .close-btn {
    background: none;
    border: none;
    font-size: 24px;
    color: #9ca3af;
    cursor: pointer;
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(0, 0, 0, 0.05);
      color: #0f172a;
    }
  }
}

.edit-message-body {
  padding: 20px;
}

.edit-message-input {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s ease;

  &:focus {
    border-color: #4f8bff;
  }
}

.edit-message-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(0, 0, 0, 0.1);

  button {
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;

    &.cancel-btn {
      background: rgba(0, 0, 0, 0.05);
      color: #0f172a;

      &:hover {
        background: rgba(0, 0, 0, 0.1);
      }
    }

    &.save-btn {
      background: #4f8bff;
      color: white;

      &:hover {
        background: #3b7ae8;
      }
    }
  }
}

.close-session-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #ef4444;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(239, 68, 68, 0.2);
    border-color: rgba(239, 68, 68, 0.5);
  }

  svg {
    width: 14px;
    height: 14px;
  }
}

/* 引用消息预览：毛玻璃效果 */
.reply-message-preview {
  background: rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-left: 3px solid rgba(59, 130, 246, 0.6);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 8px;
  max-width: 100%;
  transition: all 0.2s ease;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}

.reply-message-preview:hover {
  background: rgba(255, 255, 255, 0.12);
  border-left-color: rgba(59, 130, 246, 0.8);
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
}

.reply-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  line-height: 1.4;
  color: rgba(15, 23, 42, 0.75);
}

.reply-sender-name {
  color: rgba(59, 130, 246, 0.9);
  font-weight: 600;
  flex-shrink: 0;
}

.reply-content {
  color: rgba(15, 23, 42, 0.7);
  word-break: break-word;
  flex: 1;
}

.reply-image-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reply-image-thumbnail {
  width: 32px;
  height: 32px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.1);
}

/* 富文本样式 */
.rich-text-content {
  word-wrap: break-word;
  word-break: break-word;
}

.rich-text-content :deep(code) {
  background-color: #f1f5f9;
  padding: 3px 6px;
  border-radius: 4px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  color: #e11d48;
  border: 1px solid #e2e8f0;
  font-weight: 500;
}

.rich-text-content :deep(pre) {
  background-color: #1e293b;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid #334155;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.rich-text-content :deep(pre code) {
  background-color: transparent;
  padding: 0;
  color: #e2e8f0;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 0.9em;
  line-height: 1.6;
  border: none;
}

.rich-text-content :deep(strong) {
  font-weight: 700;
  color: #0f172a;
}

.rich-text-content :deep(em) {
  font-style: italic;
  color: #475569;
}

.rich-text-content :deep(a) {
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
  border-bottom: 1px solid rgba(37, 99, 235, 0.3);
  transition: all 0.2s ease;
}

.rich-text-content :deep(a:hover) {
  color: #1d4ed8;
  border-bottom-color: #2563eb;
  text-decoration: none;
}

.rich-text-content :deep(.mention) {
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  cursor: pointer;
  display: inline-block;
  transition: all 0.2s ease;
  border: 1px solid;
}

.rich-text-content :deep(.mention[data-mention-type="service"]) {
  color: #2563eb;
  background-color: rgba(59, 130, 246, 0.12);
  border-color: rgba(59, 130, 246, 0.2);
}

.rich-text-content :deep(.mention[data-mention-type="user"]) {
  color: #7c3aed;
  background-color: rgba(124, 58, 237, 0.12);
  border-color: rgba(124, 58, 237, 0.2);
}

.rich-text-content :deep(.mention:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.rich-text-content :deep(.mention[data-mention-type="service"]:hover) {
  background-color: rgba(59, 130, 246, 0.18);
}

.rich-text-content :deep(.mention[data-mention-type="user"]:hover) {
  background-color: rgba(124, 58, 237, 0.18);
}

.rich-text-content :deep(blockquote) {
  border-left: 4px solid #3b82f6;
  padding: 8px 12px;
  margin: 8px 0;
  background-color: #f8fafc;
  border-radius: 0 6px 6px 0;
  color: #475569;
  font-style: italic;
}

.rich-text-content :deep(ul),
.rich-text-content :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.rich-text-content :deep(li) {
  margin: 4px 0;
}

.rich-text-content :deep(h1),
.rich-text-content :deep(h2),
.rich-text-content :deep(h3),
.rich-text-content :deep(h4),
.rich-text-content :deep(h5),
.rich-text-content :deep(h6) {
  margin: 12px 0 8px 0;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.3;
}

.rich-text-content :deep(h1) {
  font-size: 20px;
}

.rich-text-content :deep(h2) {
  font-size: 18px;
}

.rich-text-content :deep(h3) {
  font-size: 16px;
}

.rich-text-content :deep(h4) {
  font-size: 14px;
}

.rich-text-content :deep(h5) {
  font-size: 13px;
}

.rich-text-content :deep(h6) {
  font-size: 12px;
}

/* 链接预览卡片 */
.link-preview-container {
  margin-top: 10px;
}

.link-preview-card {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  padding: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  max-width: 320px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.link-preview-card:hover {
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  border-color: #cbd5e1;
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.link-preview-title {
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  margin-bottom: 6px;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.link-preview-title::before {
  content: '🔗';
  font-size: 14px;
}

.link-preview-url {
  font-size: 12px;
  color: #2563eb;
  word-break: break-all;
  font-weight: 500;
  line-height: 1.5;
}

.chat-input-area {
  padding: 12px 16px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: rgba(255, 255, 255, 0.01);
  backdrop-filter: blur(20px);
}

.chat-input {
  width: 100%;
  min-height: 58px;
  max-height: 110px;
  resize: vertical;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  padding: 10px 12px;
  font-size: 13px;
  background: rgba(255, 255, 255, 0.045);
  color: #0f172a;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  overflow-y: auto;
  /* 无感滚动条样式 - Firefox */
  scrollbar-width: thin;
  scrollbar-color: transparent transparent; /* 默认透明 */
}

/* 鼠标悬停或聚焦时显示滚动条 */
.chat-input:hover,
.chat-input:focus {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

/* WebKit浏览器（Chrome/Safari/Edge）滚动条样式 */
.chat-input::-webkit-scrollbar {
  width: 4px;
}

.chat-input::-webkit-scrollbar-track {
  background: transparent;
}

.chat-input::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 2px;
  transition: background 0.3s ease;
}

.chat-input:hover::-webkit-scrollbar-thumb,
.chat-input:focus::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.chat-input::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.chat-input::placeholder {
  color: rgba(0, 0, 0, 0.45);
}

.chat-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-soft);
  background: rgba(255, 255, 255, 0.18);
}

.chat-input-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-main {
  position: relative;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.toolbar-btn {
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: var(--text-secondary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.toolbar-btn:hover {
  border-color: rgba(51, 112, 255, 0.6);
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.32);
}

.toolbar-spacer {
  flex: 1;
}

.primary-button {
  border-radius: 12px;
  border: none;
  padding: 9px 18px;
  font-size: 13px;
  font-weight: 600;
  background: linear-gradient(135deg, #3370ff, #5fc2ff);
  color: #ffffff;
  cursor: pointer;
  box-shadow: 0 12px 26px rgba(51, 112, 255, 0.2);
  transition: transform 0.1s ease, box-shadow 0.1s ease, filter 0.1s ease;
}

.primary-button:disabled {
  opacity: 0.65;
  cursor: not-allowed;
  box-shadow: none;
}

.primary-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 14px 28px rgba(51, 112, 255, 0.26);
  filter: brightness(1.02);
}

/* 表情面板与图标按钮样式 */
.toolbar-icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 999px;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  font-size: 16px;
  cursor: pointer;
  padding: 0;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.18);
  transition: transform 0.12s ease, box-shadow 0.12s ease, background 0.12s ease, filter 0.12s ease;
}

.toolbar-icon-btn:hover {
  background: rgba(255, 255, 255, 0.22);
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.26);
  filter: brightness(1.03);
}

.toolbar-icon-btn:active {
  transform: translateY(0);
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.18);
}

.emoji-panel {
  position: absolute;
  bottom: 70px;
  left: 32px;
  padding: 8px 10px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.92);
  box-shadow:
    0 18px 45px rgba(15, 23, 42, 0.55),
    0 0 0 1px rgba(148, 163, 184, 0.35);
  display: grid;
  grid-template-columns: repeat(10, 1fr);
  gap: 6px;
  max-width: 360px;
  max-height: 220px;
  overflow-y: auto;
  overflow-x: hidden;
  backdrop-filter: blur(14px);
  z-index: 20;
}

/* emoji 面板滚动条美化 */
.emoji-panel::-webkit-scrollbar {
  width: 6px;
}

.emoji-panel::-webkit-scrollbar-track {
  background: transparent;
}

.emoji-panel::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.55);
  border-radius: 999px;
  box-shadow: inset 0 0 0 1px rgba(15, 23, 42, 0.6);
}

.emoji-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(248, 250, 252, 0.85);
}

/* Firefox */
.emoji-panel {
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.7) transparent;
}

.emoji-item {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 18px;
  padding: 0;
  transition: transform 0.08s ease, background 0.08s ease, box-shadow 0.08s ease;
}

.emoji-item:hover {
  background: rgba(148, 163, 184, 0.25);
  transform: translateY(-1px) scale(1.04);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.5);
}

.emoji-item:active {
  transform: translateY(0) scale(0.98);
  box-shadow: none;
}

.detail-section {
  padding: 12px 16px 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(255, 255, 255, 0.12);
}

.detail-row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}

.label {
  color: var(--text-secondary);
}

.value {
  color: var(--text-primary);
}

.value.success {
  color: #4ade80;
}

.logout-btn {
  margin-left: 12px;
  padding: 6px 12px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  border-color: rgba(255, 255, 255, 0.5);
}

.quick-reply-list {
  list-style: none;
  margin: 0;
  padding: 8px 12px 14px;
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-height: 0; /* 允许flex子元素缩小，使overflow生效 */
  /* 无感滚动条样式 - Firefox */
  scrollbar-width: thin;
  scrollbar-color: transparent transparent; /* 默认透明 */
}

/* 鼠标悬停时显示滚动条 */
.quick-reply-list:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

/* WebKit浏览器（Chrome/Safari/Edge）滚动条样式 */
.quick-reply-list::-webkit-scrollbar {
  width: 4px;
}

.quick-reply-list::-webkit-scrollbar-track {
  background: transparent;
}

.quick-reply-list::-webkit-scrollbar-thumb {
  background: transparent;
  border-radius: 2px;
  transition: background 0.3s ease;
}

.quick-reply-list:hover::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.15);
}

.quick-reply-list::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.25);
}

.quick-reply-item {
  padding: 9px 10px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.18);
  cursor: pointer;
  transition: all 0.16s ease;
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.08);
}

.quick-reply-item:hover {
  background: rgba(245, 247, 255, 0.32);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.12);
}

.qr-title {
  font-size: 12px;
  font-weight: 500;
}

.qr-preview {
  font-size: 11px;
  color: var(--text-secondary);
  margin: 2px 0 4px;
}

.qr-tag {
  font-size: 10px;
  color: #386bf3;
}

@media (max-width: 1100px) {
  .workspace-body {
    grid-template-columns: 260px minmax(0, 1.1fr) 0;
  }

  .sidebar.detail {
    display: none;
  }
}

@media (max-width: 900px) {
  .app-shell {
    padding: 12px;
  }

  .workspace {
    border-radius: 16px;
  }

  .workspace-body {
    grid-template-columns: 0 minmax(0, 1fr);
  }

  .sidebar.sessions {
    display: none;
  }
}
</style>
