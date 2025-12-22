import pymysql
import pymysql.cursors
import bcrypt
from typing import Optional, Dict, Any
import logging
from backend.resources import get_default_avatar
from backend.logging_manager import setup_logging  # noqa: F401


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.connect()
    
    def connect(self):
        """
        建立与 MySQL 数据库的连接。

        若目标数据库不存在，则自动创建 `voice` 数据库后再连接，并初始化表结构。
        """
        db_name = "voice"
        try:
            # 优先直接连接指定数据库
            self.connection = pymysql.connect(
                host="localhost",
                user="root",
                password="123456",
                database=db_name,
            )
            logging.info("数据库连接成功")
            self.ensure_tables_exist()
        except pymysql.Error as e:
            msg = str(e)
            logging.error(f"连接数据库失败: {e}")

            # 若是数据库不存在，则先连接 MySQL 服务器创建数据库
            if "Unknown database" in msg or f"'{db_name}'" in msg:
                logging.info("检测到数据库不存在，正在自动创建数据库 %s ...", db_name)
                try:
                    # 先连接到服务器（不指定 database）
                    server_conn = pymysql.connect(
                        host="localhost",
                        user="root",
                        password="123456",
                    )
                    with server_conn.cursor() as cursor:
                        cursor.execute(
                            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                        )
                    server_conn.commit()
                    server_conn.close()
                    logging.info("数据库 %s 创建/存在检查完成", db_name)

                    # 再次连接到新建好的数据库
                    self.connection = pymysql.connect(
                        host="localhost",
                        user="root",
                        password="123456",
                        database=db_name,
                    )
                    logging.info("重新连接到新创建的数据库成功")
                    self.ensure_tables_exist()
                    return
                except pymysql.Error as ce:
                    logging.error(f"自动创建数据库 {db_name} 失败: {ce}")
                    self.connection = None
                    raise ConnectionError(f"无法创建数据库 {db_name}：{ce}")

            # 其他错误直接抛给上层
            self.connection = None
            raise ConnectionError(f"无法连接到数据库：{e}")

    def ensure_tables_exist(self):
        """确保所有表存在"""
        self.create_user_table()
        self._ensure_user_avatar_column()
        self.create_user_vip_table()
        self.create_announcement_table()

    def create_user_table(self):
        """创建用户表（如果不存在）。

        注意：avatar 列的增加会通过 `_ensure_user_avatar_column` 进行迁移，
        以兼容早期已存在但未包含 avatar 列的表结构。
        """
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
        except pymysql.Error as e:
            logging.error(f"创建用户表失败: {e}")

    def _ensure_user_avatar_column(self) -> None:
        """
        确保 users 表中存在 avatar 列。

        早期版本可能没有 avatar 列，这里通过 SHOW COLUMNS 检查并按需执行 ALTER TABLE，
        保证用户上传的头像可以长期保存在单独字段中，而不会在升级后丢失。
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW COLUMNS FROM users LIKE 'avatar'")
            result = cursor.fetchone()
            if result:
                return  # 已存在 avatar 列

            logging.info("检测到 users 表缺少 avatar 列，正在自动添加该列...")
            alter_sql = """
            ALTER TABLE users
            ADD COLUMN avatar LONGBLOB NULL AFTER password
            """
            cursor.execute(alter_sql)
            self.connection.commit()
            logging.info("users 表 avatar 列添加完成")
        except pymysql.Error as e:
            # 如果列已存在或其他错误，这里仅记录日志，不阻止服务启动
            logging.error(f"确保 users.avatar 列存在时出错: {e}")

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
        except pymysql.Error as e:
            logging.error(f"创建用户 VIP 信息表失败: {e}")

    # 已废弃：logos 表与相关功能不再使用，保留注释以便历史追溯
    # def create_logo_table(self):
    #     """创建 logo 表（如果不存在）"""
    #     try:
    #         cursor = self.connection.cursor()
    #         create_table_query = """
    #         CREATE TABLE IF NOT EXISTS logos (
    #             id INT AUTO_INCREMENT PRIMARY KEY,
    #             icon_data LONGBLOB NOT NULL,
    #             comment VARCHAR(255) NULL COMMENT '图标注释信息'
    #         )
    #         """
    #         cursor.execute(create_table_query)
    #         self.connection.commit()
    #     except pymysql.Error as e:
    #         logging.error(f"创建 logo 表失败: {e}")

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
        except pymysql.Error as e:
            logging.error(f"创建公告表失败: {e}")

    def insert_user_info(self, username: str, email: str, password: str, avatar_data: Optional[bytes] = None) -> bool:
        """插入用户信息到数据库，头像可选，默认为默认头像。

        Args:
            username: 用户名（展示用）
            email: 邮箱（登录唯一标识）
            password: 原始明文密码，将在此处进行哈希
            avatar_data: 头像二进制数据，缺省时使用默认头像
        """
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
        except pymysql.Error as e:
            logging.info(f"插入用户信息失败: {e}")
            self.connection.rollback()
            return False

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱查询用户信息。

        Returns:
            包含 id、username、password、avatar 等字段的字典，查询失败或未找到返回 None。
        """
        try:
            # PyMySQL 的 Connection.cursor() 不支持 cursorclass 关键字参数，需直接传入游标类
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = "SELECT id, username, password, avatar FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            return cursor.fetchone()  # 返回包含用户头像的结果
        except pymysql.Error as e:
            logging.error(f"查询用户信息失败: {e}")
            return None

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户 ID 查询用户基础信息（含头像）。"""
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = "SELECT id, username, avatar FROM users WHERE id = %s"
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        except pymysql.Error as e:
            logging.error(f"根据用户ID查询用户信息失败: {e}")
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
        except pymysql.Error as e:
            logging.info(f"插入用户 VIP 信息失败: {e}")
            self.connection.rollback()
            return False

    def get_user_vip_info(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户 ID 查询用户 VIP 信息。"""
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = "SELECT is_vip, vip_expiry_date, diamonds FROM user_vip WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            return cursor.fetchone()
        except pymysql.Error as e:
            logging.info(f"查询用户 VIP 信息失败: {e}")
            return None

    def read_default_avatar(self) -> Optional[bytes]:
        """读取默认头像文件并返回二进制数据，从本地文件加载"""
        return get_default_avatar()

    # 已废弃：logos 表相关查询不再使用
    # def get_icon_by_id(self, icon_id: int):
    #     """根据图标ID获取图标数据"""
    #     try:
    #         cursor = self.connection.cursor()
    #         query = "SELECT icon_data FROM logos WHERE id = %s"
    #         cursor.execute(query, (icon_id,))
    #         result = cursor.fetchone()
    #         if result:
    #             return result[0]
    #         logging.info(f"未找到ID为 {icon_id} 的图标")
    #         return None
    #     except pymysql.Error as e:
    #         logging.error(f"查询图标 ID {icon_id} 失败: {e}")
    #         return None
    #
    # def get_latest_logo(self):
    #     """获取最新的 logo 数据，这里获取 logos 表中 id 为 6 的 icon"""
    #     return self.get_icon_by_id(6)

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
        except pymysql.Error as e:
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
        except pymysql.Error as e:
            logging.error(f"更新用户头像失败: {e}")
            self.connection.rollback()
            return False

    def consume_diamonds_and_update_vip(self, user_id: int, cost: int, new_expiry) -> bool:
        """消耗钻石并更新 VIP 有效期

        使用单条 SQL 保证扣减与更新的原子性：
        - 仅当当前钻石数量 >= cost 时才会更新
        """
        try:
            cursor = self.connection.cursor()
            update_query = """
            UPDATE user_vip
            SET diamonds = diamonds - %s,
                is_vip = TRUE,
                vip_expiry_date = %s
            WHERE user_id = %s AND diamonds >= %s
            """
            cursor.execute(update_query, (cost, new_expiry, user_id, cost))
            if cursor.rowcount == 0:
                # 钻石不足或用户不存在
                self.connection.rollback()
                return False
            self.connection.commit()
            logging.info(
                f"用户 {user_id} 消耗 {cost} 钻石，VIP 有效期更新为 {new_expiry}"
            )
            return True
        except pymysql.Error as e:
            logging.error(f"更新用户 VIP 信息失败: {e}")
            self.connection.rollback()
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logging.info("数据库连接已关闭")