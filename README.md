## 变声器桌面客户端（PyQt6）

一个基于 **PyQt6** 的桌面变声器客户端，集成了用户登录 / 注册、邮箱验证、VIP 会员体系、钻石充值、系统公告展示，以及内置的客服聊天面板（关键词自动回复），适合作为**商业化变声器前端客户端**或桌面应用模板进行二次开发。


---

### 功能特性

- **现代化 UI 界面**
  - 基于 `PyQt6` 实现无边框、圆角主窗口，支持自定义拖拽、蒙版遮罩等效果  
  - 左右分栏布局，包含主功能区、聊天区、公告等区域  
  - 统一图标与插画资源（见 `resources/icons` 与 `resources/images`）

- **账户系统**
  - 邮箱注册 / 登录（密码使用 `bcrypt` 加密存储）  
  - 支持默认头像与自定义头像上传 / 裁剪  
  - 自动登录、登录状态管理、本地 Token 加密存储

- **VIP 会员 & 充值体系**
  - MySQL 中维护 `users` / `user_vip` 两张表，记录会员状态、过期时间与钻石数量  
  - 支持钻石消耗开通 / 续费 VIP  
  - 提供 VIP 套餐展示、支付二维码弹窗（微信 / 支付宝），方便接入实际支付回调

- **客服聊天面板**
  - 内置客服聊天窗口，支持文本、图片、文件消息气泡展示  
  - 基于 `backend/customer_service` 下的关键词匹配模块，实现 FAQ 智能回复  
  - 支持 FAQ 列表、常见问题卡片、表情插入、未读消息角标等交互

- **系统公告 & 图标管理**
  - `announcements` 表存储系统公告，支持在主界面滚动展示最新公告  
  - `logos` 表管理客户端图标，从数据库中读取最新 Logo 并设置为应用图标

- **邮件与安全**
  - 使用 QQ 邮箱 SMTP (`smtp.qq.com:465`) 发送验证码 / 通知邮件  
  - 本地使用对称加密保存 Token（`SECRET_KEY` / `ENCRYPTION_KEY`），降低明文泄露风险

---

### 项目结构概览

```text
change_voice/
├── main.py                      # 程序入口，初始化 QApplication 与主窗口
├── backend/                     # 业务与数据层
│   ├── config/                  # 配置（邮件、加密、文案等）
│   ├── customer_service/        # 客服关键词匹配与知识库
│   ├── database/                # MySQL 连接与线程封装
│   ├── email/                   # 邮件发送工具
│   ├── encryption/              # 加解密工具
│   ├── login/                   # 登录 / Token / 自动登录
│   ├── timer/                   # 定时任务相关
│   └── utils / validation ...   # 通用工具与校验
├── gui/                         # 界面层（PyQt6）
│   ├── main_window.py           # 主窗口，拼装整体 UI 与事件处理
│   ├── components/              # 聊天气泡、顶部栏、布局等 UI 组件
│   ├── handlers/                # 事件处理（聊天、窗口、会员、头像等）
│   └── styles/ & views/         # 样式与视图封装
├── modules/                     # 各类弹窗 / 对话框
│   ├── login_dialog.py          # 登录对话框
│   ├── vip_membership_dialog.py # VIP 相关对话框
│   └── dialogs/                 # 支付二维码、套餐说明等弹窗
└── resources/                   # 图标与图片资源
```

如需了解客服模块的详细设计与使用方式，可参见：`backend/customer_service/README.md`。

---

### 环境要求

- **操作系统**：Windows 10 / 11（其他平台需自行测试）  
- **Python**：建议 `Python 3.9+`  
- **数据库**：MySQL 5.7 / 8.x（默认连接 `host=localhost, user=root, password=123456, database=voice`，可按需修改）  
- **依赖库（核心）**：
  - `PyQt6`
  - `PyMySQL`
  - `bcrypt`

> 可以根据实际使用的三方库补充或维护 `requirements.txt`，方便一键安装依赖。

---

### 快速开始

#### 1. 克隆项目

```bash
git clone <your-repo-url> change_voice
cd change_voice
```

#### 2. 安装依赖

建议使用虚拟环境（如 `venv` / `conda`），然后安装依赖：

```bash
pip install PyQt6 pymysql bcrypt
```

或根据你实际维护的 `requirements.txt` 执行：

```bash
pip install -r requirements.txt
```

#### 3. 配置数据库

1. 启动本地 MySQL 服务  
2. 创建数据库：

```sql
CREATE DATABASE voice DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. 确认 `backend/database/database_manager.py` 中的连接配置与实际一致（主机 / 端口 / 用户名 / 密码 / 数据库名）。  
4. 首次启动程序时会自动创建以下表：
   - `users`：用户基础信息（邮箱、用户名、密码、头像等）
   - `user_vip`：会员信息（是否 VIP、到期时间、钻石数量等）
   - `logos`：Logo 图标二进制存储
   - `announcements`：系统公告

> 如需初始化一些测试用户 / VIP / 公告数据，可自行编写 SQL 脚本导入。

#### 4. 配置邮件与加密（可选但推荐）

打开 `backend/config/config.py`：

- 修改 `email_config` 中的 `sender_email` / `sender_password` / `sender_name` 为你的发信邮箱  
- 如有安全要求，请替换 `SECRET_KEY` 与 `ENCRYPTION_KEY`，并**避免将真实密钥提交到公开仓库**

#### 5. 运行程序

```bash
python main.py
```

首次运行时：

- 若数据库无法连接，会弹出错误提示对话框  
- 成功后将打开主窗口，可通过右上角 / 菜单等入口打开登录对话框、VIP 对话框与客服聊天面板

---

### 客服系统简要说明

本项目内置一个基于 **关键词匹配** 的本地客服系统：

- 知识库定义在 `backend/customer_service/knowledge_base.py`  
- 匹配逻辑封装在 `backend/customer_service/keyword_matcher.py` 中，通过 `get_matcher()` 获取单例  
- 在 GUI 中，实现了用户发送消息后自动调用匹配器生成回复的流程  

扩展方式包括但不限于：

- 增加更多 FAQ 条目与关键词  
- 替换为 TF-IDF / 余弦相似度等更复杂的文本匹配算法  
- 接入在线大模型作为兜底（例如未匹配到答案时调用外部 API）

详情可参考模块内的 `README.md`。

---

### 部署与发布建议

- **开发环境**：直接运行 `python main.py` 进行调试  
- **打包发布**：
  - 可以使用 `PyInstaller`、`cx_Freeze` 等工具打包为 Windows 可执行文件（`exe`）  
  - 将资源目录（`resources`）、配置文件及依赖 DLL 一并打包  
- **数据库与配置**：
  - 生产环境请将数据库与邮箱配置从代码中抽离到环境变量或独立配置文件  
  - 对敏感信息进行加密或最小化权限配置（单独的数据库账号，仅授予所需权限）

---

### 开发规划 / TODO（示例）

- [ ] 接入实际的音频处理 / 变声后端服务  
- [ ] 增加多语言支持（中 / 英等）  
- [ ] 丰富会员权益展示与运营位文案  
- [ ] 优化聊天窗口的性能与消息记录持久化  
- [ ] 提供一键打包脚本与安装向导

---

### 许可证

根据你的实际使用场景选择合适的开源协议（例如 MIT / Apache-2.0 / GPL 等），  
并在仓库中添加 `LICENSE` 文件。当前示例未附带具体许可证，请在正式开源前补充。 
