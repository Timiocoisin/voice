"""图片加载异步线程模块"""
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QPixmap
from typing import Optional
import logging


class ImageLoadThread(QThread):
    """图片加载异步线程
    
    用于在后台线程加载和处理图片，避免阻塞UI线程。
    特别适用于从数据库加载的大头像或大图片。
    """
    image_loaded = pyqtSignal(QPixmap, bytes)  # 加载成功信号：QPixmap, 原始字节数据
    load_failed = pyqtSignal(str)  # 加载失败信号
    
    def __init__(self, image_data: bytes, max_size: Optional[int] = None):
        """
        Args:
            image_data: 图片的二进制数据
            max_size: 可选的最大尺寸（用于缩放大图片），None表示不缩放
        """
        super().__init__()
        self.image_data = image_data
        self.max_size = max_size
    
    def run(self):
        """在线程中加载图片"""
        try:
            pixmap = QPixmap()
            if not pixmap.loadFromData(self.image_data) or pixmap.isNull():
                self.load_failed.emit("无法加载图片数据")
                return
            
            # 如果指定了最大尺寸且图片较大，进行缩放
            if self.max_size and (pixmap.width() > self.max_size or pixmap.height() > self.max_size):
                pixmap = pixmap.scaled(
                    self.max_size, self.max_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            
            self.image_loaded.emit(pixmap, self.image_data)
        except Exception as e:
            error_msg = f"图片加载失败: {str(e)}"
            logging.error(error_msg)
            self.load_failed.emit(error_msg)
