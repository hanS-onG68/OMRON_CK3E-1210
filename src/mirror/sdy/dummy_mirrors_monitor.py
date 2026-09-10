import sys
import numpy as np
from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *
import pyqtgraph as pg
from typing import List, Tuple
import random  # 用于模拟传感器数据
#from mirrors import Mirrors

# 设置pyqtgraph选项
pg.setConfigOptions(antialias=True, useOpenGL=True)  # 启用OpenGL加速

class HexagonSensorVisualizer(QMainWindow):
    """六边形传感器可视化主窗口"""
    
    def __init__(self, sensor_data: np.ndarray):
        super().__init__()
        self.sensor_count = 150  # 6*25=72（中心镜不部署传感器）
        self.sensor_data = sensor_data.copy()                  # 从外部传入的传感器数据数组
        # self.sensor_data[:5] = np.random.uniform(-10, 100, 5)  # 仅测试使用：随机生成一些初始数据，其他为NaN表示未读到数据
        
        # 几何参数：对边距离2米
        self.flat_to_flat = 2.0  # 对边距离
        self.side_length = self.flat_to_flat / np.sqrt(3)  # 边长 ≈ 1.1547米
        
        self.hexagon_centers = self.calculate_hexagon_centers() # 各个子镜的中心位置（x,y) - 蜂巢紧密排列
        self.sensor_positions = self.calculate_hexagon_layout() # 各个传感器的位置坐标（x,y)
        
        # 保存初始视图范围
        self.initial_view_range = None
        
        # 初始化属性
        self.min_label = None
        self.max_label = None
        self.avg_label = None
        self.std_label = None
        self.cmap_combo = None
        self.filter_check = None
        self.threshold_slider = None
        self.threshold_label = None
        self.show_lines_check = None
        self.show_values_check = None
        
        # 性能优化：预创建对象池
        self.connection_lines = []
        self.current_text_items = []
        self.hexagon_items = []
        
        # 分子镜统计标签
        self.mirror_stats_labels = []
        
        # 当前颜色映射
        self.current_colormap = pg.colormap.get('viridis')
        
        self.setup_ui()
        
        # 设置定时器模拟实时数据更新
        # self.timer = QTimer()
        # self.timer.timeout.connect(self.update_simulation_data)
        # self.timer.start(2000)  # 每200ms更新一次
        
        # 初始可视化
        self.update_visualization()
        
        # 保存初始视图范围
        self.save_initial_view_range()
        
    def calculate_hexagon_centers(self):
        """计算7个六边形的中心位置 - 真正蜂巢紧密排列"""
        # 中心六边形
        centers = [(0, 0)]
        
        # 中心间距 = 对边距离 = 2米
        center_distance = self.flat_to_flat  # 2.0米
        
        # 六个方向的角度（从水平向右开始，逆时针60°递增）
        angles = [0, 60, 120, 180, 240, 300]
        
        for angle in angles:
            # 将角度转换为弧度
            rad = np.radians(angle)
            x = center_distance * np.cos(rad)
            y = center_distance * np.sin(rad)
            centers.append((x, y))
        
        return centers
        
    def calculate_hexagon_layout(self) -> List[Tuple[float, float]]:
        """计算蜂窝状传感器布局坐标 - 蜂巢紧密排列"""
        positions = []
        
        # 7个六边形的中心位置
        centers = self.hexagon_centers
        
        # 每个六边形内12个传感器的角度分布
        angles = np.linspace(0, 2*np.pi, 13)[:-1]  # 12个等分角度=2π/12=30°：0、30、60、90、120、150、180、210、240、270、300、330
        
        # 传感器到六边形中心的距离（内圈和外圈）
        inner_radius = self.side_length * 0.55  # 内圈半径
        outer_radius = self.side_length * 0.75  # 外圈半径
        
        # 只计算周围6个子镜的传感器（中心镜不部署传感器）
        for center_idx, (cx, cy) in enumerate(centers):
            # 跳过中心镜（镜1）
            if center_idx == 0:
                continue
            positions.append((cx, cy))        
            for i, angle in enumerate(angles):
                x1 = cx + inner_radius * np.cos(angle)
                y1 = cy + inner_radius * np.sin(angle)
                x2 = cx + outer_radius * np.cos(angle)
                y2 = cy + outer_radius * np.sin(angle)
                positions.append((x2, y2))   # 外圈：奇数下标
                positions.append((x1, y1))   # 内圈：偶数下标
        return positions  
        # 一个子镜的25个传感器：
        #  0     1     2    3     4     5    6     7    8     9    10    11    12   13    14   15    16    17   18    19    20   21    22   23    24 
        # 中心  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈  外圈  内圈

    
    def get_available_colormaps(self):
        """获取可用的颜色映射列表 - 只保留三种"""
        # 只保留viridis、plasma、inferno三种颜色映射
        return ['viridis', 'plasma', 'inferno']
    
    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("ME传感器实时监控系统 - 蜂巢紧密排列")
        
        # 获取屏幕尺寸，设置窗口大小
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(100, 100, int(screen.width() * 0.5), int(screen.height() * 0.75))
        
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建绘图区域
        plot_widget = self.create_plot_widget()
        
        # 创建控制面板
        control_panel = self.create_control_panel()
        
        # 添加到布局
        main_layout.addWidget(plot_widget, 4)
        main_layout.addWidget(control_panel, 1)
        
        # 设置控制面板固定宽度
        #control_panel.setFixedWidth(380)
        
    def create_plot_widget(self) -> pg.GraphicsLayoutWidget:
        """创建pyqtgraph绘图部件"""
        plot_widget = pg.GraphicsLayoutWidget()
        plot_widget.setBackground('#0f0f0f')
        
        # 创建主绘图区域
        self.main_plot = plot_widget.addPlot(title="传感器分布图", row=0, col=0)
        self.main_plot.setAspectLocked(True)
        self.main_plot.showGrid(x=True, y=True, alpha=0.3)
        self.main_plot.setLabel('left', 'Y坐标 (米)')
        self.main_plot.setLabel('bottom', 'X坐标 (米)')
        
        # 设置视图范围
        self.main_plot.setXRange(-3.0, 3.0)
        self.main_plot.setYRange(-3.0, 3.0)
        
        # 绘制六边形网格
        self.draw_hexagon_grid()
        
        # 创建散点图项（传感器点） # 性能优化：预创建散点图项对象池
        self.scatter_plot = pg.ScatterPlotItem(
            size=25,
            pen=pg.mkPen('#ffffff', width=1.5),
            brush=pg.mkBrush(255, 255, 255, 180),
            pxMode=True
        )
        self.main_plot.addItem(self.scatter_plot)
        
        # 颜色条
        self.colorbar = self.create_colorbar()
        plot_widget.addItem(self.colorbar, row=0, col=1)
        
        return plot_widget
    
    def save_initial_view_range(self):
        """保存初始视图范围"""
        view_range = self.main_plot.viewRange()
        if view_range:
            self.initial_view_range = {
                'x_range': (view_range[0][0], view_range[0][1]),
                'y_range': (view_range[1][0], view_range[1][1])
            }
    
    def restore_initial_view(self):
        """恢复初始视图范围"""
        if self.initial_view_range:
            self.main_plot.setXRange(*self.initial_view_range['x_range'])
            self.main_plot.setYRange(*self.initial_view_range['y_range'])
    
    def create_colorbar(self) -> pg.ColorBarItem:
        """创建颜色条"""
        colorbar = pg.ColorBarItem(
            colorMap=self.current_colormap,
            orientation='vertical',
            label='传感器数值',
            limits=(0, 100)
        )
        return colorbar
    
    def update_colorbar(self):
        """更新颜色条的颜色映射"""
        if hasattr(self, 'colorbar'):
            self.colorbar.setColorMap(self.current_colormap)
    
    def draw_hexagon_grid(self):
        """绘制六边形网格背景和中心圆形"""
        def _get_hexagon_vertices(center_x, center_y):
            vertices = []
            for i in range(6):
                angle = 2 * np.pi/6 * i - np.pi/2
                x = center_x + self.side_length * np.cos(angle)
                y = center_y + self.side_length * np.sin(angle)
                vertices.append((x, y))
            return vertices

        self.hexagon_items = []
        
        for idx, (cx, cy) in enumerate(self.hexagon_centers):
            # 获取六边形顶点
            vertices = _get_hexagon_vertices(cx, cy)
            
            # 闭合六边形
            vertices.append(vertices[0])
            
            # 转换为numpy数组
            vertices_array = np.array(vertices)
            
            # 创建六边形边界
            hex_line = pg.PlotDataItem(
                vertices_array[:, 0], 
                vertices_array[:, 1],
                pen=pg.mkPen('#4CAF50', width=2, style=Qt.SolidLine),
                connect='all'
            )
            self.main_plot.addItem(hex_line)
            self.hexagon_items.append(hex_line)
            
            # 添加六边形中心标签
            #text = pg.TextItem(f"子镜 {idx+1}", color='#cccccc', anchor=(0.5, 0.5))
            text = pg.TextItem(f"子镜 {idx+1}", color='#4CAF50', anchor=(0.5, 1.5))
            text.setPos(cx, cy)
            text.setFont(QFont('Arial', 15))
            self.main_plot.addItem(text)
            self.hexagon_items.append(text)
            
            # 如果是中心镜（镜1），绘制半径为1米的圆形
            if idx == 0:
                # 绘制圆形
                angles = np.linspace(0, 2*np.pi, 100)
                circle_x = cx + 0.5 * np.cos(angles)
                circle_y = cy + 0.5 * np.sin(angles)
                
                circle = pg.PlotDataItem(
                    circle_x, circle_y,
                    pen=pg.mkPen('#cccccc', width=2, style=Qt.SolidLine),
                    #pen=pg.mkPen('#4CAF50', width=2, style=Qt.SolidLine),
                    connect='all'
                )
                self.main_plot.addItem(circle)
                self.hexagon_items.append(circle)
                
                # 添加圆形中心标签
                circle_text = pg.TextItem("中心筒", color='#ffaa00', anchor=(0.5, 0.5))
                circle_text.setPos(cx, cy)
                circle_text.setFont(QFont('Arial', 14))
                self.main_plot.addItem(circle_text)
                self.hexagon_items.append(circle_text)
    
    def create_control_panel(self) -> QWidget:
        """创建右侧控制面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(6)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 标题
        title = QLabel("传感器监视系统")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #4CAF50;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 分隔线
        layout.addWidget(self.create_h_line())
        
        # 几何信息
        geo_group = QGroupBox("几何参数")
        geo_layout = QVBoxLayout()
        geo_layout.addWidget(QLabel(f"六边形对边距: {self.flat_to_flat:.3f}米"))
        geo_layout.addWidget(QLabel(f"六边形边长: {self.side_length:.3f}米"))
        geo_layout.addWidget(QLabel(f"中心间距: {self.flat_to_flat:.3f}米"))
        geo_layout.addWidget(QLabel("排列方式: 蜂巢紧密"))
        geo_layout.addWidget(QLabel("传感器: 72个(6×12)"))
        geo_layout.addWidget(QLabel("中心镜: 无传感器，安装改正镜"))
        geo_layout.addWidget(QLabel("改正镜直径: 2米"))
        geo_group.setLayout(geo_layout)
        layout.addWidget(geo_group)
        
        # 视图控制
        view_group = QGroupBox("视图控制")
        view_layout = QVBoxLayout()
        
        restore_btn = QPushButton("还原视图 (恢复初始缩放)")
        restore_btn.clicked.connect(self.restore_initial_view)
        restore_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
        view_layout.addWidget(restore_btn)
        
        view_info = QLabel("视图控制说明:")
        view_info.setStyleSheet("font-weight: bold; color: #cccccc;")
        view_layout.addWidget(view_info)
        
        view_instructions = QLabel(
            "• 鼠标滚轮: 缩放视图\n"
            "• 鼠标拖动: 平移视图\n"
            "• 右键拖动: 框选放大\n"
            "• 双击: 自动缩放到适合\n"
            "• 点击上方按钮还原初始视图"
        )
        view_instructions.setStyleSheet("color: #999999; font-size: 10pt;")
        view_layout.addWidget(view_instructions)
        
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)
        
        # 数据更新频率
        freq_group = QGroupBox("更新设置")
        freq_layout = QVBoxLayout()
        
        freq_sub_layout = QHBoxLayout()
        freq_sub_layout.addWidget(QLabel("更新频率:"))
        self.freq_combo = QComboBox()
        self.freq_combo.addItems(["1 Hz", "5 Hz", "10 Hz", "20 Hz", "50 Hz"])
        self.freq_combo.setCurrentText("5 Hz")
        self.freq_combo.currentTextChanged.connect(self.update_timer_interval)
        freq_sub_layout.addWidget(self.freq_combo)
        freq_layout.addLayout(freq_sub_layout)
        
        freq_group.setLayout(freq_layout)
        layout.addWidget(freq_group)
        
        # 颜色映射选择
        cmap_group = QGroupBox("显示设置")
        cmap_layout = QVBoxLayout()
        
        cmap_sub_layout = QHBoxLayout()
        cmap_sub_layout.addWidget(QLabel("颜色方案:"))
        self.cmap_combo = QComboBox()
        available_colormaps = self.get_available_colormaps()
        self.cmap_combo.addItems(available_colormaps)
        self.cmap_combo.setCurrentText("viridis")
        self.cmap_combo.currentTextChanged.connect(self.on_colormap_changed)
        cmap_sub_layout.addWidget(self.cmap_combo)
        cmap_layout.addLayout(cmap_sub_layout)
        
        self.show_lines_check = QCheckBox("显示传感器连接线")
        self.show_lines_check.setChecked(True)
        self.show_lines_check.stateChanged.connect(self.update_visualization)
        cmap_layout.addWidget(self.show_lines_check)
        
        self.show_values_check = QCheckBox("显示传感器数值")
        self.show_values_check.setChecked(True)
        self.show_values_check.stateChanged.connect(self.update_visualization)
        cmap_layout.addWidget(self.show_values_check)
        
        cmap_group.setLayout(cmap_layout)
        layout.addWidget(cmap_group)
        
        # 传感器筛选
        filter_group = QGroupBox("筛选设置")
        filter_layout = QVBoxLayout()
        
        self.filter_check = QCheckBox("仅显示异常传感器")
        self.filter_check.stateChanged.connect(self.update_visualization)
        filter_layout.addWidget(self.filter_check)
        
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("阈值:"))
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(0, 100)
        self.threshold_slider.setValue(80)
        self.threshold_slider.valueChanged.connect(self.update_visualization)
        threshold_layout.addWidget(self.threshold_slider)
        self.threshold_label = QLabel("80")
        threshold_layout.addWidget(self.threshold_label)
        filter_layout.addLayout(threshold_layout)
        
        filter_group.setLayout(filter_layout)
        layout.addWidget(filter_group)
        
        # 全局数据统计
        global_stats_group = QGroupBox("全局数据统计")
        global_stats_layout = QVBoxLayout()
        self.min_label = QLabel("最小值: --")
        self.max_label = QLabel("最大值: --")
        self.avg_label = QLabel("平均值: --")
        self.std_label = QLabel("标准差: --")
        
        global_stats_layout.addWidget(self.min_label)
        global_stats_layout.addWidget(self.max_label)
        global_stats_layout.addWidget(self.avg_label)
        global_stats_layout.addWidget(self.std_label)
        
        global_stats_group.setLayout(global_stats_layout)
        layout.addWidget(global_stats_group)
        
        # 分子镜数据统计（现在只有6个子镜）
        mirror_stats_group = QGroupBox("分子镜数据统计")
        mirror_stats_scroll = QScrollArea()
        mirror_stats_scroll.setWidgetResizable(True)
        mirror_stats_scroll.setMaximumHeight(250)
        
        mirror_stats_widget = QWidget()
        mirror_stats_layout = QVBoxLayout(mirror_stats_widget)
        
        self.mirror_stats_labels = []
        for i in range(6):  # 只有6个子镜有传感器
            mirror_group = QGroupBox(f"子镜 {i+2}")  # 从镜2开始
            mirror_group_layout = QVBoxLayout()
            
            min_label = QLabel("最小值: --")
            max_label = QLabel("最大值: --")
            avg_label = QLabel("平均值: --")
            std_label = QLabel("标准差: --")
            
            mirror_group_layout.addWidget(min_label)
            mirror_group_layout.addWidget(max_label)
            mirror_group_layout.addWidget(avg_label)
            mirror_group_layout.addWidget(std_label)
            
            mirror_group.setLayout(mirror_group_layout)
            mirror_stats_layout.addWidget(mirror_group)
            
            self.mirror_stats_labels.append({
                'min': min_label,
                'max': max_label,
                'avg': avg_label,
                'std': std_label
            })
        
        mirror_stats_layout.addStretch()
        mirror_stats_widget.setLayout(mirror_stats_layout)
        mirror_stats_scroll.setWidget(mirror_stats_widget)
        mirror_stats_group_layout = QVBoxLayout()
        mirror_stats_group_layout.addWidget(mirror_stats_scroll)
        mirror_stats_group.setLayout(mirror_stats_group_layout)
        layout.addWidget(mirror_stats_group)
        
        # 控制按钮
        btn_group = QGroupBox("控制")
        btn_layout = QVBoxLayout()
        
        self.test_matrix_btn = QPushButton("系统响应矩阵测试")
        self.test_matrix_btn.clicked.connect(self.test_matrix)
        btn_layout.addWidget(self.test_matrix_btn)
        
        self.start_btn = QPushButton("开始模拟")
        self.start_btn.clicked.connect(self.start_simulation)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("暂停模拟")
        self.stop_btn.clicked.connect(self.stop_simulation)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("重置数据")
        self.reset_btn.clicked.connect(self.reset_data)
        btn_layout.addWidget(self.reset_btn)
        
        self.export_btn = QPushButton("导出数据")
        self.export_btn.clicked.connect(self.export_data)
        btn_layout.addWidget(self.export_btn)        
        
        btn_group.setLayout(btn_layout)
        layout.addWidget(btn_group)
        
        layout.addStretch()
        return panel
    
    def create_h_line(self):
        """创建水平分隔线"""
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #666;")
        return line
    
    def on_colormap_changed(self):
        """颜色映射改变时的处理"""
        if not self.cmap_combo:
            return
            
        cmap_name = self.cmap_combo.currentText()
        
        if cmap_name in ['viridis', 'plasma', 'inferno']:
            self.current_colormap = pg.colormap.get(cmap_name)
        else:
            self.current_colormap = pg.colormap.get('viridis')
            self.cmap_combo.setCurrentText('viridis')
        
        self.update_colorbar()
        self.update_visualization()
    
    def update_timer_interval(self):
        """更新定时器间隔"""
        freq_text = self.freq_combo.currentText()
        freq = int(freq_text.split()[0])
        
        if freq > 0:
            interval = int(1000 / freq)
            self.timer.setInterval(interval)
    
    def update_simulation_data(self):
        """更新模拟数据"""
        """
        random_values = np.random.random(self.sensor_count)
                
        normal_mask = random_values < 0.8
        if np.any(normal_mask):
            changes = np.random.normal(0, 1.5, np.sum(normal_mask))
            self.sensor_data[normal_mask] = np.clip(
                self.sensor_data[normal_mask] + changes, 0, 100
            )
        
        change_mask = ~normal_mask
        if np.any(change_mask):
            anomaly_mask = random_values[change_mask] < 0.15
            anomaly_indices = np.where(change_mask)[0][anomaly_mask]
            if len(anomaly_indices) > 0:
                self.sensor_data[anomaly_indices] = np.random.uniform(85, 100, len(anomaly_indices))
            
            normal_change_indices = np.where(change_mask)[0][~anomaly_mask]
            if len(normal_change_indices) > 0:
                self.sensor_data[normal_change_indices] = np.random.uniform(0, 100, len(normal_change_indices))
        """
        
        for i in range(5):
            change = np.random.normal(0, 1.5)
            new_val = self.sensor_data[i] + change
            # if np.isnan(self.sensor_data[i]):
            #     new_val = np.random.uniform(-100, 100)
            # self.sensor_data[i] = np.clip(new_val, -100, 100)
        
        self.update_visualization()
    
    def update_visualization(self):
        """更新可视化"""
        self.update_global_statistics()
        self.update_mirror_statistics()
        
        if self.cmap_combo is None:
            return
        
        threshold = 80
        if self.threshold_slider:
            threshold = self.threshold_slider.value()
            if self.threshold_label:
                self.threshold_label.setText(str(threshold))
        
        filter_enabled = False
        if self.filter_check:
            filter_enabled = self.filter_check.isChecked()
        
        #data_min = self.sensor_data.min()
        #data_max = self.sensor_data.max()
        data_min, data_max = -100, 100
        
        spots = []
        
        for item in self.current_text_items:
            self.main_plot.removeItem(item)
        self.current_text_items = []
        
        show_values = self.show_values_check and self.show_values_check.isChecked()
        data_range = data_max - data_min
        
        for i, (x, y) in enumerate(self.sensor_positions):
            value = self.sensor_data[i]
            
            if filter_enabled and value <= threshold:
                continue
            if np.isnan(value):
                color = QColor(128, 128, 128)  # 灰色
            else:
                if data_range > 0:
                    normalized = (value - data_min) / data_range
                else:
                    normalized = 0.5
                color = self.current_colormap.mapToQColor(normalized)
                
            if i%25%2 == 0:  # 外圈点用方形，内圈点用圆形
                spots.append({
                    'pos': (x, y),
                    'size': 25,
                    'brush': pg.mkBrush(color),
                    'pen': pg.mkPen('#ffffff', width=2.5),
                    'symbol': 'o' # 散点形状：'o'代表圆形
                })
            else:
                spots.append({
                    'pos': (x, y),
                    'size': 25,
                    'brush': pg.mkBrush(color),
                    'pen': pg.mkPen('#ffffff', width=2.5),
                    'symbol': 's'  # 散点形状：'s'代表方形
                })
            
            if show_values:
                text = pg.TextItem(f"{value:.1f}", anchor=(0.5, 0.5))
                text.setPos(x, y - 0.12)
                text.setColor('#ffffff')
                text.setFont(QFont('Arial', 14))
                self.main_plot.addItem(text)
                self.current_text_items.append(text)
        
        self.scatter_plot.setData(spots)
        
        """
        if self.show_lines_check and self.show_lines_check.isChecked():
            self.update_hexagon_connections(filter_enabled, threshold)
        else:
            for line in self.connection_lines:
                line.setVisible(False)
        """
        
    def update_hexagon_connections(self, filter_enabled: bool, threshold: float):
        """更新六边形连接线"""
        if not self.connection_lines:
            self.create_hexagon_connections()
        
        line_index = 0
        # 注意：现在只有6个子镜有传感器
        for hex_idx in range(1, 7):  # 从镜2开始（索引1）
            sensor_indices = list(range((hex_idx-1) * 12, hex_idx * 12))
            
            for i in range(12):
                idx1 = sensor_indices[i]
                idx2 = sensor_indices[(i + 1) % 12]
                
                if filter_enabled:
                    visible1 = bool(self.sensor_data[idx1] > threshold)
                    visible2 = bool(self.sensor_data[idx2] > threshold)
                else:
                    visible1 = visible2 = True
                
                if line_index < len(self.connection_lines):
                    line = self.connection_lines[line_index]
                    line.setVisible(visible1 and visible2)
                    line_index += 1
        
        for i in range(line_index, len(self.connection_lines)):
            self.connection_lines[i].setVisible(False)
    
    def create_hexagon_connections(self):
        """创建六边形连接线"""
        for hex_idx in range(1, 7):  # 从镜2开始
            sensor_indices = list(range((hex_idx-1) * 12, hex_idx * 12))
            
            for i in range(12):
                idx1 = sensor_indices[i]
                idx2 = sensor_indices[(i + 1) % 12]
                
                x1, y1 = self.sensor_positions[idx1]
                x2, y2 = self.sensor_positions[idx2]
                
                line = pg.PlotDataItem(
                    [x1, x2], [y1, y2],
                    pen=pg.mkPen('#666666', width=0.8, style=Qt.DashLine),
                    connect='all'
                )
                self.main_plot.addItem(line)
                self.connection_lines.append(line)
    
    def update_global_statistics(self):
        """更新全局统计数据"""
        if len(self.sensor_data) > 0 and self.min_label:
            self.min_label.setText(f"最小值: {self.sensor_data.min():.2f}")
            self.max_label.setText(f"最大值: {self.sensor_data.max():.2f}")
            self.avg_label.setText(f"平均值: {self.sensor_data.mean():.2f}")
            self.std_label.setText(f"标准差: {self.sensor_data.std():.2f}")
    
    def update_mirror_statistics(self):
        """更新分子镜统计数据"""
        if not self.mirror_stats_labels:
            return
        
        for mirror_idx in range(6):  # 只有6个子镜
            start_idx = mirror_idx * 12
            end_idx = start_idx + 12
            mirror_data = self.sensor_data[start_idx:end_idx]
            
            if len(mirror_data) > 0:
                min_val = mirror_data.min()
                max_val = mirror_data.max()
                avg_val = mirror_data.mean()
                std_val = mirror_data.std()
                
                labels = self.mirror_stats_labels[mirror_idx]
                labels['min'].setText(f"最小值: {min_val:.2f}")
                labels['max'].setText(f"最大值: {max_val:.2f}")
                labels['avg'].setText(f"平均值: {avg_val:.2f}")
                labels['std'].setText(f"标准差: {std_val:.2f}")
    
    def start_simulation(self):
        """开始模拟"""
        self.timer.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_simulation(self):
        """停止模拟"""
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def reset_data(self):
        """重置数据"""
        self.sensor_data = np.random.uniform(0, 100, self.sensor_count)
        self.update_visualization()
    
    def export_data(self):
        """导出数据"""
        filename, _ = QFileDialog.getSaveFileName(
            self, "导出数据", "sensor_data.csv", "CSV Files (*.csv);;All Files (*)"
        )
        
        if filename:
            try:
                import csv
                with open(filename, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(['传感器ID', '子镜编号', 'X坐标(米)', 'Y坐标(米)', '数值', '状态'])
                    
                    for i in range(self.sensor_count):
                        mirror_idx = (i // 12) + 2  # 从镜2开始
                        x, y = self.sensor_positions[i]
                        value = self.sensor_data[i]
                        threshold = self.threshold_slider.value() if self.threshold_slider else 80
                        status = "正常" if value <= threshold else "异常"
                        writer.writerow([i+1, mirror_idx, f"{x:.3f}", f"{y:.3f}", f"{value:.3f}", status])
                
                QMessageBox.information(self, "成功", f"72个传感器数据已导出到:\n{filename}")
            except Exception as e:
                QMessageBox.warning(self, "错误", f"导出失败: {str(e)}")

    def test_matrix(self):   # 和mirror_contronller.py结合部分
        """系统响应矩阵测试"""
        dialog = QDialog(self)
        dialog.setWindowTitle("系统响应矩阵测试 - 促动器选择")
        dialog.setModal(False)           # 非模态
        dialog.setMinimumWidth(1000)
        dialog.setMinimumHeight(600)

        main_layout = QVBoxLayout(dialog)

        # 说明标签
        info_label = QLabel("请选择要激活的促动器，并输入测试力值（N）")
        info_label.setStyleSheet("font-weight: bold; margin: 5px;")
        main_layout.addWidget(info_label)

        # 创建一个滚动区域，用于放置子镜分组
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        main_layout.addWidget(scroll)

        # 滚动区域内的容器
        container = QWidget()
        container_layout = QVBoxLayout(container)
        scroll.setWidget(container)

        # 存储子镜分组控件
        self.test_dialog_groups = []
        
        actuators_per_mirror = 25   # 每个子镜的促动器数量（根据原代码布局）
        num_mirrors = 6              # 周围子镜数量

        # 为每个子镜创建分组框
        for mirror_idx in range(num_mirrors):
            start_idx = mirror_idx * actuators_per_mirror
            end_idx = start_idx + actuators_per_mirror
            actuator_indices = list(range(start_idx, end_idx))

            group_box = QGroupBox(f"子镜 {mirror_idx+2} （促动器 {start_idx+1} ~ {end_idx}）")
            group_layout = QVBoxLayout(group_box)

            # 子镜全选复选框
            select_all_cb = QCheckBox("全选此子镜所有促动器")
            select_all_cb.setStyleSheet("font-weight: bold; color: #4CAF50;")
            group_layout.addWidget(select_all_cb)

            # 促动器列表区域（网格布局）
            actuator_grid = QWidget()
            grid_layout = QGridLayout(actuator_grid)
            # 每行放5个复选框（25个促动器，5x5）
            checkboxes = []
            for i, act_idx in enumerate(actuator_indices):
                # 促动器编号从1开始显示
                cb = QCheckBox(f"促动器 {act_idx+1}")
                row = i // 8
                col = i % 8
                grid_layout.addWidget(cb, row, col)
                checkboxes.append(cb)

            group_layout.addWidget(actuator_grid)
            group_box.setLayout(group_layout)
            container_layout.addWidget(group_box)

            # 存储分组信息
            self.test_dialog_groups.append({
                'group_box': group_box,
                'checkboxes': checkboxes,
                'select_all': select_all_cb,
                'mirror_idx': mirror_idx,
                'start_idx': start_idx
            })

            # 连接子镜全选信号
            select_all_cb.stateChanged.connect(
                lambda state, cbs=checkboxes: self._on_select_all_mirror(state, cbs)  # state是stateChanged信号自带的参数，所有绑定这个信号的槽函数，都可以使用它
            )

        container_layout.addStretch()

        # 下方控制区
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("目标力 (N):"))
        force_edit = QLineEdit("10.0")
        force_edit.setValidator(QDoubleValidator())   # 只允许数字
        control_layout.addWidget(force_edit)

        execute_btn = QPushButton("执行")
        execute_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px;")
        control_layout.addWidget(execute_btn)

        close_btn = QPushButton("关闭")
        control_layout.addWidget(close_btn)

        main_layout.addLayout(control_layout)

        # 连接按钮事件
        execute_btn.clicked.connect(lambda: self._test_matrix_execute(dialog, force_edit))
        close_btn.clicked.connect(dialog.close)

        # 显示对话框（非模态）
        dialog.show()
        # 保存对话框引用，防止被垃圾回收
        self.test_matrix_dialog = dialog

    def _on_select_all_mirror(self, state, checkboxes):
        """子镜全选复选框的状态改变时，同步该组所有促动器复选框"""
        for cb in checkboxes:
            cb.setChecked(state == Qt.Checked)
        if self.test_dialog_groups[0]["mirror_idx"] == 0:  # 镜2是第一个子镜
            print(f"[测试矩阵] 子镜 {self.test_dialog_groups[0]['mirror_idx']+2} 全选状态: {'选中' if state == Qt.Checked else '未选中'}")
            # 收集所有选中的促动器编号（全局索引，从1开始）
            selected_actuators = []
            print(f"当前子镜复选框总数: {len(checkboxes)}")
            for i, cb in enumerate(checkboxes):
                if cb.isChecked():
                    act_global_index = self.test_dialog_groups[0]['start_idx'] + i + 1  # 1-based
                    selected_actuators.append(act_global_index)
                    print(f"[测试矩阵] 当前选中促动器: {cb.text()} (全局编号: {act_global_index})",  flush=True)

            if not selected_actuators:
                print(f"[测试矩阵]提示: 未选择任何促动器")
                return
            

    def _test_matrix_execute(self, dialog, force_edit):
        """执行测试：收集选中的促动器编号和目标力，并输出（可扩展为实际发送指令）"""
        # 获取目标力
        try:
            target_force = float(force_edit.text())
        except ValueError:
            QMessageBox.warning(dialog, "输入错误", "目标力必须为数字")
            return

        # 收集所有选中的促动器编号（全局索引，从1开始）
        selected_actuators = []
        for group in self.test_dialog_groups:
            for i, cb in enumerate(group['checkboxes']):
                if cb.isChecked():
                    act_global_index = group['start_idx'] + i + 1  # 1-based
                    selected_actuators.append(act_global_index)

        if not selected_actuators:
            QMessageBox.information(dialog, "提示", "未选择任何促动器")
            return

        # 这里可以调用实际的主动光学控制接口
        # 例如：self.ao_system.apply_forces(selected_actuators, target_force)
        # 目前仅打印到控制台并弹出提示框
        msg = f"将施加力 {target_force} N 到以下 {len(selected_actuators)} 个促动器:\n"
        # 每行最多显示10个编号
        for i in range(0, len(selected_actuators), 10):
            msg += ", ".join(str(idx) for idx in selected_actuators[i:i+10]) + "\n"
        QMessageBox.information(dialog, "测试指令", msg)

        # 也可在控制台打印
        print(f"[主动光学测试] 施加力 {target_force} N 到促动器: {selected_actuators}")


def displayer(sensor_data: np.ndarray):
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.white)
    app.setPalette(palette)
    
    window = HexagonSensorVisualizer(sensor_data)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    from pycallgraph2 import PyCallGraph
    from pycallgraph2.output import GraphvizOutput

    # 配置输出，生成图片文件
    graphviz = GraphvizOutput()
    graphviz.output_file = 'call_graph.png'

    # 运行目标代码，自动生成调用图
    with PyCallGraph(output=graphviz):
    # 这里替换成你自己的主函数，开始跟踪调用
        displayer(np.random.uniform(-10, 100, 150))  # 传递随机生成的传感器数据


