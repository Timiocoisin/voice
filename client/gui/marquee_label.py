from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QPainter


class MarqueeLabel(QLabel):
    """简易横向滚动公告标签（跑马灯效果）。

    - 文本超出标签宽度时，自动从右往左循环滚动。
    - 文本较短时，保持居中不滚动。
    """

    def __init__(self, parent=None, interval: int = 30, step: int = 1):
        super().__init__(parent)
        self._offset = 0
        self._step = max(1, step)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_timeout)
        self._timer.start(max(10, interval))  # 默认 30ms 一次
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def _on_timeout(self):
        """更新滚动偏移量并重绘。

        无论文本是否超出宽度，都缓慢向左滚动。
        - 文本较短：只显示一条，从右往左滑过，滑出后从右侧重新进入，但不会同时出现两条。
        - 文本较长：保持原来的无缝循环效果。
        """
        if not self.text():
            return
        metrics = self.fontMetrics()
        text_width = metrics.horizontalAdvance(self.text())
        if text_width <= 0:
            return
        
        gap = 40
        label_width = max(1, self.width())

        if text_width <= label_width:
            # 短文本：只绘制一条，在整个「控件宽度 + 文本宽度」范围内循环
            loop_width = label_width + text_width + gap
            self._offset = (self._offset + self._step) % loop_width
        else:
            # 长文本：保持原先的循环长度
            self._offset = (self._offset + self._step) % (text_width + gap)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        text = self.text()
        if not text:
            return super().paintEvent(event)

        metrics = self.fontMetrics()
        text_width = metrics.horizontalAdvance(text)
        height = self.height()
        baseline = int((height + metrics.ascent() - metrics.descent()) / 2)

        gap = 40
        label_width = self.width()

        if text_width <= label_width:
            # 短文本：只画一份，始终只有一条在屏幕上滑动
            x = label_width - self._offset
            # 只有当与控件区域有交集时才绘制
            if x + text_width > 0 and x < label_width:
                painter.drawText(x, baseline, text)
        else:
            # 文本超出宽度：画两份以实现无缝循环
            x = label_width - self._offset
            painter.drawText(x, baseline, text)
            painter.drawText(x - text_width - gap, baseline, text)

        painter.end()
