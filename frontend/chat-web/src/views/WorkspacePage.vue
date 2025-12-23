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
            <button class="tab active">我的会话</button>
            <button class="tab">待接入</button>
          </div>
        </div>
        <ul class="session-list">
          <li
            v-for="session in sessions"
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
        </header>

        <div class="chat-messages" ref="messagesRef">
          <div
            v-for="msg in messages"
            :key="msg.id"
            :class="['msg-row', msg.from === 'agent' ? 'from-agent' : 'from-user']"
          >
            <div class="msg-avatar">
              <span>{{ msg.from === 'agent' ? '客' : '用' }}</span>
            </div>
            <div class="msg-bubble">
              <div class="msg-text">
                {{ msg.text }}
              </div>
              <div class="msg-time">{{ msg.time }}</div>
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
            <button type="button" class="toolbar-btn">
              常用回复
            </button>
            <div class="toolbar-spacer" />
            <button type="submit" class="primary-button" :disabled="!inputText.trim()">
              发送
            </button>
          </div>
        </form>
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { customerServiceApi } from '@/api/client';

const router = useRouter();

interface Session {
  id: string;
  userName: string;
  isVip: boolean;
  category: string;
  lastMessage: string;
  lastTime: string;
  duration: string;
  unread: number;
}

interface ChatMessage {
  id: string;
  from: 'user' | 'agent';
  text: string;
  time: string;
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
const changeStatus = (status: StatusOption) => {
  currentStatus.value = status;
  saveStatus(status.type);
  showStatusMenu.value = false;
};

// 获取状态样式
const getStatusStyle = (status: StatusOption) => {
  return {
    '--status-color': status.color,
    '--status-shadow': status.shadowColor,
    '--animation-duration': status.animationDuration
  } as any;
};

// 点击外部关闭菜单
const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as HTMLElement;
  if (!target.closest('.status-container')) {
    showStatusMenu.value = false;
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
const inputText = ref('');
const messagesRef = ref<HTMLDivElement | null>(null);

const activeSession = computed(() =>
  sessions.value.find((s) => s.id === activeSessionId.value)
);

// 检查登录状态并验证 token
onMounted(async () => {
  const storedUser = localStorage.getItem('user');
  const storedToken = localStorage.getItem('token');
  
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
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.push('/login');
        return;
      }
      // 更新用户信息（以防后端有更新）
      if (verifyResponse.user) {
        currentUser.value = verifyResponse.user;
        localStorage.setItem('user', JSON.stringify(verifyResponse.user));
      }
    } catch (error) {
      console.error('Token 验证失败:', error);
      // Token 验证失败，清除并跳转登录
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      router.push('/login');
      return;
    }

    loadSessions();
  } catch (error) {
    console.error('解析用户信息失败:', error);
    // 清除无效数据
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    router.push('/login');
  }
});

// 组件卸载时移除事件监听
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

// 加载会话列表
const loadSessions = async () => {
  if (!currentUser.value || !token.value) return;

  loading.value = true;
  try {
    const response = await customerServiceApi.getSessions(currentUser.value.id, token.value);
    if (response.success) {
      sessions.value = response.sessions.map((s: any) => ({
        id: s.id,
        userName: s.userName,
        isVip: s.isVip,
        category: s.category || '待分类',
        lastMessage: s.lastMessage || '',
        lastTime: s.lastTime || '刚刚',
        duration: s.duration || '00:00',
        unread: s.unread || 0
      }));

      // 自动选择第一个会话
      if (sessions.value.length > 0 && !activeSessionId.value) {
        selectSession(sessions.value[0].id);
      }
    }
  } catch (error) {
    console.error('加载会话列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 选择会话
const selectSession = async (id: string) => {
  activeSessionId.value = id;
  await loadMessages(id);
};

// 加载消息
const loadMessages = async (sessionId: string) => {
  if (!currentUser.value || !token.value) return;

  try {
    const response = await customerServiceApi.getMessages(sessionId, currentUser.value.id, token.value);
    if (response.success) {
      messages.value = (response.messages || []).map((m: any) => ({
        id: m.id,
        from: m.from || 'user',
        text: m.text || '',
        time: m.time || '刚刚'
      }));
      scrollToBottom();
    } else {
      console.error('加载消息失败:', response.message);
      // 如果是 token 失效，跳转到登录页
      if (response.message?.includes('Token') || response.message?.includes('无效')) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        router.push('/login');
      }
    }
  } catch (error: any) {
    console.error('加载消息失败:', error);
    // 如果是 401 或 403，跳转到登录页
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      router.push('/login');
    }
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

// 发送消息
const handleSend = async () => {
  const text = inputText.value.trim();
  if (!text || !activeSessionId.value || !currentUser.value || !token.value) return;

  // 检查消息长度
  if (text.length > 5000) {
    alert('消息内容过长，不能超过5000个字符');
    return;
  }

  const tempMessageId = `m-${Date.now()}`;
  try {
    // 先添加到本地消息列表（乐观更新）
    const tempMessage = {
      id: tempMessageId,
      from: 'agent' as const,
      text,
      time: '现在'
    };
    messages.value.push(tempMessage);
    const originalText = inputText.value;
    inputText.value = '';
    scrollToBottom();

    // 发送到后端
    const response = await customerServiceApi.sendMessage({
      session_id: activeSessionId.value,
      from_user_id: currentUser.value.id,
      message: text,
      token: token.value
    });

    if (!response.success) {
      throw new Error(response.message || '发送失败');
    }

    // 重新加载消息以确保同步（使用真实的消息ID）
    await loadMessages(activeSessionId.value);
  } catch (error: any) {
    console.error('发送消息失败:', error);
    // 移除临时消息
    messages.value = messages.value.filter(m => m.id !== tempMessageId);
    // 恢复输入框内容
    inputText.value = text;
    // 显示错误提示
    const errorMsg = error.response?.data?.message || error.message || '发送失败，请稍后重试';
    alert(errorMsg);
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

const handleLogout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
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
}

.sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
}

.sidebar.detail {
  border-right: none;
  border-left: 1px solid rgba(255, 255, 255, 0.25);
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(20px);
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
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.3);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
}

.tab {
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 11px;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.18s ease;
}

.tab.active {
  background: #ffffff;
  color: var(--accent);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
}

.session-list {
  list-style: none;
  margin: 0;
  padding: 10px;
  overflow-y: auto;
  flex: 1;
}

.session-item {
  padding: 10px 11px;
  border-radius: 14px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 5px;
  margin-bottom: 8px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all 0.16s ease;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(51, 112, 255, 0.35);
}

.session-item.active {
  background: rgba(232, 241, 255, 0.14);
  border-color: var(--accent-soft);
  box-shadow: 0 12px 22px rgba(15, 23, 42, 0.12);
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
}

.session-time {
  font-size: 11px;
  color: var(--text-secondary);
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
  color: var(--text-secondary);
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
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: rgba(255, 255, 255, 0.0035);
  backdrop-filter: blur(22px);
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
}

.msg-bubble {
  max-width: 72%;
  padding: 10px 12px 8px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.04);
  box-shadow: var(--shadow-subtle);
  color: #0f172a;
  text-shadow: 0 1px 2px rgba(255, 255, 255, 0.45);
}

.from-agent .msg-bubble {
  background: rgba(229, 239, 255, 0.08);
  border-color: rgba(51, 112, 255, 0.04);
}

.msg-text {
  font-size: 13px;
  line-height: 1.55;
  color: #0f172a;
}

.msg-time {
  margin-top: 4px;
  font-size: 10px;
  color: rgba(15, 23, 42, 0.55);
  text-align: right;
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
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
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
