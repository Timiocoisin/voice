import os
from pathlib import Path
from backend.encryption.encryption_utils import encrypt_file, decrypt_file

# 将 token 存放在客户端目录下的 tokens 子目录中：<项目根>/client/tokens
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLIENT_DIR = PROJECT_ROOT / "client"
TOKEN_DIR = CLIENT_DIR / "tokens"

# 确保文件夹存在
TOKEN_DIR.mkdir(parents=True, exist_ok=True)

# 完整的文件路径
TOKEN_FILE = TOKEN_DIR / "token.enc"

def save_token(token):
    """将加密后的令牌保存到文件中"""
    encrypted_token = encrypt_file(token)
    with open(TOKEN_FILE, 'wb') as f:
        f.write(encrypted_token)

def read_token():
    """读取并解密令牌文件"""
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as f:
            encrypted_token = f.read()
        try:
            token = decrypt_file(encrypted_token)
            return token
        except Exception:
            return None
    return None

def clear_token():
    """清除本地保存的 token 文件"""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except OSError:
            pass