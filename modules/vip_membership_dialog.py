# 文件：vip_membership_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QGraphicsDropShadowEffect, QStackedWidget, QGridLayout
)
from PyQt6.QtCore import Qt, QPoint, QByteArray
from PyQt6.QtGui import QPainter, QColor, QCursor
from backend.resources import load_icon_data
from backend.database.database_manager import DatabaseManager
import logging

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class VipMembershipDialog(QDialog):
    def __init__(self, parent=None, user_id=None, is_vip=False):
        super().__init__(parent)
        self.user_id = user_id
        self.is_vip = is_vip
        self.db_manager = DatabaseManager()
        
        # 设置窗口属性（不强制固定宽高，交给布局自适应）
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)
        
        # 创建内容容器（半透明背景）
        content_widget = QWidget()
        content_widget.setObjectName("vipDialogCard")
        content_widget.setStyleSheet("""
            #vipDialogCard {
                background-color: rgba(255, 255, 255, 200);
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 180);
            }
        """)
        
        # 添加阴影效果
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 50))
        content_widget.setGraphicsEffect(shadow)
        
        content_layout = QVBoxLayout(content_widget)
        # 适中一些的内边距，兼顾两种页面的高度
        content_layout.setContentsMargins(36, 18, 36, 18)
        content_layout.setSpacing(16)
        
        # 直接使用“会员提示”页面作为此对话框的唯一内容
        non_vip_page = self.create_non_vip_page()
        content_layout.addWidget(non_vip_page)

        main_layout.addWidget(content_widget)
        # 让对话框根据内容自动调整大小
        self.adjustSize()
    
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


class VipPackageDialog(QDialog):
    """独立的会员套餐选择弹窗"""

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_widget.setObjectName("vipPackageCard")
        content_widget.setStyleSheet("""
            #vipPackageCard {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 180);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 50))
        content_widget.setGraphicsEffect(shadow)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(36, 24, 36, 24)
        content_layout.setSpacing(20)

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

        # 会员卡2x2网格布局
        cards_grid = QGridLayout()
        cards_grid.setVerticalSpacing(25)
        cards_grid.setHorizontalSpacing(20)
        cards_grid.setContentsMargins(20, 10, 20, 10)

        membership_cards = [
            {"name": "日卡", "price": 10, "period": "每日", "row": 0, "col": 0},
            {"name": "周卡", "price": 50, "period": "每周", "row": 0, "col": 1},
            {"name": "月卡", "price": 60, "period": "每月", "row": 1, "col": 0},
            {"name": "年卡", "price": 600, "period": "每年", "row": 1, "col": 1}
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

        # 返回按钮
        back_button = QPushButton("返回")
        back_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                font-weight: 600;
                color: #475569;
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(226, 232, 240, 200);
                border-radius: 12px;
                padding: 10px 34px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: rgba(248, 250, 252, 250);
                border-color: rgba(203, 213, 225, 250);
            }
            QPushButton:pressed {
                background-color: rgba(241, 245, 249, 250);
            }
        """)
        back_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back_button.clicked.connect(self.reject)
        content_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(content_widget)
        self.adjustSize()

    def _create_membership_card(self, card_info):
        """创建单个会员卡组件"""
        card_widget = QWidget()
        card_widget.setObjectName(f"membershipCard_{card_info['name']}")
        card_widget.setFixedSize(140, 140)
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
        layout.setContentsMargins(15, 18, 15, 18)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        period_label = QLabel(card_info["period"])
        period_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 20px;
                font-weight: 700;
                color: #3b82f6;
                padding: 0px;
                margin: 0px;
            }
        """)
        period_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(period_label)

        price_label = QLabel(f"¥ {card_info['price']}")
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

        def on_card_click():
            logging.info(
                f"用户选择了 {card_info['name']}，价格：¥{card_info['price']}"
            )
            # TODO: 这里可以添加支付逻辑或更新数据库
            self.accept()

        card_widget.mousePressEvent = (
            lambda event: on_card_click()
            if event.button() == Qt.MouseButton.LeftButton
            else None
        )

        return card_widget


class DiamondPackageDialog(QDialog):
    """独立的钻石套餐弹窗"""

    def __init__(self, parent=None, user_id=None):
        super().__init__(parent)
        self.user_id = user_id

        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        content_widget = QWidget()
        content_widget.setObjectName("diamondPackageCard")
        content_widget.setStyleSheet("""
            #diamondPackageCard {
                background-color: rgba(255, 255, 255, 210);
                border-radius: 24px;
                border: 1px solid rgba(226, 232, 240, 180);
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 12)
        shadow.setColor(QColor(0, 0, 0, 50))
        content_widget.setGraphicsEffect(shadow)

        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(36, 24, 36, 24)
        content_layout.setSpacing(20)

        # 标题
        title = QLabel("选择钻石套餐")
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

        # 钻石档位配置
        diamond_plans = [
            {"diamonds": 300, "price": 30, "row": 0, "col": 0},
            {"diamonds": 500, "price": 50, "row": 0, "col": 1},
            {"diamonds": 1000, "price": 100, "row": 0, "col": 2},
            {"diamonds": 1680, "price": 168, "row": 1, "col": 0},
            {"diamonds": 3280, "price": 328, "row": 1, "col": 1},
            {"diamonds": 6480, "price": 648, "row": 1, "col": 2},
        ]

        for plan in diamond_plans:
            card = self._create_diamond_card(plan)
            cards_grid.addWidget(
                card,
                plan["row"],
                plan["col"],
                alignment=Qt.AlignmentFlag.AlignCenter,
            )

        content_layout.addLayout(cards_grid)

        # 返回按钮
        back_button = QPushButton("返回")
        back_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                font-weight: 600;
                color: #475569;
                background-color: rgba(255, 255, 255, 220);
                border: 1px solid rgba(226, 232, 240, 200);
                border-radius: 12px;
                padding: 10px 34px;
                min-width: 120px;
            }
            QPushButton:hover {
                background-color: rgba(248, 250, 252, 250);
                border-color: rgba(203, 213, 225, 250);
            }
            QPushButton:pressed {
                background-color: rgba(241, 245, 249, 250);
            }
        """)
        back_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        back_button.clicked.connect(self.reject)
        content_layout.addWidget(back_button, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(content_widget)
        self.adjustSize()

    def _create_diamond_card(self, plan: dict) -> QWidget:
        """单个钻石套餐卡片"""
        card = QWidget()
        card.setObjectName("diamondCard")
        card.setFixedSize(130, 130)
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
            logging.info(
                f"用户选择了 {plan['diamonds']} 钻石，价格：¥{plan['price']}"
            )
            # TODO: 在这里添加充值/扣费逻辑
            self.accept()

        card.mousePressEvent = (
            lambda event: on_click()
            if event.button() == Qt.MouseButton.LeftButton
            else None
        )

        return card
