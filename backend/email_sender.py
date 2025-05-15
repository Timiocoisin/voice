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
        """
        初始化 EmailSender 类，配置信息通过参数传入
        """
        self.config = config
        self.server = None

    def connect(self):
        """
        连接到 SMTP 服务器。

        :return: 连接成功返回 True，失败返回 False
        """
        try:
            # 使用 SSL 连接到 SMTP 服务器
            self.server = smtplib.SMTP_SSL(self.config['smtp_server'], self.config['smtp_port'])
            # 登录发件人邮箱
            self.server.login(self.config['sender_email'], self.config['sender_password'])
            logging.info("成功连接到邮件服务器")
            return True
        except Exception as e:
            logging.error(f"邮件服务器连接失败: {e}")
            return False

    def close(self):
        """
        关闭与 SMTP 服务器的连接。
        """
        if self.server:
            self.server.quit()
            logging.info("已关闭与邮件服务器的连接")

    def send_verification_code(self, recipient_email, code, expires_in_minutes=5):
        """
        发送验证码邮件。

        :param recipient_email: 收件人邮箱地址
        :param code: 验证码
        :param expires_in_minutes: 验证码有效期（分钟），默认为 5 分钟
        :return: 发送成功返回 True，失败返回 False
        """
        # 尝试连接到 SMTP 服务器
        if not self.connect():
            return False

        # 计算验证码过期时间
        expire_time = datetime.now() + timedelta(minutes=expires_in_minutes)
        expire_str = expire_time.strftime("%H:%M:%S")

        # 邮件主题
        subject = "【语音转换系统】您的验证码"
        # 邮件内容（HTML 格式）
        content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; border-radius: 8px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <h2 style="color: #333; border-bottom: 1px solid #eee; padding-bottom: 10px;">账号安全验证</h2>
                <p style="color: #555; line-height: 1.6;">尊敬的用户：</p>
                <p style="color: #555; line-height: 1.6;">您正在进行账号注册/登录操作，请在验证码有效期内完成验证：</p>
                <div style="background-color: #e9f5ff; border-left: 4px solid #2196F3; padding: 15px; margin: 20px 0; font-size: 24px; font-weight: bold; color: #2196F3; text-align: center;">
                    {code}
                </div>
                <p style="color: #777; font-size: 14px;">验证码有效期至 {expire_str}（{expires_in_minutes}分钟内有效）</p>
                <p style="color: #777; font-size: 14px;">如非本人操作，请忽略此邮件。</p>
                <div style="border-top: 1px solid #eee; margin-top: 20px; padding-top: 15px; color: #999; font-size: 12px;">
                    <p>此为系统邮件，请勿直接回复</p>
                </div>
            </div>
        </body>
        </html>
        """

        try:
            # 创建 MIMEText 对象，指定邮件内容为 HTML 格式
            msg = MIMEText(content, 'html', 'utf-8')
            # 正确设置发件人头部
            sender_name = Header(self.config['sender_name'], 'utf-8').encode()
            sender_email = self.config['sender_email']
            msg['From'] = f"{sender_name} <{sender_email}>"
            # 设置收件人邮箱地址
            msg['To'] = recipient_email
            # 设置邮件主题
            msg['Subject'] = Header(subject, 'utf-8')

            # 发送邮件
            self.server.sendmail(self.config['sender_email'], recipient_email, msg.as_string())
            logging.info(f"验证码邮件已成功发送至 {recipient_email}")
            return True
        except Exception as e:
            logging.error(f"邮件发送失败: {e}")
            return False
        finally:
            # 关闭与 SMTP 服务器的连接
            self.close()

def generate_verification_code(length=6):
    """
    生成指定长度的验证码。

    :param length: 验证码长度，默认为 6 位
    :return: 生成的验证码字符串
    """
    import string
    all_characters = string.digits + string.ascii_letters
    return ''.join(random.choices(all_characters, k=length))