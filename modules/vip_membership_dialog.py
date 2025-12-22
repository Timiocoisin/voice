# 文件：vip_membership_dialog.py
import os
from typing import Optional, Dict, TYPE_CHECKING
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QGraphicsDropShadowEffect, QStackedWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, QByteArray
from PyQt6.QtGui import QPainter, QColor, QCursor, QPixmap
from backend.resources import load_icon_data, get_default_avatar
from backend.config import texts as text_cfg
from gui.custom_message_box import CustomMessageBox
from gui.base_dialog import BaseDialog
from gui import api_client
import logging
from backend.logging_manager import setup_logging  # noqa: F401

if TYPE_CHECKING:
    from gui.main_window import MainWindow

# ---------------- 统一配置区域：会员套餐 / 钻石套餐 ----------------

# 会员套餐配置：天卡、月卡、年卡、永久（统一文案与展示）
MEMBERSHIP_CARDS = [
    {"name": "天卡至尊", "subtitle": "连续使用 1 天", "diamonds": 30, "days": 1, "row": 0, "col": 0},
    {"name": "月卡至尊", "subtitle": "连续使用 30 天", "diamonds": 300, "days": 30, "row": 0, "col": 1},
    {"name": "年卡至尊", "subtitle": "连续使用 365 天", "diamonds": 1000, "days": 365, "row": 1, "col": 0},
    {"name": "永久至尊", "subtitle": "一次开通，永久有效", "diamonds": 3000, "days": None, "row": 1, "col": 1},
]

# 钻石套餐配置：2×3 网格布局
DIAMOND_PLANS = [
    {"diamonds": 300, "price": 30, "row": 0, "col": 0},
    {"diamonds": 500, "price": 50, "row": 0, "col": 1},
    {"diamonds": 1000, "price": 100, "row": 0, "col": 2},
    {"diamonds": 1680, "price": 168, "row": 1, "col": 0},
    {"diamonds": 3280, "price": 328, "row": 1, "col": 1},
    {"diamonds": 6480, "price": 648, "row": 1, "col": 2},
]


