import os
from backend.encryption_utils import encrypt_file, decrypt_file

# 定义存放 token.enc 的文件夹路径
TOKEN_DIR = 'tokens'
# 确保文件夹存在
if not os.path.exists(TOKEN_DIR):
    os.makedirs(TOKEN_DIR)

# 完整的文件路径
TOKEN_FILE = os.path.join(TOKEN_DIR, 'token.enc')

def save_token(token):
    """将加密后的令牌保存到文件中"""
    encrypted_token = encrypt_file(token)
    with open(TOKEN_FILE, 'wb') as f:
        f.write(encrypted_token)

def read_token():
    """读取并解密令牌文件"""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as f:
            encrypted_token = f.read()
        try:
            token = decrypt_file(encrypted_token)
            return token
        except Exception:
            return None
    return None