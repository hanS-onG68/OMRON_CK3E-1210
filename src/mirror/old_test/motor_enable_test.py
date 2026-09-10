

import time
from datetime import datetime
import asyncio
from typing import Optional
# from sensor import SensorReader
from hs.src.mirror.pmac_controller import PMAC_Controller,SSH_Config 
import csv
import signal

import curses

async def MotorAction(pmac: PMAC_Controller):
    await pmac.exec_command(f"#1J/")
    await pmac.exec_command(f"#1J=1000")



async def main():
    ssh_config = SSH_Config(host="192.168.0.200")
    async with PMAC_Controller(ssh_config) as pmac:
        if not pmac.is_connected:
            await pmac.connect()
        await MotorAction(pmac)
        await pmac.exec_command(f"#1K")
        


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("程序出现异常，正在退出...")
    finally:
        loop.close()