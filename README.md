## 变声器桌面客户端（PyQt6）

一个基于 **PyQt6** 的桌面变声器客户端，采用**前后端分离架构**。客户端负责 UI 展示，后端提供 HTTP API 服务，集成了用户登录/注册、邮箱验证、VIP 会员体系、钻石充值、系统公告展示，以及内置的客服聊天面板（关键词自动回复），适合作为**商业化变声器前端客户端**或桌面应用模板进行二次开发。

---

## 架构说明

本项目采用**前后端分离架构**：

- **后端（`backend/`）**：提供 HTTP API 服务，处理业务逻辑、数据库操作、邮件发送等
- **客户端（`client/`）**：纯 UI 层，通过 HTTP 请求与后端通信，不直接访问数据库

### 架构优势

- ✅ **完全解耦**：客户端与后端可独立开发、部署、升级
- ✅ **安全性**：客户端不包含数据库连接、业务逻辑等敏感信息
- ✅ **可扩展性**：后端可同时服务多个客户端（桌面、Web、移动端等）
- ✅ **易维护**：前后端职责清晰，便于团队协作

---

## 功能特性

- **现代化 UI 界面**
  - 基于 `PyQt6` 实现无边框、圆角主窗口，支持自定义拖拽、蒙版遮罩等效果  
  - 左右分栏布局，包含主功能区、聊天区、公告等区域  
  - 统一图标与插画资源（见 `client/resources/icons` 与 `client/resources/images`）

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
  - 基于 `client/customer_service` 下的关键词匹配模块，实现 FAQ 智能回复（本地匹配）  
  - 支持 FAQ 列表、常见问题卡片、表情插入、未读消息角标等交互

- **系统公告**
  - `announcements` 表存储系统公告，支持在主界面滚动展示最新公告

- **邮件与安全**
  - 使用 QQ 邮箱 SMTP (`smtp.qq.com:465`) 发送验证码 / 通知邮件  
  - 本地使用对称加密保存 Token（`ENCRYPTION_KEY`），降低明文泄露风险
  - Token 签名验证由后端完成，客户端仅做格式检查

---

## 项目结构概览

```text
change_voice/
├── backend/                     # 后端服务（HTTP API）
│   ├── api_server.py            # Flask API 服务器入口
│   ├── config/                  # 配置（邮件、加密、数据库、文案等）
│   ├── customer_service/        # 客服关键词匹配与知识库（后端版本）
│   ├── database/                # MySQL 连接与线程封装
│   ├── email/                   # 邮件发送工具
│   ├── encryption/              # 加解密工具
│   ├── login/                   # 登录 / Token 生成与验证
│   ├── membership_service.py    # VIP 会员业务逻辑
│   ├── resources/               # 资源加载（后端版本）
│   ├── timer/                   # 定时任务相关
│   └── utils / validation ...   # 通用工具与校验
│
├── client/                      # 客户端（PyQt6 UI）
│   ├── main.py                  # 程序入口，初始化 QApplication 与主窗口
│   ├── api_client.py            # HTTP API 客户端封装
│   ├── config/                  # 客户端配置（UI 文案、加密密钥等）
│   ├── customer_service/        # 客服关键词匹配（本地版本，用于聊天）
│   ├── encryption/              # 本地加密工具（Token 加密）
│   ├── login/                   # 登录状态管理、Token 存储
│   ├── resources/               # 图标与图片资源
│   ├── validation/              # 前端表单验证
│   ├── timer/                    # UI 定时器
│   ├── utils/                    # UI 工具类
│   ├── gui/                      # 界面层（PyQt6）
│   │   ├── main_window.py       # 主窗口，拼装整体 UI 与事件处理
│   │   ├── components/          # 聊天气泡、顶部栏、布局等 UI 组件
│   │   ├── handlers/            # 事件处理（聊天、窗口、会员、头像等）
│   │   └── styles/ & views/     # 样式与视图封装
│   └── modules/                  # 各类弹窗 / 对话框
│       ├── login_dialog.py      # 登录对话框
│       ├── vip_membership_dialog.py # VIP 相关对话框
│       └── dialogs/              # 支付二维码、套餐说明等弹窗
│
└── frontend/                     # Web 前端（可选，Vue.js）
    └── chat-web/                 # Web 聊天界面
```

---

## 环境要求

### 后端
- **操作系统**：Windows / Linux / macOS  
- **Python**：建议 `Python 3.9+`  
- **数据库**：MySQL 5.7 / 8.x
- **依赖库（核心）**：
  - `Flask` - Web 框架
  - `PyMySQL` - MySQL 数据库连接
  - `bcrypt` - 密码加密
  - `cryptography` - Token 加密
  - `requests` - HTTP 客户端（用于测试）

### 客户端
- **操作系统**：Windows 10 / 11（其他平台需自行测试）  
- **Python**：建议 `Python 3.9+`  
- **依赖库（核心）**：
  - `PyQt6` - GUI 框架
  - `requests` - HTTP 请求
  - `cryptography` - Token 加密

> 可以根据实际使用的三方库补充或维护 `requirements.txt`，方便一键安装依赖。

---

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url> change_voice
cd change_voice
```

### 2. 安装依赖

建议使用虚拟环境（如 `venv` / `conda`），然后安装依赖：

```bash
# 后端依赖
pip install Flask pymysql bcrypt cryptography requests

