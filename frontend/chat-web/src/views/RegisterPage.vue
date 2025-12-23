<template>
  <div class="auth-page">
    <div class="auth-card">
      <div class="auth-logo">VC</div>
      <h1 class="auth-title">创建客服账号</h1>
      <p class="auth-subtitle">注册后可登录客服工作台</p>

      <form class="auth-form" @submit.prevent="handleRegister">
        <label class="form-label">
          昵称
          <input
            v-model="form.username"
            type="text"
            class="form-input"
            :class="{ 'input-error': fieldErrors.username }"
            placeholder="请输入昵称（2-20个字符）"
            @input="clearFieldError('username')"
            @blur="fieldErrors.username = !usernameValidation.valid ? usernameValidation.message : ''"
          />
          <span v-if="fieldErrors.username" class="field-error">{{ fieldErrors.username }}</span>
        </label>

        <label class="form-label">
          邮箱
          <input
            v-model="form.email"
            type="email"
            class="form-input"
            :class="{ 'input-error': fieldErrors.email }"
            placeholder="用于找回账号"
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
            placeholder="至少 8 位，包含字母和符号"
            @input="clearFieldError('password')"
            @blur="fieldErrors.password = !passwordValidation.valid ? passwordValidation.message : ''"
          />
          <span v-if="fieldErrors.password" class="field-error">{{ fieldErrors.password }}</span>
        </label>

        <label class="form-label">
          确认密码
          <input
            v-model="form.confirm"
            type="password"
            class="form-input"
            :class="{ 'input-error': fieldErrors.confirm }"
            placeholder="再次输入密码"
            @input="clearFieldError('confirm')"
            @blur="fieldErrors.confirm = !confirmValidation.valid ? confirmValidation.message : ''"
          />
          <span v-if="fieldErrors.confirm" class="field-error">{{ fieldErrors.confirm }}</span>
        </label>

        <button class="primary-button" type="submit" :disabled="loading">
          {{ loading ? '注册中...' : '完成注册' }}
        </button>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <p class="switch-tip">
          已有账号？
          <router-link to="/login" class="link">去登录</router-link>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { customerServiceApi } from '@/api/client';
import { validateEmail, validatePassword, validateUsername, validateConfirmPassword } from '@/utils/validation';

const router = useRouter();

const form = reactive({
  username: '',
  email: '',
  password: '',
  confirm: ''
});

const loading = ref(false);
const errorMessage = ref('');
const fieldErrors = reactive({
  username: '',
  email: '',
  password: '',
  confirm: ''
});

// 实时验证
const usernameValidation = computed(() => validateUsername(form.username));
const emailValidation = computed(() => validateEmail(form.email));
const passwordValidation = computed(() => validatePassword(form.password, 8, 50, true)); // 注册需要强度检查
const confirmValidation = computed(() => validateConfirmPassword(form.password, form.confirm));

// 监听输入变化，清除错误
const clearFieldError = (field: keyof typeof fieldErrors) => {
  fieldErrors[field] = '';
  errorMessage.value = '';
};

const handleRegister = async () => {
  // 清除之前的错误
  errorMessage.value = '';
  Object.keys(fieldErrors).forEach(key => {
    fieldErrors[key as keyof typeof fieldErrors] = '';
  });

  // 验证所有字段
  const usernameValid = validateUsername(form.username);
  const emailValid = validateEmail(form.email);
  const passwordValid = validatePassword(form.password, 8, 50, true); // 注册需要强度检查
  const confirmValid = validateConfirmPassword(form.password, form.confirm);

  if (!usernameValid.valid) {
    fieldErrors.username = usernameValid.message;
    return;
  }
  if (!emailValid.valid) {
    fieldErrors.email = emailValid.message;
    return;
  }
  if (!passwordValid.valid) {
    fieldErrors.password = passwordValid.message;
    return;
  }
  if (!confirmValid.valid) {
    fieldErrors.confirm = confirmValid.message;
    return;
  }

  // 防止重复提交
  if (loading.value) {
    return;
  }

  loading.value = true;
  errorMessage.value = '';

  try {
    const response = await customerServiceApi.register({
      username: form.username.trim(),
      email: form.email.trim().toLowerCase(),
      password: form.password,
    });

    if (response.success) {
      // 保存 token 和用户信息
      if (response.token) {
        localStorage.setItem('token', response.token);
      }
      if (response.user) {
        localStorage.setItem('user', JSON.stringify(response.user));
      }
      // 跳转到工作台
      router.push('/workspace');
    } else {
      errorMessage.value = response.message || '注册失败，请稍后重试';
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.message || error.message || '注册失败，请稍后重试';
    errorMessage.value = errorMsg;
    
    // 如果是网络错误，给出更友好的提示
    if (!error.response) {
      errorMessage.value = '网络连接失败，请检查网络后重试';
    }
  } finally {
    loading.value = false;
  }
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

@media (max-width: 600px) {
  .auth-card {
    width: 100%;
    max-width: 380px;
    padding-inline: 22px;
  }
}
</style>

