from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def create_chat_panel(main_window: "MainWindow", parent=None):
    from gui.components.chat_panel_ui import create_chat_panel_ui
    return create_chat_panel_ui(main_window, parent)
