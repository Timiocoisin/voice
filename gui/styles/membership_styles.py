"""会员相关对话框的样式配置。"""

# 会员卡片容器样式
VIP_CARD_CONTAINER = """
    #vipPackageCard {
        background-color: rgba(255, 255, 255, 210);
        border-radius: 24px;
        border: 1px solid rgba(226, 232, 240, 180);
    }
"""

# 钻石卡片容器样式
DIAMOND_CARD_CONTAINER = """
    #diamondPackageCard {
        background-color: rgba(255, 255, 255, 210);
        border-radius: 24px;
        border: 1px solid rgba(226, 232, 240, 180);
    }
"""

# 支付二维码卡片样式
PAYMENT_CARD_CONTAINER = """
    #paymentCard {
        background-color: rgba(255, 255, 255, 220);
        border-radius: 24px;
        border: 1px solid rgba(226, 232, 240, 200);
    }
"""

# 标题样式
TITLE_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 28px;
        font-weight: 700;
        color: #1e293b;
        padding: 4px 0px;
    }
"""

# 会员有效期标签样式
VIP_EXPIRY_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 14px;
        color: #64748b;
        padding: 2px 0px 8px 0px;
    }
"""

# 会员卡片基础样式（需要格式化name）
MEMBERSHIP_CARD_STYLE = """
    #membershipCard_{name} {{
        background-color: rgba(255, 255, 255, 240);
        border: 1px solid rgba(226, 232, 240, 220);
        border-radius: 16px;
    }}
    #membershipCard_{name}:hover {{
        background-color: rgba(255, 255, 255, 255);
        border: 1.5px solid rgba(59, 130, 246, 250);
    }}
"""

# 卡片名称样式
CARD_NAME_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 18px;
        font-weight: 700;
        color: #1e293b;
        padding: 2px 0px;
    }
"""

# 钻石数量样式
DIAMOND_COUNT_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 16px;
        font-weight: 600;
        color: #3b82f6;
        padding: 2px 0px;
    }
"""

# 购买按钮样式
BUY_BUTTON_STYLE = """
    QPushButton {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 13px;
        font-weight: 700;
        color: white;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #60a5fa, stop:1 #3b82f6);
        border: none;
        border-radius: 12px;
        padding: 8px 24px;
        min-width: 100px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #3b82f6, stop:1 #2563eb);
    }
    QPushButton:pressed {
        background: #2563eb;
    }
"""

# 支付按钮样式
PAY_BUTTON_STYLE = """
    QPushButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #10b981, stop:1 #059669);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 28px;
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 14px;
        font-weight: 700;
        min-width: 120px;
    }
    QPushButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 #059669, stop:1 #047857);
    }
    QPushButton:pressed {
        background: #047857;
    }
"""

# 取消按钮样式
CANCEL_BUTTON_STYLE = """
    QPushButton {
        background-color: rgba(226, 232, 240, 200);
        color: #475569;
        border: none;
        border-radius: 12px;
        padding: 10px 28px;
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 14px;
        font-weight: 600;
        min-width: 120px;
    }
    QPushButton:hover {
        background-color: rgba(203, 213, 225, 230);
    }
    QPushButton:pressed {
        background-color: rgba(148, 163, 184, 200);
    }
"""

# 支付金额样式
PAYMENT_AMOUNT_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 36px;
        font-weight: 700;
        color: #ef4444;
        padding: 8px 0px;
    }
"""

# 支付说明文本样式
PAYMENT_NOTE_STYLE = """
    QLabel {
        font-family: "Microsoft YaHei", "SimHei", "Arial";
        font-size: 13px;
        color: #64748b;
        padding: 4px 0px;
        line-height: 1.6;
    }
"""