# 客户端依赖
pip install PyQt6 requests cryptography
```

或根据你实际维护的 `requirements.txt` 执行：

```bash
pip install -r requirements.txt
```

### 3. 配置数据库

1. 启动本地 MySQL 服务  
2. 创建数据库（后端会自动创建，也可手动创建）：

```sql
CREATE DATABASE voice DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

3. 确认 `backend/config/database_config.py` 中的连接配置与实际一致（主机 / 端口 / 用户名 / 密码 / 数据库名）。  
4. 首次启动后端服务时会自动创建以下表：
   - `users`：用户基础信息（邮箱、用户名、密码、头像等）
   - `user_vip`：会员信息（是否 VIP、到期时间、钻石数量等）
   - `announcements`：系统公告

> 如需初始化一些测试用户 / VIP / 公告数据，可自行编写 SQL 脚本导入。

### 4. 配置邮件与加密（可选但推荐）

打开 `backend/config/config.py`：

- 修改 `email_config` 中的 `sender_email` / `sender_password` / `sender_name` 为你的发信邮箱  
- 如有安全要求，请替换 `SECRET_KEY` 与 `ENCRYPTION_KEY`
- 确保 `client/config/config.py` 中的 `ENCRYPTION_KEY` 与后端一致

### 5. 启动后端服务

在项目根目录下运行：

```bash
# 方式一：使用模块方式运行（推荐）
python -m backend.api_server

# 方式二：直接运行（需要确保在正确的路径下）
cd backend
python api_server.py
```

后端服务默认运行在 `http://127.0.0.1:8000`，你可以在浏览器访问 `http://127.0.0.1:8000/api/health` 检查服务是否正常。

### 6. 启动客户端

在项目根目录下运行：

```bash
# 方式一：使用模块方式运行（推荐）
python -m client.main

# 方式二：直接运行
cd client
python main.py
```

首次运行时：

- 客户端会自动检查后端服务是否可用（`http://127.0.0.1:8000/api/health`）
- 若后端服务未启动，会弹出错误提示对话框
- 成功后将打开主窗口，可通过右上角 / 菜单等入口打开登录对话框、VIP 对话框与客服聊天面板

---

## API 接口说明

后端提供以下 HTTP API 接口（详见 `backend/api_server.py`）：

### 健康检查
- `GET /api/health` - 检查服务状态

### 用户相关
- `POST /api/send_verification_code` - 发送验证码
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `POST /api/check_token` - 验证 Token 并获取用户信息
- `POST /api/user/profile` - 获取用户信息
- `POST /api/user/avatar` - 更新用户头像

### VIP 相关
- `POST /api/vip/info` - 获取 VIP 信息
- `POST /api/vip/purchase` - 购买会员套餐
- `POST /api/diamond/balance` - 获取钻石余额

### 公告相关
- `GET /api/announcement/latest` - 获取最新公告

所有接口的详细说明和请求/响应格式，请参考 `backend/api_server.py` 和 `client/api_client.py`。

---

## 客服系统简要说明

本项目内置一个基于 **关键词匹配** 的本地客服系统：

- 知识库定义在 `client/customer_service/knowledge_base.py`（客户端本地匹配）  
- 匹配逻辑封装在 `client/customer_service/keyword_matcher.py` 中，通过 `get_matcher()` 获取单例  
- 在 GUI 中，实现了用户发送消息后自动调用匹配器生成回复的流程  

扩展方式包括但不限于：

- 增加更多 FAQ 条目与关键词  
- 替换为 TF-IDF / 余弦相似度等更复杂的文本匹配算法  
- 接入在线大模型作为兜底（例如未匹配到答案时调用外部 API）
- 将匹配逻辑迁移到后端，通过 API 调用（当前为客户端本地匹配）

详情可参考模块内的 `README.md`。

---

## 部署与发布建议

### 开发环境

- **后端**：直接运行 `python -m backend.api_server` 进行调试
- **客户端**：直接运行 `python -m client.main` 进行调试

### 生产环境

#### 后端部署

- 使用 `gunicorn` 或 `uwsgi` 部署 Flask 应用
- 配置 Nginx 反向代理
- 使用环境变量或配置文件管理敏感信息（数据库密码、密钥等）
- 配置 HTTPS 证书

#### 客户端打包

- 可以使用 `PyInstaller`、`cx_Freeze` 等工具打包为 Windows 可执行文件（`exe`）
- 将资源目录（`client/resources`）、配置文件及依赖 DLL 一并打包
- 修改 `client/api_client.py` 中的 `BASE_URL` 为生产环境的后端地址

#### 安全建议

- 生产环境请将数据库与邮箱配置从代码中抽离到环境变量或独立配置文件  
- 对敏感信息进行加密或最小化权限配置（单独的数据库账号，仅授予所需权限）
- 使用 HTTPS 保护 API 通信
- 定期更新密钥和依赖库

---

## 开发规划 / TODO（示例）

- [ ] 接入实际的音频处理 / 变声后端服务  
- [ ] 增加多语言支持（中 / 英等）  
- [ ] 丰富会员权益展示与运营位文案  
- [ ] 优化聊天窗口的性能与消息记录持久化  
- [ ] 提供一键打包脚本与安装向导
- [ ] 添加 API 文档（Swagger / OpenAPI）
- [ ] 实现 WebSocket 实时通信（可选）
- [ ] 添加单元测试与集成测试

---

## 许可证

根据你的实际使用场景选择合适的开源协议（例如 MIT / Apache-2.0 / GPL 等），  
并在仓库中添加 `LICENSE` 文件。当前示例未附带具体许可证，请在正式开源前补充。
