from typing import TYPE_CHECKING
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt6.QtCore import Qt
from gui.handlers import chat_handlers

if TYPE_CHECKING:
    from gui.main_window import MainWindow


def create_faq_container(main_window: "MainWindow") -> QWidget:
    faq_container = QWidget()
    faq_container.setObjectName("faqContainer")
    faq_container.setFixedWidth(280)
    faq_container.setStyleSheet("""
        #faqContainer {
            background-color: #ffffff;
            border-left: 1px solid rgba(226, 232, 240, 0.5);
        }
    """)
    faq_layout = QVBoxLayout(faq_container)
    faq_layout.setContentsMargins(14, 14, 14, 14)
    faq_layout.setSpacing(8)

    faq_title = QLabel("💡 常见问题")
    faq_title.setStyleSheet("""
        QLabel {
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 14px;
            font-weight: 700;
            color: #7c3aed;
            padding-bottom: 8px;
        }
    """)
    faq_layout.addWidget(faq_title)

    faq_scroll = QScrollArea()
    faq_scroll.setWidgetResizable(True)
    faq_scroll.setStyleSheet("""
        QScrollArea {
            border: none;
            background-color: transparent;
        }
        QScrollBar:vertical {
            width: 6px;
            background: transparent;
            margin: 0px;
            padding: 0px;
        }
        QScrollBar::handle:vertical {
            background: rgba(148, 163, 184, 0);
            border-radius: 3px;
            min-height: 30px;
        }
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {
            background: transparent;
        }
    """)
    faq_scroll.enterEvent = lambda e: chat_handlers.show_scrollbar_handle(faq_scroll)
    faq_scroll.leaveEvent = lambda e: chat_handlers.hide_scrollbar_handle(faq_scroll)

    faq_content = QWidget()
    faq_content_layout = QVBoxLayout(faq_content)
    faq_content_layout.setContentsMargins(0, 0, 0, 0)
    faq_content_layout.setSpacing(10)

    faq1 = chat_handlers.create_faq_item(
        "📱 手机能不能使用变声器？",
        """<p style="color:#374151; margin:0 0 8px 0;">软件需要电脑运行，可转接到手机：</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>方法一</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
买转接器（如 <span style="color:#7c3aed;">直播一号</span> / <span style="color:#7c3aed;">ds7pro</span>），把声音转到手机。
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>方法二</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
用支持 OTG 的声卡（如 <span style="color:#7c3aed;">艾肯micu</span> / <span style="color:#7c3aed;">midi r2</span>），直接插上即可。
</p>"""
    )
    faq_content_layout.addWidget(faq1)

    faq2 = chat_handlers.create_faq_item(
        "🎛️ 变声参数怎么设置？",
        """<p style="color:#374151; margin:0 0 8px 0;">参数：<b>音调、音量、延迟、阈值</b></p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>音调</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
男→女：<span style="color:#7c3aed;">10~14</span><br/>
女→男：<span style="color:#7c3aed;">-14~-10</span><br/>
同性：<span style="color:#7c3aed;">0 左右</span>
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>音量</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
不要太高，易爆音失真<br/>
建议 <span style="color:#7c3aed;">0.5 左右</span>
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>延迟</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
一般 <span style="color:#7c3aed;">0.5~0.7</span><br/>
配置好可压低到 <span style="color:#7c3aed;">0.3</span><br/>
打游戏时适当调高
</p>

<p style="margin:0 0 3px 0;"><span style="color:#7c3aed;">▸</span> <b>阈值</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
默认 <span style="color:#7c3aed;">-60</span><br/>
环境吵选 <span style="color:#7c3aed;">-57</span> 减少噪音
</p>"""
    )
    faq_content_layout.addWidget(faq2)

    faq3 = chat_handlers.create_faq_item_with_images(
        main_window,
        "🔊 如何安装虚拟声卡？",
        """<p style="color:#374151; margin:0 0 8px 0;"><b>步骤：</b></p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>打开设置中心，安装虚拟声卡</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
点击虚拟声卡，一键安装后，打开声音设置。<br/>
确保系统声音中：<br/>
• 默认播放：<span style="color:#7c3aed;">耳机</span><br/>
• 默认录制：<span style="color:#7c3aed;">幻音麦克风</span>
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>设置幻音麦克风</b></p>
<p style="margin:0 0 6px 12px; color:#64748b;">
需要设置采样和监听：<br/>
• 不设置采样 → 无法变声<br/>
• 不设置监听 → 听不到效果
</p>

<p style="margin:0 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>对齐采样 48000</b>（点击图片放大）</p>""",
        [("resources/images/play.png", "采样设置")],
        """<p style="margin:8px 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>监听设置</b>（不想听可去掉）</p>""",
        [("resources/images/monitor.png", "监听设置")],
        """<p style="margin:8px 0 4px 0;"><span style="color:#7c3aed;">▸</span> <b>无法直接安装？</b></p>
<p style="margin:0 0 0 12px; color:#64748b;">
找到安装目录：<br/>
<span style="color:#7c3aed;">\\resources\\server\\driver</span><br/>
右键管理员运行 <span style="color:#7c3aed;">Setup.exe</span>
</p>"""
    )
    faq_content_layout.addWidget(faq3)

    faq_content_layout.addStretch()
    faq_scroll.setWidget(faq_content)
    faq_layout.addWidget(faq_scroll, stretch=1)

    return faq_container
