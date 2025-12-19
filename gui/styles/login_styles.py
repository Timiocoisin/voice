"""登录对话框样式配置。"""

# 登录卡片样式（柔和渐变 + 阴影友好边框）
LOGIN_CARD_STYLE = """
    #loginCard {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 255, 255, 250),
            stop:1 rgba(249, 250, 251, 250));
        border-radius: 28px;
        border: 1px solid rgba(226, 232, 240, 200);
    }
"""

"""
预留：登录对话框顶部 Logo / 副标题样式，如需再次使用可在此定义：

LOGO_STYLE = \"\"\"
    QLabel { ... }
\"\"\"

SUBTITLE_STYLE = \"\"\"
    QLabel { ... }
\"\"\"
"""

# 输入框样式
INPUT_STYLE = """
    QLineEdit {
        border: 1px solid rgba(203, 213, 225, 200);
        border-radius: 10px;
        padding: 10px 14px;
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 14px;
        background-color: rgba(248, 250, 252, 1);
        color: #1e293b;
    }
    QLineEdit:focus {
        border: 1.5px solid rgba(99, 102, 241, 255);
        background-color: #ffffff;
    }
    QLineEdit::placeholder {
        color: #9ca3af;
    }
"""

# 主按钮样式（登录/注册）
PRIMARY_BUTTON_STYLE = """
    QPushButton {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 16px;
        font-weight: 700;
        color: white;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #8b5cf6, stop:1 #6366f1);
        border: none;
        border-radius: 16px;
        padding: 12px 32px;
        letter-spacing: 1px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #7c3aed, stop:1 #4f46e5);
    }
    QPushButton:pressed {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #6d28d9, stop:1 #4338ca);
    }
"""

# 次要按钮样式（发送验证码等）
SECONDARY_BUTTON_STYLE = """
    QPushButton {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 13px;
        font-weight: 600;
        color: #6366f1;
        background-color: rgba(238, 242, 255, 1);
        border: 1px solid rgba(199, 210, 254, 1);
        border-radius: 10px;
        padding: 8px 16px;
    }
    QPushButton:hover {
        background-color: rgba(224, 231, 255, 1);
    }
    QPushButton:pressed {
        background-color: rgba(199, 210, 254, 1);
    }
    QPushButton:disabled {
        color: #9ca3af;
        background-color: rgba(243, 244, 246, 1);
        border: 1px solid rgba(229, 231, 235, 1);
    }
"""

# 文本链接样式
TEXT_LINK_STYLE = """
    color: #6366f1;
    text-decoration: none;
    font-weight: 500;
"""

# 错误提示样式
ERROR_LABEL_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 12px;
        color: #ef4444;
        padding: 2px 0px;
    }
"""

# 模式切换按钮样式
MODE_BUTTON_ACTIVE = """
    QPushButton {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 15px;
        font-weight: 700;
        color: #1e293b;
        background-color: transparent;
        border: none;
        border-bottom: 2px solid #6366f1;
        padding: 6px 16px;
    }
"""

MODE_BUTTON_INACTIVE = """
    QPushButton {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 15px;
        font-weight: 500;
        color: #9ca3af;
        background-color: transparent;
        border: none;
        padding: 6px 16px;
    }
    QPushButton:hover {
        color: #6366f1;
    }
"""

# 协议链接样式
AGREEMENT_LINK_STYLE = """
    QLabel {
        color: #6366f1;
        text-decoration: underline;
    }
    QLabel:hover {
        color: #4f46e5;
    }
"""
