import axios from 'axios';

const BASE_URL = 'http://127.0.0.1:8000';

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器：添加 token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器：处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 客服系统 API
export const customerServiceApi = {
  // 注册
  register: async (data: { email: string; password: string; username: string }) => {
    const response = await api.post('/api/customer_service/register', data);
    return response.data;
  },

  // 登录
  login: async (data: { email: string; password: string }) => {
    const response = await api.post('/api/customer_service/login', data);
    return response.data;
  },

  // 验证 token
  verifyToken: async (token: string) => {
    const response = await api.post('/api/customer_service/verify_token', { token });
    return response.data;
  },

  // 获取会话列表
  getSessions: async (userId: number, token: string, type: 'my' | 'pending' = 'my') => {
    const response = await api.post('/api/customer_service/sessions', {
      user_id: userId,
      token: token,
      type: type,
    });
    return response.data;
  },

  // 获取待接入会话列表
  getPendingSessions: async (userId: number, token: string) => {
    const response = await api.post('/api/customer_service/pending_sessions', {
      user_id: userId,
      token: token,
    });
    return response.data;
  },

  // 接入会话（从待接入移到我的会话）
  acceptSession: async (userId: number, sessionId: string, token: string) => {
    const response = await api.post('/api/customer_service/accept_session', {
      user_id: userId,
      session_id: sessionId,
      token: token,
    });
    return response.data;
  },

  // 更新客服状态
  updateStatus: async (userId: number, status: string, token: string) => {
    const response = await api.post('/api/customer_service/update_status', {
      user_id: userId,
      status: status,
      token: token,
    });
    return response.data;
  },

  // 获取聊天消息
  getMessages: async (sessionId: string, userId: number, token: string) => {
    const response = await api.post('/api/customer_service/messages', {
      session_id: sessionId,
      user_id: userId,
      token: token,
    });
    return response.data;
  },

  // 发送消息
  sendMessage: async (data: {
    session_id: string;
    from_user_id: number;
    to_user_id?: number;
    message: string;
    token: string;
    reply_to_message_id?: number;
  }) => {
    const response = await api.post('/api/customer_service/send_message', data);
    return response.data;
  },

  // 撤回消息
  recallMessage: async (data: { message_id: number; user_id: number; token: string }) => {
    const response = await api.post('/api/message/recall', data);
    return response.data;
  },

  // 编辑消息
  editMessage: async (data: { message_id: number; user_id: number; new_content: string; token: string }) => {
    const response = await api.post('/api/message/edit', data);
    return response.data;
  },

  // 获取被引用的消息详情
  getReplyMessage: async (data: { message_id: number; token?: string }) => {
    const response = await api.post('/api/message/reply', data);
    return response.data;
  },

  // 忘记密码
  forgotPassword: async (email: string) => {
    const response = await api.post('/api/forgot_password', { email });
    return response.data;
  },

  // 重置密码
  resetPassword: async (token: string, newPassword: string) => {
    const response = await api.post('/api/reset_password', {
      token,
      new_password: newPassword,
    });
    return response.data;
  },
};

export default api;

