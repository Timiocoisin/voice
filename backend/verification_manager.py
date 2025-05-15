from datetime import datetime, timedelta

class VerificationManager:
    def __init__(self):
        self.verification_codes = {}  # 存储格式: {email: (code, expire_time)}
        self.code_lifetime = 5  # 验证码有效期(分钟)

    def set_verification_code(self, email, code):
        expire_time = datetime.now() + timedelta(minutes=self.code_lifetime)
        self.verification_codes[email] = (code, expire_time)

    def verify_code(self, email, input_code):
        if email not in self.verification_codes:
            return False

        code, expire_time = self.verification_codes[email]
        
        # 检查验证码是否过期
        if datetime.now() > expire_time:
            del self.verification_codes[email]  # 删除过期验证码
            return False

        # 检查验证码是否匹配
        if input_code == code:
            del self.verification_codes[email]  # 验证通过后删除验证码
            return True

        return False

    def clear_expired_codes(self):
        """清理过期的验证码"""
        current_time = datetime.now()
        self.verification_codes = {
            email: (code, expire_time) 
            for email, (code, expire_time) in self.verification_codes.items()
            if expire_time > current_time
        }    