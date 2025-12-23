import os
import sys

# 确保项目根目录在 sys.path 中，便于导入 client 等顶层包
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QByteArray
from gui.main_window import MainWindow
from client.resources import load_icon_data
from client.logging_manager import setup_logging  # noqa: F401
from client.api_client import health_check
import logging


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    # 启动时检查后端 HTTP 服务是否可用
    if not health_check():
        QMessageBox.critical(
            None,
            "后端连接失败",
            "无法连接到后端服务。\n\n请检查后端服务是否已启动（http://127.0.0.1:8000）。",
        )
        sys.exit(1)

    app_icon_data = load_icon_data(5)
    if app_icon_data:
        byte_array = QByteArray(app_icon_data)
        pixmap = QPixmap()
        if pixmap.loadFromData(byte_array):
            app_icon = QIcon(pixmap)
            app.setWindowIcon(app_icon)
    
    window = MainWindow() 
    window.show()  
    sys.exit(app.exec())