import mysql.connector
import os
import bcrypt
from typing import Optional
from PyQt6.QtGui import QPixmap, QIcon
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
        # 确保 logo 表存在
        create_logo_table(connection)
        # 确保公告表存在
        create_announcement_table(connection)

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


def read_default_avatar(connection: mysql.connector.MySQLConnection) -> Optional[bytes]:
    """读取默认头像文件并返回二进制数据，默认头像为 logos 表中 id 为 4 的 icon"""
    return get_icon_by_id(connection, 4)


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
            avatar_data = read_default_avatar(connection)

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


def create_logo_table(connection: mysql.connector.MySQLConnection) -> None:
    """创建 logo 表（如果不存在）"""
    try:
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS logos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            icon_data LONGBLOB NOT NULL,
            comment VARCHAR(255) NULL COMMENT '图标注释信息'
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    except mysql.connector.Error as e:
        logging.error(f"创建 logo 表失败: {e}")


def create_announcement_table(connection: mysql.connector.MySQLConnection) -> None:
    """创建公告表（如果不存在）"""
    try:
        cursor = connection.cursor()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS announcements (
            id INT AUTO_INCREMENT PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        cursor.execute(create_table_query)
        connection.commit()
    except mysql.connector.Error as e:
        logging.error(f"创建公告表失败: {e}")


def insert_logo(connection: mysql.connector.MySQLConnection, logo_data: bytes) -> bool:
    """插入 logo 数据到数据库"""
    try:
        cursor = connection.cursor()
        insert_query = "INSERT INTO logos (logo_data) VALUES (%s)"
        cursor.execute(insert_query, (logo_data,))
        connection.commit()
        logging.info("logo 插入成功")
        return True
    except mysql.connector.Error as e:
        logging.info(f"插入 logo 失败: {e}")
        connection.rollback()
        return False


def get_latest_logo(connection: mysql.connector.MySQLConnection):
    """获取最新的 logo 数据，这里获取 logos 表中 id 为 6 的 icon"""
    return get_icon_by_id(connection, 6)


def insert_announcement(connection: mysql.connector.MySQLConnection, content: str) -> bool:
    """插入公告内容到数据库"""
    try:
        cursor = connection.cursor()
        insert_query = "INSERT INTO announcements (content) VALUES (%s)"
        cursor.execute(insert_query, (content,))
        connection.commit()
        logging.info("公告插入成功")
        return True
    except mysql.connector.Error as e:
        logging.info(f"插入公告失败: {e}")
        connection.rollback()
        return False


def get_latest_announcement(connection: mysql.connector.MySQLConnection):
    """获取最新的公告内容"""
    try:
        cursor = connection.cursor()
        query = "SELECT content FROM announcements ORDER BY id DESC LIMIT 1"
        cursor.execute(query)
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except mysql.connector.Error as e:
        logging.info(f"查询公告失败: {e}")
        connection.rollback()
        return False
    
def get_icon_by_id(connection: mysql.connector.MySQLConnection, icon_id: int):
    """根据图标ID获取图标数据"""
    try:
        cursor = connection.cursor()
        query = "SELECT icon_data FROM logos WHERE id = %s"
        cursor.execute(query, (icon_id,))
        result = cursor.fetchone()
        if result:
            return result[0]
        logging.info(f"未找到ID为 {icon_id} 的图标")
        return None
    except mysql.connector.Error as e:
        logging.error(f"查询图标 ID {icon_id} 失败: {e}")
        return None



def load_app_icon(icon_id: int) -> QIcon:
    """从数据库加载应用程序图标"""
    connection = create_connection()
    icon = QIcon()
    
    if connection:
        try:
            # 获取图标二进制数据
            icon_data = get_icon_by_id(connection, icon_id)
            
            if icon_data:
                # 创建QPixmap并加载数据
                pixmap = QPixmap()
                if pixmap.loadFromData(icon_data):
                    icon.addPixmap(pixmap, QIcon.Mode.Normal, QIcon.State.Off)
                else:
                    logging.error(f"图标数据无效（ID={icon_id}）")
            else:
                logging.warning(f"图标未找到（ID={icon_id}）")
                
        except Exception as e:
            logging.error(f"加载图标时出错: {str(e)}")
        finally:
            connection.close()
    
    return icon