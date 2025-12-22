<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">VC</div>
      <h1 class="auth-title">创建客服账号</h1>
      <p class="auth-subtitle">注册后可登录客服工作台</p>

      <form class="auth-form" @submit.prevent="handleRegister">
        <label class="form-label">
          账号
          <input
            v-model="form.username"
            type="text"
            class="form-input"
            placeholder="请输入账号"
          />
        </label>

        <label class="form-label">
          邮箱
          <input
            v-model="form.email"
            type="email"
            class="form-input"
            placeholder="用于找回或通知"
          />
        </label>

        <label class="form-label">
          密码
          <input
            v-model="form.password"
            type="password"
            class="form-input"
            placeholder="至少 6 位"
          />
        </label>

        <label class="form-label">
          确认密码
          <input
            v-model="form.confirm"
            type="password"
            class="form-input"
            placeholder="再次输入密码"
          />
        </label>

        <button class="primary-button" type="submit">
          完成注册
        </button>

        <p class="switch-tip">
          已有账号？
          <router-link to="/login" class="link">去登录</router-link>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirm: ''
});

const handleRegister = () => {
  if (!form.username || !form.email || !form.password || form.password !== form.confirm) {
    return;
  }
  router.push('/login');
};
</script>

<style scoped>
.auth-page {
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

.auth-card {
  width: 460px;
  padding: 40px 36px 34px;
  border-radius: 22px;
  backdrop-filter: blur(24px);
  /* 更接近纯玻璃：约 50% 透明度 */
  background: rgba(255, 255, 255, 0.5);
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.7);
  position: relative;
  overflow: hidden;
}

.auth-logo {
  width: 50px;
  height: 50px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #4f8bff, #5ac8fa);
  color: #fff;
  font-weight: 700;
  font-size: 18px;
  box-shadow: 0 16px 30px rgba(79, 139, 255, 0.35);
  margin-bottom: 18px;
}

.auth-title {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.auth-subtitle {
  margin: 8px 0 24px;
  font-size: 13px;
  color: #6f7680;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-label {
  display: flex;
  flex-direction: column;
  font-size: 13px;
  color: #6f7680;
  gap: 6px;
}

.form-input {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.7);
  color: #0f172a;
  font-size: 13px;
  outline: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
}

.form-input::placeholder {
  color: #a0a7b0;
}

.form-input:focus {
  border-color: #3370ff;
  box-shadow: 0 0 0 1px rgba(51, 112, 255, 0.2);
  background: #fff;
}

.primary-button {
  margin-top: 6px;
  width: 100%;
  border: none;
  padding: 12px 14px;
  border-radius: 14px;
  background: linear-gradient(135deg, #3370ff, #5ac8fa);
  color: #f9fafb;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  box-shadow: 0 12px 28px rgba(51, 112, 255, 0.25);
  transition: transform 0.12s ease, box-shadow 0.12s ease, filter 0.12s ease;
}

.primary-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  box-shadow: none;
}

.primary-button:not(:disabled):hover {
  transform: translateY(-1px);
  box-shadow: 0 18px 36px rgba(51, 112, 255, 0.32);
  filter: brightness(1.02);
}

.switch-tip {
  margin: 10px 0 0;
  font-size: 12px;
  color: #6f7680;
}

.link {
  color: #3370ff;
  text-decoration: none;
}

.link:hover {
  text-decoration: underline;
}

@media (max-width: 600px) {
  .auth-card {
    width: 100%;
    max-width: 380px;
    padding-inline: 22px;
  }
}
</style>