class VipMembershipDialog(QDialog):
    def __init__(self, parent=None, user_id=None, is_vip=False):
        # 兼容旧调用：直接转到新的会员套餐弹窗
        dlg = VipPackageDialog(parent, user_id=user_id)
        dlg.exec()
    
    def create_non_vip_page(self):
        """创建非会员提示页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        # 进一步压缩上下留白，尽量“吃掉”一半空白
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 标题
        title = QLabel("会员提示")
        title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 22px;
                font-weight: 700;
                color: #1e293b;
                padding: 0px 0px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # 提示信息
        info_label = QLabel("您当前是非会员状态\n是否开通会员享受更多特权？")
        info_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 500;
                color: #64748b;
                padding: 2px 0px;
                line-height: 1.4;
            }
        """)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 按钮布局（放入容器，避免溢出）
        button_row = QWidget()
        button_row.setFixedWidth(300)  # 再收窄一点，减少整体占高
        button_layout = QHBoxLayout(button_row)
        button_layout.setSpacing(8)
        button_layout.setContentsMargins(0, 4, 0, 0)
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 600;
                color: #64748b;
                background-color: rgba(241, 245, 249, 210);
                border: 1px solid rgba(226, 232, 240, 200);
                border-radius: 12px;
                padding: 8px 24px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: rgba(226, 232, 240, 240);
                border-color: rgba(203, 213, 225, 240);
            }
            QPushButton:pressed {
                background-color: rgba(203, 213, 225, 240);
            }
        """)
        cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # 开通会员按钮
        confirm_button = QPushButton("开通会员")
        confirm_button.setStyleSheet("""
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
        """)
        confirm_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 打开独立的“会员套餐”弹窗
        confirm_button.clicked.connect(self.open_membership_packages)
        button_layout.addWidget(confirm_button)
        
        layout.addWidget(button_row, alignment=Qt.AlignmentFlag.AlignCenter)
        # 移除addStretch，使页面更紧凑
        
        return page

    def open_membership_packages(self):
        """打开独立的会员套餐弹窗"""
        # 先关闭当前提示弹窗，再打开套餐弹窗
        self.close()
        dialog = VipPackageDialog(self.parent(), user_id=self.user_id)
        dialog.exec()
    
    def paintEvent(self, event):
        """绘制半透明背景"""
        painter = QPainter(self)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
        painter.end()


class VipPackageDialog(BaseDialog):
    """独立的会员套餐选择弹窗"""

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id
        self.vip_expiry = None  # type: Optional[datetime]

        # 读取当前 VIP 信息
        self._load_vip_info()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # 统一使用基础对话框的卡片容器
        content_widget, content_layout = self.create_card_container(
            "vipPackageCard",
            layout_margins=(36, 24, 36, 24),
            layout_spacing=20,
        )
        content_widget.setStyleSheet("""
            #vipPackageCard {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 180);
            }
        """)

        # 标题
        title = QLabel("选择会员套餐")
        title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
                padding: 4px 0px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title)

        # 有效期显示：有效期至：xxxx-xx-xx / 已过期 / 已永久
        self.vip_expiry_label = QLabel()
        self.vip_expiry_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._update_vip_expiry_label()
        content_layout.addWidget(self.vip_expiry_label)

        # 会员卡2x2网格布局
        cards_grid = QGridLayout()
        cards_grid.setVerticalSpacing(25)
        cards_grid.setHorizontalSpacing(20)
        cards_grid.setContentsMargins(20, 10, 20, 10)

        # 使用统一配置的会员套餐列表
        for card_info in MEMBERSHIP_CARDS:
            card_widget = self._create_membership_card(card_info)
            cards_grid.addWidget(
                card_widget,
                card_info["row"],
                card_info["col"],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )

        content_layout.addLayout(cards_grid)

        main_layout.addWidget(content_widget)
        self.adjustSize()

    def _create_membership_card(self, card_info):
        """创建单个会员卡组件"""
        card_widget = QWidget()
        card_widget.setObjectName(f"membershipCard_{card_info['name']}")
        card_widget.setFixedSize(190, 190)
        card_widget.setStyleSheet(f"""
            #membershipCard_{card_info['name']} {{
                background-color: rgba(255, 255, 255, 240);
                border: 1px solid rgba(226, 232, 240, 220);
                border-radius: 16px;
            }}
            #membershipCard_{card_info['name']}:hover {{
                background-color: rgba(255, 255, 255, 255);
                border: 1.5px solid rgba(59, 130, 246, 250);
            }}
        """)
        card_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        shadow = QGraphicsDropShadowEffect(card_widget)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 20))
        card_widget.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card_widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        period_label = QLabel(card_info["name"])
        period_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;
                font-weight: 700;
                color: #3b82f6;
                padding: 0px;
                margin: 0px;
            }
        """)
        period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(period_label)

        # 副标题：使用时长说明，保持所有卡片文案风格一致
        subtitle = QLabel(card_info.get("subtitle", ""))
        subtitle.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #6b7280;
                padding: 0px;
                margin: 0px;
            }
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        price_label = QLabel(f"{card_info['diamonds']} 钻石")
        price_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 20px;
                font-weight: 600;
                color: #1e293b;
                padding: 0px;
                margin: 0px;
            }
        """)
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)
        # 购买按钮
        buy_button = QPushButton("购买")
        buy_button.setFixedHeight(32)
        buy_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        buy_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 600;
                color: #ffffff;
                background-color: #ec4899;
                border-radius: 16px;
                padding: 4px 18px;
            }
            QPushButton:hover {
                background-color: #db2777;
            }
            QPushButton:pressed {
                background-color: #be185d;
            }
        """)
        buy_button.clicked.connect(lambda: self._on_buy_membership(card_info))
        layout.addWidget(buy_button, alignment=Qt.AlignmentFlag.AlignCenter)

        return card_widget

    # --------- 会员套餐相关逻辑 ---------

    def _load_vip_info(self):
        """加载当前用户 VIP 有效期"""
        self.vip_expiry = None
        if not self.user_id:
            return
        vip_info = api_client.get_vip_info_by_user_id(self.user_id)
        if not vip_info:
            return
        self.vip_expiry = getattr(vip_info, "vip_expiry", None)

    def _update_vip_expiry_label(self):
        """根据当前 VIP 信息更新“有效期至”显示"""
        if not hasattr(self, "vip_expiry_label"):
            return

        text = ""
        now = datetime.now()
        if not self.vip_expiry:
            text = (
                "<span style=\"font-family:'Microsoft YaHei','SimHei','Arial';"
                "font-size:13px; color:#4b5563;\">"
                "有效期至：<span style=\"color:#ef4444; font-weight:700;\">已过期</span>"
                "</span>"
            )
        else:
            # 认为大于等于 2099 的为永久
            if self.vip_expiry.year >= 2099:
                text = (
                    "<span style=\"font-family:'Microsoft YaHei','SimHei','Arial';"
                    "font-size:13px; color:#4b5563;\">"
                    "有效期至：<span style=\"color:#facc15; font-weight:700;\">已永久</span>"
                    "</span>"
                )
            elif self.vip_expiry > now:
                date_str = self.vip_expiry.strftime("%Y-%m-%d")
                text = (
                    "<span style=\"font-family:'Microsoft YaHei','SimHei','Arial';"
                    "font-size:13px; color:#4b5563;\">"
                    "有效期至：<span style=\"color:#facc15; font-weight:700;\">"
                    f"{date_str}</span>"
                    "</span>"
                )
            else:
                text = (
                    "<span style=\"font-family:'Microsoft YaHei','SimHei','Arial';"
                    "font-size:13px; color:#4b5563;\">"
                    "有效期至：<span style=\"color:#ef4444; font-weight:700;\">已过期</span>"
                    "</span>"
                )

        self.vip_expiry_label.setText(text)

    def _on_buy_membership(self, card_info: Dict):
        """购买会员套餐：消耗钻石并更新 VIP 有效期"""
        if not self.user_id:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setWindowTitle(text_cfg.LOGIN_REQUIRED_TITLE)
            msg_box.setText(text_cfg.LOGIN_REQUIRED_BEFORE_PURCHASE)
            msg_box.exec()
            return

        cost = int(card_info.get("diamonds", 0))

        vip_info = api_client.get_vip_info_by_user_id(self.user_id)
        diamonds = getattr(vip_info, "diamonds", 0) if vip_info else 0

        if diamonds < cost:
            # 钻石不足：提示并跳转到钻石套餐弹窗
            msg_box = CustomMessageBox(self.parent())
            msg_box.setWindowTitle(text_cfg.DIAMOND_NOT_ENOUGH_TITLE)
            msg_box.setText(text_cfg.DIAMOND_NOT_ENOUGH_FOR_VIP_MESSAGE)
            msg_box.exec()

            self.close()
            dialog = DiamondPackageDialog(self.parent(), user_id=self.user_id)
            dialog.exec()
            return

        # 调用统一 API：扣减钻石并更新 VIP
        success, new_expiry = api_client.purchase_membership(self.user_id, card_info)

        if not success:
            msg_box = CustomMessageBox(self.parent(), variant="error")
            msg_box.setWindowTitle(text_cfg.VIP_PURCHASE_FAILED_TITLE)
            msg_box.setText(text_cfg.VIP_PURCHASE_FAILED_MESSAGE)
            msg_box.exec()
            return

        # 本地更新状态并刷新有效期显示
        self.vip_expiry = new_expiry
        self._update_vip_expiry_label()
        msg_box = CustomMessageBox(self.parent())
        msg_box.setWindowTitle(text_cfg.VIP_PURCHASE_SUCCESS_TITLE)
        msg_box.setText(
            text_cfg.VIP_PURCHASE_SUCCESS_MESSAGE_TEMPLATE.format(
                name=card_info.get("name", "会员")
            )
        )
        msg_box.exec()

        # 购买成功后，自动刷新主界面顶部的 VIP 徽章与钻石数量
        parent = self.parent()
        if parent is not None and hasattr(parent, "refresh_membership_from_db"):
            try:
                parent.refresh_membership_from_db()
            except Exception as e:
                logging.error("刷新主界面会员信息失败：%s", e, exc_info=True)


