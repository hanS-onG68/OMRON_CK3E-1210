import asyncio
from mirror.amplifier.domestic_amplifier import Amplifier as amp
from contextlib import AsyncExitStack


params1 = {
        "host":     "192.168.0.100" ,    # 设备IP
        "port":     502,                # Modbus TCP端口，默认502
        "timeout":  3,                  # 连接/响应超时(秒)
        "retries":  3,                  # 重试次数
        "slave_id": 1                   # Modbus从站地址，文档默认1
}

params2 = {
        "host":     "192.168.0.102" ,    # 设备IP
        "port":     502,                # Modbus TCP端口，默认502
        "timeout":  3,                  # 连接/响应超时(秒)
        "retries":  3,                  # 重试次数
        "slave_id": 1                   # Modbus从站地址，文档默认1
}

async def main():
    # 用AsyncExitStack统一管理两个异步资源，并行建立连接
    async with AsyncExitStack() as stack:
        reader1, reader2 = await asyncio.gather(
            stack.enter_async_context(amp(**params1)),
            stack.enter_async_context(amp(**params2))
        )
        # 两个设备连接就绪后再执行读取操作
        await asyncio.gather(
            reader1.display_all_channels(),
            reader2.display_all_channels()
        )

asyncio.run(main())