import mysql.connector
import bcrypt
from typing import Optional
import logging
from backend.resources import get_default_avatar

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()

    def connect(self):
        """建立与 MySQL 数据库的连接"""
        try:
            self.connection = mysql.connector.connect(
                host="localhost",
                user="root",
                password="123456",
                database="voice"
            )
            logging.info("数据库连接成功")
            self.ensure_tables_exist()
        except mysql.connector.Error as e:
            logging.error(f"连接数据库失败: {e}")

    def ensure_tables_exist(self):
        """确保所有表存在"""
        self.create_user_table()
        self.create_user_vip_table()
        self.create_logo_table()
        self.create_announcement_table()

    def create_user_table(self):
        """创建用户表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
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
            self.connection.commit()
        except mysql.connector.Error as e:
            logging.error(f"创建用户表失败: {e}")

    def create_user_vip_table(self):
        """创建用户 VIP 信息表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
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
            self.connection.commit()
        except mysql.connector.Error as e:
            logging.error(f"创建用户 VIP 信息表失败: {e}")

    def create_logo_table(self):
        """创建 logo 表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS logos (
                id INT AUTO_INCREMENT PRIMARY KEY,
                icon_data LONGBLOB NOT NULL,
                comment VARCHAR(255) NULL COMMENT '图标注释信息'
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
        except mysql.connector.Error as e:
            logging.error(f"创建 logo 表失败: {e}")

    def create_announcement_table(self):
        """创建公告表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS announcements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
        except mysql.connector.Error as e:
            logging.error(f"创建公告表失败: {e}")

    def insert_user_info(self, username: str, email: str, password: str, avatar_data: Optional[bytes] = None) -> bool:
        """插入用户信息到数据库，头像可选，默认为默认头像"""
        try:
            cursor = self.connection.cursor()

            # 如果没有提供头像数据，使用默认头像
            if not avatar_data:
                avatar_data = self.read_default_avatar()

            # 加密密码
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

            # 插入用户数据
            insert_query = """
            INSERT INTO users (username, email, password, avatar) 
            VALUES (%s, %s, %s, %s)
            """
            cursor.execute(insert_query, (username, email, hashed, avatar_data))
            user_id = cursor.lastrowid
            self.connection.commit()

            # 插入默认的 VIP 信息
            self.insert_user_vip_info(user_id)

            logging.info(f"用户 {username} 注册成功，ID: {user_id}")
            return True
        except mysql.connector.Error as e:
            logging.info(f"插入用户信息失败: {e}")
            self.connection.rollback()
            return False

    def get_user_by_email(self, email: str):
        """根据邮箱查询用户信息"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT id, username, password, avatar FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            return cursor.fetchone()  # 返回包含用户头像的结果
        except mysql.connector.Error as e:
            logging.error(f"查询用户信息失败: {e}")
            return None

    def insert_user_vip_info(self, user_id: int) -> bool:
        """插入用户 VIP 信息到数据库，默认非会员，钻石数量为 0"""
        try:
            cursor = self.connection.cursor()
            insert_query = """
            INSERT INTO user_vip (user_id) 
            VALUES (%s)
            """
            cursor.execute(insert_query, (user_id,))
            self.connection.commit()

            logging.info(f"用户 {user_id} VIP 信息插入成功")
            return True
        except mysql.connector.Error as e:
            logging.info(f"插入用户 VIP 信息失败: {e}")
            self.connection.rollback()
            return False

    def get_user_vip_info(self, user_id: int):
        """根据用户 ID 查询用户 VIP 信息"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT is_vip, vip_expiry_date, diamonds FROM user_vip WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        except mysql.connector.Error as e:
            logging.info(f"查询用户 VIP 信息失败: {e}")
            return None

    def read_default_avatar(self) -> Optional[bytes]:
        """读取默认头像文件并返回二进制数据，从本地文件加载"""
        return get_default_avatar()

    def get_icon_by_id(self, icon_id: int):
        """根据图标ID获取图标数据"""
        try:
            cursor = self.connection.cursor()
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

    def get_latest_logo(self):
        """获取最新的 logo 数据，这里获取 logos 表中 id 为 6 的 icon"""
        return self.get_icon_by_id(6)

    def get_latest_announcement(self):
        """获取最新的公告内容"""
        try:
            cursor = self.connection.cursor()
            query = "SELECT content FROM announcements ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                return result[0]
            return None
        except mysql.connector.Error as e:
            logging.info(f"查询公告失败: {e}")
            self.connection.rollback()
            return False
        
    def update_user_avatar(self, user_id: int, avatar_data: bytes) -> bool:
        """更新用户头像"""
        try:
            cursor = self.connection.cursor()
            update_query = """
            UPDATE users
            SET avatar = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (avatar_data, user_id))
            self.connection.commit()
            logging.info(f"用户 {user_id} 的头像已更新")
            return True
        except mysql.connector.Error as e:
            logging.error(f"更新用户头像失败: {e}")
            self.connection.rollback()
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logging.info("数据库连接已关闭")