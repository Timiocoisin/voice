import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from gui.main_window import MainWindow 

if __name__ == "__main__":
    # 设置高DPI策略
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)  

    window = MainWindow() 
    window.show()  
    sys.exit(app.exec())  