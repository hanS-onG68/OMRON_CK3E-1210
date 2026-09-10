from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException
import struct
import logging
from typing import Optional, Dict
import asyncio

from hs.src.mirror.logger import setup_logger
logger = setup_logger()

# ==================== 配置区（按实际设备修改） ====================
DEVICE_IP: str = "192.168.0.102"     # 设备IP
DEVICE_PORT: int = 502               # Modbus TCP端口，默认502
TIMEOUT: float = 3.0                 # 连接/响应超时(秒)
RETRY_COUNT: int = 3                 # 重试次数
SLAVE_ID: int = 1                    # Modbus从站地址，文档默认1


class DomesticAmplifier:
    """异步版称重设备Modbus TCP读取工具，遵循设备寄存器协议"""
    client: Optional[AsyncModbusTcpClient] = None
    def __init__(self):
        self.client: Optional[AsyncModbusTcpClient] = None
        # 配置属性放在这里

    @staticmethod
    def calc_measure_addr(channel: int) -> int:
        """根据通道号计算测量值起始寄存器地址（遵循文档地址规则）
        :param channel: 通道号，范围 1-8
        :return: 寄存器起始地址（十进制）
        """
        if not (1 <= channel <= 8):
            raise ValueError("通道号必须在1~8之间")
        # 原协议公式：0001 + (n-1)*2H → 十进制计算结果一致
        return 1 + (channel - 1) * 2

    async def connect(self) -> None:
        """异步建立Modbus TCP连接"""
        if self.client and self.client.connected:
            self.client.close()

        self.client = AsyncModbusTcpClient(
            host=DEVICE_IP,
            port=DEVICE_PORT,
            timeout=TIMEOUT,
            retries=RETRY_COUNT,
            # source_address=('192.168.0.188', 22)
        )

        connected = await self.client.connect()
        if not connected:
            raise ConnectionError(f"无法连接设备 {DEVICE_IP}:{DEVICE_PORT}，请检查网络/配置")
        logger.info(f"已成功连接设备 {DEVICE_IP}:{DEVICE_PORT}")

    async def disconnect(self) -> None:
        """异步断开连接释放资源"""
        if self.client and self.client.connected:
            self.client.close()
            logger.info("设备连接已关闭")

    async def read_channel_measure(self, channel: int) -> Optional[float]:
        """异步读取指定通道测量值
        :param channel: 目标通道号 (1~8)
        :return: 成功返回测量值，失败返回None
        """
        if not self.client or not self.client.connected:
            logger.error("尚未连接设备，请先调用connect()")
            return None

        start_addr = self.calc_measure_addr(channel)
        reg_count = 2  # 32位浮点数占2个连续寄存器

        try: # 使用03H功能码读取保持寄存器
            # 适配pymodbus 3.x新版本参数名
            response = await self.client.read_holding_registers(
                address=start_addr,
                count=reg_count,
                device_id=SLAVE_ID  # 通讯地址默认为01
            )

            if response.isError():
                logger.error(f"通道{channel}读取失败: {response}")
                return None

            # 兼容不同版本pymodbus的浮点数解析
            try:
                val = self.client.convert_from_registers(
                    response.registers,
                    data_type=self.client.DATATYPE.FLOAT32
                )
            except AttributeError:
                logger.warning("pymodbus版本不支持convert_from_registers，尝试手动解析")
                from pymodbus.payload import BinaryPayloadDecoder
                from pymodbus.constants import Endian
                decoder = BinaryPayloadDecoder.fromRegisters(
                    response.registers,
                    byteorder=Endian.Big,
                    wordorder=Endian.Big
                )
                val = [decoder.decode_32bit_float()]
            result_val = val[0] if isinstance(val, (list, tuple)) else val
            if result_val is None or not isinstance(result_val, float):  # 注意：result_val=0.0
                logger.error(f"通道{channel}数据解析异常")
                return None
            logger.info(f"通道{channel}测量值: {result_val:.4f}")
            return result_val
        except ModbusException as e:
            logger.error(f"通道{channel} Modbus协议错误: {str(e)}")
            return None
        # except struct.error:
        #     logger.error(f"通道{channel} 数据解析失败：寄存器值异常")
        #     return None
        except Exception as e:
            logger.error(f"通道{channel} 未知错误: {str(e)}", exc_info=True)
            return None

    async def read_all_channels(self) -> Dict[int, Optional[float]]:
        """异步并发读取1~8所有通道测量值，比顺序读取效率更高"""
        # 创建所有通道读取任务，并发执行
        tasks = [self.read_channel_measure(ch) for ch in range(1, 9)]
        results = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=10) # 效率低，直接从内存中读数据
        return {ch+1: val for ch, val in enumerate(results)}  # 整理为 {通道号: 数值} 的字典
    
    """"
    async def run():
    """


if __name__ == "__main__":
    """
    运行前检查：
    1. PC和设备处于同一网段，可ping通设备IP
    2. 防火墙放行502端口，设备上电网线连接正常
    安装依赖：pip install pymodbus
    """
    reader = DomesticAmplifier()
    async def main():
        try:
            await reader.connect()
            # 示例1：读取单通道数值
            channel1_val = await reader.read_channel_measure(channel=1)
            # 示例2：并发读取所有8个通道，效率更高
            # all_vals = await reader.read_all_channels()
        except Exception as e:
            logger.error(f"运行异常: {str(e)}", exc_info=True)
        finally:
            await reader.disconnect()

    asyncio.run(main())
