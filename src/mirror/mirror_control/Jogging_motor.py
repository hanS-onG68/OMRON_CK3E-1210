import time
from datetime import datetime
import asyncio
from typing import Optional
# from mirror.sensor_KP.sensor import SensorReader
from mirror.amplifier.domestic_amplifier import Amplifier as DomesticAmplifier
from mirror.amplifier.imported_amplifier import Amplifier as ImportedAmplifier
from mirror.pmac_controller import PMAC_Controller, SSH_Config
import csv
from mirror.logger import setup_logger
import signal
import aiofiles
from dataclasses import dataclass
from bidict import bidict
import pathlib
from mirror.sensor_KP.one_motor_test import OneMotorTest
import pandas as pd
import inspect
from mirror.sensor_KP.one_motor_test import GLOBAL_PLOT_POOL
from mirror.sensor_KP.plot import kp
import ipaddress
from pathlib import Path
import json,os
from mirror.sensor_KP.excel_generator import ExcelDataHandler

from PySide2.QtWidgets import *
from PySide2.QtCore import *
from PySide2.QtGui import *

# 6个子镜对应6个pmac控制器
# config = SSH_Config(host = "192.168.0.200")
# pmac_controler = PMAC_Controller(config)

import sys
import asyncio
import qasync


class JogMotor(QMainWindow):
    def __init__(self):
        super().__init__()
        # 存储所有已初始化的PMAC控制器实例，避免覆盖旧连接
        self.pmac_controllers = {}
        
        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("传感器-电机 点动")

        # 获取屏幕尺寸，设置窗口大小
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(100, 100, int(screen.width() * 0.5), int(screen.height() * 0.75))

        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # 左侧布局
        left_layout = QVBoxLayout()

        # PMAC控制器分组
        controller_group_box = QGroupBox("PMAC控制器")
        self.controller_group_box_layout = QVBoxLayout()
        controller_group_box.setLayout(self.controller_group_box_layout)

        controller_layout = QHBoxLayout()
        for i in range(200, 201):
            host = f"192.168.0.{i}"
            checkBox = QCheckBox(host)
            checkBox.stateChanged.connect(lambda state, h=host: asyncio.create_task(self.toggle_pmac_connection(state, h)))
            controller_layout.addWidget(checkBox)

        self.controller_group_box_layout.addLayout(controller_layout)
        left_layout.addWidget(controller_group_box)

        # 电机控制点动分组
        motor_group_box = QGroupBox("电机组")
        self.motor_group_box_layout = QVBoxLayout()
        motor_group_box.setLayout(self.motor_group_box_layout)

        motor_layout = QGridLayout()
        button_list = []
        from functools import partial
        for motor_id in range(0, 25, 1):
            button = QPushButton(f"电机{motor_id}")
            # 按钮设置成可勾选样式，点动时按住/勾选持续运行
            button.setCheckable(True)
            button_list.append(button)
            # 绑定电机点动异步槽
            button.pressed.connect(
                partial(self.on_motor_pressed, motor_id, button)
            )
            button.released.connect(
                partial(self.on_motor_released, motor_id)
            )
            i = motor_id // 5
            j = motor_id % 5
            motor_layout.addWidget(button, i, j)
        self.motor_group_box_layout.addLayout(motor_layout)
        left_layout.addWidget(motor_group_box)

        main_layout.addLayout(left_layout)

    
    def on_motor_pressed(self, motor_id, button):
        """电机按钮按下"""
        asyncio.create_task(self.motor_jog_start(motor_id, button))

    def on_motor_released(self, motor_id):
        """电机按钮释放"""
        asyncio.create_task(self.motor_jog_stop(motor_id))

    async def toggle_pmac_connection(self, state, ip):
        """异步切换PMAC控制器连接: 勾选则建立连接, 取消勾选则断开释放"""
        if state == Qt.Checked:
            try:
                print(f"正在连接PMAC设备 {ip}")
                config = SSH_Config(host=ip)
                self.pmac_controller = PMAC_Controller(config)
                await self.pmac_controller.connect()
                print(f"PMAC设备 {ip} 连接成功")
            except Exception as e:
                print(f"PMAC设备 {ip} 连接失败: {str(e)}")
        else:
                try:
                    await self.pmac_controller.disconnect()
                    print(f"PMAC设备 {ip} 已断开连接")
                except Exception as e:
                    print(f"断开PMAC {ip} 失败: {str(e)}")

    async def motor_jog_start(self, motor_id, button):
        """开始点动电机"""
        # if not self.pmac_controller.is_connected:
        #     print("请先连接PMAC控制器")
        #     return
        
        cmd = f"#{motor_id}J=2000"
        print(f"电机{motor_id} 开始点动")

        try:
            # ✅ 使用 button.isDown() 检测是否按下
            while button.isDown():
                await self.pmac_controller.exec_command(cmd)
                print(f"[电机{motor_id}] 执行: {cmd}")
                await asyncio.sleep(0.05)
                pos = await self.pmac_controller.get_variable("ActPos", axis=motor_id)
                print(f"电机{motor_id} 当前的位置: {pos}")
        except asyncio.CancelledError:
            print(f"电机{motor_id}点动被取消")
        except Exception as e:
            print(f"电机{motor_id}指令发送失败: {str(e)}")

    async def motor_jog_stop(self, motor_id):
        """停止点动电机"""
        if not self.pmac_controller.is_connected:
            print("PMAC控制器已断开连接")
            return

        if self.pmac_controller.is_connected:
            await self.pmac_controller.exec_command(f"#{motor_id}k")
            print(f"电机{motor_id} 停止")

    def closeEvent(self, event):
        """窗口关闭事件，统一清理所有异步任务和连接"""

        # 关闭所有PMAC连接
        asyncio.create_task(self.pmac_controller.disconnect())

        # 停止事件循环
        loop = asyncio.get_event_loop()
        loop.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 使用qasync替换Qt默认事件循环，原生支持asyncio协程调度
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    win = JogMotor()
    win.show()

    with loop:
        loop.run_forever()
