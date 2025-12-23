/**
 * 前端表单验证工具
 */

// 邮箱验证
export function validateEmail(email: string): { valid: boolean; message: string } {
  if (!email || !email.trim()) {
    return { valid: false, message: '邮箱不能为空' };
  }
  const emailRegex = /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/;
  if (!emailRegex.test(email)) {
    return { valid: false, message: '邮箱格式不正确' };
  }
  if (email.length > 100) {
    return { valid: false, message: '邮箱长度不能超过100个字符' };
  }
  return { valid: true, message: '' };
}

// 密码验证
export function validatePassword(
  password: string,
  minLength: number = 6,
  maxLength: number = 50,
  requireStrength: boolean = false
): { valid: boolean; message: string } {
  if (!password || !password.trim()) {
    return { valid: false, message: '密码不能为空' };
  }
  if (password.length < minLength) {
    return { valid: false, message: `密码至少${minLength}位` };
  }
  if (password.length > maxLength) {
    return { valid: false, message: `密码长度不能超过${maxLength}个字符` };
  }
  
  // 强度检查：至少包含一个字母和一个符号
  if (requireStrength || password.length >= 6) {
    const hasLetter = /[a-zA-Z]/.test(password);
    const hasSymbol = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?~`]/.test(password);
    
    if (!hasLetter) {
      return { valid: false, message: '密码至少包含一个字母' };
    }
    if (!hasSymbol) {
      return { valid: false, message: '密码至少包含一个符号' };
    }
  }
  
  return { valid: true, message: '' };
}

// 用户名验证
export function validateUsername(username: string): { valid: boolean; message: string } {
  if (!username || !username.trim()) {
    return { valid: false, message: '昵称不能为空' };
  }
  const trimmed = username.trim();
  if (trimmed.length < 2) {
    return { valid: false, message: '昵称至少2个字符' };
  }
  if (trimmed.length > 20) {
    return { valid: false, message: '昵称长度不能超过20个字符' };
  }
  // 允许中文、英文、数字、下划线
  const usernameRegex = /^[\u4e00-\u9fa5a-zA-Z0-9_]+$/;
  if (!usernameRegex.test(trimmed)) {
    return { valid: false, message: '昵称只能包含中文、英文、数字和下划线' };
  }
  return { valid: true, message: '' };
}

// 确认密码验证
export function validateConfirmPassword(password: string, confirm: string): { valid: boolean; message: string } {
  if (!confirm || !confirm.trim()) {
    return { valid: false, message: '请再次输入密码' };
  }
  if (password !== confirm) {
    return { valid: false, message: '两次输入的密码不一致' };
  }
  return { valid: true, message: '' };
}

