"""文件上传进度对话框组件"""
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QColor, QBrush, QPen, QPainterPath


class FileUploadThread(QThread):
    """模拟文件上传的线程"""
    progress_updated = pyqtSignal(int)  # 进度百分比 0-100
    finished = pyqtSignal(bool, str)  # (成功, 文件名)
    
    def __init__(self, file_path: str, file_size: int):
        super().__init__()
        self.file_path = file_path
        self.file_size = file_size
        self._canceled = False
    
    def cancel(self):
        """取消上传"""
        self._canceled = True
    
    def run(self):
        """模拟文件上传过程"""
        import time
        
        # 模拟读取和上传文件（分块）
        chunk_size = max(1024 * 1024, self.file_size // 100)  # 至少1MB或分为100块
        chunks = (self.file_size + chunk_size - 1) // chunk_size
        
        try:
            with open(self.file_path, 'rb') as f:
                uploaded = 0
                for i in range(chunks):
                    if self._canceled:
                        self.finished.emit(False, "上传已取消")
                        return
                    
                    # 读取一块数据（模拟上传）
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    
                    uploaded += len(chunk)
                    progress = min(100, int((uploaded / self.file_size) * 100))
                    self.progress_updated.emit(progress)
                    
                    # 模拟网络延迟（小文件延迟小，大文件延迟稍大）
                    delay = 0.01 if self.file_size < 1024 * 1024 else 0.02
                    time.sleep(delay)
            
            if not self._canceled:
                self.finished.emit(True, "")
        except Exception as e:
            if not self._canceled:
                self.finished.emit(False, str(e))


class FileUploadProgressDialog(QDialog):
    """文件上传进度对话框"""
    
    def __init__(self, parent=None, filename: str = "", file_size: int = 0):
        super().__init__(parent)
        self.filename = filename
        self.file_size = file_size
        self.upload_thread = None
        self.canceled = False
        
        self.setWindowTitle("正在上传文件")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        # 适当增大整体高度和宽度，避免内容被压缩成一条线
        self.setFixedSize(480, 280)
        
        self.init_ui()
    
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(18)
        
        # 内容容器
        content_widget = QWidget()
        content_widget.setObjectName("progressDialog")
        content_widget.setStyleSheet("""
            #progressDialog {
                background-color: rgba(255, 255, 255, 250);
                border-radius: 18px;
                border: 1px solid rgba(226, 232, 240, 200);
            }
        """)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(26, 22, 26, 22)
        content_layout.setSpacing(16)
        
        # 标题
        title_label = QLabel("正在上传文件")
        title_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 20px;
                font-weight: 600;
                color: #1e293b;
            }
        """)
        content_layout.addWidget(title_label)
        
        # 文件名
        filename_label = QLabel(self.filename or "正在上传选中的文件…")
        filename_label.setWordWrap(True)
        filename_label.setMinimumHeight(32)
        filename_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 500;
                color: #111827;
                padding: 6px 10px;
                background-color: #f8fafc;
                border-radius: 8px;
            }
        """)
        content_layout.addWidget(filename_label)
        
        # 文件大小
        size_str = self._format_size(self.file_size)
        size_label = QLabel(f"文件大小：{size_str}")
        size_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 12px;
                color: #6b7280;
            }
        """)
        content_layout.addWidget(size_label)

        # 进度百分比文本（放在进度条上方，独立一行）
        self.progress_label = QLabel("0 %")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 16px;
                font-weight: 700;
                color: #1d4ed8;
            }
        """)
        content_layout.addWidget(self.progress_label)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        # 适度高度的进度条，既清晰又不压缩其它控件
        self.progress_bar.setFixedHeight(16)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cbd5e1;
                border-radius: 7px;
                background-color: #e5e7eb;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6,
                    stop:1 #2563eb
                );
                border-radius: 6px;
            }
        """)
        content_layout.addWidget(self.progress_bar)
        
        # 取消按钮
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 8, 0, 0)
        
        self.cancel_button = QPushButton("取消上传")
        self.cancel_button.setMinimumHeight(36)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                font-weight: 500;
                color: #64748b;
                background-color: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px 24px;
            }
            QPushButton:hover {
                background-color: #e2e8f0;
                color: #475569;
            }
            QPushButton:pressed {
                background-color: #cbd5e1;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_upload)
        button_layout.addWidget(self.cancel_button, alignment=Qt.AlignmentFlag.AlignCenter)
        
        content_layout.addLayout(button_layout)
        main_layout.addWidget(content_widget)
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.1f} MB"
    
    def start_upload(self, file_path: str):
        """开始上传文件"""
        self.upload_thread = FileUploadThread(file_path, self.file_size)
        self.upload_thread.progress_updated.connect(self.update_progress)
        self.upload_thread.finished.connect(self.on_upload_finished)
        self.upload_thread.start()
    
    def update_progress(self, value: int):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(f"{value}%")
    
    def cancel_upload(self):
        """取消上传"""
        if self.upload_thread and self.upload_thread.isRunning():
            self.canceled = True
            self.upload_thread.cancel()
            self.cancel_button.setText("正在取消...")
            self.cancel_button.setEnabled(False)
    
    def on_upload_finished(self, success: bool, error: str = ""):
        """上传完成"""
        if success:
            self.progress_bar.setValue(100)
            self.progress_label.setText("100%")
            # 延迟关闭，让用户看到完成状态
            QTimer.singleShot(300, self.accept)
        else:
            self.reject()
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.upload_thread and self.upload_thread.isRunning():
            self.cancel_upload()
            self.upload_thread.wait(1000)  # 等待线程结束
        super().closeEvent(event)
