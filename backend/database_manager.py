import mysql.connector
import os
import bcrypt
from typing import Optional
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_connection() -> Optional[mysql.connector.MySQLConnection]:
    """建立与 MySQL 数据库的连接，并确保用户表存在"""
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            password="123456",
            database="voice"
        )
        logging.info("数据库连接成功")
        
        # 确保用户表存在
        create_user_table(connection)
        
        return connection
    except mysql.connector.Error as e:
        logging.error(f"连接数据库失败: {e}")
        return None

def create_user_table(connection: mysql.connector.MySQLConnection) -> None:
    """创建用户表（如果不存在）"""
    try:
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            avatar LONGBLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    except mysql.connector.Error as e:
        logging.error(f"创建用户表失败: {e}")

def read_default_avatar() -> Optional[bytes]:
    """读取默认头像文件并返回二进制数据"""
    try:
        avatar_path = "icons/head.ico"
        if os.path.exists(avatar_path):
            with open(avatar_path, 'rb') as file:
                return file.read()
        else:
            logging.info("默认头像文件不存在，使用空白图片")
            # 返回一个1x1像素的透明PNG作为默认头像
            return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDAT\x08\xd7c`\x00\x00\x00\x02\x00\x01\xe2!\xbc3\x00\x00\x00\x00IEND\xaeB`\x82'
    except Exception as e:
        logging.error(f"读取默认头像失败: {e}")
        return None

def insert_user_info(
    connection: mysql.connector.MySQLConnection, 
    username: str, 
    email: str, 
    password: str,
    avatar_data: Optional[bytes] = None
) -> bool:
    """插入用户信息到数据库，头像可选，默认为默认头像"""
    try:
        cursor = connection.cursor()
        
        # 如果没有提供头像数据，使用默认头像
        if not avatar_data:
            avatar_data = read_default_avatar()
        
        # 加密密码
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        # 插入用户数据
        insert_query = """
        INSERT INTO users (username, email, password, avatar) 
        VALUES (%s, %s, %s, %s)
        """
        cursor.execute(insert_query, (username, email, hashed, avatar_data))
        connection.commit()
        
        logging.info(f"用户 {username} 注册成功，ID: {cursor.lastrowid}")
        return True
    except mysql.connector.Error as e:
        logging.info(f"插入用户信息失败: {e}")
        connection.rollback()
        return False

def get_user_by_email(connection: mysql.connector.MySQLConnection, email: str):
    """根据邮箱查询用户信息"""
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        return cursor.fetchone()
    except mysql.connector.Error as e:
        logging.info(f"查询用户信息失败: {e}")
        return None