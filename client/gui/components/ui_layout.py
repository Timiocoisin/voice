from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt

from gui.components.chat_bubble import RoundedBackgroundWidget
from gui.components.sections import create_section_widget, create_merged_section_widget, create_bottom_bar
from gui.components.top_bar import create_top_bar
from gui.components.chat_panel import create_chat_panel

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def create_main_layout(main_window: "MainWindow") -> tuple:
    rounded_bg = RoundedBackgroundWidget()
    rounded_bg.setObjectName("roundedBackground")
    rounded_bg.setStyleSheet("""
        #roundedBackground {
            background-color: transparent;
            border-radius: 20px;
        }
    """)

    rounded_layout = QVBoxLayout(rounded_bg)
    rounded_layout.setContentsMargins(0, 0, 0, 0)
    rounded_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    top_bar = create_top_bar(main_window)
    rounded_layout.addWidget(top_bar)

    main_content_widget = QWidget()
    main_content_layout = QHBoxLayout(main_content_widget)
    # 收紧左右留白与行间距，使整体更紧凑
    main_content_layout.setContentsMargins(14, 6, 14, 10)
    main_content_layout.setSpacing(12)
    main_content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    left_column_widget, merged_section2, merged_section2_layout, right_column_widget = create_content_layout(main_window)
    
    main_content_layout.addWidget(left_column_widget, 1)
    main_content_layout.addLayout(merged_section2_layout, 3)
    main_content_layout.addWidget(right_column_widget, 1)

    chat_panel = create_chat_panel(main_window, main_content_widget)
    chat_panel.setVisible(False)

    rounded_layout.addWidget(main_content_widget, stretch=1)

    bottom_bar = create_bottom_bar()
    rounded_layout.addWidget(bottom_bar)

    return rounded_bg, main_content_widget, main_content_layout, merged_section2, merged_section2_layout, left_column_widget, right_column_widget, chat_panel


def _add_section_to_layout(layout: QVBoxLayout, section_index: int, min_height: int = 250) -> None:
    section = create_section_widget(section_index)
    section.setMinimumHeight(min_height)
    section_layout = QVBoxLayout()
    section_layout.setContentsMargins(0, 0, 0, 0)
    section_layout.addWidget(section)
    layout.addLayout(section_layout, 1)


def create_content_layout(main_window: "MainWindow") -> tuple:
    left_column_widget = QWidget()
    left_column_layout = QVBoxLayout(left_column_widget)
    left_column_layout.setContentsMargins(0, 0, 0, 0)
    left_column_layout.setSpacing(10)

    _add_section_to_layout(left_column_layout, 0)
    _add_section_to_layout(left_column_layout, 3)

    merged_section2 = create_merged_section_widget()
    merged_section2.setMinimumHeight(520)
    merged_section2_layout = QVBoxLayout()
    merged_section2_layout.setContentsMargins(0, 0, 0, 0)
    merged_section2_layout.addWidget(merged_section2)

    right_column_widget = QWidget()
    right_column_layout = QVBoxLayout(right_column_widget)
    right_column_layout.setContentsMargins(0, 0, 0, 0)
    right_column_layout.setSpacing(10)

    _add_section_to_layout(right_column_layout, 2)
    _add_section_to_layout(right_column_layout, 5)

    return left_column_widget, merged_section2, merged_section2_layout, right_column_widget