"""消息提示工具函数模块"""
from typing import TYPE_CHECKING, Optional
from gui.custom_message_box import CustomMessageBox

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def show_message(
    main_window: "MainWindow",
    text: str,
    title: str = "提示",
    variant: str = "info"
) -> None:
    """显示统一的消息提示框（居中显示）
    
    Args:
        main_window: 主窗口实例
        text: 消息内容
        title: 对话框标题，默认为"提示"
        variant: 消息类型，可选值：'info', 'warning', 'error'，默认为'info'
    """
    msg_box = CustomMessageBox(main_window, variant=variant)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    # 使用 exec_centered_dialog 居中显示
    from gui.handlers.dialog_handlers import exec_centered_dialog
    exec_centered_dialog(main_window, msg_box)
