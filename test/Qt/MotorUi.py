import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtWidgets import *


class MotorUi:
    def __init__(self):
        self.main_window = QMainWindow()                            # 1. 创建主窗口
        self.central_widget = QWidget()                             # 2. 创建一个通用的QWidget作为中心部件
        self.main_layout = QGridLayout(self.central_widget)         # 3. 创建布局管理器，并指定父部件为central_widget
        
        # 4. 创建组件
        self.is_enable_label = QLabel("功能未启用")              # 4.1 创建一个标签，用于显示电机使能状态
        self.sensor_label = QLabel("Sensor num:")               # 4.2 创建一个标签，用于显示传感器数量
        self.is_enable_checkbox = QCheckBox("是否使能电机")      # 4.3 创建一个复选框，用于控制电机使能状态
        self.move_button = QPushButton("MOVE")                  # 4.4 创建一个按钮，用于触发移动操作
        self.step_num_box = QSpinBox(self.central_widget)       # 4.5 创建一个SpinBox，用于输入步数
        self.lcd_number = QLCDNumber(self.central_widget)       # 4.6 创建一个LCD显示器，用于显示当前步数   
        
        self.__init_ui()  # 初始化UI组件和布局


    def __init_ui(self):
        self.__init_main_window()
        self.__init_central_widget()
        self.__init_label()
        self.__init_lcd_number()
        self.__init_spin_box()
        self.__init_move_button()
        self.__init_checkbox()
        self.__init_main_layout()

    def on_move_button_clicked(self):
        message = self.step_num_box.value()
        print(f"按钮被点击了，当前输入的值是: {message}")
        self.lcd_number.display(message)  # 更新LCD显示的值
    
    def on_is_enable_checkbox_changed(self, state):
        # state: 0-未选中, 2-选中
        if state == 2:  # 选中
            self.is_enable_label.setEnabled(True)
            self.is_enable_label.setText("电机已使能 ✅")
        else:  # 未选中
            self.is_enable_label.setEnabled(False)
            self.is_enable_label.setText("电机未使能 ❌")
    
    def __init_main_window(self):
        self.main_window.setWindowTitle("主窗口与布局关联示例")
        self.main_window.resize(400, 300)

    def __init_central_widget(self):
        self.main_window.setCentralWidget(self.central_widget)    # 将中心部件设置给主窗口
    

    def __init_lcd_number(self):
        self.lcd_number.display(0)  # 初始化显示为 0
        self.lcd_number.setSegmentStyle(QLCDNumber.Flat)  # 设置段样式为 Flat
        self.lcd_number.setStyleSheet("background-color: black; color: green;")  # 设置背景和前景颜色
        self.lcd_number.setFixedSize(100, 60)  # 调整LCD显示器的大小

    def __init_move_button(self):
        self.move_button.setFixedSize(80, 30)                          # 调整按钮的大小
        self.move_button.clicked.connect(self.on_move_button_clicked)  # 连接按钮点击事件

    def __init_checkbox(self):
        self.is_enable_checkbox.stateChanged.connect(self.on_is_enable_checkbox_changed)  # 连接复选框状态改变事件
    
    def __init_spin_box(self):
        self.step_num_box.setRange(0, 100000)  # 设置输入范围

    def __init_label(self):
        self.is_enable_label.setEnabled(False)  # 初始禁用

    def __init_main_layout(self):
            # 设置列的拉伸因子，实现1:2:3:4的比例
            # self.main_layout.setColumnStretch(0, 1)  # 第0列，因子为1
            # self.main_layout.setColumnStretch(1, 2)  # 第1列，因子为2
            # self.main_layout.setColumnStretch(2, 3)  # 第2列，因子为3 
            # self.main_layout.setColumnStretch(3, 4)  # 第3列，因子为4
        self.main_layout.setContentsMargins(50, 50, 50, 50); # 设置布局整体边距
        self.main_layout.addWidget(self.sensor_label, 0, 0)  # 将标签添加到布局中
        self.main_layout.addWidget(self.lcd_number, 0, 1)    # 将LCD显示器添加到布局中
        self.main_layout.addWidget(self.move_button, 2, 0)
        self.main_layout.addWidget(self.step_num_box, 2, 1)
        self.main_layout.addWidget(self.is_enable_checkbox, 3, 0)
        self.main_layout.addWidget(self.is_enable_label, 3, 1)

    
    def start(self):
        self.main_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)  # 创建应用实例
    ui = MotorUi()
    ui.start()
    sys.exit(app.exec())