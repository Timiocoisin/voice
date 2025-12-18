import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QByteArray  # 引入 QByteArray
from gui.main_window import MainWindow
from backend.database.database_manager import DatabaseManager
from backend.resources import load_icon_data
from backend.logging_manager import setup_logging  # noqa: F401
import logging


if __name__ == "__main__":
    # 设置高DPI策略
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    db_manager = DatabaseManager()

    # 从本地文件加载应用图标
    app_icon_data = load_icon_data(5)

    # 如果获取到的图标数据是字节类型，则将其转换为 QIcon
    if app_icon_data:
        # 将字节数据转换为 QByteArray
        byte_array = QByteArray(app_icon_data)
        pixmap = QPixmap()
        if pixmap.loadFromData(byte_array):  # 使用 QByteArray 加载图像
            app_icon = QIcon(pixmap)

    # 设置窗口图标
    app.setWindowIcon(app_icon)
    
    window = MainWindow() 
    window.show()  
    sys.exit(app.exec())