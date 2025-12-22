"""支付二维码对话框。"""
from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCursor, QPixmap

from backend.resources import load_icon_data
from gui.base_dialog import BaseDialog
from gui.styles.membership_styles import (
    PAYMENT_CARD_CONTAINER, TITLE_STYLE, PAYMENT_AMOUNT_STYLE,
    PAYMENT_NOTE_STYLE, PAY_BUTTON_STYLE, CANCEL_BUTTON_STYLE
)


class PaymentQRCodeDialog(BaseDialog):
    """支付二维码弹窗"""

    def __init__(self, parent=None, pay_method="wechat", plan=None):
        super().__init__(parent)
        self.pay_method = pay_method  # "wechat" or "alipay"
        self.plan = plan or {}

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(0)

        content_widget, content_layout = self.create_card_container(
            "paymentCard",
            layout_margins=(28, 24, 28, 24),
            layout_spacing=16,
        )
        content_widget.setStyleSheet(PAYMENT_CARD_CONTAINER)

        title_text = "微信支付" if pay_method == "wechat" else "支付宝支付"
        title = QLabel(title_text)
        title.setStyleSheet(TITLE_STYLE)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(title)

        amount_label = QLabel(f"¥ {self.plan.get('price', 0)}")
        amount_label.setStyleSheet(PAYMENT_AMOUNT_STYLE)
        amount_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(amount_label)

        qr_label = QLabel()
        qr_label.setFixedSize(240, 240)
        qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_id = 12 if pay_method == "wechat" else 11
        qr_bytes = load_icon_data(icon_id)
        if qr_bytes:
            pixmap = QPixmap()
            pixmap.loadFromData(qr_bytes)
            scaled = pixmap.scaled(
                240, 240,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            qr_label.setPixmap(scaled)
        content_layout.addWidget(qr_label, alignment=Qt.AlignmentFlag.AlignCenter)

        note = QLabel("请使用手机扫描二维码完成支付")
        note.setStyleSheet(PAYMENT_NOTE_STYLE)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        content_layout.addWidget(note)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        confirm_button = QPushButton("已支付")
        confirm_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        confirm_button.setStyleSheet(PAY_BUTTON_STYLE)
        confirm_button.clicked.connect(self.accept)
        buttons_row.addWidget(confirm_button)

        cancel_button = QPushButton("取消")
        cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_button.setStyleSheet(CANCEL_BUTTON_STYLE)
        cancel_button.clicked.connect(self.reject)
        buttons_row.addWidget(cancel_button)

        content_layout.addLayout(buttons_row)

        main_layout.addWidget(content_widget)
        self.adjustSize()
