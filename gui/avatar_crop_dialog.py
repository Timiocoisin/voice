# 头像裁剪对话框
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                             QWidget, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QPoint, QRect, QRectF, QSize, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import (QPixmap, QPainter, QPainterPath, QBrush, QColor, QPen, 
                        QMouseEvent, QWheelEvent, QImage, QCursor)
import logging
from backend.logging_manager import setup_logging  # noqa: F401


class CropArea(QWidget):
    """可拖动的圆形裁剪区域"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.crop_radius = 160  # 裁剪圆的半径（固定大小，进一步增大）
        self.crop_center = QPoint(275, 225)  # 裁剪圆的中心点
        self.dragging = False
        self.drag_offset = QPoint()
        self.min_radius = 160  # 固定大小
        self.max_radius = 160  # 固定大小
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background-color: transparent;")
        
    def set_center(self, center: QPoint):
        """设置裁剪中心点"""
        self.crop_center = center
        self.update()
        
    def set_radius(self, radius: int):
        """设置裁剪半径（固定大小，不改变）"""
        # 保持固定大小
        self.crop_radius = 160
        self.update()
        
    def get_crop_rect(self):
        """获取裁剪矩形区域"""
        return QRect(
            self.crop_center.x() - self.crop_radius,
            self.crop_center.y() - self.crop_radius,
            self.crop_radius * 2,
            self.crop_radius * 2
        )
        
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            # 检查是否点击在圆形区域内
            distance = ((event.pos().x() - self.crop_center.x()) ** 2 + 
                       (event.pos().y() - self.crop_center.y()) ** 2) ** 0.5
            if distance <= self.crop_radius:
                self.dragging = True
                self.drag_offset = event.pos() - self.crop_center
                
    def mouseMoveEvent(self, event: QMouseEvent):
        if self.dragging:
            new_center = event.pos() - self.drag_offset
            # 限制在父窗口范围内
            parent_rect = self.parent().rect() if self.parent() else self.rect()
            new_center.setX(max(self.crop_radius, min(parent_rect.width() - self.crop_radius, new_center.x())))
            new_center.setY(max(self.crop_radius, min(parent_rect.height() - self.crop_radius, new_center.y())))
            self.crop_center = new_center
            self.update()
            # 找到对话框并更新预览
            dialog = self.parent()
            while dialog and not isinstance(dialog, AvatarCropDialog):
                dialog = dialog.parent()
            if dialog:
                dialog.update_preview()
                
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            
    def wheelEvent(self, event: QWheelEvent):
        """鼠标滚轮事件（已禁用，固定大小）"""
        # 裁剪区域固定大小，不响应滚轮事件
        pass
            
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 获取矩形区域（转换为QRectF）
        rect_f = QRectF(self.rect())
        
        # 绘制半透明遮罩（更深的遮罩，突出裁剪区域）
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(rect_f)
        
        # 清除圆形区域（显示原图）
        path = QPainterPath()
        path.addRect(rect_f)
        circle_path = QPainterPath()
        circle_path.addEllipse(self.crop_center.x() - self.crop_radius,
                              self.crop_center.y() - self.crop_radius,
                              self.crop_radius * 2,
                              self.crop_radius * 2)
        path = path.subtracted(circle_path)
        painter.setBrush(QBrush(QColor(0, 0, 0, 150)))
        painter.drawPath(path)
        
        # 绘制外圈装饰（渐变边框效果）
        gradient = QBrush(QColor(255, 255, 255, 200))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # 外圈白色边框（较粗）
        pen = QPen(QColor(255, 255, 255), 3)
        painter.setPen(pen)
        painter.drawEllipse(self.crop_center.x() - self.crop_radius,
                           self.crop_center.y() - self.crop_radius,
                           self.crop_radius * 2,
                           self.crop_radius * 2)
        
        # 内圈蓝色边框（较细，更醒目）
        pen = QPen(QColor(59, 130, 246), 2)  # 蓝色
        painter.setPen(pen)
        painter.drawEllipse(self.crop_center.x() - self.crop_radius + 2,
                           self.crop_center.y() - self.crop_radius + 2,
                           (self.crop_radius - 2) * 2,
                           (self.crop_radius - 2) * 2)
        
        # 绘制控制点（四个方向，更美观的样式）
        control_size = 10
        control_inner_size = 6
        
        # 控制点位置
        points = [
            QPoint(self.crop_center.x() - self.crop_radius, self.crop_center.y()),  # 左
            QPoint(self.crop_center.x() + self.crop_radius, self.crop_center.y()),  # 右
            QPoint(self.crop_center.x(), self.crop_center.y() - self.crop_radius),  # 上
            QPoint(self.crop_center.x(), self.crop_center.y() + self.crop_radius),  # 下
        ]
        
        for point in points:
            # 外圈（白色，带阴影效果）
            painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
            painter.setPen(QPen(QColor(59, 130, 246), 2))
            painter.drawEllipse(point.x() - control_size // 2,
                              point.y() - control_size // 2,
                              control_size,
                              control_size)
            
            # 内圈（蓝色实心）
            painter.setBrush(QBrush(QColor(59, 130, 246)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(point.x() - control_inner_size // 2,
                              point.y() - control_inner_size // 2,
                              control_inner_size,
                              control_inner_size)


class AvatarCropDialog(QDialog):
    """头像裁剪对话框"""
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("裁剪头像")
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(900, 550)  # 调整尺寸以适应更大的裁剪区域
        
        # 加载图片
        self.original_pixmap = QPixmap(image_path)
        if self.original_pixmap.isNull():
            logging.error(f"无法加载图片: {image_path}")
            return
            
        # 调整图片大小以适应对话框（增大尺寸）
        self.scaled_pixmap = self.original_pixmap.scaled(
            550, 450,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        
        self.init_ui()
        
    def init_ui(self):
        """初始化UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(0)
        
        # 主容器
        container = QWidget()
        container.setObjectName("cropContainer")
        container.setStyleSheet("""
            #cropContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(255, 255, 255, 255),
                    stop:1 rgba(248, 250, 252, 255));
                border-radius: 20px;
                border: 1px solid rgba(226, 232, 240, 250);
            }
        """)
        
        # 添加阴影
        shadow = QGraphicsDropShadowEffect(container)
        shadow.setBlurRadius(40)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 60))
        container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(30, 30, 30, 30)
        container_layout.setSpacing(25)
        
        # 主内容区域：水平布局（左侧裁剪，右侧预览）
        main_content_layout = QHBoxLayout()
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(30)
        
        # 左侧：图片显示和裁剪区域
        image_container = QWidget()
        image_container.setFixedSize(570, 470)
        image_container.setObjectName("imageContainer")
        image_container.setStyleSheet("""
            #imageContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff,
                    stop:0.5 #f8fafc,
                    stop:1 #f1f5f9);
                border-radius: 18px;
                border: 2px solid rgba(226, 232, 240, 250);
            }
        """)
        
        # 为图片容器添加阴影
        image_shadow = QGraphicsDropShadowEffect(image_container)
        image_shadow.setBlurRadius(25)
        image_shadow.setOffset(0, 5)
        image_shadow.setColor(QColor(0, 0, 0, 35))
        image_container.setGraphicsEffect(image_shadow)
        
        image_layout = QVBoxLayout(image_container)
        image_layout.setContentsMargins(10, 10, 10, 10)
        image_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图片标签容器（用于定位裁剪区域）
        self.image_label = QLabel()
        self.image_label.setPixmap(self.scaled_pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(550, 450)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: transparent;
                border-radius: 10px;
            }
        """)
        image_layout.addWidget(self.image_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        # 裁剪区域覆盖层（作为image_label的子控件）
        self.crop_area = CropArea(self.image_label)
        self.crop_area.setGeometry(0, 0, 550, 450)
        # 初始化裁剪中心在图片中心
        self.crop_area.set_center(QPoint(275, 225))
        self.crop_area.set_radius(160)
        self.crop_area.raise_()  # 确保在最上层
        
        main_content_layout.addWidget(image_container, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # 右侧：预览区域（垂直居中）
        preview_widget = QWidget()
        preview_widget.setObjectName("previewWidget")
        preview_widget.setFixedWidth(240)
        preview_widget.setStyleSheet("""
            #previewWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 220),
                    stop:1 rgba(241, 245, 249, 220));
                border-radius: 16px;
                border: 1px solid rgba(226, 232, 240, 250);
                padding: 25px;
            }
        """)
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(25)
        
        # 添加顶部弹性空间，使内容垂直居中
        preview_layout.addStretch()
        
        preview_label_text = QLabel("预览效果")
        preview_label_text.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 17px;
                font-weight: 600;
                color: #1e293b;
                background-color: transparent;
            }
        """)
        preview_label_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_label_text)
        
        # 预览头像容器
        preview_avatar_container = QWidget()
        preview_avatar_container.setFixedSize(160, 160)
        preview_avatar_container.setObjectName("previewAvatarContainer")
        preview_avatar_container.setStyleSheet("""
            #previewAvatarContainer {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(255, 255, 255, 250),
                    stop:1 rgba(248, 250, 252, 250));
                border-radius: 80px;
                border: 3px solid rgba(59, 130, 246, 220);
            }
        """)
        
        # 为预览头像添加阴影
        preview_shadow = QGraphicsDropShadowEffect(preview_avatar_container)
        preview_shadow.setBlurRadius(18)
        preview_shadow.setOffset(0, 4)
        preview_shadow.setColor(QColor(59, 130, 246, 100))
        preview_avatar_container.setGraphicsEffect(preview_shadow)
        preview_avatar_layout = QVBoxLayout(preview_avatar_container)
        preview_avatar_layout.setContentsMargins(12, 12, 12, 12)
        preview_avatar_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(136, 136)
        self.preview_label.setStyleSheet("""
            QLabel {
                border-radius: 68px;
                background-color: #f1f5f9;
            }
        """)
        self.update_preview()
        preview_avatar_layout.addWidget(self.preview_label, alignment=Qt.AlignmentFlag.AlignCenter)
        preview_layout.addWidget(preview_avatar_container, alignment=Qt.AlignmentFlag.AlignHCenter)
        
        # 提示文字
        hint_label = QLabel("拖动圆形区域\n移动位置")
        hint_label.setStyleSheet("""
            QLabel {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 13px;
                color: #64748b;
                font-weight: 400;
                background-color: transparent;
            }
        """)
        hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint_label.setWordWrap(True)
        preview_layout.addWidget(hint_label)
        
        # 添加底部弹性空间，使内容垂直居中
        preview_layout.addStretch()
        
        main_content_layout.addWidget(preview_widget, alignment=Qt.AlignmentFlag.AlignVCenter)
        
        # 将主内容区域添加到容器
        container_layout.addLayout(main_content_layout)
        
        # 按钮区域
        button_widget = QWidget()
        button_widget.setStyleSheet("background-color: transparent;")
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(15)
        
        button_layout.addStretch()
        
        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        cancel_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                font-weight: 600;
                color: #475569;
                background-color: rgba(241, 245, 249, 250);
                border: 1.5px solid rgba(226, 232, 240, 250);
                border-radius: 12px;
                padding: 13px 36px;
                min-width: 110px;
            }
            QPushButton:hover {
                background-color: rgba(226, 232, 240, 250);
                border-color: rgba(203, 213, 225, 250);
            }
            QPushButton:pressed {
                background-color: rgba(203, 213, 225, 250);
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        # 确认按钮
        confirm_button = QPushButton("✓ 确认裁剪")
        confirm_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        confirm_button.setStyleSheet("""
            QPushButton {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 15px;
                font-weight: 600;
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #60a5fa, stop:1 #3b82f6);
                border: none;
                border-radius: 12px;
                padding: 13px 36px;
                min-width: 130px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 #3b82f6, stop:1 #2563eb);
            }
            QPushButton:pressed {
                background: #2563eb;
            }
        """)
        confirm_button.clicked.connect(self.accept)
        button_layout.addWidget(confirm_button)
        
        # 为确认按钮添加阴影
        button_shadow = QGraphicsDropShadowEffect(confirm_button)
        button_shadow.setBlurRadius(12)
        button_shadow.setOffset(0, 4)
        button_shadow.setColor(QColor(59, 130, 246, 100))
        confirm_button.setGraphicsEffect(button_shadow)
        
        button_layout.addStretch()
        
        container_layout.addWidget(button_widget)
        
        main_layout.addWidget(container)
        
    def update_preview(self):
        """更新预览头像"""
        cropped = self.get_cropped_avatar()
        if cropped:
            # 缩放为预览大小
            preview_pixmap = cropped.scaled(
                136, 136,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(preview_pixmap)
            
    def get_cropped_avatar(self) -> QPixmap:
        """获取裁剪后的圆形头像"""
        # 计算缩放比例（考虑KeepAspectRatio）
        original_width = self.original_pixmap.width()
        original_height = self.original_pixmap.height()
        scaled_width = self.scaled_pixmap.width()
        scaled_height = self.scaled_pixmap.height()
        
        # 计算实际显示的尺寸（保持宽高比）
        scale_w = scaled_width / original_width
        scale_h = scaled_height / original_height
        scale = min(scale_w, scale_h)  # 使用较小的缩放比例
        
        # 计算实际显示的尺寸
        display_width = int(original_width * scale)
        display_height = int(original_height * scale)
        
        # 计算偏移（居中显示）
        offset_x = (scaled_width - display_width) // 2
        offset_y = (scaled_height - display_height) // 2
        
        # 获取裁剪区域
        crop_rect = self.crop_area.get_crop_rect()
        crop_center = self.crop_area.crop_center
        crop_radius = self.crop_area.crop_radius
        
        # 转换到显示坐标（减去偏移）
        display_center_x = crop_center.x() - offset_x
        display_center_y = crop_center.y() - offset_y
        
        # 转换到原图坐标
        original_center_x = display_center_x / scale
        original_center_y = display_center_y / scale
        original_radius = crop_radius / scale
        
        # 确保坐标在有效范围内
        original_center_x = max(original_radius, min(original_width - original_radius, original_center_x))
        original_center_y = max(original_radius, min(original_height - original_radius, original_center_y))
        
        # 创建裁剪矩形
        original_rect = QRect(
            int(original_center_x - original_radius),
            int(original_center_y - original_radius),
            int(original_radius * 2),
            int(original_radius * 2)
        )
        
        # 确保矩形在图片范围内
        original_rect.setLeft(max(0, original_rect.left()))
        original_rect.setTop(max(0, original_rect.top()))
        original_rect.setRight(min(original_width, original_rect.right()))
        original_rect.setBottom(min(original_height, original_rect.bottom()))
        
        # 裁剪图片
        cropped = self.original_pixmap.copy(original_rect)
        
        # 创建圆形头像
        size = min(cropped.width(), cropped.height())
        if size <= 0:
            size = 200  # 默认大小
        
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制圆形裁剪路径
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)
        
        # 绘制图片
        scaled_cropped = cropped.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        x_offset = (size - scaled_cropped.width()) // 2
        y_offset = (size - scaled_cropped.height()) // 2
        painter.drawPixmap(x_offset, y_offset, scaled_cropped)
        painter.end()
        
        return circular_pixmap
        
    def get_cropped_avatar_bytes(self) -> bytes:
        """获取裁剪后的头像字节数据"""
        cropped_pixmap = self.get_cropped_avatar()
        if cropped_pixmap:
            # 转换为字节
            image = cropped_pixmap.toImage()
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
            # 保存为PNG格式
            if image.save(buffer, "PNG"):
                buffer.close()
                return bytes(byte_array)
            buffer.close()
        return None
