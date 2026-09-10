import time
from datetime import datetime
import asyncio
from typing import Optional
from mirror.sensor_KP.sensor import SensorReader
from mirror.pmac_controller import PMAC_Controller
import csv
import signal

import curses

async def main():
    sensor = SensorReader("/dev/ttyr00", 3, 1.0)
    while True:
            res = sensor.read_data()
            timestamp = res[1].strftime("%Y-%m-%dT%H:%M:%S.%f")
            sensor_values = res[2]
            chan1_val = sensor_values[0]
            chan2_val = sensor_values[1]
            chan3_val = sensor_values[2]
            chan4_val = sensor_values[3]
            chan5_val = sensor_values[4]
            # chan6_val = sensor_values[5]
            # chan7_val = sensor_values[6]
            # chan8_val = sensor_values[7]
            print(f"[{timestamp[:-5]}]: chan1_val={chan1_val:.3f}, chan2_val={chan2_val:.3f}, chan3_val={chan3_val:.3f}, chan4_val={chan4_val:.3f},  chan5_val={chan5_val:.3f}\n")
            await asyncio.sleep(1.0)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("程序出现异常，正在退出...")
    finally:
        loop.close()