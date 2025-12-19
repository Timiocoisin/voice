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
        QMessageBox.critical(None, "数据库连接失败", 
                            f"{e}\n\n请检查数据库服务是否运行。")
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