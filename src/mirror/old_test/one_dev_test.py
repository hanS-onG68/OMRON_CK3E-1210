
import time
from datetime import datetime
import asyncio
from typing import Optional
from mirror.sensor_KP.sensor import SensorReader
from mirror.pmac_controller import PMAC_Controller
import csv
from mirror.old_test.plot_show import DataAnalyzer
from mirror.logger import setup_logger
import signal
import aiofiles
from dataclasses import dataclass
from bidict import bidict
import pathlib

logger = setup_logger()

dev1_sensor2motor= bidict({
    0: 0,  # 1号通道sensor0对应电机0
    1: 1,  # 2号通道sensor1对应电机1
    2: 2,  # 3号通道sensor2对应电机2
    3: 3,  # 4号通道sensor3对应电机3
    4: 4,  # 5号通道sensor4对应电机4
    5: 5,  # 6号通道sensor5对应电机5
    6: 6,  # 7号通道sensor6对应电机6
    7: 7,  # 8号通道sensor7对应电机7
})


class OneDevTest:
    __slots__ = ('val0', 'val1', 'val2', 'val3', 'val4', 'val5', 'val6', 'val7')  # 声明固定属性, 加速属性访问
    def __init__(self, dev_path: str):
        self.dev_path = dev_path             # 传感器设备路径
        self._stop_event0 = asyncio.Event()  # 用于安全监控sensor_0 的停止信号
        self._stop_event1 = asyncio.Event()  # 用于安全监控sensor_1 的停止信号
        self._stop_event2 = asyncio.Event()  # 用于安全监控sensor_2 的停止信号
        self._stop_event3 = asyncio.Event()  # 用于安全监控sensor_3 的停止信号
        self._stop_event4 = asyncio.Event()  # 用于安全监控sensor_4 的停止信号
        self._stop_event5 = asyncio.Event()  # 用于安全监控sensor_5 的停止信号
        self._stop_event6 = asyncio.Event()  # 用于安全监控sensor_6 的停止信号
        self._stop_event7 = asyncio.Event()  # 用于安全监控sensor_7 的停止信号

        self.val0: Optional[float] = None    # 对应物理放大器的1号通道
        self.val1: Optional[float] = None    # 对应物理放大器的2号通道
        self.val2: Optional[float] = None    # 对应物理放大器的3号通道
        self.val3: Optional[float] = None    # 对应物理放大器的4号通道
        self.val4: Optional[float] = None    # 对应物理放大器的5号通道
        self.val5: Optional[float] = None    # 对应物理放大器的6号通道
        self.val6: Optional[float] = None    # 对应物理放大器的7号通道
        self.val7: Optional[float] = None    # 对应物理放大器的8号通道
        self.value_getters = [               # 调用 self.value_getters[i]() 会返回 self.val{i} 的当前值
            lambda i=i: getattr(self, f'val{i}') for i in range(8)
        ]

    async def get_sensor_data(self):
        def format_val(val: Optional[float]) -> str:
            return f"{val:.3f}" if val is not None else "None"
        
        sensor = SensorReader(self.dev_path, 3, 1.0)
        while True:
            try:
                res = sensor.read_data()
                timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
                sensor_values = res[2]

                self.val0, self.val1, self.val2, self.val3, self.val4, self.val5, self.val6, self.val7 = sensor_values[:8]
                formatted_vals = ", ".join(f"val{i}={format_val(v)}" for i, v in enumerate([self.val0, self.val1, self.val2, self.val3, self.val4, self.val5, self.val6, self.val7]))
                
                async with aiofiles.open("sensor_log.txt", "a") as log_file:
                    await log_file.write(f"[{timestamp[:-5]}]: {formatted_vals}\n")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Sensor reading error: {e}")

    async def safety_monitor(self, stop_event: asyncio.Event, sensor_id: int):
        """安全监控任务"""
        while not stop_event.is_set():
            await asyncio.sleep(0.1)
            val = self.value_getters[sensor_id]()
            if val is not None and (val > 80.0 or val < -80.0):
                logger.warning("⚠️  val out of bounds! Stopping system.")
                stop_event.set()  # 设置停止信号
                break
    
    async def save_to_csv(self, data_pairs, motor_id: int):
        if data_pairs:
            filename = f"/data/{motor_id}_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # 设置表头
                writer.writerow(['序号', 'Steps', 'Force_Value'])
                # 写入所有数据行
                for i, (first_data, second_data) in enumerate(data_pairs, 1):
                    writer.writerow([i, first_data, second_data])
            logger.info(f"\n✅ 所有数据已保存到: {filename}")
            logger.info(f"📊 共保存 {len(data_pairs)} 行数据")
            DataAnalyzer(filename).plot(x_col='Steps', y_col='Force_Value')
        else:
            logger.error("❌ 没有数据需要保存")
        return data_pairs

    def signal_handler(self, loop):
        logger.info("\n接收到关闭信号，正在退出...")

        self._stop_event0.set()  # 设置停止信号
        self._stop_event1.set()  # 设置停止信号
        self._stop_event2.set()  # 设置停止信号
        self._stop_event3.set()  # 设置停止信号
        self._stop_event4.set()  # 设置停止信号
        self._stop_event5.set()  # 设置停止信号
        self._stop_event6.set()  # 设置停止信号
        self._stop_event7.set()  # 设置停止信号
        
        # 取消所有任务
        for task in asyncio.all_tasks():
            task.cancel()
        loop.call_later(0.1, loop.stop)
        loop.close()
    

    async def one_motor_test(self, sensor_id: int, stop_event: asyncio.Event = None, task: asyncio.Task = None):
        data_pairs = []
        motor_id = dev1_sensor2motor[sensor_id]  # 根据传感器id, 获取对应的电机ID
        try:
            async with PMAC_Controller() as pmac:
                if not pmac.is_connected:
                    await pmac.connect()
                try:
                    await pmac.exec_command(f"#{motor_id}J/")  # 使能电机
                    while not stop_event.is_set():
                        val = self.value_getters[sensor_id]()  # 获取当前传感器值
                        step = await self.async_input("请输入步数: ")
                        if step.lower() == 'exit':
                            break
                        try:
                            await pmac.exec_command(f"#{motor_id}J={step}")
                            await asyncio.sleep(10)  # 等待数据稳定
                            if stop_event.is_set():
                                logger.info("🛑 安全监控触发，提前终止等待")
                                break
                            if val is not None:
                                data_pairs.append((step, val))
                                logger.info(f"✅ 记录: 步数={step}, 力值={val:.3f}")
                            else:
                                logger.warning("⚠️ 传感器数据为空")
                        except Exception as e:
                            logger.error(f"Error executing command: {e}")
                            break
                except Exception as e:
                    logger.error(f"Error: {e}")
        except Exception as e:
            logger.error(f"💥 系统错误: {e}")
        finally:
            # 清理
            stop_event.set()

            # 安全停止任务
            if not task.cancelled():
                task.cancel()
                await task

            # 停止电机
            try:
                async with PMAC_Controller() as pmac:
                    await pmac.connect()
                    await pmac.exec_command(f"#{motor_id}k")
            except:
                logger.warning("⚠️ 电机停止失败")

        await self.save_to_csv(data_pairs, motor_id)
    
    async def main(self):
        loop = asyncio.get_running_loop()
        for sig in [signal.SIGINT, signal.SIGTERM]:  # Ctrl+C 和 kill 信号
            loop.add_signal_handler(sig, self.signal_handler, loop)
        tasks = []
        try:
            sensor_task = asyncio.create_task(self.get_sensor_data())

            safety_task0 = asyncio.create_task(self.safety_monitor(self._stop_event0, sensor_id=0))
            safety_task1 = asyncio.create_task(self.safety_monitor(self._stop_event1, sensor_id=1))
            safety_task2 = asyncio.create_task(self.safety_monitor(self._stop_event2, sensor_id=2))
            safety_task3 = asyncio.create_task(self.safety_monitor(self._stop_event3, sensor_id=3))
            safety_task4 = asyncio.create_task(self.safety_monitor(self._stop_event4, sensor_id=4))
            safety_task5 = asyncio.create_task(self.safety_monitor(self._stop_event5, sensor_id=5))
            safety_task6 = asyncio.create_task(self.safety_monitor(self._stop_event6, sensor_id=6))
            safety_task7 = asyncio.create_task(self.safety_monitor(self._stop_event7, sensor_id=7))

            tasks = [sensor_task, safety_task0, safety_task1, safety_task2, safety_task3, safety_task4, safety_task5, safety_task6, safety_task7]

            sensor0_task = asyncio.create_task(self.one_motor_test(sensor_id=0, stop_event=self._stop_event0, task=safety_task0))
            sensor1_task = asyncio.create_task(self.one_motor_test(sensor_id=1, stop_event=self._stop_event1, task=safety_task1))
            sensor2_task = asyncio.create_task(self.one_motor_test(sensor_id=2, stop_event=self._stop_event2, task=safety_task2))
            sensor3_task = asyncio.create_task(self.one_motor_test(sensor_id=3, stop_event=self._stop_event3, task=safety_task3))
            sensor4_task = asyncio.create_task(self.one_motor_test(sensor_id=4, stop_event=self._stop_event4, task=safety_task4))
            sensor5_task = asyncio.create_task(self.one_motor_test(sensor_id=5, stop_event=self._stop_event5, task=safety_task5))
            sensor6_task = asyncio.create_task(self.one_motor_test(sensor_id=6, stop_event=self._stop_event6, task=safety_task6))
            sensor7_task = asyncio.create_task(self.one_motor_test(sensor_id=7, stop_event=self._stop_event7, task=safety_task7))

            sensor_tasks = [sensor0_task, sensor1_task, sensor2_task, sensor3_task, sensor4_task, sensor5_task, sensor6_task, sensor7_task]

            result = await asyncio.gather(*sensor_tasks, return_exceptions=True)
            for i, res in enumerate(result):
                if isinstance(res, Exception):
                    logger.error(f"Sensor {i} test error: {res}")
                else:
                    logger.info(f"sensor{i} test completed successfully.")

        except Exception as e:
            logger.error(f"{e}")
        finally:
            self._stop_event0.set()  # 设置停止信号
            self._stop_event1.set()  # 设置停止信号
            self._stop_event2.set()  # 设置停止信号
            self._stop_event3.set()  # 设置停止信号
            self._stop_event4.set()  # 设置停止信号
            self._stop_event5.set()  # 设置停止信号
            self._stop_event6.set()  # 设置停止信号
            self._stop_event7.set()  # 设置停止信号
            
            # 取消所有任务
            for task in asyncio.all_tasks():
                task.cancel()


if __name__ == "__main__":
    ###### 获取ttryXX 设备列表 ######
    def get_ttry_devices():
        ttyr_list = []
        try:
            path = pathlib.Path("/dev/").iterdir()
            ttyr_list = sorted([f"{device}" for device in path if device.name.startswith("ttyr")])
            print(f"Found {len(ttyr_list)} ttyr devices:")
            print(*[item for item in ttyr_list], sep=", ")
            return ttyr_list
        except Exception as e:
            print(f"Error: {e}")
            return []
    
    async def devs_test(dev_list):
        tasks= []
        for dev in dev_list:
            test = asyncio.create_task(OneDevTest(dev_path=dev))
            tasks.append(test)
        await asyncio.gather(*tasks, return_exceptions=True)
        
    try:
        dev_list = get_ttry_devices()
        if not dev_list:
            logger.error("❌ 没有找到任何ttyr设备，程序退出")
        else:
            logger.info(f"✅ 找到ttyr设备: {[dev for dev in dev_list]}")
            
            # asyncio.run(devs_test(dev_list))
    except KeyboardInterrupt:
        logger.error("程序出现异常，正在退出...")
        pass

