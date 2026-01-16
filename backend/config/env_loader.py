"""环境变量加载工具

统一管理环境变量的加载，确保在所有模块使用环境变量前已正确加载。
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 获取 backend 目录的绝对路径
BACKEND_DIR = Path(__file__).parent.parent
ENV_FILE = BACKEND_DIR / ".env"

# 加载 .env 文件
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"已加载环境变量文件: {ENV_FILE}")
else:
    print(f"警告: 未找到环境变量文件 {ENV_FILE}，将使用系统环境变量")
    # 尝试从项目根目录加载
    ROOT_ENV = BACKEND_DIR.parent / ".env"
    if ROOT_ENV.exists():
        load_dotenv(ROOT_ENV)
        print(f"已从项目根目录加载环境变量文件: {ROOT_ENV}")
    else:
        # 如果都没有，尝试加载默认的 .env（可能在当前工作目录）
        load_dotenv()

