from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGraphicsDropShadowEffect,
)


def create_section_widget(index: int) -> QWidget:
    """创建标准板块控件（首页上的功能卡片）"""
    section_widget = QWidget()
    section_widget.setObjectName(f"section{index}")
    
    # 优化板块样式：使用约 50% 透明的浅色渐变和阴影，让中间区域与背景更融合
    section_widget.setStyleSheet(f"""
        #section{index} {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 140),
                stop:1 rgba(236, 252, 203, 130));
            border: 1px solid rgba(226, 232, 240, 140);
            border-radius: 16px;
            padding: 16px 18px;
        }}
        #section{index}:hover {{
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 170),
                stop:1 rgba(219, 234, 254, 155));
            border: 1px solid rgba(203, 213, 225, 170);
        }}
    """)
    
    # 添加阴影效果
    shadow = QGraphicsDropShadowEffect(section_widget)
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 30))
    section_widget.setGraphicsEffect(shadow)

    layout = QVBoxLayout(section_widget)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(10)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    # 优化标题样式：更贴合首页功能区块
    title = QLabel(f"板块 {index + 1}")
    title.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-weight: 700;
            font-size: 17px;
            color: #1e293b;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(226, 232, 240, 200);
            margin-bottom: 4px;
        }
    """)
    layout.addWidget(title)

    # 内容区域：说明/提示文案
    content = QLabel(f"这是板块 {index + 1} 的内容")
    content.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 14px;
            color: #64748b;
            padding: 8px 0px;
            line-height: 1.6;
        }
    """)
    content.setWordWrap(True)
    layout.addWidget(content)
    
    # 添加弹性空间
    layout.addStretch()

    return section_widget


def create_merged_section_widget() -> QWidget:
    """创建合并后的版块2（原版块2和版块5合并）"""
    section_widget = QWidget()
    section_widget.setObjectName("section2_merged")
    
    # 优化板块样式：添加约 50% 透明的渐变背景、阴影效果
    section_widget.setStyleSheet("""
        #section2_merged {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 150),
                stop:1 rgba(255, 255, 255, 135));
            border: 1px solid rgba(226, 232, 240, 150);
            border-radius: 16px;
            padding: 20px;
        }
        #section2_merged:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 180),
                stop:1 rgba(255, 255, 255, 165));
            border: 1px solid rgba(203, 213, 225, 175);
        }
    """)
    
    # 添加阴影效果
    shadow = QGraphicsDropShadowEffect(section_widget)
    shadow.setBlurRadius(20)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(0, 0, 0, 30))
    section_widget.setGraphicsEffect(shadow)

    layout = QVBoxLayout(section_widget)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.setSpacing(12)
    layout.setAlignment(Qt.AlignmentFlag.AlignTop)

    # 标题：版块2
    title = QLabel("板块 2")
    title.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-weight: 700;
            font-size: 18px;
            color: #1e293b;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(226, 232, 240, 200);
            margin-bottom: 4px;
        }
    """)
    layout.addWidget(title)

    # 原版块2的内容
    content1 = QLabel("这是板块 2 的内容")
    content1.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 14px;
            color: #64748b;
            padding: 8px 0px;
            line-height: 1.6;
        }
    """)
    content1.setWordWrap(True)
    layout.addWidget(content1)
    
    # 添加分隔线
    separator = QWidget()
    separator.setFixedHeight(1)
    separator.setStyleSheet("background-color: rgba(226, 232, 240, 200); margin: 12px 0px;")
    layout.addWidget(separator)
    
    # 标题：版块5（作为合并版块的一部分）
    title2 = QLabel("板块 5")
    title2.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-weight: 700;
            font-size: 18px;
            color: #1e293b;
            padding-bottom: 8px;
            border-bottom: 2px solid rgba(226, 232, 240, 200);
            margin-bottom: 4px;
        }
    """)
    layout.addWidget(title2)

    # 原版块5的内容
    content2 = QLabel("这是板块 5 的内容")
    content2.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 14px;
            color: #64748b;
            padding: 8px 0px;
            line-height: 1.6;
        }
    """)
    content2.setWordWrap(True)
    layout.addWidget(content2)
    
    # 添加弹性空间
    layout.addStretch()

    return section_widget


def create_bottom_bar() -> QWidget:
    """创建底部导航栏模块"""
    bottom_bar = QWidget()
    bottom_bar.setObjectName("bottomBar")
    bottom_bar.setMinimumHeight(60)  # 设置最小高度，使导航栏更高
    bottom_bar.setStyleSheet("""
        #bottomBar {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 200),
                stop:1 rgba(255, 255, 255, 180));
            border-radius: 12px;
            border: 1px solid rgba(226, 232, 240, 200);
            padding: 18px 20px;
        }
    """)
    
    # 添加阴影效果
    shadow = QGraphicsDropShadowEffect(bottom_bar)
    shadow.setBlurRadius(15)
    shadow.setOffset(0, 3)
    shadow.setColor(QColor(0, 0, 0, 25))
    bottom_bar.setGraphicsEffect(shadow)

    # 底部导航栏内容
    title = QLabel("底部导航栏")
    title.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-weight: 600;
            font-size: 16px;
            color: #475569;
            text-align: center;
        }
    """)
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)

    layout = QHBoxLayout(bottom_bar)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(title)

    return bottom_bar
