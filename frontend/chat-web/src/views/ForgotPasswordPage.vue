<template>
  <div class="forgot-password-page">
    <div class="forgot-password-card">
      <div class="forgot-password-logo">VC</div>
      <h1 class="forgot-password-title">忘记密码</h1>
      <p class="forgot-password-subtitle">请输入您的邮箱，我们将发送密码重置链接</p>

      <form class="forgot-password-form" @submit.prevent="handleForgotPassword">
        <label class="form-label">
          邮箱
          <input
            v-model="form.email"
            type="email"
            class="form-input"
            :class="{ 'input-error': fieldErrors.email }"
            placeholder="请输入注册邮箱"
            @input="clearFieldError('email')"
            @blur="fieldErrors.email = !emailValidation.valid ? emailValidation.message : ''"
          />
          <span v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</span>
        </label>

        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '发送中...' : '发送重置链接' }}
        </button>
      </form>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <p v-if="successMessage" class="success-message">{{ successMessage }}</p>
      <p class="switch-tip">
        想起密码了？
        <router-link to="/login" class="link">返回登录</router-link>
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { customerServiceApi } from '@/api/client';
import { validateEmail } from '@/utils/validation';

const router = useRouter();

const form = reactive({
  email: ''
});

const loading = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const fieldErrors = reactive({
  email: ''
});

// 实时验证
const emailValidation = computed(() => validateEmail(form.email));

// 监听输入变化，清除错误
const clearFieldError = (field: keyof typeof fieldErrors) => {
  fieldErrors[field] = '';
  errorMessage.value = '';
  successMessage.value = '';
};

const handleForgotPassword = async () => {
  // 清除之前的错误
  errorMessage.value = '';
  successMessage.value = '';
  Object.keys(fieldErrors).forEach(key => {
    fieldErrors[key as keyof typeof fieldErrors] = '';
  });

  // 验证邮箱
  const emailValid = validateEmail(form.email);
  if (!emailValid.valid) {
    fieldErrors.email = emailValid.message;
    return;
  }

  // 防止重复提交
  if (loading.value) {
    return;
  }

  loading.value = true;

  try {
    const response = await customerServiceApi.forgotPassword(form.email.trim().toLowerCase());

    if (response.success) {
      successMessage.value = response.message || '重置链接已发送到您的邮箱，请查收';
      // 3秒后跳转到登录页
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    } else {
      errorMessage.value = response.message || '发送失败，请稍后重试';
    }
  } catch (error: any) {
    const msg = error.response?.data?.message;
    errorMessage.value = msg || '发送失败，请稍后重试';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.forgot-password-page {
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

.forgot-password-card {
  width: 460px;
  padding: 40px 36px 32px;
  border-radius: 22px;
  backdrop-filter: blur(26px);
  background: rgba(255, 255, 255, 0.5);
  box-shadow: 0 24px 56px rgba(15, 23, 42, 0.22);
  border: 1px solid rgba(255, 255, 255, 0.7);
  position: relative;
  overflow: hidden;
}

.forgot-password-card::before {
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

.forgot-password-card::after {
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

.forgot-password-logo {
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

.forgot-password-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.01em;
  position: relative;
  z-index: 1;
}

.forgot-password-subtitle {
  margin: 10px 0 26px;
  font-size: 13px;
  color: var(--text-secondary);
  position: relative;
  z-index: 1;
}

.forgot-password-form {
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

.error-message {
  margin-top: 12px;
  font-size: 12px;
  color: #ef4444;
  text-align: center;
  padding: 8px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: 8px;
}

.success-message {
  margin-top: 12px;
  font-size: 12px;
  color: #10b981;
  text-align: center;
  padding: 8px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 8px;
}

.field-error {
  display: block;
  margin-top: 4px;
  font-size: 11px;
  color: #ef4444;
}

.input-error {
  border-color: #ef4444 !important;
  background: rgba(239, 68, 68, 0.05) !important;
}

.input-error:focus {
  box-shadow: 0 0 0 1px rgba(239, 68, 68, 0.3) !important;
}

@media (max-width: 960px) {
  .forgot-password-page {
    padding: 32px 16px;
  }
  .forgot-password-card {
    width: 100%;
    max-width: 420px;
  }
}

@media (max-width: 600px) {
  .forgot-password-card {
    padding-inline: 22px;
  }
}
</style>

