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


  // 获取聊天消息（已删除：改用 WebSocket get_session_messages）

  // 发送消息
  /**
   * 发送消息（已废弃，请使用 WebSocket）
   * 
   * 注意：HTTP 消息发送接口已移除，现在必须使用 WebSocket 发送消息。
   * 请使用 WebSocket 客户端发送消息，参考：
   * - backend/websocket/README.md
   * - 需要在前端实现 WebSocket 客户端
   */
  sendMessage: async (data: {
    session_id: string;
    from_user_id: number;
    to_user_id?: number;
    message: string;
    token: string;
    reply_to_message_id?: number;
  }) => {
    throw new Error(
      'HTTP 消息发送接口已移除。请使用 WebSocket 发送消息。\n' +
      '参考: backend/websocket/README.md'
    );
    // 旧代码（已移除）
    // const response = await api.post('/api/customer_service/send_message', data);
    // return response.data;
  },

  // 撤回消息（已删除：改用 WebSocket recall_message）

  // 获取被引用的消息详情（已删除：引用消息摘要由服务端随消息推送）

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

