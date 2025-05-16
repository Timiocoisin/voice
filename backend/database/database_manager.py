import mysql.connector
import os
import bcrypt
from typing import Optional
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_connection() -> Optional[mysql.connector.MySQLConnection]:
    """建立与 MySQL 数据库的连接，并确保用户表和 VIP 信息表存在"""
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
        # 确保用户 VIP 信息表存在
        create_user_vip_table(connection)

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
        user_id = cursor.lastrowid
        connection.commit()

        # 插入默认的 VIP 信息
        insert_user_vip_info(connection, user_id)

        logging.info(f"用户 {username} 注册成功，ID: {user_id}")
        return True
    except mysql.connector.Error as e:
        logging.info(f"插入用户信息失败: {e}")
        connection.rollback()
        return False


def get_user_by_email(connection: mysql.connector.MySQLConnection, email: str):
    """根据邮箱查询用户信息"""
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT id, username, avatar FROM users WHERE email = %s"
        cursor.execute(query, (email,))
        return cursor.fetchone()  # 返回包含用户头像的结果
    except mysql.connector.Error as e:
        logging.error(f"查询用户信息失败: {e}")
        return None


def create_user_vip_table(connection: mysql.connector.MySQLConnection) -> None:
    """创建用户 VIP 信息表（如果不存在）"""
    try:
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS user_vip (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            is_vip BOOLEAN DEFAULT FALSE,
            vip_expiry_date DATETIME,
            diamonds INT DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    except mysql.connector.Error as e:
        logging.error(f"创建用户 VIP 信息表失败: {e}")


def insert_user_vip_info(connection: mysql.connector.MySQLConnection, user_id: int) -> bool:
    """插入用户 VIP 信息到数据库，默认非会员，钻石数量为 0"""
    try:
        cursor = connection.cursor()
        insert_query = """
        INSERT INTO user_vip (user_id) 
        VALUES (%s)
        """
        cursor.execute(insert_query, (user_id,))
        connection.commit()

        logging.info(f"用户 {user_id} VIP 信息插入成功")
        return True
    except mysql.connector.Error as e:
        logging.info(f"插入用户 VIP 信息失败: {e}")
        connection.rollback()
        return False


def get_user_vip_info(connection: mysql.connector.MySQLConnection, user_id: int):
    """根据用户 ID 查询用户 VIP 信息"""
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT is_vip, vip_expiry_date, diamonds FROM user_vip WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        return cursor.fetchone()
    except mysql.connector.Error as e:
        logging.info(f"查询用户 VIP 信息失败: {e}")
        return None