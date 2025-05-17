import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QPixmap
from gui.main_window import MainWindow 
from backend.database.database_manager import create_connection, get_icon_by_id, load_app_icon
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


if __name__ == "__main__":
    # 设置高DPI策略
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # 从数据库加载ID=5的图标（软件Logo）
    app_icon = load_app_icon(5)
    
    # 设置窗口图标（若加载失败则使用系统默认）
    app.setWindowIcon(app_icon)
    
    window = MainWindow() 
    window.show()  
    sys.exit(app.exec())