import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QCheckBox, QLabel

class CheckBoxExample(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
    
    def initUI(self):
        layout = QVBoxLayout()
        
        # 创建复选框
        self.checkbox = QCheckBox("启用功能")
        
        # 创建受控制的组件
        self.status_label = QLabel("功能未启用")
        self.status_label.setEnabled(False)  # 初始禁用
        
        # 连接信号
        self.checkbox.stateChanged.connect(self.on_checkbox_changed)
        
        layout.addWidget(self.checkbox)
        layout.addWidget(self.status_label)
        self.setLayout(layout)
    
    def on_checkbox_changed(self, state):
        # state: 0-未选中, 2-选中
        if state == 2:  # 选中
            self.status_label.setEnabled(True)
            self.status_label.setText("功能已启用 ✅")
        else:  # 未选中
            self.status_label.setEnabled(False)
            self.status_label.setText("功能未启用 ❌")

app = QApplication(sys.argv)
window = CheckBoxExample()
window.show()
sys.exit(app.exec())
