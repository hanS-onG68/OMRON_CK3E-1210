import asyncio

async def tcp_echo_client(message):
    """
    异步TCP客户端，连接服务器并发送一条消息。
    """
    # 建立与服务器的连接
    reader, writer = await asyncio.open_connection('127.0.0.1', 8888)

    # 发送消息
    print(f'发送: {message!r}')
    writer.write(message.encode('utf-8'))
    await writer.drain()  # 确保数据已发出

    # 等待并读取服务器的回声响应
    data = await reader.read(100)
    received_message = data.decode('utf-8')
    print(f'接收到: {received_message!r}')

    # 关闭连接
    print('关闭连接')
    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    # 要发送的消息内容
    message_to_send = "1234"
    asyncio.run(tcp_echo_client(message_to_send))
