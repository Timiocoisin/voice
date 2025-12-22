<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">VC</div>
      <h1 class="login-title">变声器客服工作台</h1>
      <p class="login-subtitle">为变声器用户提供专业、快速的在线支持</p>

      <form class="login-form" @submit.prevent="handleLogin">
        <label class="form-label">
          账号
          <input
            v-model="form.username"
            type="text"
            class="form-input"
            placeholder="请输入员工账号"
          />
        </label>

        <label class="form-label">
          密码
          <input
            v-model="form.password"
            type="password"
            class="form-input"
            placeholder="请输入密码"
          />
        </label>

        <button class="primary-button" type="submit">
          进入工作台
        </button>
      </form>

      <p class="login-tip">当前为前端演示环境，登录信息不会提交到后端。</p>
      <p class="switch-tip">
        还没有账号？
        <router-link to="/register" class="link">去注册</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const form = reactive({
  username: '',
  password: ''
});

const handleLogin = () => {
  if (!form.username || !form.password) {
    return;
  }
  router.push('/workspace');
};
</script>

<style scoped>
.login-page {
  flex: 1;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 18px;
  background: radial-gradient(circle at 15% 20%, rgba(90, 200, 250, 0.2), transparent 35%),
    radial-gradient(circle at 85% 10%, rgba(79, 139, 255, 0.18), transparent 32%),
    radial-gradient(circle at 50% 100%, rgba(255, 255, 255, 0.15), transparent 40%);
}

.login-card {
  width: 460px;
  padding: 40px 36px 32px;
  border-radius: 22px;
  backdrop-filter: blur(26px);
  /* 更接近纯玻璃：约 50% 透明度 */
  background: rgba(255, 255, 255, 0.5);
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.7);
  position: relative;
  overflow: hidden;
}

.login-card::before {
  content: '';
  position: absolute;
  inset: -30% 40% auto auto;
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(79, 139, 255, 0.25), rgba(255, 255, 255, 0));
  filter: blur(18px);
  opacity: 0.8;
  pointer-events: none;
}

.login-card::after {
  content: '';
  position: absolute;
  inset: auto auto -28% -10%;
  width: 240px;
  height: 240px;
  background: radial-gradient(circle, rgba(90, 200, 250, 0.22), rgba(255, 255, 255, 0));
  filter: blur(18px);
  opacity: 0.8;
  pointer-events: none;
}

.login-logo {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #4f8bff, #5ac8fa);
  color: #ffffff;
  font-weight: 800;
  font-size: 18px;
  box-shadow: 0 16px 30px rgba(79, 139, 255, 0.35);
  margin-bottom: 18px;
  position: relative;
  z-index: 1;
}

.login-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.01em;
  position: relative;
  z-index: 1;
}

.login-subtitle {
  margin: 10px 0 26px;
  font-size: 13px;
  color: var(--text-secondary);
  position: relative;
  z-index: 1;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: relative;
  z-index: 1;
}

.form-label {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  color: var(--text-secondary);
  gap: 6px;
}

.form-input {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.7);
  color: var(--text-primary);
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.form-input::placeholder {
  color: #bcc1c7;
}

.form-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent-soft), 0 10px 24px rgba(51, 112, 255, 0.18);
  background: #ffffff;
}

.primary-button {
  margin-top: 8px;
  width: 100%;
  border: none;
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, #3370ff, #5ac8fa);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 16px 34px rgba(51, 112, 255, 0.3);
  transition: transform 0.08s ease, box-shadow 0.08s ease, filter 0.08s ease;
}

.primary-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

.primary-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 38px rgba(51, 112, 255, 0.32);
  filter: brightness(1.02);
}

.login-tip {
  margin-top: 14px;
  font-size: 11px;
  color: var(--text-secondary);
  position: relative;
  z-index: 1;
}

.switch-tip {
  margin: 8px 0 0;
  font-size: 12px;
  color: #6f7680;
  position: relative;
  z-index: 1;
}

.link {
  color: #3370ff;
  text-decoration: none;
  font-weight: 600;
}

.link:hover {
  text-decoration: underline;
}

@media (max-width: 960px) {
  .login-page {
    padding: 32px 16px;
  }
  .login-card {
    width: 100%;
    max-width: 420px;
  }
}

@media (max-width: 600px) {
  .login-card {
    padding-inline: 22px;
  }
}
</style>
