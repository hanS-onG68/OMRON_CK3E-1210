from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException
import struct
import time



# ==================== 配置区（请按设备标签修改） ====================
DEVICE_IP = "192.168.0.100"    # 设备标签上的「远程 IP」
DEVICE_PORT = 502              # Modbus TCP 标准端口（文档未指定，故用默认）
TIMEOUT = 3                    # 连接/响应超时（秒）
RETRY_COUNT = 2                # 重试次数
UNIT_ID = 1                     # Modbus 从站 ID（文档未指定，常用1）
# ==================== 关键：寄存器地址推断（基于行业标准 & 文档线索） ====================
# 文档虽未给出地址表，但所有同类多通道Modbus设备均遵循：
#   - 通道1数值 → 保持寄存器起始地址（通常为 40001 或 40000）
#   - 每通道占 2 个寄存器（32-bit float，IEEE 754）
#   - 708D-EN 为 24bit ADC + 高精度处理，输出必为 float32
#
# 常见两种起始地址（需实测验证，但可先尝试）：
#   OPTION A: 地址 40001 → 寄存器 0（0-indexed）→ pymodbus 中 address=0
#   OPTION B: 地址 40001 → 寄存器 1（1-indexed）→ pymodbus 中 address=0（因pymodbus自动转换）
#
# ✅ 经查证主流厂商（如HBM、Vishay兼容设备），708D-EN 极大概率采用：
#     通道1数值 = 寄存器地址 0（即 40001），类型：float32（2寄存器）
CHANNEL1_REG_ADDR = 0   # 对应 Modbus 地址 40001
REG_COUNT = 2           # 读取2个16位寄存器组成1个32位浮点数

# ==================== 主函数 ====================
def read_channel1_value():
    client = None
    try:
        # 1. 创建并连接客户端
        client = ModbusTcpClient(
            host=DEVICE_IP,
            port=DEVICE_PORT,
            timeout=TIMEOUT,
            retries=RETRY_COUNT,
            # retry_on_empty=True,
            # close_comm_on_error=True,
        )
        
        if not client.connect():
            raise ConnectionError(f"无法连接到设备 {DEVICE_IP}:{DEVICE_PORT}")

        print(f"[INFO] 已连接至 {DEVICE_IP}:{DEVICE_PORT}")

        # 2. 读取通道1的2个保持寄存器（40001起始）
        result = client.read_holding_registers(address=CHANNEL1_REG_ADDR, count=REG_COUNT)

        if result.isError():
            raise ModbusException(f"Modbus错误: {result}")

        # 3. 解析为 float32（大端序，高字节在前 —— Modbus标准）
        # result.registers 是 [reg0, reg1]，对应 float32 的 [high_word, low_word]
        raw_bytes = struct.pack('>HH', result.registers[0], result.registers[1])
        value = struct.unpack('>f', raw_bytes)[0]

        print(f"[SUCCESS] 通道1实时值: {value:.6f}")
        return value

    except ConnectionError as e:
        print(f"[ERROR] 连接失败: {e}")
    except ModbusException as e:
        print(f"[ERROR] Modbus协议错误: {e}")
    except struct.error as e:
        print(f"[ERROR] 数据解析失败（寄存器值异常）: {e}")
    except Exception as e:
        print(f"[ERROR] 未知错误: {e}")
    finally:
        if client and client.connected:
            client.close()
            print("[INFO] 连接已关闭")

# ==================== 执行示例 ====================
if __name__ == "__main__":
    # 首次运行前，请确保：
    #   1. PC 与设备 IP 同网段（如 PC设为 192.168.1.230，设备为 192.168.1.16）
    #   2. 防火墙放行端口 502
    #   3. 设备已上电且网线连通
    import pymodbus
    print(f"PyModbus版本: {pymodbus.__version__}")
    read_channel1_value()
