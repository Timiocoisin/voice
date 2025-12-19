import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import QByteArray
from gui.main_window import MainWindow
from backend.database.database_manager import DatabaseManager
from backend.resources import load_icon_data
from backend.logging_manager import setup_logging  # noqa: F401
import logging


if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    try:
        _manager = DatabaseManager()
    except ConnectionError as e:
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("数据库连接失败")
        msg.setText("无法连接到数据库")
        msg.setInformativeText(str(e))
        msg.setDetailedText("请检查：\n1. MySQL 服务是否已启动\n2. 数据库配置是否正确\n3. 网络连接是否正常")
        msg.exec()
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