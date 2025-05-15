from PyQt6.QtCore import QTimer

class TimerManager:
    def __init__(self, button):
        self.button = button
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_countdown)
        self.remaining_time = 60

    def start_countdown(self):
        self.button.setText("正在发送验证码")
        self.button.setEnabled(False)  # 禁用按钮
        self.remaining_time = 60
        self.timer.start(1000)

    def update_countdown(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.button.setText(f"重新获取验证码 ({self.remaining_time}s)")
        else:
            self.timer.stop()
            self.button.setText("重新获取验证码")
            self.button.setEnabled(True)  # 启用按钮