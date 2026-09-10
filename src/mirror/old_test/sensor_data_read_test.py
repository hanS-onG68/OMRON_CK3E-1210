from mirror.sensor_KP.sensor import SensorReader
from mirror.pmac_controller import PMAC_Controller
import asyncio
import signal

async def get_sensor_data():
    sensor = SensorReader("/dev/ttyr00", 3, 1.0)
    try:
        while True:
            try:
                res = sensor.read_data()
                timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
                values = res[2]
                print(f"[{timestamp[:-5]}]: val4={values[4]:0.3f}, val5={values[5]:0.3f}")
                await asyncio.sleep(1)
            except Exception as e:
                print(f"Sensor reading error: {e}")
    except asyncio.CancelledError:
        print("\n正在优雅关闭传感器连接...")
        # 这里可以添加资源清理代码
        print("传感器连接已关闭")

def signal_handler():
    print("\n接收到关闭信号，正在退出...")
    # 取消所有任务
    for task in asyncio.all_tasks():
        task.cancel()

async def main():
    # 设置信号处理
    loop = asyncio.get_running_loop()
    for sig in [signal.SIGINT, signal.SIGTERM]:  # Ctrl+C 和 kill 信号
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await asyncio.create_task(get_sensor_data())

    except asyncio.CancelledError:
        print("程序已退出")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"Error: {e}")
