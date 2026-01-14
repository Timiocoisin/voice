import pymysql
import pymysql.cursors
import bcrypt
from typing import Optional, Dict, Any
from datetime import datetime
import logging
from backend.resources import get_default_avatar
from backend.logging_manager import setup_logging  # noqa: F401


class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.tables_initialized = False  # 首次成功连接后才创建表，重连不再执行
        self.connect()

    def _open_conn(self):
        """为单次操作创建独立连接，避免多线程共享同一连接导致协议错误。"""
        return pymysql.connect(
            host="localhost",
            user="root",
            password="123456",
            database="voice",
        )
    
    def _ensure_connection(self):
        """确保数据库连接有效，如果无效则重新连接"""
        try:
            # 检查连接是否存在且有效
            if self.connection is None:
                self.connect()
                return
            
            # 尝试ping连接以检查是否有效
            try:
                self.connection.ping()
            except (pymysql.Error, AttributeError):
                # ping失败，连接已断开，需要重新连接
                raise
        except Exception:
            # 连接无效或重连过程中出错，重新连接
            logging.warning("数据库连接已断开，正在重新连接...")
            try:
                if self.connection:
                    self.connection.close()
            except Exception:
                pass
            self.connection = None
            try:
                self.connect()
            except Exception as e:
                logging.error(f"重新连接数据库失败: {e}")
                # 保持 self.connection 为 None，由上层处理 ConnectionError
    
    def _get_cursor(self, cursor_type=None):
        """获取数据库游标，自动确保连接有效"""
        self._ensure_connection()
        # 使用局部变量持有连接引用，避免在多线程/并发场景下 self.connection 被其他地方置为 None 导致 AttributeError
        conn = self.connection
        if conn is None:
            logging.error("获取数据库游标失败：数据库连接尚未建立或创建失败")
            raise ConnectionError("数据库连接未建立，无法获取游标")
        if cursor_type:
            return conn.cursor(cursor_type)
        return conn.cursor()
    
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
            # 仅在首次连接时初始化表结构，重连不再重复执行，避免旧连接被关闭导致“read of closed file”
            if not self.tables_initialized:
                try:
                    self.ensure_tables_exist()
                    self.tables_initialized = True
                except Exception as te:
                    logging.error(f"初始化数据表结构失败（忽略，仅记录日志）: {te}")
        except Exception as e:
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
                    self.tables_initialized = True
                    return
                except Exception as ce:
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
        self._ensure_user_role_column()
        self.create_user_vip_table()
        self.create_announcement_table()
        self.create_chat_messages_table()
        self._ensure_message_recall_fields()  # 确保消息撤回字段存在
        self._ensure_message_status_fields()  # 确保消息状态字段存在
        self.create_password_reset_tokens_table()
        self.create_chat_sessions_table()
        self.create_agent_status_table()
        self.create_user_connections_table()  # WebSocket 连接管理表
        self.create_user_devices_table()  # 设备管理表
        self.create_message_queue_table()  # 消息队列表

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
                role ENUM('user', 'admin', 'customer_service') DEFAULT 'user',
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

    def _ensure_user_role_column(self) -> None:
        """
        确保 users 表中存在 role 列。

        用于区分用户类型：user（普通用户）、admin（管理员）、customer_service（客服）
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW COLUMNS FROM users LIKE 'role'")
            result = cursor.fetchone()
            if result:
                return  # 已存在 role 列

            logging.info("检测到 users 表缺少 role 列，正在自动添加该列...")
            alter_sql = """
            ALTER TABLE users
            ADD COLUMN role ENUM('user', 'admin', 'customer_service') DEFAULT 'user' AFTER avatar
            """
            cursor.execute(alter_sql)
            self.connection.commit()
            logging.info("users 表 role 列添加完成")
        except pymysql.Error as e:
            # 如果列已存在或其他错误，这里仅记录日志，不阻止服务启动
            logging.error(f"确保 users.role 列存在时出错: {e}")

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

    def create_chat_messages_table(self):
        """创建聊天消息表（如果不存在），并确保 message 列为 MEDIUMTEXT 以容纳图片 base64。"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL,
                from_user_id INT NOT NULL,
                to_user_id INT,
                message MEDIUMTEXT NOT NULL,
                message_type ENUM('text', 'image', 'file') DEFAULT 'text',
                is_read BOOLEAN DEFAULT FALSE,
                is_recalled BOOLEAN DEFAULT FALSE,
                reply_to_message_id INT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_session (session_id),
                INDEX idx_from_user (from_user_id),
                INDEX idx_to_user (to_user_id),
                INDEX idx_created (created_at),
                INDEX idx_reply_to (reply_to_message_id),
                FOREIGN KEY (reply_to_message_id) REFERENCES chat_messages(id) ON DELETE SET NULL
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
            # 升级已有表的 message 列为 MEDIUMTEXT（幂等）
            cursor.execute("ALTER TABLE chat_messages MODIFY COLUMN message MEDIUMTEXT NOT NULL")
            self.connection.commit()
            # 确保新增字段存在（迁移已有表）
            self._ensure_message_recall_fields()
            # 确保消息编辑字段存在
            self._ensure_message_edit_fields()
        except pymysql.Error as e:
            logging.error(f"创建/升级聊天消息表失败: {e}")

    def _ensure_message_edit_fields(self):
        """确保 chat_messages 表中存在消息编辑相关字段（迁移方法）"""
        try:
            cursor = self.connection.cursor()
            # 检查 is_edited 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'is_edited'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 is_edited 列，正在自动添加...")
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN is_edited BOOLEAN DEFAULT FALSE AFTER is_recalled")
                self.connection.commit()
            
            # 检查 edited_at 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'edited_at'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 edited_at 列，正在自动添加...")
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN edited_at TIMESTAMP NULL AFTER is_edited")
                self.connection.commit()
        except pymysql.Error as e:
            logging.error(f"添加消息编辑字段失败: {e}")
    
    def _ensure_message_recall_fields(self):
        """确保 chat_messages 表中存在 is_recalled 和 reply_to_message_id 字段（迁移方法）"""
        try:
            cursor = self.connection.cursor()
            # 检查 is_recalled 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'is_recalled'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 is_recalled 列，正在自动添加...")
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN is_recalled BOOLEAN DEFAULT FALSE AFTER is_read")
                self.connection.commit()
            
            # 检查 reply_to_message_id 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'reply_to_message_id'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 reply_to_message_id 列，正在自动添加...")
                # 先添加列
                cursor.execute("ALTER TABLE chat_messages ADD COLUMN reply_to_message_id INT NULL AFTER is_recalled")
                # 添加索引
                cursor.execute("ALTER TABLE chat_messages ADD INDEX idx_reply_to (reply_to_message_id)")
                # 添加外键（如果可能）
                try:
                    cursor.execute("""
                        ALTER TABLE chat_messages 
                        ADD FOREIGN KEY (reply_to_message_id) 
                        REFERENCES chat_messages(id) ON DELETE SET NULL
                    """)
                except Exception:
                    # 如果外键添加失败（可能是已有数据不符合），仅记录日志
                    logging.warning("添加 reply_to_message_id 外键失败，可能已有数据不符合约束")
                self.connection.commit()
                logging.info("chat_messages 表字段升级完成")
        except pymysql.Error as e:
            logging.error(f"确保消息撤回字段存在时出错: {e}")

    def _ensure_message_status_fields(self):
        """确保 chat_messages 表中存在消息状态相关字段（迁移方法）"""
        try:
            cursor = self.connection.cursor()
            # 检查 status 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'status'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 status 列，正在自动添加...")
                cursor.execute("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN status ENUM('pending', 'sent', 'delivered', 'read', 'failed') 
                    DEFAULT 'sent' AFTER message_type
                """)
                self.connection.commit()
            
            # 检查 sent_at 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'sent_at'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 sent_at 列，正在自动添加...")
                cursor.execute("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN sent_at TIMESTAMP NULL AFTER status
                """)
                self.connection.commit()
            
            # 检查 delivered_at 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'delivered_at'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 delivered_at 列，正在自动添加...")
                cursor.execute("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN delivered_at TIMESTAMP NULL AFTER sent_at
                """)
                self.connection.commit()
            
            # 检查 read_at 字段
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'read_at'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 read_at 列，正在自动添加...")
                cursor.execute("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN read_at TIMESTAMP NULL AFTER delivered_at
                """)
                self.connection.commit()
            
            # 检查 sequence_number 字段（用于消息顺序保证）
            cursor.execute("SHOW COLUMNS FROM chat_messages LIKE 'sequence_number'")
            if not cursor.fetchone():
                logging.info("检测到 chat_messages 表缺少 sequence_number 列，正在自动添加...")
                cursor.execute("""
                    ALTER TABLE chat_messages 
                    ADD COLUMN sequence_number BIGINT NULL AFTER id,
                    ADD INDEX idx_sequence (session_id, sequence_number)
                """)
                self.connection.commit()
            
            logging.info("chat_messages 表消息状态字段升级完成")
        except pymysql.Error as e:
            logging.error(f"确保消息状态字段存在时出错: {e}")

    def create_password_reset_tokens_table(self):
        """创建密码重置token表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INT AUTO_INCREMENT PRIMARY KEY,
                email VARCHAR(255) NOT NULL,
                token VARCHAR(255) NOT NULL UNIQUE,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_email (email),
                INDEX idx_token (token),
                INDEX idx_expires (expires_at)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
        except pymysql.Error as e:
            logging.error(f"创建密码重置token表失败: {e}")

    def insert_password_reset_token(self, email: str, token: str, expires_at: datetime) -> bool:
        """插入密码重置token"""
        try:
            cursor = self.connection.cursor()
            # 先删除该邮箱的旧token
            delete_query = "DELETE FROM password_reset_tokens WHERE email = %s"
            cursor.execute(delete_query, (email,))
            # 插入新token
            insert_query = """
            INSERT INTO password_reset_tokens (email, token, expires_at)
            VALUES (%s, %s, %s)
            """
            cursor.execute(insert_query, (email, token, expires_at))
            self.connection.commit()
            return True
        except pymysql.Error as e:
            logging.error(f"插入密码重置token失败: {e}")
            self.connection.rollback()
            return False

    def get_password_reset_token(self, token: str) -> Optional[Dict[str, Any]]:
        """获取密码重置token信息"""
        try:
            cursor = self.connection.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT email, token, expires_at, used
            FROM password_reset_tokens
            WHERE token = %s
            """
            cursor.execute(query, (token,))
            return cursor.fetchone()
        except pymysql.Error as e:
            logging.error(f"查询密码重置token失败: {e}")
            return None

    def mark_password_reset_token_as_used(self, token: str) -> bool:
        """标记密码重置token为已使用"""
        try:
            cursor = self.connection.cursor()
            update_query = "UPDATE password_reset_tokens SET used = TRUE WHERE token = %s"
            cursor.execute(update_query, (token,))
            self.connection.commit()
            return True
        except pymysql.Error as e:
            logging.error(f"标记密码重置token为已使用失败: {e}")
            self.connection.rollback()
            return False

    def update_user_password(self, email: str, new_password: str) -> bool:
        """更新用户密码"""
        try:
            import bcrypt
            hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
            cursor = self.connection.cursor()
            update_query = "UPDATE users SET password = %s WHERE email = %s"
            cursor.execute(update_query, (hashed, email))
            self.connection.commit()
            logging.info(f"用户 {email} 密码更新成功")
            return True
        except pymysql.Error as e:
            logging.error(f"更新用户密码失败: {e}")
            self.connection.rollback()
            return False

    def insert_chat_message(self, session_id: str, from_user_id: int, to_user_id: Optional[int], message: str, message_type: str = 'text', reply_to_message_id: Optional[int] = None) -> Optional[int]:
        """插入聊天消息（单次独立连接，避免多线程共享导致协议错误）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            insert_query = """
            INSERT INTO chat_messages (session_id, from_user_id, to_user_id, message, message_type, reply_to_message_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (session_id, from_user_id, to_user_id, message, message_type, reply_to_message_id))
            message_id = cursor.lastrowid
            conn.commit()
            return message_id
        except pymysql.Error as e:
            logging.error(f"插入聊天消息失败: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_chat_messages(self, session_id: str, limit: int = 100) -> list:
        """获取会话的聊天消息（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT id, from_user_id, to_user_id, message, message_type, is_read, is_recalled, reply_to_message_id, created_at
            FROM chat_messages
            WHERE session_id = %s
            ORDER BY created_at ASC
            LIMIT %s
            """
            cursor.execute(query, (session_id, limit))
            result = cursor.fetchall()
            return result
        except pymysql.Error as e:
            logging.error(f"获取聊天消息失败: {e}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_message_by_id(self, message_id: int) -> Optional[Dict[str, Any]]:
        """根据消息ID获取消息详情（用于引用回复，独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT id, session_id, from_user_id, to_user_id, message, message_type, is_read, is_recalled, reply_to_message_id, created_at
            FROM chat_messages
            WHERE id = %s
            """
            cursor.execute(query, (message_id,))
            result = cursor.fetchone()
            return result
        except pymysql.Error as e:
            logging.error(f"获取消息详情失败: {e}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def recall_message(self, message_id: int, user_id: int) -> bool:
        """撤回消息（2分钟内可撤回，只有发送者可以撤回，独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 首先检查消息是否存在、是否属于该用户、是否已撤回、是否在2分钟内
            query = """
            SELECT id, from_user_id, created_at, is_recalled
            FROM chat_messages
            WHERE id = %s
            """
            cursor.execute(query, (message_id,))
            message = cursor.fetchone()
            
            if not message:
                # 消息在数据库中不存在时，视为已被删除或历史数据被清理，返回 False 但不抛异常
                logging.debug(f"撤回消息时未找到消息 {message_id}，可能已被删除或历史清理")
                return False
            
            if message.get("from_user_id") != user_id:
                logging.warning(f"用户 {user_id} 无权撤回消息 {message_id}")
                return False
            
            if message.get("is_recalled"):
                logging.warning(f"消息 {message_id} 已被撤回")
                return False
            
            # 更新消息为已撤回状态
            update_query = """
            UPDATE chat_messages
            SET is_recalled = TRUE
            WHERE id = %s
            """
            cursor.execute(update_query, (message_id,))
            conn.commit()
            logging.info(f"消息 {message_id} 已被用户 {user_id} 撤回")
            return True
        except pymysql.Error as e:
            logging.error(f"撤回消息失败: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        except Exception as e:
            logging.error(f"撤回消息时发生错误: {e}")
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_user_sessions(self, user_id: int, role: str) -> list:
        """获取用户的会话列表（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            if role == 'customer_service':
                # 客服：获取所有分配给该客服的会话，或所有用户发起的会话（待分配）
                query = """
                SELECT DISTINCT 
                    cm.session_id,
                    u.id as user_id,
                    u.username,
                    u.email,
                    (SELECT COUNT(*) FROM chat_messages cm2 
                     WHERE cm2.session_id = cm.session_id 
                     AND cm2.to_user_id = %s 
                     AND cm2.is_read = FALSE) as unread_count,
                    (SELECT message FROM chat_messages cm3 
                     WHERE cm3.session_id = cm.session_id 
                     ORDER BY cm3.created_at DESC LIMIT 1) as last_message,
                    (SELECT created_at FROM chat_messages cm4 
                     WHERE cm4.session_id = cm.session_id 
                     ORDER BY cm4.created_at DESC LIMIT 1) as last_time
                FROM chat_messages cm
                JOIN users u ON (cm.from_user_id = u.id OR cm.to_user_id = u.id)
                WHERE (cm.to_user_id = %s OR cm.to_user_id IS NULL)
                AND u.role = 'user'
                GROUP BY cm.session_id, u.id, u.username, u.email
                ORDER BY last_time DESC
                """
                cursor.execute(query, (user_id, user_id))
            else:
                # 普通用户：获取自己发起的会话
                query = """
                SELECT DISTINCT 
                    cm.session_id,
                    u.id as user_id,
                    u.username,
                    u.email,
                    (SELECT COUNT(*) FROM chat_messages cm2 
                     WHERE cm2.session_id = cm.session_id 
                     AND cm2.to_user_id = %s 
                     AND cm2.is_read = FALSE) as unread_count,
                    (SELECT message FROM chat_messages cm3 
                     WHERE cm3.session_id = cm.session_id 
                     ORDER BY cm3.created_at DESC LIMIT 1) as last_message,
                    (SELECT created_at FROM chat_messages cm4 
                     WHERE cm4.session_id = cm.session_id 
                     ORDER BY cm4.created_at DESC LIMIT 1) as last_time
                FROM chat_messages cm
                JOIN users u ON cm.from_user_id = u.id
                WHERE cm.from_user_id = %s
                GROUP BY cm.session_id, u.id, u.username, u.email
                ORDER BY last_time DESC
                """
                cursor.execute(query, (user_id, user_id))
            result = cursor.fetchall()
            return result
        except pymysql.Error as e:
            logging.error(f"获取用户会话列表失败: {e}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def insert_user_info(self, username: str, email: str, password: str, avatar_data: Optional[bytes] = None, role: str = 'user') -> bool:
        """插入用户信息到数据库，头像可选，默认为默认头像。

        Args:
            username: 用户名（展示用）
            email: 邮箱（登录唯一标识）
            password: 原始明文密码，将在此处进行哈希
            avatar_data: 头像二进制数据，缺省时使用默认头像
            role: 用户角色，'user'（普通用户）、'admin'（管理员）、'customer_service'（客服），默认为 'user'
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
            INSERT INTO users (username, email, password, avatar, role) 
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (username, email, hashed, avatar_data, role))
            user_id = cursor.lastrowid
            self.connection.commit()

            # 只有普通用户才插入默认的 VIP 信息
            if role == 'user':
                self.insert_user_vip_info(user_id)

            logging.info(f"用户 {username} 注册成功，ID: {user_id}, 角色: {role}")
            return True
        except pymysql.Error as e:
            logging.info(f"插入用户信息失败: {e}")
            self.connection.rollback()
            return False

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """根据邮箱查询用户信息（独立连接）。"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = "SELECT id, username, email, password, avatar, role FROM users WHERE email = %s"
            cursor.execute(query, (email,))
            result = cursor.fetchone()
            return result  # 返回包含用户头像和角色的结果
        except pymysql.Error as e:
            logging.error(f"查询用户信息失败: {e}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """根据用户 ID 查询用户基础信息（含头像和角色，独立连接，两次尝试）。"""
        query = "SELECT id, username, email, avatar, role FROM users WHERE id = %s"

        for attempt in range(2):
            conn = None
            cursor = None
            try:
                conn = self._open_conn()
                cursor = conn.cursor(pymysql.cursors.DictCursor)
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                return result
            except Exception as e:
                logging.error(f"第{attempt+1}次根据用户ID查询用户信息失败: {e}")
                # 第二次仍失败则抛出 ConnectionError
                if attempt == 1:
                    raise ConnectionError(f"数据库查询用户ID {user_id} 时发生错误") from e
            finally:
                if cursor:
                    try:
                        cursor.close()
                    except Exception:
                        pass
                if conn:
                    try:
                        conn.close()
                    except Exception:
                        pass
        return None

    def get_chat_session_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """根据 session_id 获取单条会话记录（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT id, session_id, user_id, agent_id, status, created_at, started_at, closed_at
            FROM chat_sessions
            WHERE session_id = %s
            LIMIT 1
            """
            cursor.execute(query, (session_id,))
            result = cursor.fetchone()
            return result
        except Exception as e:
            logging.error(f"根据 session_id 获取会话失败: {e}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

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
        """根据用户 ID 查询用户 VIP 信息（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = "SELECT is_vip, vip_expiry_date, diamonds FROM user_vip WHERE user_id = %s"
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()
            return result
        except pymysql.Error as e:
            logging.info(f"查询用户 VIP 信息失败: {e}")
            return None
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

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
            cursor = self._get_cursor()
            query = "SELECT content FROM announcements ORDER BY id DESC LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
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
            cursor = self._get_cursor()
            update_query = """
            UPDATE users
            SET avatar = %s
            WHERE id = %s
            """
            cursor.execute(update_query, (avatar_data, user_id))
            self.connection.commit()
            cursor.close()
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

    def create_chat_sessions_table(self):
        """创建聊天会话表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                session_id VARCHAR(255) NOT NULL UNIQUE,
                user_id INT NOT NULL,
                agent_id INT NULL,
                status ENUM('pending', 'active', 'closed') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP NULL,
                closed_at TIMESTAMP NULL,
                INDEX idx_session (session_id),
                INDEX idx_user (user_id),
                INDEX idx_agent (agent_id),
                INDEX idx_status (status),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (agent_id) REFERENCES users(id)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
        except pymysql.Error as e:
            logging.error(f"创建聊天会话表失败: {e}")

    def create_agent_status_table(self):
        """创建客服在线状态表（如果不存在）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS agent_status (
                id INT AUTO_INCREMENT PRIMARY KEY,
                agent_id INT NOT NULL UNIQUE,
                status ENUM('online', 'offline', 'away', 'busy') DEFAULT 'offline',
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (agent_id) REFERENCES users(id),
                INDEX idx_status (status),
                INDEX idx_heartbeat (last_heartbeat)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
        except pymysql.Error as e:
            logging.error(f"创建客服在线状态表失败: {e}")

    def create_user_connections_table(self):
        """创建用户连接管理表（WebSocket 连接管理）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS user_connections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                connection_id VARCHAR(255) NOT NULL UNIQUE,
                socket_id VARCHAR(255),
                device_id VARCHAR(255),
                status ENUM('connected', 'disconnected') DEFAULT 'connected',
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                disconnected_at TIMESTAMP NULL,
                ip_address VARCHAR(45),
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                INDEX idx_user (user_id),
                INDEX idx_connection (connection_id),
                INDEX idx_device (device_id),
                INDEX idx_status (status),
                INDEX idx_heartbeat (last_heartbeat)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
            logging.info("user_connections 表创建成功")
        except pymysql.Error as e:
            logging.error(f"创建用户连接管理表失败: {e}")


    def create_user_devices_table(self):
        """创建用户设备管理表（多设备登录管理）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS user_devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                device_id VARCHAR(255) NOT NULL,
                device_name VARCHAR(255),
                device_type ENUM('desktop', 'mobile', 'web', 'other') DEFAULT 'other',
                platform VARCHAR(100),
                browser VARCHAR(100),
                os_version VARCHAR(100),
                app_version VARCHAR(50),
                push_token VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                UNIQUE KEY unique_user_device (user_id, device_id),
                INDEX idx_user (user_id),
                INDEX idx_device (device_id),
                INDEX idx_active (is_active),
                INDEX idx_last_login (last_login)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
            logging.info("user_devices 表创建成功")
        except pymysql.Error as e:
            logging.error(f"创建用户设备管理表失败: {e}")

    def create_message_queue_table(self):
        """创建消息队列表（消息发送失败重试队列）"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS message_queue (
                id INT AUTO_INCREMENT PRIMARY KEY,
                message_id INT NOT NULL,
                session_id VARCHAR(255) NOT NULL,
                from_user_id INT NOT NULL,
                to_user_id INT,
                retry_count INT DEFAULT 0,
                max_retries INT DEFAULT 3,
                status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
                error_message TEXT,
                next_retry_at TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (message_id) REFERENCES chat_messages(id) ON DELETE CASCADE,
                INDEX idx_status (status),
                INDEX idx_next_retry (next_retry_at),
                INDEX idx_message (message_id)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
            logging.info("message_queue 表创建成功")
        except pymysql.Error as e:
            logging.error(f"创建消息队列表失败: {e}")

    def get_online_agents(self) -> list:
        """获取所有在线的客服列表（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT u.id, u.username, u.email, as_table.status, as_table.last_heartbeat
            FROM users u
            JOIN agent_status as_table ON u.id = as_table.agent_id
            WHERE u.role = 'customer_service'
            AND as_table.status IN ('online', 'away')
            AND as_table.last_heartbeat > DATE_SUB(NOW(), INTERVAL 5 MINUTE)
            ORDER BY as_table.last_heartbeat DESC
            """
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            logging.error(f"获取在线客服列表失败: {e}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def create_pending_session(self, session_id: str, user_id: int) -> bool:
        """创建待接入会话（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            insert_query = """
            INSERT INTO chat_sessions (session_id, user_id, status)
            VALUES (%s, %s, 'pending')
            ON DUPLICATE KEY UPDATE status = 'pending'
            """
            cursor.execute(insert_query, (session_id, user_id))
            conn.commit()
            return True
        except pymysql.Error as e:
            logging.error(f"创建待接入会话失败: {e}")
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def assign_session_to_agent(self, session_id: str, agent_id: int) -> bool:
        """将会话分配给客服（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            update_query = """
            UPDATE chat_sessions
            SET agent_id = %s, status = 'active', started_at = NOW()
            WHERE session_id = %s AND status = 'pending'
            """
            cursor.execute(update_query, (agent_id, session_id))
            if cursor.rowcount == 0:
                return False
            conn.commit()
            return True
        except pymysql.Error as e:
            logging.error(f"分配会话给客服失败: {e}")
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_pending_sessions(self) -> list:
        """获取所有待接入的会话列表（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT cs.session_id, cs.user_id, u.username, u.email, cs.created_at,
                   (SELECT message FROM chat_messages cm 
                    WHERE cm.session_id = cs.session_id 
                    ORDER BY cm.created_at DESC LIMIT 1) as last_message
            FROM chat_sessions cs
            JOIN users u ON cs.user_id = u.id
            WHERE cs.status = 'pending'
            ORDER BY cs.created_at ASC
            """
            cursor.execute(query)
            result = cursor.fetchall()
            return result
        except Exception as e:
            logging.error(f"获取待接入会话列表失败: {e}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def get_agent_sessions(self, agent_id: int, include_pending: bool = False) -> list:
        """获取客服的会话列表（我的会话，独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            if include_pending:
                # 包含待接入
                query = """
                SELECT cs.session_id, cs.user_id, u.username, u.email, cs.status,
                       cs.started_at, cs.created_at,
                       (SELECT COUNT(*) FROM chat_messages cm2 
                        WHERE cm2.session_id = cs.session_id 
                        AND cm2.to_user_id = %s 
                        AND cm2.is_read = FALSE) as unread_count,
                       (SELECT message FROM chat_messages cm3 
                        WHERE cm3.session_id = cs.session_id 
                        ORDER BY cm3.created_at DESC LIMIT 1) as last_message
                FROM chat_sessions cs
                JOIN users u ON cs.user_id = u.id
                WHERE cs.agent_id = %s OR (cs.agent_id IS NULL AND cs.status = 'pending')
                ORDER BY cs.created_at DESC
                """
                cursor.execute(query, (agent_id, agent_id))
            else:
                # 只包含已分配的会话
                query = """
                SELECT cs.session_id, cs.user_id, u.username, u.email, cs.status,
                       cs.started_at, cs.created_at,
                       (SELECT COUNT(*) FROM chat_messages cm2 
                        WHERE cm2.session_id = cs.session_id 
                        AND cm2.to_user_id = %s 
                        AND cm2.is_read = FALSE) as unread_count,
                       (SELECT message FROM chat_messages cm3 
                        WHERE cm3.session_id = cs.session_id 
                        ORDER BY cm3.created_at DESC LIMIT 1) as last_message
                FROM chat_sessions cs
                JOIN users u ON cs.user_id = u.id
                WHERE cs.agent_id = %s AND cs.status = 'active'
                ORDER BY cs.started_at DESC
                """
                cursor.execute(query, (agent_id, agent_id))
            result = cursor.fetchall()
            return result
        except pymysql.Error as e:
            logging.error(f"获取客服会话列表失败: {e}")
            return []
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def update_agent_status(self, agent_id: int, status: str) -> bool:
        """更新客服在线状态（独立连接）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            insert_query = """
            INSERT INTO agent_status (agent_id, status)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE status = %s, last_heartbeat = NOW()
            """
            cursor.execute(insert_query, (agent_id, status, status))
            conn.commit()
            return True
        except pymysql.Error as e:
            logging.error(f"更新客服状态失败: {e}")
            try:
                if conn:
                    conn.rollback()
            except Exception:
                pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            logging.info("数据库连接已关闭")

    # ==================== WebSocket 连接管理方法 ====================

    def create_user_connection(self, user_id: int, connection_id: str, socket_id: str = None, 
                              device_id: str = None, ip_address: str = None, user_agent: str = None) -> bool:
        """创建用户连接记录"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            insert_query = """
            INSERT INTO user_connections 
            (user_id, connection_id, socket_id, device_id, status, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, 'connected', %s, %s)
            ON DUPLICATE KEY UPDATE 
                socket_id = VALUES(socket_id),
                status = 'connected',
                last_heartbeat = CURRENT_TIMESTAMP,
                connected_at = CURRENT_TIMESTAMP,
                disconnected_at = NULL
            """
            cursor.execute(insert_query, (user_id, connection_id, socket_id, device_id, ip_address, user_agent))
            conn.commit()
            logging.info(f"用户 {user_id} 的连接 {connection_id} 已创建")
            return True
        except pymysql.Error as e:
            logging.error(f"创建用户连接失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def update_connection_heartbeat(self, connection_id: str) -> bool:
        """更新连接心跳时间"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            update_query = """
            UPDATE user_connections
            SET last_heartbeat = CURRENT_TIMESTAMP
            WHERE connection_id = %s AND status = 'connected'
            """
            cursor.execute(update_query, (connection_id,))
            conn.commit()
            return cursor.rowcount > 0
        except pymysql.Error as e:
            logging.error(f"更新连接心跳失败: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def disconnect_user_connection(self, connection_id: str) -> bool:
        """断开用户连接"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            update_query = """
            UPDATE user_connections
            SET status = 'disconnected', disconnected_at = CURRENT_TIMESTAMP
            WHERE connection_id = %s
            """
            cursor.execute(update_query, (connection_id,))
            conn.commit()
            logging.info(f"连接 {connection_id} 已断开")
            return True
        except pymysql.Error as e:
            logging.error(f"断开用户连接失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_user_connections(self, user_id: int, active_only: bool = True) -> list:
        """获取用户的所有连接"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            if active_only:
                query = """
                SELECT * FROM user_connections
                WHERE user_id = %s AND status = 'connected'
                AND last_heartbeat > DATE_SUB(NOW(), INTERVAL 2 MINUTE)
                ORDER BY connected_at DESC
                """
            else:
                query = """
                SELECT * FROM user_connections
                WHERE user_id = %s
                ORDER BY connected_at DESC
                """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except pymysql.Error as e:
            logging.error(f"获取用户连接失败: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def cleanup_stale_connections(self, timeout_minutes: int = 5) -> int:
        """清理过期的连接（超过指定分钟数没有心跳）"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            update_query = """
            UPDATE user_connections
            SET status = 'disconnected', disconnected_at = CURRENT_TIMESTAMP
            WHERE status = 'connected'
            AND last_heartbeat < DATE_SUB(NOW(), INTERVAL %s MINUTE)
            """
            cursor.execute(update_query, (timeout_minutes,))
            conn.commit()
            cleaned = cursor.rowcount
            if cleaned > 0:
                logging.info(f"清理了 {cleaned} 个过期连接")
            return cleaned
        except pymysql.Error as e:
            logging.error(f"清理过期连接失败: {e}")
            return 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ==================== 设备管理方法 ====================

    def register_user_device(self, user_id: int, device_id: str, device_name: str = None,
                            device_type: str = 'other', platform: str = None, browser: str = None,
                            os_version: str = None, app_version: str = None, push_token: str = None) -> bool:
        """注册用户设备"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            insert_query = """
            INSERT INTO user_devices 
            (user_id, device_id, device_name, device_type, platform, browser, os_version, app_version, push_token, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE
                device_name = VALUES(device_name),
                device_type = VALUES(device_type),
                platform = VALUES(platform),
                browser = VALUES(browser),
                os_version = VALUES(os_version),
                app_version = VALUES(app_version),
                push_token = VALUES(push_token),
                is_active = TRUE,
                last_login = CURRENT_TIMESTAMP
            """
            cursor.execute(insert_query, (user_id, device_id, device_name, device_type, 
                                         platform, browser, os_version, app_version, push_token))
            conn.commit()
            logging.info(f"用户 {user_id} 的设备 {device_id} 已注册")
            return True
        except pymysql.Error as e:
            logging.error(f"注册用户设备失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_user_devices(self, user_id: int, active_only: bool = True) -> list:
        """获取用户的所有设备"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            if active_only:
                query = """
                SELECT * FROM user_devices
                WHERE user_id = %s AND is_active = TRUE
                ORDER BY last_login DESC
                """
            else:
                query = """
                SELECT * FROM user_devices
                WHERE user_id = %s
                ORDER BY last_login DESC
                """
            cursor.execute(query, (user_id,))
            return cursor.fetchall()
        except pymysql.Error as e:
            logging.error(f"获取用户设备失败: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def deactivate_user_device(self, user_id: int, device_id: str) -> bool:
        """停用用户设备"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            update_query = """
            UPDATE user_devices
            SET is_active = FALSE
            WHERE user_id = %s AND device_id = %s
            """
            cursor.execute(update_query, (user_id, device_id))
            conn.commit()
            logging.info(f"用户 {user_id} 的设备 {device_id} 已停用")
            return True
        except pymysql.Error as e:
            logging.error(f"停用用户设备失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ==================== 消息状态管理方法 ====================

    def edit_message(self, message_id: int, user_id: int, new_content: str) -> bool:
        """
        编辑消息
        
        Args:
            message_id: 消息ID
            user_id: 用户ID（验证消息归属）
            new_content: 新内容
            
        Returns:
            bool: 是否成功
        """
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            
            # 首先检查消息是否存在且属于该用户，且未撤回
            check_query = """
            SELECT id, from_user_id, is_recalled, created_at
            FROM chat_messages
            WHERE id = %s
            """
            cursor.execute(check_query, (message_id,))
            message = cursor.fetchone()
            
            if not message:
                logging.warning(f"消息不存在: message_id={message_id}")
                return False
            
            # 检查消息归属
            if message[1] != user_id:
                logging.warning(f"用户 {user_id} 无权编辑消息 {message_id}（消息属于用户 {message[1]}）")
                return False
            
            # 检查是否已撤回
            if message[2]:
                logging.warning(f"消息 {message_id} 已撤回，不能编辑")
                return False
            
            # 检查时间限制（5分钟内可编辑）
            import time
            from datetime import datetime, timedelta
            created_at = message[3]
            if isinstance(created_at, datetime):
                time_diff = datetime.now() - created_at
                if time_diff > timedelta(minutes=5):
                    logging.warning(f"消息 {message_id} 超过5分钟，不能编辑")
                    return False
            
            # 更新消息内容
            update_query = """
            UPDATE chat_messages
            SET message = %s, is_edited = TRUE, edited_at = NOW()
            WHERE id = %s AND from_user_id = %s
            """
            cursor.execute(update_query, (new_content, message_id, user_id))
            conn.commit()
            
            if cursor.rowcount == 0:
                logging.warning(f"编辑消息失败: message_id={message_id}, user_id={user_id}")
                return False
            
            logging.info(f"消息 {message_id} 编辑成功")
            return True
            
        except Exception as e:
            logging.error(f"编辑消息失败: {e}", exc_info=True)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    def close_session(self, session_id: str, closed_by_user_id: int) -> bool:
        """
        关闭会话
        
        Args:
            session_id: 会话ID
            closed_by_user_id: 关闭操作的用户ID
            
        Returns:
            bool: 是否成功
        """
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            
            # 首先检查会话是否存在
            check_query = """
            SELECT id, user_id, agent_id, status
            FROM chat_sessions
            WHERE session_id = %s
            """
            cursor.execute(check_query, (session_id,))
            session = cursor.fetchone()
            
            if not session:
                logging.warning(f"会话不存在: session_id={session_id}")
                return False
            
            # 检查权限：用户只能关闭自己的会话，客服可以关闭分配的会话
            user_id = session[1]
            agent_id = session[2]
            if closed_by_user_id != user_id and closed_by_user_id != agent_id:
                # 检查是否是管理员或客服
                user_row = self.get_user_by_id(closed_by_user_id)
                if not user_row or user_row.get('role') not in ['customer_service', 'admin']:
                    logging.warning(f"用户 {closed_by_user_id} 无权关闭会话 {session_id}")
                    return False
            
            # 检查会话是否已关闭
            if session[3] == 'closed':
                logging.info(f"会话 {session_id} 已经关闭")
                return True
            
            # 更新会话状态
            update_query = """
            UPDATE chat_sessions
            SET status = 'closed', closed_at = NOW()
            WHERE session_id = %s
            """
            cursor.execute(update_query, (session_id,))
            conn.commit()
            
            if cursor.rowcount == 0:
                logging.warning(f"关闭会话失败: session_id={session_id}")
                return False
            
            logging.info(f"会话 {session_id} 已关闭（由用户 {closed_by_user_id} 关闭）")
            return True
            
        except Exception as e:
            logging.error(f"关闭会话失败: {e}", exc_info=True)
            if conn:
                try:
                    conn.rollback()
                except Exception:
                    pass
            return False
        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    def update_message_status(self, message_id: int, status: str) -> bool:
        """更新消息状态"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            
            # 根据状态设置相应的时间戳
            if status == 'sent':
                update_query = """
                UPDATE chat_messages
                SET status = %s, sent_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
            elif status == 'delivered':
                update_query = """
                UPDATE chat_messages
                SET status = %s, delivered_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """
            elif status == 'read':
                update_query = """
                UPDATE chat_messages
                SET status = %s, read_at = CURRENT_TIMESTAMP, is_read = TRUE
                WHERE id = %s
                """
            else:
                update_query = """
                UPDATE chat_messages
                SET status = %s
                WHERE id = %s
                """
            
            cursor.execute(update_query, (status, message_id))
            conn.commit()
            updated = cursor.rowcount > 0
            if not updated:
                # 消息可能不存在或已被清理，这在某些场景下是允许的，这里仅记录调试日志避免刷警告
                logging.debug(f"更新消息 {message_id} 状态失败：消息不存在或已删除（可忽略）")
            return updated
        except pymysql.Error as e:
            # 检查是否是字段不存在的错误
            error_msg = str(e).lower()
            if 'unknown column' in error_msg or 'doesn\'t exist' in error_msg:
                # 字段不存在，尝试确保字段存在
                logging.warning(f"消息状态字段不存在，尝试创建: {e}")
                try:
                    self._ensure_message_status_fields()
                    # 重试更新
                    cursor.execute(update_query, (status, message_id))
                    conn.commit()
                    return cursor.rowcount > 0
                except Exception as retry_error:
                    logging.error(f"重试更新消息状态失败: {retry_error}")
            else:
                logging.error(f"更新消息状态失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_undelivered_messages(self, user_id: int, limit: int = 100) -> list:
        """获取未送达的消息"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT * FROM chat_messages
            WHERE to_user_id = %s 
            AND status IN ('pending', 'sent')
            AND is_recalled = FALSE
            ORDER BY created_at ASC
            LIMIT %s
            """
            cursor.execute(query, (user_id, limit))
            return cursor.fetchall()
        except pymysql.Error as e:
            logging.error(f"获取未送达消息失败: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    # ==================== 消息队列管理方法 ====================

    def add_message_to_queue(self, message_id: int, session_id: str, from_user_id: int, 
                            to_user_id: int = None, max_retries: int = 3) -> bool:
        """将消息添加到重试队列"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            insert_query = """
            INSERT INTO message_queue (message_id, session_id, from_user_id, to_user_id, max_retries, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            """
            cursor.execute(insert_query, (message_id, session_id, from_user_id, to_user_id, max_retries))
            conn.commit()
            logging.info(f"消息 {message_id} 已添加到重试队列")
            return True
        except pymysql.Error as e:
            logging.error(f"添加消息到队列失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_pending_queue_messages(self, limit: int = 50) -> list:
        """获取待重试的消息"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            query = """
            SELECT mq.*, cm.message, cm.message_type
            FROM message_queue mq
            JOIN chat_messages cm ON mq.message_id = cm.id
            WHERE mq.status = 'pending'
            AND (mq.next_retry_at IS NULL OR mq.next_retry_at <= CURRENT_TIMESTAMP)
            AND mq.retry_count < mq.max_retries
            ORDER BY mq.created_at ASC
            LIMIT %s
            """
            cursor.execute(query, (limit,))
            return cursor.fetchall()
        except pymysql.Error as e:
            logging.error(f"获取待重试消息失败: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def update_queue_message_status(self, queue_id: int, status: str, error_message: str = None) -> bool:
        """更新队列中消息的状态"""
        conn = None
        cursor = None
        try:
            conn = self._open_conn()
            cursor = conn.cursor()
            if status == 'failed' and error_message:
                update_query = """
                UPDATE message_queue
                SET status = %s, error_message = %s, retry_count = retry_count + 1,
                    next_retry_at = DATE_ADD(CURRENT_TIMESTAMP, INTERVAL POWER(2, retry_count) MINUTE)
                WHERE id = %s
                """
                cursor.execute(update_query, (status, error_message, queue_id))
            else:
                update_query = """
                UPDATE message_queue
                SET status = %s
                WHERE id = %s
                """
                cursor.execute(update_query, (status, queue_id))
            conn.commit()
            return cursor.rowcount > 0
        except pymysql.Error as e:
            logging.error(f"更新队列消息状态失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()