import asyncio

async def handle_client(reader, writer):
    """
    处理每个新接入的客户端连接。
    reader: StreamReader对象，用于读取客户端发送的数据。
    writer: StreamWriter对象，用于向客户端发送数据。
    """
    # 获取客户端的地址信息
    addr = writer.get_extra_info('peername')
    print(f"接收到来自 {addr} 的新连接")

    # 读取客户端发送的数据（最多100字节）
    data = await reader.read(100)
    message = data.decode('utf-8')
    print(f"从 {addr} 接收到消息: {message!r}")

    # 将接收到的数据原样发回给客户端
    print(f"向 {addr} 发送回声: {message!r}")
    writer.write(data)
    await writer.drain()  # 等待数据全部发送完成

    # 关闭连接
    print(f"关闭与 {addr} 的连接")
    writer.close()
    await writer.wait_closed()

async def main():
    # 启动服务器，绑定到本地回环地址(127.0.0.1)的8888端口
    server = await asyncio.start_server(
        handle_client, '127.0.0.1', 8888
    )

    # 显示服务器监听的地址
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'服务端运行在: {addrs}')

    # 持续运行服务器，处理连接
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
