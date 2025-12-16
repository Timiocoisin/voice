import smtplib
import logging
from email.mime.text import MIMEText
from email.header import Header
import random
from datetime import datetime, timedelta

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EmailSender:
    def __init__(self, config):
        """初始化 EmailSender 类，固定使用配置中的发送方信息"""
        self.config = config  # 固定使用配置好的发送方信息
        self.server = None

    def connect(self):
        """连接到 SMTP 服务器"""
        try:
            self.server = smtplib.SMTP_SSL(self.config['smtp_server'], self.config['smtp_port'])
            self.server.login(self.config['sender_email'], self.config['sender_password'])
            logging.info("成功连接到邮件服务器")
            return True
        except Exception as e:
            logging.error(f"邮件服务器连接失败: {e}")
            return False

    def close(self):
        """关闭与 SMTP 服务器的连接"""
        if self.server:
            self.server.quit()
            logging.info("已关闭与邮件服务器的连接")

    def send_verification_code(self, recipient_email, code, expires_in_minutes=5):
        """发送验证码邮件
        :param recipient_email: 接收方邮箱（用户输入的目标邮箱）
        :param code: 验证码
        :param expires_in_minutes: 有效期（分钟）
        """
        if not self.connect():
            return False

        # 获取当前系统年份
        current_year = datetime.now().year
        expire_time = datetime.now() + timedelta(minutes=expires_in_minutes)
        expire_str = expire_time.strftime("%Y年%m月%d日 %H:%M:%S")

        subject = "【语音转换系统】您的验证码"
        # 邮件内容（使用HTML格式）
        content = f"""
            <!DOCTYPE html>
            <html lang="zh-CN">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{subject}</title>
                <style>
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                    }}
                    body {{
                        background-color: #f9fafb;
                        line-height: 1.5;
                        color: #374151;
                    }}
                    .container {{
                        max-width: 640px;
                        margin: 0 auto;
                        padding: 16px;
                    }}
                    .email-container {{
                        background-color: #ffffff;
                        border-radius: 10px;
                        box-shadow: 0 3px 15px rgba(0, 0, 0, 0.07);
                        overflow: hidden;
                        border-top: 3px solid #165DFF;
                    }}
                    .header {{
                        padding: 18px 24px;
                        background-color: #f8fafc;
                        display: flex;
                        align-items: center;
                        border-bottom: 1px solid #e2e8f0;
                    }}
                    .logo {{
                        color: #165DFF;
                        font-size: 20px;
                        font-weight: 600;
                        letter-spacing: -0.3px;
                    }}
                    .email-content {{
                        padding: 24px;
                    }}
                    .greeting {{
                        margin-bottom: 12px;
                    }}
                    .greeting p {{
                        font-size: 16px;
                        font-weight: 500;
                    }}
                    .message {{
                        margin-bottom: 20px;
                        font-size: 15px;
                        color: #4b5563;
                    }}
                    /* 扁平化验证码区域样式 */
                    .verification-card {{
                        position: relative;
                        background: linear-gradient(135deg, #f0f7ff 0%, #e6f7ff 100%);
                        border-radius: 10px;
                        padding: 18px 16px;
                        margin: 18px 0;
                        border: 1px solid #cce6ff;
                        box-shadow: 0 3px 15px rgba(22, 93, 255, 0.08);
                        overflow: hidden;
                    }}
                    .verification-card::before {{
                        content: '';
                        position: absolute;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 3px;
                        background: linear-gradient(90deg, #165DFF, #4080FF);
                    }}
                    .verification-code {{
                        text-align: center;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        gap: 8px;
                    }}
                    .code {{
                        font-size: 32px;
                        font-weight: 800;
                        color: #1E40AF;
                        letter-spacing: 5px;
                        font-family: 'Consolas', 'Monaco', monospace;
                        display: inline-block;
                        padding: 8px 16px;
                        background-color: rgba(255, 255, 255, 0.95);
                        border-radius: 6px;
                        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05) inset, 
                                   0 1px 2px rgba(22, 93, 255, 0.1);
                        position: relative;
                        overflow: hidden;
                    }}
                    .code::after {{
                        content: '';
                        position: absolute;
                        top: 0;
                        left: -100%;
                        width: 50%;
                        height: 100%;
                        background: linear-gradient(90deg, 
                                    rgba(255,255,255,0) 0%, 
                                    rgba(255,255,255,0.2) 50%, 
                                    rgba(255,255,255,0) 100%);
                        transform: skewX(-25deg);
                        animation: shine 3s infinite;
                    }}
                    @keyframes shine {{
                        100% {{
                            left: 150%;
                        }}
                    }}
                    .expiry {{
                        color: #64748B;
                        font-size: 13px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        padding-top: 6px;
                        border-top: 1px dashed #BFDBFE;
                        width: 90%;
                    }}
                    .expiry svg {{
                        margin-right: 5px;
                        width: 13px;
                        height: 13px;
                        color: #3B82F6;
                    }}
                    .security-note {{
                        background-color: #fff5f5;
                        border-radius: 6px;
                        padding: 12px 16px;
                        margin-top: 16px;
                        font-size: 13px;
                        color: #7f1d1d;
                        border-left: 3px solid #ef4444;
                    }}
                    .footer {{
                        padding: 16px 24px;
                        text-align: center;
                        color: #9ca3af;
                        font-size: 12px;
                        background-color: #f9fafb;
                        border-top: 1px solid #e5e7eb;
                        margin-top: 10px;
                    }}
                    @media (max-width: 500px) {{
                        .container {{
                            padding: 10px;
                        }}
                        .email-content {{
                            padding: 18px 16px;
                        }}
                        .code {{
                            font-size: 26px;
                            letter-spacing: 3px;
                            padding: 6px 12px;
                        }}
                        .verification-card {{
                            padding: 14px 12px;
                        }}
                        .message, .security-note {{
                            font-size: 14px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="email-container">
                        <div class="header">
                            <div class="logo">语音转换系统</div>
                        </div>
                        <div class="email-content">
                            <div class="greeting">
                                <p>尊敬的用户：</p>
                            </div>
                            <div class="message">
                                <p>您正在进行账号注册/登录操作，请在验证码有效期内完成验证：</p>
                            </div>
                            <div class="verification-card">
                                <div class="verification-code">
                                    <p class="code">{code}</p>
                                    <p class="expiry">
                                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clock" viewBox="0 0 16 16">
                                            <path d="M8 3.5a.5.5 0 0 0-1 0V9a.5.5 0 0 0 .252.434l3.5 2a.5.5 0 0 0 .496-.868L8 8.71V3.5z"/>
                                            <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16zm7-8A7 7 0 1 1 1 8a7 7 0 0 1 14 0z"/>
                                        </svg>
                                        有效期至 {expire_str}（{expires_in_minutes}分钟内有效）
                                    </p>
                                </div>
                            </div>
                            <div class="security-note">
                                <p>安全提示：如非本人操作，请忽略此邮件。请勿向任何人泄露此验证码。</p>
                            </div>
                        </div>
                        <div class="footer">
                            <p>此为系统邮件，请勿直接回复</p>
                            <p>© {current_year} 语音转换系统 版权所有</p>
                        </div>
                    </div>
                </div>
            </body>
            </html>
        """

        try:
            msg = MIMEText(content, 'html', 'utf-8')
            sender_name = Header(self.config['sender_name'], 'utf-8').encode()
            sender_email = self.config['sender_email']
            msg['From'] = f"{sender_name} <{sender_email}>"
            msg['To'] = recipient_email
            msg['Subject'] = Header(subject, 'utf-8')

            # 发送方固定为配置中的邮箱，接收方为用户输入的邮箱
            self.server.sendmail(sender_email, recipient_email, msg.as_string())
            logging.info(f"验证码邮件已成功发送至 {recipient_email}")
            return True
        except Exception as e:
            logging.error(f"邮件发送失败: {e}")
            return False
        finally:
            self.close()

def generate_verification_code(length=6):
    """生成指定长度的验证码"""
    import string
    all_characters = string.digits + string.ascii_letters
    return ''.join(random.choices(all_characters, k=length))    


# 使用示例
if __name__ == "__main__":
    # 用户输入的目标邮箱（接收方）
    user_email = input("请输入接收验证码的邮箱：")
    
    # 生成验证码
    code = generate_verification_code()
    
    # 发送验证码
    sender = EmailSender()
    if sender.send_verification_code(user_email, code):
        print(f"验证码 {code} 已发送至 {user_email}")
    else:
        print("验证码发送失败")