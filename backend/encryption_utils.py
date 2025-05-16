from cryptography.fernet import Fernet
from backend.config import ENCRYPTION_KEY

def encrypt_file(data):
    """加密数据并返回加密后的字节流"""
    f = Fernet(ENCRYPTION_KEY)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data

def decrypt_file(encrypted_data):
    """解密加密的字节流并返回原始数据"""
    f = Fernet(ENCRYPTION_KEY)
    decrypted_data = f.decrypt(encrypted_data).decode()
    return decrypted_data