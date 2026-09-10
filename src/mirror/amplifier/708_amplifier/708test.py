from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import logging
from typing import Optional, Dict, List, Tuple
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian

from hs.src.mirror.logger import setup_logger
logger = setup_logger()

# ==================== 基础配置 ====================
DEVICE_IP: str = "192.168.0.102"
DEVICE_PORT: int = 502
TIMEOUT: float = 3.0
RETRY_COUNT: int = 3
SLAVE_ID: int = 1

class DomesticAmplifier:
    """国产多通道称重传感器放大器 Modbus TCP 操作工具
    支持: 测量值读取、参数读写、通道清零、IP配置等全协议功能
    """

    def __init__(self, slave_id: int = SLAVE_ID):
        self.client: Optional[ModbusTcpClient] = None
        self._stop = False
        self.slave_id = slave_id

    def connect(self, ip: str = DEVICE_IP, port: int = DEVICE_PORT) -> None:
        """建立Modbus TCP连接"""
        if self.client and hasattr(self.client, 'connected') and self.client.connected:
            self.client.close()

        self.client = ModbusTcpClient(
            host=ip,
            port=port,
            timeout=TIMEOUT,
            retries=RETRY_COUNT,
            framer="socket",
        )
        # 适配常见串口转TCP场景，关闭本地回显处理
        if hasattr(self.client.comm_params, 'handle_local_echo'):
            self.client.comm_params.handle_local_echo = False

        connected = self.client.connect()
        if not connected:
            raise ConnectionError(f"无法连接设备 {ip}:{port}")
        logger.info(f"已成功连接设备 {ip}:{port}")

    def disconnect(self) -> None:
        """断开连接释放资源"""
        if self.client and hasattr(self.client, 'connected') and self.client.connected:
            self.client.close()
            logger.info("设备连接已关闭")

    # -------------------------- 内部工具函数 --------------------------
    def _decode_float(self, registers: List[int]) -> float:
        """协议固定字节序解析32位浮点数"""
        decoder = BinaryPayloadDecoder.fromRegisters(
            registers,
            byteorder=Endian.Big,
            wordorder=Endian.Big
        )
        return decoder.decode_32bit_float()

    def _encode_float(self, value: float) -> List[int]:
        """将32位浮点数编码为Modbus寄存器"""
        import struct
        packed = struct.pack('>f', value)
        high = (packed[0] << 8) | packed[1]
        low = (packed[2] << 8) | packed[3]
        return [high, low]

    def _read_holding_float(self, addr: int) -> Optional[float]:
        """内部通用方法：读取单个32位浮点数（占2个保持寄存器）"""
        try:
            response = self.client.read_holding_registers(
                address=addr,
                count=2,
                slave=self.slave_id
            )
            if response.isError():
                logger.error(f"读取寄存器[地址:{hex(addr)}]失败: {response}")
                return None
            return self._decode_float(response.registers)
        except Exception as e:
            logger.error(f"读取寄存器[地址:{hex(addr)}]异常: {str(e)}", exc_info=True)
            return None

    def _write_holding_float(self, addr: int, value: float) -> bool:
        """内部通用方法：写入单个32位浮点数（占2个保持寄存器）"""
        try:
            regs = self._encode_float(value)
            response = self.client.write_registers(
                address=addr,
                values=regs,
                slave=self.slave_id
            )
            if response.isError():
                logger.error(f"写入寄存器[地址:{hex(addr)}, 值:{value}]失败: {response}")
                return False
            return True
        except Exception as e:
            logger.error(f"写入寄存器[地址:{hex(addr)}, 值:{value}]异常: {str(e)}", exc_info=True)
            return False

    # -------------------------- 测量值读取接口 --------------------------
    @staticmethod
    def calc_measure_addr(channel: int) -> int:
        """计算指定通道测量值的起始寄存器地址，遵循协议文档定义"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间，超出设备支持范围")
        return 1 + (channel - 1) * 2

    def read_channel_measure(self, channel: int) -> Optional[float]:
        """读取指定通道的实时测量值"""
        if not self.client or not (hasattr(self.client, 'connected') and self.client.connected):
            logger.error("尚未连接设备，请先调用connect()")
            return None
        start_addr = self.calc_measure_addr(channel)
        return self._read_holding_float(start_addr)

    def read_all_channels(self, max_channel: int = 18) -> Dict[int, Optional[float]]:
        """批量读取1~max_channel通道测量值，默认读取全部18通道"""
        if not (1 <= max_channel <= 18):
            raise ValueError("最大通道号范围必须为1~18")
        results = {}
        for ch in range(1, max_channel + 1):
            results[ch] = self.read_channel_measure(ch)
        return results

    # -------------------------- 通道参数读写接口 --------------------------
    def read_sensitivity(self, channel: int) -> Optional[float]:
        """读取指定通道的传感器灵敏度，范围0-4.0"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        addr = 0x0202 + (channel - 1)*2 + 2
        return self._read_holding_float(addr)

    def write_sensitivity(self, channel: int, value: float) -> bool:
        """写入指定通道的传感器灵敏度，范围0-4.0"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        if not (0 <= value <= 4):
            logger.warning("灵敏度超出范围0~4，写入可能不生效")
        addr = 0x0202 + (channel - 1)*2 + 2
        return self._write_holding_float(addr, value)

    def read_decimal_places(self, channel: int) -> Optional[int]:
        """读取指定通道的小数点位数，范围0-5位"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        addr = 0x09A6 + (channel - 1)*2
        val = self._read_holding_float(addr)
        return int(val) if val is not None else None

    def write_decimal_places(self, channel: int, decimal: int) -> bool:
        """写入指定通道的小数点位数，范围0-5位"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        if not (0 <= decimal <=5):
            raise ValueError("小数点位数必须在0~5之间")
        addr = 0x09A6 + (channel - 1)*2
        return self._write_holding_float(addr, float(decimal))

    def read_cap_value(self, channel: int) -> Optional[float]:
        """读取指定通道的载荷值，范围1~999999"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        addr = 0x04D6 + (channel - 1)*2 + 2
        return self._read_holding_float(addr)

    def write_cap_value(self, channel: int, value: float) -> bool:
        """写入指定通道的载荷值，范围1~999999"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        if not (1 <= value <= 999999):
            logger.warning("载荷值超出范围1~999999，写入可能不生效")
        addr = 0x04D6 + (channel - 1)*2 + 2
        return self._write_holding_float(addr, value)

    # -------------------------- 控制功能接口 --------------------------
    def channel_zero_clear(self, channel: int) -> bool:
        """对指定通道执行清零操作"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        addr = 0x0A36 + (channel - 1)*2
        # 写入任意值即可触发清零，这里写1
        return self._write_holding_float(addr, 1.0)

    def channel_cancel_zero(self, channel: int) -> bool:
        """撤销指定通道清零，恢复清零前保存的值"""
        if not (1 <= channel <= 18):
            raise ValueError("通道号必须在1~18之间")
        addr = 0x0A7E + (channel - 1)*2
        return self._write_holding_float(addr, 1.0)

    # -------------------------- 通用配置参数接口 --------------------------
    def read_sample_rate(self) -> Optional[int]:
        """读取采样速率，范围10HZ~4800HZ"""
        return int(self._read_holding_float(0x0B0E)) if self._read_holding_float(0x0B0E) else None

    def write_sample_rate(self, rate: int) -> bool:
        """写入采样速率，范围10HZ~4800HZ"""
        if not (10 <= rate <= 4800):
            logger.warning("采样率超出范围10~4800HZ，写入可能不生效")
        return self._write_holding_float(0x0B0E, float(rate))

    def read_calib_mode(self) -> Optional[int]:
        """读取标定方式：1=砝码标定，2=灵敏度标定"""
        val = self._read_holding_float(0x0F42)
        return int(val) if val else None

    def write_calib_mode(self, mode: int) -> bool:
        """写入标定方式：1=砝码标定，2=灵敏度标定"""
        if mode not in (1, 2):
            raise ValueError("标定方式只能为1(砝码标定)或2(灵敏度标定)")
        return self._write_holding_float(0x0F42, float(mode))

    def read_analog_config(self) -> Dict[int, str]:
        """读取所有通道模拟量输出配置"""
        config = {}
        base_addr = 0x0EC0
        for ch in range(1, 19):
            val = int(self._read_holding_float(base_addr + (ch-1)*2) or 0)
            analog_map = {
                0: "0V~5V",
                1: "0V~10V",
                2: "-5V~+5V",
                3: "-10V~+10V",
                4: "12mA~8mA",
                5: "0mA~20mA",
                6: "0mA~24mA",
                7: "10mA±10mA",
                8: "12mA±12mA",
                9: "4mA-20mA"
            }
            config[ch] = analog_map.get(val, f"未知配置({val})")
        return config

    def read_device_ip(self) -> Optional[str]:
        """读取设备当前IP地址"""
        octets = []
        for offset in [0x0F08, 0x0F0A, 0x0F0C, 0x0DE0]:
            val = int(self._read_holding_float(offset) or 0)
            if not 0 <= val <= 255:
                logger.error("IP段解析错误")
                return None
            octets.append(str(val))
        return ".".join(octets)

    def write_device_ip(self, ip_str: str) -> bool:
        """写入设备IP地址，示例: 192.168.0.100"""
        try:
            octets = [int(x) for x in ip_str.split(".")]
            if len(octets) != 4 or any(not (0 <= x <=255) for x in octets):
                raise ValueError
        except (ValueError, IndexError):
            raise ValueError("IP格式错误，示例: 192.168.0.100")

        addrs = [0x0F08, 0x0F0A, 0x0F0C, 0x0DE0]
        for octet, addr in zip(octets, addrs):
            if not self._write_holding_float(addr, float(octet)):
                return False
        return True

    # -------------------------- 循环读取功能 --------------------------
    def start_loop_read(self, max_channel: int = 18, interval: float = 0.5) -> None:
        """循环读取所有通道并打印结果，直到调用stop()停止"""
        self._stop = False
        while not self._stop:
            data = self.read_all_channels(max_channel)
            logger.info(f"实时采集结果: {data}")
            import time
            time.sleep(interval)

    def stop(self) -> None:
        """停止循环读取"""
        self._stop = True

    # -------------------------- 上下文管理器支持 --------------------------
    def __enter__(self) -> "DomesticAmplifier":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.disconnect()
        self.stop()
        return False


if __name__ == "__main__":
    # 使用示例
    with DomesticAmplifier() as amp:
        # 1. 读取所有通道测量值
        all_measure = amp.read_all_channels(max_channel=8)
        print("所有通道测量值:", all_measure)
        
        # 2. 读取1号通道灵敏度
        sens = amp.read_sensitivity(1)
        print(f"通道1灵敏度: {sens}")
        
        # 3. 对1号通道执行清零
        # amp.channel_zero_clear(1)
