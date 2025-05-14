from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTextEdit
from PyQt6.QtGui import QPainter, QColor, QPen
from PyQt6.QtCore import Qt, QEvent

class AgreementDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("用户协议")
        self.setFixedSize(600, 1000)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        title_label = QLabel("用户协议")
        title_label.setStyleSheet("""
            font-family: "Microsoft YaHei", "SimHei", "Arial";
            font-size: 18px; 
            font-weight: bold; 
            color: #333; 
            padding: 5px 0;
            text-align: center;
        """)
        main_layout.addWidget(title_label)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setStyleSheet("""
            QTextEdit {
                font-family: "Microsoft YaHei", "SimHei", "Arial";
                font-size: 14px;
                border: none;  
                background-color: transparent;  
                line-height: 1.5;
            }
            QScrollBar:vertical {
                width: 10px;
                background-color: transparent;
            }
            QScrollBar::handle:vertical {
                background-color: #ccc;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                width: 0px;
                background-color: transparent;
            }
        """)
        text_edit.setHtml("""
            <style>
                h3 {
                    color: #007bff;
                    font-size: 16px;
                    margin-top: 1.5em;  
                }
                hr {
                    border: none;
                    border-bottom: 3px solid #007bff;  
                    margin: 10px 0 15px 0;
                }
                p {
                    text-indent: 2em;
                    color: #666;
                    margin-top: 0.8em;  
                    margin-bottom: 0.8em;
                }
                h4 {  
                    color: #ff0000;  
                    font-weight: 500;  
                    margin-top: 1.5em;  
                }
            </style>
            <h3>1. 引言</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;欢迎使用本变声软件！在使用本软件前，请您仔细阅读并理解本用户协议。一旦您下载、安装或使用本软件，即表示您同意遵守本协议的所有条款。</p>
            <h3>2. 软件使用许可</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.1 本软件授予您非独占、不可转让的使用许可，仅供个人非商业用途。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;2.2 您不得对软件进行反向工程、反编译或试图以任何方式发现软件的源代码。</p>
            <h3>3. 用户行为规范</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.1 用户不得利用本软件进行任何违法或不当行为，包括但不限于传播非法、诈骗、侵犯他人版权或其他知识产权的内容。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;3.2 用户应当遵守所有适用的本地、国家及国际法律法规。对于用户通过软件进行的任何行为及其结果，用户应当独立承担全部责任。</p>
            <h3>4. 免责声明</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.1 用户明确同意其使用本软件所存在的风险将完全由其自己承担；因其使用软件而产生的一切后果也由其自己承担。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;4.2 本软件不对用户使用软件的行为及其结果承担责任。若用户的行为导致第三方损害的，用户应当独立承担责任；若因此给软件开发者或其关联方造成损失的，用户还应负责赔偿。</p>
            <h3>5. 修订和终止</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.1 本协议的修改和更新由软件开发者自行决定，并通过软件更新或官方公告的方式通知用户。用户继续使用软件将被视为接受修改后的协议。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;5.2 若用户违反本协议的任何条款，开发者有权随时终止用户的使用许可。</p>
            <h3>6. 其他</h3>
            <hr>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6.1 本协议的解释权和修改权归软件开发者所有。</p>
            <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;6.2 若本协议中的任何一条被视为废止、无效或因任何原因不可执行，该条应视为可从本协议中分离，不影响其余条款的有效性和可执行性。</p>
            <h4>通过安装、复制、下载或以其他方式使用本软件，您确认您已阅读本协议，并同意受其条款的约束。如果您不同意本协议的条款，请不要安装或使用本变声软件。</h4>
        """)
        main_layout.addWidget(text_edit)

        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if not self.geometry().contains(event.globalPosition().toPoint()):
                self.close()
                return True
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(255, 255, 255, 220))  
        painter.drawRoundedRect(rect, 15, 15)

        painter.end()