class DiamondPackageDialog(BaseDialog):
    """独立的钻石套餐弹窗"""

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id

        # 当前选中的钻石套餐与支付方式
        self.selected_plan = None
        self.diamond_cards = []  # [(card_widget, plan_dict), ...]
        self.selected_pay_method = "wechat"  # "wechat" 或 "alipay"

        # 加载用户基础信息与钻石余额
        self.username = "未登录"
        self.diamond_balance = 0
        self.avatar_pixmap = self._load_user_avatar()
        self._load_user_diamond_balance()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # 使用基础对话框的卡片容器
        content_widget, content_layout = self.create_card_container(
            "diamondPackageCard",
            layout_margins=(36, 24, 36, 24),
            layout_spacing=20,
        )
        content_widget.setStyleSheet("""
            #diamondPackageCard {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 180);
            }
        """)

        # 顶部用户信息区域（头像 + 用户名 + 钻石余额 + 刷新）
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        # 头像
        avatar_label = QLabel()
        avatar_label.setFixedSize(56, 56)
        if self.avatar_pixmap and not self.avatar_pixmap.isNull():
            scaled = self.avatar_pixmap.scaled(
                56, 56,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # 裁剪成圆形
            circle = QPixmap(56, 56)
            circle.fill(Qt.GlobalColor.transparent)
            painter = QPainter(circle)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(Qt.PenStyle.NoPen)
            from PyQt6.QtGui import QPainterPath
            path = QPainterPath()
            path.addEllipse(0, 0, 56, 56)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, scaled)
            painter.end()
            avatar_label.setPixmap(circle)
        header_layout.addWidget(avatar_label)

        # 用户名 + 钻石余额
        info_col = QVBoxLayout()
        info_col.setContentsMargins(0, 0, 0, 0)
        info_col.setSpacing(4)

        self.username_label = QLabel(self.username)
        self.username_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;
                font-weight: 700;
                color: #1e293b;
            }
        """)
        info_col.addWidget(self.username_label)

        self.diamond_label = QLabel(f"钻石余额：{self.diamond_balance}")
        self.diamond_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                color: #64748b;
            }
        """)
        info_col.addWidget(self.diamond_label)

        header_layout.addLayout(info_col)
        header_layout.addStretch()

        # 刷新按钮
        refresh_button = QPushButton("刷新")
        refresh_button.setFixedHeight(32)
        refresh_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 500;
                color: #2563eb;
                background-color: rgba(239, 246, 255, 1);
                border-radius: 16px;
                padding: 4px 14px;
                border: 1px solid rgba(191, 219, 254, 1);
            }
            QPushButton:hover {
                background-color: rgba(219, 234, 254, 1);
            }
            QPushButton:pressed {
                background-color: rgba(191, 219, 254, 1);
            }
        """)
        refresh_button.clicked.connect(self._refresh_user_info)
        header_layout.addWidget(refresh_button)

        # 右上角关闭图标按钮
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 600;
                color: #9ca3af;
                background-color: transparent;
                border: none;
                border-radius: 14px;
            }
            QPushButton:hover {
                background-color: rgba(248, 250, 252, 1);
                color: #ef4444;
            }
            QPushButton:pressed {
                background-color: rgba(241, 245, 249, 1);
            }
        """)
        close_btn.clicked.connect(self.reject)
        header_layout.addWidget(close_btn)

        content_layout.addWidget(header)

        # 标题
        title = QLabel("钻石充值")
        title.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 28px;
                font-weight: 700;
                color: #1e293b;
                padding: 4px 0px;
            }
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title)

        # 钻石卡 2×3 网格布局
        cards_grid = QGridLayout()
        cards_grid.setVerticalSpacing(18)
        cards_grid.setHorizontalSpacing(20)
        cards_grid.setContentsMargins(20, 10, 20, 10)

        # 使用统一配置的钻石档位
        for plan in DIAMOND_PLANS:
            card = self._create_diamond_card(plan)
            self.diamond_cards.append((card, plan))
            cards_grid.addWidget(
                card,
                plan["row"],
                plan["col"],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )

        content_layout.addLayout(cards_grid)

        # 充值提示说明（美化为富文本样式）
        tip_label = QLabel()
        tip_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tip_label.setTextFormat(Qt.TextFormat.RichText)
        tip_label.setText(
            """
            <div style="font-family:'Microsoft YaHei','SimHei','Arial'; font-size:13px; line-height:1.7;">
              <span style="color:#4b5563;">
                请确认
                <span style="color:#ec4899; font-weight:600;">充值数量</span>
                和
                <span style="color:#6366f1; font-weight:600;">支付方式</span>
              </span><br/>
              <span style="color:#4b5563;">
                请
                <span style="color:#22c55e; font-weight:600;">试用满意后再购买</span>，
                充值后
                <span style="color:#ef4444; font-weight:700;">不支持退款</span>
              </span><br/>
              <span style="color:#4b5563;">
                选中的套餐
                <span style="color:#ec4899; font-weight:600;">颜色会变深</span>
              </span>
            </div>
            """
        )
        content_layout.addWidget(tip_label)

        # 支付方式选择 + 按钮区
        buttons_row = QHBoxLayout()
        buttons_row.setContentsMargins(0, 8, 0, 0)
        buttons_row.setSpacing(12)

        self.wechat_button = QPushButton("微信")
        self.alipay_button = QPushButton("支付宝")
        for btn in (self.wechat_button, self.alipay_button):
            btn.setFixedHeight(40)
            btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        self.wechat_button.clicked.connect(lambda: self._set_pay_method("wechat"))
        self.alipay_button.clicked.connect(lambda: self._set_pay_method("alipay"))

        buttons_row.addWidget(self.wechat_button)
        buttons_row.addWidget(self.alipay_button)

        buttons_row.addStretch()

        confirm_button = QPushButton("确认充值")
        confirm_button.setFixedHeight(40)
        confirm_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        confirm_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                font-weight: 700;
                color: #ffffff;
                background-color: #ec4899;
                border-radius: 20px;
                padding: 0 28px;
            }
            QPushButton:hover {
                background-color: #db2777;
            }
            QPushButton:pressed {
                background-color: #be185d;
            }
        """)
        confirm_button.clicked.connect(self._on_confirm_recharge)
        buttons_row.addWidget(confirm_button)

        content_layout.addLayout(buttons_row)

        # 初始化支付方式按钮样式
        self._update_pay_method_buttons()

        main_layout.addWidget(content_widget)
        self.adjustSize()

    def _create_diamond_card(self, plan: dict) -> QWidget:
        """单个钻石套餐卡片"""
        card = QWidget()
        card.setObjectName("diamondCard")
        card.setFixedSize(130, 130)
        self._set_card_selected_style(card, selected=False)
        card.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 20))
        card.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        diamonds_label = QLabel(f"{plan['diamonds']} 钻石")
        diamonds_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;
                font-weight: 700;
                color: #3b82f6;
            }
        """)
        diamonds_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(diamonds_label)

        price_label = QLabel(f"¥ {plan['price']}")
        price_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 18px;
                font-weight: 600;
                color: #1e293b;
            }
        """)
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(price_label)

        def on_click():
            if Qt.MouseButton.LeftButton:
                self._on_diamond_card_clicked(card, plan)

        def mouse_press_event(event):
            if event.button() == Qt.MouseButton.LeftButton:
                on_click()

        card.mousePressEvent = mouse_press_event

        return card

    # ---------------- 私有辅助方法 ----------------

    def _load_user_avatar(self) -> QPixmap:
        """从数据库或默认资源加载用户头像"""
        if not self.user_id:
            # 未登录：仅使用默认头像
            avatar_bytes = get_default_avatar()
            pix = QPixmap()
            if avatar_bytes and pix.loadFromData(avatar_bytes):
                return pix
            return QPixmap()

        # 通过统一 API 获取用户名与头像
        username, pixmap = api_client.get_user_basic_with_avatar(self.user_id)
        self.username = username or self.username
        return pixmap

    def _load_user_diamond_balance(self):
        """加载用户当前钻石余额"""
        self.diamond_balance = api_client.get_diamond_balance(self.user_id or 0)

    def _refresh_user_info(self):
        """刷新用户名和钻石余额显示"""
        # 重新加载余额
        self._load_user_diamond_balance()
        if hasattr(self, "username_label"):
            self.username_label.setText(self.username)
        if hasattr(self, "diamond_label"):
            self.diamond_label.setText(f"钻石余额：{self.diamond_balance}")

    def _set_card_selected_style(self, card: QWidget, selected: bool):
        """根据是否选中设置套餐卡片样式"""
        if selected:
            card.setStyleSheet("""
                #diamondCard {
                    background-color: rgba(244, 114, 182, 0.95);
                    border: 2px solid rgba(236, 72, 153, 1);
                    border-radius: 16px;
                }
            """)
        else:
            card.setStyleSheet("""
                #diamondCard {
                    background-color: rgba(255, 255, 255, 240);
                    border: 1px solid rgba(226, 232, 240, 220);
                    border-radius: 16px;
                }
                #diamondCard:hover {
                    background-color: rgba(255, 255, 255, 255);
                    border: 1.5px solid rgba(59, 130, 246, 250);
                }
            """)

    def _on_diamond_card_clicked(self, card: QWidget, plan: dict):
        """选择某个钻石套餐，并让颜色变深"""
        self.selected_plan = plan
        for c, p in self.diamond_cards:
            self._set_card_selected_style(c, selected=(c is card))

    def _set_pay_method(self, method: str):
        """设置当前支付方式并刷新按钮样式"""
        if method not in ("wechat", "alipay"):
            return
        self.selected_pay_method = method
        self._update_pay_method_buttons()

    def _update_pay_method_buttons(self):
        """根据选中状态更新微信/支付宝按钮样式"""
        if not hasattr(self, "wechat_button") or not hasattr(self, "alipay_button"):
            return

        def get_style(selected: bool, method: str):
            if selected:
                # 微信选中使用绿色，支付宝选中使用蓝色
                bg_color = "#22c55e" if method == "wechat" else "#3b82f6"
                hover_color = "#16a34a" if method == "wechat" else "#2563eb"
                pressed_color = "#15803d" if method == "wechat" else "#1d4ed8"
                return f"""
                    QPushButton {{
                        font-family: "Microsoft YaHei", "SimHei", "Arial";
                        font-size: 14px;
                        font-weight: 700;
                        color: #ffffff;
                        background-color: {bg_color};
                        border-radius: 18px;
                        padding: 0 20px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_color};
                    }}
                    QPushButton:pressed {{
                        background-color: {pressed_color};
                    }}
                """
            return """
                QPushButton {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 14px;
                    font-weight: 500;
                    color: #4b5563;
                    background-color: #e5e7eb;
                    border-radius: 18px;
                    padding: 0 20px;
                }
                QPushButton:hover {
                    background-color: #d4d4d8;
                }
                QPushButton:pressed {
                    background-color: #a1a1aa;
                }
            """

        self.wechat_button.setStyleSheet(get_style(self.selected_pay_method == "wechat", "wechat"))
        self.alipay_button.setStyleSheet(get_style(self.selected_pay_method == "alipay", "alipay"))

    def _on_confirm_recharge(self):
        """点击确认充值后，弹出对应软件的收款码窗口"""
        if not self.selected_plan:
            # 未选择套餐时，不进行处理（可根据需要添加提示）
            return

        method = self.selected_pay_method or "wechat"
        dialog = PaymentQRCodeDialog(
            self,
            pay_method=method,
            plan=self.selected_plan,
        )
        dialog.exec()


class PaymentQRCodeDialog(BaseDialog):
    """展示微信/支付宝收款二维码的弹窗"""

    def __init__(self, parent=None, pay_method: str = "wechat", plan: Optional[Dict] = None):
        super().__init__(parent)
        self.pay_method = pay_method
        self.plan = plan or {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        # 使用基础对话框卡片容器
        card, layout = self.create_card_container(
            "payQrCard",
            blur_radius=30,
            y_offset=8,
            shadow_alpha=60,
            layout_margins=(24, 24, 24, 24),
            layout_spacing=16,
        )
        card.setStyleSheet("""
            #payQrCard {
                background-color: #ffffff;
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 200);
            }
        """)

        # 标题
        pay_name = "微信支付" if self.pay_method == "wechat" else "支付宝支付"
        title = QLabel(pay_name)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_color = "#16a34a" if self.pay_method == "wechat" else "#2563eb"
        title.setStyleSheet(f"""
            QLabel {{
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 20px;
                font-weight: 700;
                color: {title_color};
            }}
        """)
        layout.addWidget(title)

        # 套餐信息
        info_text = f"{self.plan.get('diamonds', 0)} 钻石  ¥{self.plan.get('price', 0)}"
        info_label = QLabel(info_text)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                color: #4b5563;
            }
        """)
        layout.addWidget(info_label)

        # 二维码图片
        qr_label = QLabel()
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        base_dir = os.path.dirname(os.path.dirname(__file__))
        img_name = "wechat_qr.png" if self.pay_method == "wechat" else "alipay_qr.png"
        img_path = os.path.join(base_dir, "resources", "images", img_name)

        pix = QPixmap()
        if os.path.exists(img_path) and pix.load(img_path):
            scaled = pix.scaled(260, 260, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            qr_label.setPixmap(scaled)
        else:
            qr_label.setText("暂未配置二维码图片，请在 resources/images/\n放置 " + img_name)
            qr_label.setStyleSheet("""
                QLabel {
                    font-family: "Microsoft YaHei", "SimHei", "Arial";
                    font-size: 12px;
                    color: #ef4444;
                }
            """)

        layout.addWidget(qr_label)

        hint = QLabel("请使用对应 App 扫码完成支付")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #6b7280;
            }
        """)
        layout.addWidget(hint)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setFixedHeight(34)
        close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_btn.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                font-weight: 500;
                color: #4b5563;
                background-color: #e5e7eb;
                border-radius: 17px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #d4d4d8;
            }
            QPushButton:pressed {
                background-color: #a1a1aa;
            }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(card)
        self.adjustSize()
