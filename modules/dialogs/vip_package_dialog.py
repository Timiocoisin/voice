"""会员套餐选择对话框。"""
from typing import Optional, Dict
from datetime import datetime
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QGraphicsDropShadowEffect, QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QColor

from backend.membership_service import MembershipService
from backend.config import texts as text_cfg
from gui.custom_message_box import CustomMessageBox
from gui.base_dialog import BaseDialog
from gui.styles.membership_styles import (
    VIP_CARD_CONTAINER, TITLE_STYLE, MEMBERSHIP_CARD_STYLE,
    BUY_BUTTON_STYLE
)


class VipPackageDialog(BaseDialog):
    """独立的会员套餐选择弹窗"""

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id
        # 使用会员服务封装数据库访问与业务逻辑
        self.membership_service = MembershipService()
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
        content_widget.setStyleSheet(VIP_CARD_CONTAINER)

        # 标题
        title = QLabel("选择会员套餐")
        title.setStyleSheet(TITLE_STYLE)
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

        # 会员套餐配置：天卡、月卡、年卡、永久
        membership_cards = [
            {"name": "天卡至尊", "diamonds": 30, "days": 1, "row": 0, "col": 0},
            {"name": "月卡至尊", "diamonds": 300, "days": 30, "row": 0, "col": 1},
            {"name": "年卡至尊", "diamonds": 1000, "days": 365, "row": 1, "col": 0},
            {"name": "永久至尊", "diamonds": 3000, "days": None, "row": 1, "col": 1},
        ]

        for card_info in membership_cards:
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
        card_widget.setFixedSize(180, 170)
        card_widget.setStyleSheet(MEMBERSHIP_CARD_STYLE.format(name=card_info['name']))
        card_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        shadow = QGraphicsDropShadowEffect(card_widget)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 20))
        card_widget.setGraphicsEffect(shadow)

        layout = QVBoxLayout(card_widget)
        layout.setContentsMargins(15, 16, 15, 16)
        layout.setSpacing(10)
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

        price_label = QLabel(f"{card_info['diamonds']} 钻石")
        price_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 22px;
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
        vip_info = self.membership_service.get_vip_info(self.user_id)
        if not vip_info:
            return
        self.vip_expiry = vip_info.vip_expiry

    def _update_vip_expiry_label(self):
        """根据当前 VIP 信息更新"有效期至"显示"""
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
        # 延迟导入避免循环依赖
        from modules.dialogs.diamond_package_dialog import DiamondPackageDialog
        
        if not self.user_id:
            msg_box = CustomMessageBox(self.parent())
            msg_box.setWindowTitle(text_cfg.LOGIN_REQUIRED_TITLE)
            msg_box.setText(text_cfg.LOGIN_REQUIRED_BEFORE_PURCHASE)
            msg_box.exec()
            return

        cost = int(card_info.get("diamonds", 0))

        vip_info = self.membership_service.get_vip_info(self.user_id)
        diamonds = vip_info.diamonds if vip_info else 0

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

        # 调用服务层：扣减钻石并更新 VIP
        success, new_expiry = self.membership_service.purchase_membership(
            user_id=self.user_id,
            card_info=card_info,
        )

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
