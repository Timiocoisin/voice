from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QSizePolicy, QGraphicsDropShadowEffect
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QCursor, QColor
from gui.marquee_label import MarqueeLabel
from gui.handlers import dialog_handlers, avatar_handlers
from client.api_client import get_latest_announcement
from gui.handlers.window_handlers import minimize_app, close_app

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def create_top_bar(main_window: "MainWindow") -> QWidget:
    """创建顶部导航栏"""
    top_bar = QWidget()
    top_bar.setObjectName("topBar")
    # 顶部导航栏保持完全透明，不再使用底部分割线
    top_bar.setStyleSheet("""
        #topBar {
            background-color: transparent;
        }
    """)
    # 高度保持当前较高的效果
    top_bar.setFixedHeight(80)

    top_bar_layout = QHBoxLayout(top_bar)
    # 稍微增加上下内边距，让内容不贴边，看起来更精致
    top_bar_layout.setContentsMargins(18, 6, 18, 6)
    # 略微增大左右元素间距，让 Logo、公告、用户区之间更舒展
    top_bar_layout.setSpacing(20)
    top_bar_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # 添加Logo图标
    logo_label = create_logo_label(main_window, top_bar)
    top_bar_layout.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    # 添加弹性空间，使公告区域居中
    top_bar_layout.addSpacing(10)

    # 公告显示区域
    announcement_layout = create_announcement_layout(main_window)
    top_bar_layout.addLayout(announcement_layout, stretch=1)

    # 添加弹性空间
    top_bar_layout.addSpacing(10)

    # 右侧功能按钮
    right_layout = create_right_layout(main_window, top_bar)
    top_bar_layout.addLayout(right_layout)

    return top_bar


def create_logo_label(main_window: "MainWindow", parent_widget: QWidget) -> QLabel:
    """创建艺术字风格 Logo（云汐幻声）"""
    logo_widget = QWidget(parent_widget)
    layout = QVBoxLayout(logo_widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)

    # 主标题使用富文本 + 渐变配色，模拟艺术字效果
    title_label = QLabel(logo_widget)
    title_label.setTextFormat(Qt.TextFormat.RichText)
    # 通过在字之间加入不间断空格，再配合 letter-spacing 拉开间距
    title_label.setText(
        '<span style="color:#38bdf8;">云</span>&nbsp;&nbsp;'
        '<span style="color:#6366f1;">汐</span>&nbsp;&nbsp;'
        '<span style="color:#a855f7;">幻</span>&nbsp;&nbsp;'
        '<span style="color:#22c55e;">声</span>'
    )
    title_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 8px;
            padding: 0px;
            margin: 0px;
            background: transparent;
        }
    """)
    # 加强阴影参数，让文字更有立体悬浮感
    shadow = QGraphicsDropShadowEffect(logo_widget)
    shadow.setBlurRadius(32)
    shadow.setOffset(0, 4)
    shadow.setColor(QColor(15, 23, 42, 120))
    title_label.setGraphicsEffect(shadow)

    subtitle_label = QLabel("CloudVox · AI 实时变声", logo_widget)
    subtitle_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "Segoe UI", "SimHei", "Arial";
            font-size: 11px;
            font-weight: 500;
            color: #6b7280;
            letter-spacing: 1px;
            padding: 0px;
            margin-top: 2px;
        }
    """)

    layout.addWidget(title_label)
    layout.addWidget(subtitle_label)

    logo_widget.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    logo_widget.setStyleSheet("margin: 0 0 0 0; padding: 0px;")

    return logo_widget


