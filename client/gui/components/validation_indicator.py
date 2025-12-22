"""输入验证状态指示器组件"""
from typing import Optional
from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont


class ValidationIndicator(QLabel):
    """验证状态指示器，显示绿色✓或红色✗"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._is_valid: Optional[bool] = None
        self.setText("")
        self.setStyleSheet("background-color: transparent;")
    
    def set_valid(self, is_valid: Optional[bool]):
        """设置验证状态
        
        Args:
            is_valid: True表示有效，False表示无效，None表示未验证
        """
        self._is_valid = is_valid
        if is_valid is True:
            self.setText("✓")
            self.setStyleSheet("""
                QLabel {
                    color: #10b981;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        elif is_valid is False:
            self.setText("✗")
            self.setStyleSheet("""
                QLabel {
                    color: #ef4444;
                    font-size: 16px;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
        else:
            self.setText("")
            self.setStyleSheet("background-color: transparent;")
    
    def is_valid(self) -> Optional[bool]:
        """获取当前验证状态"""
        return self._is_valid
