from pymodbus.client import ModbusTcpClient          # 同步客户端
from pymodbus.exceptions import ModbusException
import struct
import logging
from typing import Optional, Dict
import time
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder

from hs.src.mirror.logger import setup_logger
logger = setup_logger()

# ==================== 配置区 ====================
DEVICE_IP: str = "192.168.0.102"
DEVICE_PORT: int = 502
TIMEOUT: float = 5.0
RETRY_COUNT: int = 3
SLAVE_ID: int = 1

class DomesticAmplifier:
    """同步版称重设备Modbus TCP读取工具"""

    def __init__(self):
        self.client: Optional[ModbusTcpClient] = None
        self._stop = False                    # 简单的停止标志


    def connect(self) -> None:
        """建立Modbus TCP连接"""
        if self.client and self.client.connected:
            self.client.close()

        self.client = ModbusTcpClient(
            host=DEVICE_IP,
            port=DEVICE_PORT,
            timeout=TIMEOUT,
            retries=RETRY_COUNT,
            framer="socket",
            keepalive=True,  # 直接开启保活
            # source_address=('192.168.0.101', 502)  # 可选：指定本地IP和端口
        )
        self.client.comm_params.handle_local_echo = False

        connected = self.client.connect()
        if not connected:
            raise ConnectionError(f"无法连接设备 {DEVICE_IP}:{DEVICE_PORT}")
        logger.info(f"已成功连接设备 {DEVICE_IP}:{DEVICE_PORT}")


    def disconnect(self) -> None:
        """断开连接"""
        if self.client and self.client.connected:
            self.client.close()
            logger.info("设备连接已关闭")

    def read_channel_measure(self) -> Optional[float]:
        """同步读取所有通道测量值，失败返回None"""
        if not self.client or not self.client.connected:
            logger.error("尚未连接设备，请先调用connect()")
            return None

        start_addr = 1  # 通道1的寄存器起始地址：1+（n-1）*2
        reg_count = 16  # 32位浮点数占2个连续寄存器，8个通道共16个寄存器

        try:
            response = self.client.read_holding_registers(
                address=start_addr,
                count=reg_count,
                slave=SLAVE_ID
            )

            if response.isError():
                logger.error(f"读取失败: {response}")
                return None
            print(f"response = {response}, response.registers: {response.registers}, len = {len(response.registers)}")
            results = {}
            try:
                for index in range(0, len(response.registers), 2):
                    reg_pair = response.registers[index:index+2]
                    decoder = BinaryPayloadDecoder.fromRegisters(
                        reg_pair,
                        byteorder=Endian.BIG,
                        wordorder=Endian.BIG,
                    )
                    val = decoder.decode_32bit_float()
                    channel = int(index / 2 + 1)
                    logger.info(f"通道{channel}测量值: {val:.4f}")
                    results[f"channel_{channel}"] = val
                return results
            except Exception as e:
                logger.error(f"数据解析异常: {e}", exc_info=True)
                return None
        except ModbusException as e:
            logger.error(f"Modbus协议错误: {e}")
            return None
        except Exception as e:
            logger.error(f"未知错误: {e}", exc_info=True)
            return None

    def display_all_channels(self) -> None:
        """循环读取所有通道，直到 stop 方法被调用"""
        while not self._stop:
            data = self.read_channel_measure()
            logger.info(f"本轮采集结果: {data}")
            time.sleep(10)  # 每次采集后等待1秒
    
    def _read_holding_float(self, addr: int) -> Optional[float]:
        """内部通用方法：读取单个32位浮点数（占2个保持寄存器）"""
        try:
            response = self.client.read_holding_registers(
                address=addr,
                count=2,
                slave=SLAVE_ID
            )
            if response.isError():
                logger.error(f"读取寄存器[地址:{hex(addr)}]失败: {response}")
                return None
            decoder = BinaryPayloadDecoder.fromRegisters(
                response.registers,
                byteorder=Endian.BIG,
                wordorder=Endian.BIG,
            )
            return decoder.decode_32bit_float()
        except Exception as e:
            logger.error(f"读取寄存器[地址:{hex(addr)}]异常: {str(e)}", exc_info=True)
            return None

    def read_sample_rate(self) -> Optional[int]:
        """读取采样速率，范围10HZ~4800HZ"""
        return int(self._read_holding_float(0x0B0E)) if self._read_holding_float(0x0B0E) else None

    # 支持 with 语句的同步上下文管理器
    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        self._stop = True
        return False


if __name__ == "__main__":
    # 使用示例
    with DomesticAmplifier() as reader:
        # 单次读取所有通道
        # results = reader.read_channel_measure()
        # print("所有通道测量值:", results)
        # time.sleep(1)  # 每次采集后等待1秒
        reader.display_all_channels()