def create_announcement_layout(main_window: "MainWindow") -> QHBoxLayout:
    """创建公告布局"""
    announcement_layout = QHBoxLayout()
    announcement_layout.setContentsMargins(0, 0, 0, 0)
    announcement_layout.setSpacing(8)  # 公告容器和客服按钮之间的间距
    announcement_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter)

    # 创建公告容器，包含背景样式
    announcement_container = QWidget()
    announcement_container.setObjectName("announcementContainer")
    announcement_container.setStyleSheet("""
        #announcementContainer {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255, 255, 255, 0.95),
                stop:1 rgba(248, 250, 252, 0.95));
            border: 1px solid rgba(226, 232, 240, 0.8);
            border-radius: 12px;  
            max-width: 600px;  
            min-width: 120px;
        }
    """)
    announcement_container.setFixedHeight(26)  # 优化高度

    # 容器内部布局
    container_layout = QHBoxLayout(announcement_container)
    container_layout.setContentsMargins(10, 0, 10, 0)  # 内边距
    container_layout.setSpacing(8)  # 图标和文字之间的间距
    container_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # 公告左侧喇叭图标（放在容器内的最左侧）
    speaker_icon = main_window.create_svg_widget(10, 20, 20, "margin: 0px; opacity: 0.75;")
    if speaker_icon:
        container_layout.addWidget(speaker_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

    # 通过后端接口获取公告文本
    announcement_text = get_latest_announcement()
    if not announcement_text:
        announcement_text = "欢迎使用《声音序章》软件！！！"

    # 公告标签使用自定义滚动组件（跑马灯效果）
    announcement_label = MarqueeLabel()
    announcement_label.setObjectName("announcementLabel")
    announcement_label.setText(announcement_text)
    announcement_label.setStyleSheet("""
        #announcementLabel {
            background: transparent;
            padding: 0px;
            font-family: \"Microsoft YaHei\", \"Roboto\", \"Arial\";
            font-size: 13px;  
            font-weight: 500;
            color: #475569;
        }
    """)
    announcement_label.setFixedHeight(20)
    container_layout.addWidget(announcement_label, stretch=1, alignment=Qt.AlignmentFlag.AlignVCenter)

    # 添加公告容器到布局
    announcement_layout.addWidget(announcement_container, alignment=Qt.AlignmentFlag.AlignVCenter)

    # 客服按钮（耳机图标）- 放在公告容器外面，单独放大一档
    # 用一个容器包裹耳机图标和未读消息badge
    main_window.headset_container = QWidget()
    main_window.headset_container.setFixedSize(32, 32)
    main_window.headset_container.setStyleSheet("background: transparent;")
    
    main_window.headset_icon = main_window.create_svg_widget(9, 26, 26, "margin: 0px; opacity: 0.85;")
    if main_window.headset_icon:
        main_window.headset_icon.setParent(main_window.headset_container)
        main_window.headset_icon.move(3, 3)
        main_window.headset_container.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        # 事件处理将在 main_window 中设置，避免循环引用
    
    # 未读消息 badge（默认隐藏）
    main_window.unread_badge = QLabel("0", main_window.headset_container)
    main_window.unread_badge.setFixedSize(18, 18)
    main_window.unread_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
    main_window.unread_badge.move(16, -2)  # 右上角位置
    main_window.unread_badge.setStyleSheet("""
        QLabel {
            background-color: #ef4444;
            color: #ffffff;
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 10px;
            font-weight: 700;
            border-radius: 9px;
        }
    """)
    main_window.unread_badge.setVisible(False)
    main_window.unread_count = 0  # 未读消息计数
    
    announcement_layout.addWidget(main_window.headset_container, alignment=Qt.AlignmentFlag.AlignVCenter)

    return announcement_layout


def create_right_layout(main_window: "MainWindow", parent_widget: QWidget) -> QHBoxLayout:
    """创建右侧功能按钮布局"""
    right_layout = QHBoxLayout()
    right_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(12)  # 优化元素间距

    # 用户信息（头像在左；右侧一列：用户名在上，VIP/钻石并列在下）
    user_widget = QWidget()
    user_widget.setObjectName("userWidget")
    user_widget.setStyleSheet("""
        #userWidget {
            background-color: transparent;
            border-radius: 8px;
            padding: 2px 8px;
        }
    """)
    user_layout = QHBoxLayout(user_widget)
    user_layout.setContentsMargins(0, 0, 0, 0)
    user_layout.setSpacing(8)
    user_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

    # 头像（包装在固定尺寸容器中，实现真正的原地中心放大）
    # 注意：如果头像尺寸过大，会超出顶部导航栏的高度，被下边界"截断"
    # 这里按导航栏高度的 70% 来计算头像大小，避免被遮挡
    avatar_size = int(parent_widget.height() * 0.7)
    avatar_size = max(40, avatar_size)
    main_window.avatar_expand_margin = 12  # 为放大预留的边距
    main_window.avatar_container = QWidget()
    main_window.avatar_container.setFixedSize(avatar_size + main_window.avatar_expand_margin * 2, avatar_size + main_window.avatar_expand_margin * 2)
    main_window.avatar_container.setStyleSheet("background: transparent;")
    
    main_window.user_avatar_label = QLabel(main_window.avatar_container)
    main_window.user_avatar_label.setFixedSize(avatar_size, avatar_size)
    # 初始居中放置
    main_window.user_avatar_label.move(main_window.avatar_expand_margin, main_window.avatar_expand_margin)
    main_window.user_avatar_label.setScaledContents(True)
    main_window.user_avatar_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    # 默认圆形 + 非会员灰色描边
    main_window.user_avatar_label.setStyleSheet("""
        QLabel {
            border-radius: %dpx;
            border: 2px solid rgba(148, 163, 184, 160);
        }
    """ % (avatar_size // 2))
    # 点击头像仍然可以上传头像
    main_window.user_avatar_label.mousePressEvent = lambda event: avatar_handlers.upload_avatar(main_window, event)
    # 悬停时放大并显示"退出登录"浮窗（事件处理将在 main_window 中设置）
    
    user_layout.addWidget(main_window.avatar_container, alignment=Qt.AlignmentFlag.AlignVCenter)

    # 右侧信息列
    right_col = QWidget()
    right_col_layout = QVBoxLayout(right_col)
    right_col_layout.setContentsMargins(0, 0, 0, 0)
    right_col_layout.setSpacing(4)  # 优化间距
    right_col_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

    # 用户名（右上）- 字体加大
    main_window.username_display_label = QLabel("未登录")
    main_window.username_display_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "Roboto", "Arial";
            font-size: 15px;
            font-weight: 700;
            color: #0f172a;
            padding: 0px;
            margin: 0px;
        }
    """)
    right_col_layout.addWidget(main_window.username_display_label, alignment=Qt.AlignmentFlag.AlignLeft)

    # 会员 + 钻石（右下并列）
    membership_row = QWidget()
    membership_layout = QHBoxLayout(membership_row)
    membership_layout.setContentsMargins(0, 0, 0, 0)
    membership_layout.setSpacing(8)  # VIP 和钻石之间更紧凑
    membership_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

    # VIP - 优化样式
    vip_group = QHBoxLayout()
    vip_group.setContentsMargins(0, 0, 0, 0)
    vip_group.setSpacing(5)  # 优化图标和文字间距
    # VIP 图标稍微放大
    main_window.vip_icon = main_window.create_svg_widget(13, 20, 20, "margin: 0px;")
    if main_window.vip_icon:
        # 设置VIP图标可点击
        main_window.vip_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        main_window.vip_icon.mousePressEvent = lambda event: dialog_handlers.show_vip_dialog(main_window) if event.button() == Qt.MouseButton.LeftButton else None
        vip_group.addWidget(main_window.vip_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
    main_window.vip_status_label = QLabel("未开通会员")
    main_window.vip_status_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px;
            font-weight: 600;
            color: #64748b;
            padding: 2px 8px;
            border-radius: 10px;
            background-color: rgba(226, 232, 240, 120);
        }
    """)
    # 设置VIP状态标签也可点击
    main_window.vip_status_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    main_window.vip_status_label.mousePressEvent = lambda event: dialog_handlers.show_vip_dialog(main_window) if event.button() == Qt.MouseButton.LeftButton else None
    vip_group.addWidget(main_window.vip_status_label, alignment=Qt.AlignmentFlag.AlignVCenter)
    membership_layout.addLayout(vip_group)

    # 钻石 - 优化样式
    diamond_group = QHBoxLayout()
    diamond_group.setContentsMargins(0, 0, 0, 0)
    diamond_group.setSpacing(4)  # 图标和数字紧挨在一起显示
    # 钻石图标稍微放大
    main_window.diamond_icon = main_window.create_svg_widget(2, 20, 20, "margin: 0px;")
    if main_window.diamond_icon:
        # 设置钻石图标可点击，打开钻石套餐弹窗
        main_window.diamond_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        main_window.diamond_icon.mousePressEvent = (
            lambda event: dialog_handlers.show_diamond_dialog(main_window)
            if event.button() == Qt.MouseButton.LeftButton
            else None
        )
        diamond_group.addWidget(main_window.diamond_icon, alignment=Qt.AlignmentFlag.AlignVCenter)
    main_window.diamond_count_label = QLabel("0 钻石")
    main_window.diamond_count_label.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 13px;
            font-weight: 600;
            color: #1e293b;
            padding: 0px;
            margin: 0px;
        }
    """)
    # 预留更大的数字显示空间（支持 1w+ 钻石）
    main_window.diamond_count_label.setMinimumWidth(80)
    main_window.diamond_count_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    # 与钻石图标紧挨显示，整体仍然靠左
    diamond_group.addWidget(main_window.diamond_count_label, alignment=Qt.AlignmentFlag.AlignVCenter)
    # 在数字右侧添加伸缩空间，避免被后面的分隔线和按钮"挤回去"
    diamond_group.addStretch()
    membership_layout.addLayout(diamond_group)

    right_col_layout.addWidget(membership_row, alignment=Qt.AlignmentFlag.AlignLeft)
    user_layout.addWidget(right_col)

    # 让用户信息块可以向左扩展，占据更多空间，避免被右侧图标挤压
    user_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    right_layout.addWidget(user_widget, stretch=1)

    # 初始化默认头像（资源缺失时会自动回退）
    avatar_handlers.update_user_avatar_display(main_window, None)

    # 添加分隔线
    separator = QWidget()
    separator.setFixedWidth(1)
    separator.setFixedHeight(24)
    separator.setStyleSheet("background-color: rgba(226, 232, 240, 0.6);")
    right_layout.addWidget(separator, alignment=Qt.AlignmentFlag.AlignVCenter)

    # 最小化图标 - 优化样式和交互
    minimize_icon = main_window.create_svg_widget(7, 18, 18, "margin: 0px; padding: 4px;")
    if minimize_icon:
        minimize_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        minimize_icon.setStyleSheet("""
            QWidget {
                border-radius: 4px;
                padding: 4px;
            }
            QWidget:hover {
                background-color: rgba(241, 245, 249, 0.8);
            }
        """)
        minimize_icon.mousePressEvent = lambda event: minimize_app(main_window, event)
        right_layout.addWidget(minimize_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

    # 关闭图标 - 优化样式和交互
    close_icon = main_window.create_svg_widget(1, 18, 18, "margin: 0px; padding: 4px;")
    if close_icon:
        close_icon.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        close_icon.setStyleSheet("""
            QWidget {
                border-radius: 4px;
                padding: 4px;
            }
            QWidget:hover {
                background-color: rgba(254, 242, 242, 0.8);
            }
        """)
        close_icon.mousePressEvent = lambda event: close_app(main_window, event)
        right_layout.addWidget(close_icon, alignment=Qt.AlignmentFlag.AlignVCenter)

    return right_layout
