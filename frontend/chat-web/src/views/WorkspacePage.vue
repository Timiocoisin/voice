<template>
  <div class="workspace">
    <header class="workspace-header">
      <div class="brand">
        <span class="brand-logo">VC</span>
        <span class="brand-name">变声器客服工作台</span>
      </div>
      <div class="header-actions">
        <span class="agent-name">客服：小音</span>
        <span class="status-dot online"></span>
        <span class="status-text">在线</span>
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
import { computed, onMounted, ref, watch } from 'vue';

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

const sessions = ref<Session[]>([
  {
    id: 's1',
    userName: '用户-1234',
    isVip: true,
    category: '没有声音',
    lastMessage: '游戏里没有声音怎么办？',
    lastTime: '刚刚',
    duration: '03:25',
    unread: 2
  },
  {
    id: 's2',
    userName: '用户-5678',
    isVip: false,
    category: '安装失败',
    lastMessage: '提示我驱动安装失败',
    lastTime: '5 分钟前',
    duration: '12:10',
    unread: 0
  }
]);

const messages = ref<ChatMessage[]>([
  {
    id: 'm1',
    from: 'user',
    text: '客服你好，我这边游戏里完全没有声音。',
    time: '10:01'
  },
  {
    id: 'm2',
    from: 'agent',
    text: '您好，请问在系统里播放音乐时有声音吗？',
    time: '10:02'
  }
]);

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

const activeSessionId = ref<string>('s1');
const inputText = ref('');
const messagesRef = ref<HTMLDivElement | null>(null);

const activeSession = computed(() =>
  sessions.value.find((s) => s.id === activeSessionId.value)
);

const selectSession = (id: string) => {
  activeSessionId.value = id;
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

onMounted(() => {
  scrollToBottom();
});

const handleSend = () => {
  const text = inputText.value.trim();
  if (!text) return;

  messages.value.push({
    id: `m-${Date.now()}`,
    from: 'agent',
    text,
    time: '现在'
  });

  inputText.value = '';
};

const appendQuickReply = (content: string) => {
  if (!content) return;
  if (!inputText.value) {
    inputText.value = content;
  } else {
    inputText.value = `${inputText.value}\n${content}`;
  }
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

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--success);
  box-shadow: 0 0 0 5px rgba(34, 197, 94, 0.25);
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
