<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-logo">VC</div>
      <h1 class="login-title">变声器客服工作台</h1>
      <p class="login-subtitle">为变声器用户提供专业、快速的在线支持</p>

      <form class="login-form" @submit.prevent="handleLogin">
        <label class="form-label">
          邮箱
          <input
            v-model="form.email"
            type="email"
            class="form-input"
            :class="{ 'input-error': fieldErrors.email }"
            placeholder="请输入邮箱"
            @input="clearFieldError('email')"
            @blur="fieldErrors.email = !emailValidation.valid ? emailValidation.message : ''"
          />
          <span v-if="fieldErrors.email" class="field-error">{{ fieldErrors.email }}</span>
        </label>

        <label class="form-label">
          密码
          <input
            v-model="form.password"
            type="password"
            class="form-input"
            :class="{ 'input-error': fieldErrors.password }"
            placeholder="请输入密码"
            @input="clearFieldError('password')"
            @blur="fieldErrors.password = !passwordValidation.valid ? passwordValidation.message : ''"
            @keyup.enter="handleLogin"
          />
          <span v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</span>
        </label>

        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '进入工作台' }}
        </button>
      </form>

      <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>
      <div class="switch-tip">
        <span>
          还没有账号？
          <router-link to="/register" class="link">去注册</router-link>
        </span>
        <router-link to="/forgot-password" class="link">忘记密码？</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { customerServiceApi } from '@/api/client';
import { validateEmail, validatePassword } from '@/utils/validation';

const router = useRouter();

const form = reactive({
  email: '',
  password: ''
});

const loading = ref(false);
const errorMessage = ref('');
const fieldErrors = reactive({
  email: '',
  password: ''
});

// 实时验证
const emailValidation = computed(() => validateEmail(form.email));
const passwordValidation = computed(() => validatePassword(form.password));

// 检查是否已登录
onMounted(() => {
  const token = sessionStorage.getItem('token');
  const user = sessionStorage.getItem('user');
  if (token && user) {
    // 已登录，跳转到工作台
    router.push('/workspace');
  }
});

// 监听输入变化，清除错误
const clearFieldError = (field: keyof typeof fieldErrors) => {
  fieldErrors[field] = '';
  errorMessage.value = '';
};

const handleLogin = async () => {
  // 清除之前的错误
  errorMessage.value = '';
  Object.keys(fieldErrors).forEach(key => {
    fieldErrors[key as keyof typeof fieldErrors] = '';
  });

  // 验证所有字段
  const emailValid = validateEmail(form.email);
  const passwordValid = validatePassword(form.password);

  if (!emailValid.valid) {
    fieldErrors.email = emailValid.message;
    return;
  }
  if (!passwordValid.valid) {
    fieldErrors.password = passwordValid.message;
    return;
  }

  // 防止重复提交
  if (loading.value) {
    return;
  }

  loading.value = true;
  errorMessage.value = '';

  try {
    const response = await customerServiceApi.login({
      email: form.email.trim().toLowerCase(),
      password: form.password,
    });

    if (response.success) {
      // 保存 token 和用户信息到 sessionStorage（刷新页面不丢失，关闭浏览器清空）
      if (response.token) {
        sessionStorage.setItem('token', response.token);
      }
      if (response.user) {
        sessionStorage.setItem('user', JSON.stringify(response.user));
      }
      // 跳转到工作台
      router.push('/workspace');
    } else {
      errorMessage.value = response.message || '登录失败，请稍后重试';
    }
  } catch (error: any) {
    const status = error.response?.status;
    let errorMsg = '登录失败，请稍后重试';
    
    if (status === 401 || status === 403) {
      errorMsg = error.response?.data?.message || '邮箱或密码错误，或账号无权限';
    } else if (status === 400) {
      errorMsg = error.response?.data?.message || '请求参数错误';
    } else if (!error.response) {
      errorMsg = '网络连接失败，请检查网络后重试';
    } else {
      errorMsg = error.response?.data?.message || error.message || '登录失败，请稍后重试';
    }
    
    errorMessage.value = errorMsg;
    
    // 如果返回了剩余尝试次数，显示更详细的提示
    if (error.response?.data?.remaining_attempts !== undefined) {
      const remaining = error.response.data.remaining_attempts;
      if (remaining > 0) {
        errorMessage.value = `${errorMsg}（还可尝试 ${remaining} 次）`;
      }
    }
  } finally {
    loading.value = false;
  }
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
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
