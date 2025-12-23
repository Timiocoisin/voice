<template>
  <div class="reset-password-page">
    <div class="reset-password-card">
      <!-- 成功状态：显示成功消息和倒计时 -->
      <div v-if="successMessage" class="success-container">
        <div class="reset-password-logo">VC</div>
        <p class="success-title">密码重置成功！</p>
        <p class="success-message-text">{{ successMessage }}</p>
        <p class="countdown-tip">
          3 秒后自动跳转到登录页面...
        </p>
        <button class="primary-button" @click="router.push('/login')">
          立即前往登录
        </button>
      </div>

      <!-- 表单状态：显示重置表单 -->
      <template v-else>
        <div class="reset-password-logo">VC</div>
        <h1 class="reset-password-title">重置密码</h1>
        <p class="reset-password-subtitle">请输入您的新密码</p>
        <form class="reset-password-form" @submit.prevent="handleResetPassword">
        <label class="form-label">
          新密码
          <input
            v-model="form.newPassword"
            type="password"
            class="form-input"
            :class="{ 'input-error': fieldErrors.newPassword }"
            placeholder="至少 8 位，包含字母和符号"
            @input="clearFieldError('newPassword')"
            @blur="fieldErrors.newPassword = !passwordValidation.valid ? passwordValidation.message : ''"
          />
          <span v-if="fieldErrors.newPassword" class="field-error">{{ fieldErrors.newPassword }}</span>
        </label>

        <label class="form-label">
          确认密码
          <input
            v-model="form.confirmPassword"
            type="password"
            class="form-input"
            :class="{ 'input-error': fieldErrors.confirmPassword }"
            placeholder="请再次输入新密码"
            @input="clearFieldError('confirmPassword')"
            @blur="checkPasswordMatch"
          />
          <span v-if="fieldErrors.confirmPassword" class="field-error">{{ fieldErrors.confirmPassword }}</span>
        </label>

        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '重置中...' : '重置密码' }}
        </button>
        </form>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
        <p class="switch-tip">
          <router-link to="/login" class="link">返回登录</router-link>
        </p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { customerServiceApi } from '@/api/client';
import { validatePassword } from '@/utils/validation';

const router = useRouter();
const route = useRoute();

const form = reactive({
  newPassword: '',
  confirmPassword: ''
});

const loading = ref(false);
const errorMessage = ref('');
const successMessage = ref('');
const token = ref<string>('');
const fieldErrors = reactive({
  newPassword: '',
  confirmPassword: ''
});

// 实时验证
const passwordValidation = computed(() => validatePassword(form.newPassword, 8, 50));

// 检查密码是否匹配
const checkPasswordMatch = () => {
  if (form.confirmPassword && form.newPassword !== form.confirmPassword) {
    fieldErrors.confirmPassword = '两次输入的密码不一致';
  } else {
    fieldErrors.confirmPassword = '';
  }
};

// 监听输入变化，清除错误
const clearFieldError = (field: keyof typeof fieldErrors) => {
  fieldErrors[field] = '';
  errorMessage.value = '';
  successMessage.value = '';
};

onMounted(() => {
  // 从URL参数获取token
  const tokenParam = route.query.token as string;
  if (!tokenParam) {
    errorMessage.value = '重置链接无效，缺少token参数';
    return;
  }
  token.value = tokenParam;
});

const handleResetPassword = async () => {
  // 清除之前的错误
  errorMessage.value = '';
  successMessage.value = '';
  Object.keys(fieldErrors).forEach(key => {
    fieldErrors[key as keyof typeof fieldErrors] = '';
  });

  // 验证新密码（重置密码需要强度检查）
  const passwordValid = validatePassword(form.newPassword, 8, 50, true);
  if (!passwordValid.valid) {
    fieldErrors.newPassword = passwordValid.message;
    return;
  }

  // 检查密码是否匹配
  if (form.newPassword !== form.confirmPassword) {
    fieldErrors.confirmPassword = '两次输入的密码不一致';
    return;
  }

  if (!token.value) {
    errorMessage.value = '重置链接无效';
    return;
  }

  // 防止重复提交
  if (loading.value) {
    return;
  }

  loading.value = true;

  try {
    const response = await customerServiceApi.resetPassword(token.value, form.newPassword);

    if (response.success) {
      successMessage.value = response.message || '密码重置成功，请使用新密码登录';
      // 3秒后跳转到登录页
      setTimeout(() => {
        router.push('/login');
      }, 3000);
    } else {
      errorMessage.value = response.message || '重置失败，请稍后重试';
    }
  } catch (error: any) {
    const msg = error.response?.data?.message;
    errorMessage.value = msg || '重置失败，请稍后重试';
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.reset-password-page {
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

.reset-password-card {
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

.reset-password-card::before {
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

.reset-password-card::after {
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

.reset-password-logo {
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

.reset-password-title {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.01em;
  position: relative;
  z-index: 1;
}

.reset-password-subtitle {
  margin: 10px 0 26px;
  font-size: 13px;
  color: var(--text-secondary);
  position: relative;
  z-index: 1;
}

.reset-password-form {
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
  text-align: center;
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

.success-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 20px 0;
  position: relative;
  z-index: 1;
}

.success-title {
  margin: 20px 0 12px;
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
}

.success-message-text {
  margin: 0 0 24px;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}

.countdown-tip {
  margin: 0 0 24px;
  font-size: 13px;
  color: #94a3b8;
}

@media (max-width: 960px) {
  .reset-password-page {
    padding: 32px 16px;
  }
  .reset-password-card {
    width: 100%;
    max-width: 420px;
  }
}

@media (max-width: 600px) {
  .reset-password-card {
    padding-inline: 22px;
  }
}
</style>

