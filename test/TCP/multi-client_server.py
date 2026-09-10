import asyncio
import logging
import signal
import sys
from typing import Set, Dict, Any
from asyncio import StreamReader, StreamWriter

# 配置结构化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('HighPerfServer')

class HighPerformanceTCPServer:
    """高性能异步TCP服务器，支持多客户端并发处理"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8888,max_connections: int = 1000,buffer_size: int = 4096,timeout: int = 300):
        self.host = host
        self.port = port
        self.max_connections = max_connections
        self.buffer_size = buffer_size
        self.timeout = timeout
        
        # 连接管理
        self.active_connections: Set[StreamWriter] = set()
        self.connection_semaphore = asyncio.Semaphore(max_connections)  # asyncio.Semaphore 实际上是一个计数器，它跟踪可以同时运行的并发任务数量。当计数器为 0 时，任何尝试获取信号量的任务都会被挂起，直到计数器大于 0 时才会允许新的任务执行。
        self.server: asyncio.Server = None
        
        # 统计信息
        self.stats = {
            'total_connections': 0,
            'current_connections': 0,
            'messages_processed': 0,
            'errors_count': 0
        }
        
        # 信号处理
        self.is_shutting_down = False

    async def handle_client(self, reader: StreamReader, writer: StreamWriter) -> None:
        """处理单个客户端连接的协程"""
        client_addr = writer.get_extra_info('peername')
        connection_id = f"{client_addr[0]}:{client_addr[1]}"
        
        async with self.connection_semaphore:  # 连接数限制
            # 连接建立
            self._add_connection(writer, connection_id)
            
            try:
                # 设置超时
                await asyncio.wait_for(self._client_communication_loop(reader, writer, connection_id), timeout=30)
                    
            except asyncio.TimeoutError:
                logger.warning(f"客户端 {connection_id} 通信超时")
                writer.write(b"Error: Connection timeout\n")
            except ConnectionResetError:
                logger.warning(f"客户端 {connection_id} 连接重置")
            except Exception as e:
                logger.error(f"客户端 {connection_id} 处理错误: {e}")
                self.stats['errors_count'] += 1
            finally:
                # 资源清理
                self._remove_connection(writer, connection_id)

    async def _client_communication_loop(self, reader: StreamReader, writer: StreamWriter, connection_id: str):
        """客户端通信主循环"""
        while not self.is_shutting_down:
            # 异步读取数据
            data = await reader.read(self.buffer_size)
            
            if not data:
                logger.info(f"客户端 {connection_id} 主动断开连接")
                break
            
            # 处理消息
            message = data.decode('utf-8', errors='ignore').strip()
            logger.info(f"从 {connection_id} 收到消息: {message[:50]}...")
            
            # 处理特殊命令
            response = await self._process_message(message, connection_id, writer)
            if response is None:  # 退出命令
                break
            
            # 发送响应
            writer.write(message.encode('utf-8'))
            await writer.drain()  # 确保数据发送完成
            
            self.stats['messages_processed'] += 1

    async def _process_message(self, message: str, connection_id: str, writer: StreamWriter) -> str or None:
        """处理客户端消息并生成响应"""
        message_lower = message.lower()
        logger.info(f"message_lower = {message_lower}")
        
        if message_lower == 'quit':
            logger.info(f"客户端 {connection_id} 请求退出")
            return "Goodbye!\n"
        elif message_lower == 'status':
            status_info = (
                f"服务器状态 - 总连接: {self.stats['total_connections']}, "
                f"当前连接: {self.stats['current_connections']}, "
                f"处理消息: {self.stats['messages_processed']}\n"
            )
            return status_info
        elif message_lower == 'help':
            help_text = (
                "可用命令:\n"
                "status - 查看服务器状态\n"
                "quit   - 断开连接\n"
                "help   - 显示此帮助信息\n"
                "其他内容将原样返回\n"
            )
            return help_text
        else:
            # 回声服务 + 时间戳
            import datetime
            timestamp = datetime.datetime.now().isoformat()
            return f"[{timestamp}] ECHO: {message}\n"

    def _add_connection(self, writer: StreamWriter, connection_id: str):
        """添加连接到活跃连接集合"""
        self.active_connections.add(writer)
        self.stats['total_connections'] += 1
        self.stats['current_connections'] = len(self.active_connections)
        logger.info(f"客户端 {connection_id} 已连接. 当前连接数: {self.stats['current_connections']}")

    def _remove_connection(self, writer: StreamWriter, connection_id: str):
        """从活跃连接集合中移除连接"""
        if writer in self.active_connections:
            self.active_connections.remove(writer)
            self.stats['current_connections'] = len(self.active_connections)
            
        if not writer.is_closing():
            writer.close()
        
        logger.info(f"客户端 {connection_id} 已断开. 剩余连接数: {self.stats['current_connections']}")

    async def start_server(self):
        """启动高性能TCP服务器"""
        try:
            # 创建服务器
            self.server = await asyncio.start_server(
                self.handle_client, self.host, self.port
            )
            
            # 输出服务器信息
            server_addr = self.server.sockets[0].getsockname()
            logger.info(f"🚀 高性能TCP服务器启动成功!")
            logger.info(f"📍 监听地址: {server_addr}")
            logger.info(f"📊 最大连接数: {self.max_connections}")
            logger.info(f"⏱️  超时时间: {self.timeout}秒")
            logger.info(f"💾 缓冲区大小: {self.buffer_size}字节")
            
            # 注册信号处理
            self._register_signal_handlers()
            
            # 启动统计任务
            asyncio.create_task(self._stats_reporter())
            
            # 开始服务
            async with self.server:
                await self.server.serve_forever()
                
        except OSError as e:
            logger.error(f"启动服务器失败: {e}")
            if e.errno == 98:  # 地址已使用
                logger.error(f"端口 {self.port} 已被占用，请更换端口或终止相关进程")
        except Exception as e:
            logger.error(f"服务器运行异常: {e}")
        finally:
            await self.graceful_shutdown()

    def _register_signal_handlers(self):
        """注册信号处理器实现优雅关闭"""
        loop = asyncio.get_running_loop()
        
        for sig in [signal.SIGINT, signal.SIGTERM]:  # 用于请求终止进程的信号
            loop.add_signal_handler(sig, lambda: asyncio.create_task(self.graceful_shutdown()))

    async def _stats_reporter(self):
        """定期报告服务器统计信息"""
        while not self.is_shutting_down:
            await asyncio.sleep(60)  # 每分钟报告一次
            if not self.is_shutting_down:
                logger.info(
                    f"📈 统计报告 - 连接数: {self.stats['current_connections']}/"
                    f"{self.stats['total_connections']}, 消息数: {self.stats['messages_processed']}, "
                    f"错误数: {self.stats['errors_count']}"
                )

    async def graceful_shutdown(self):
        """优雅关闭服务器"""
        if self.is_shutting_down:
            return
            
        self.is_shutting_down = True
        logger.info("开始优雅关闭服务器...")
        
        # 关闭所有活跃连接
        if self.active_connections:
            logger.info(f"正在关闭 {len(self.active_connections)} 个活跃连接...")
            for writer in self.active_connections.copy():
                if not writer.is_closing():
                    writer.write(b"Server is shutting down. Goodbye!\n")
                    writer.close()
                    await writer.wait_closed()  # 等待连接完全关闭
            
            # 等待连接关闭
            await asyncio.sleep(2)
        
        # 停止服务器
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        logger.info("服务器关闭完成")


async def main():
    """主函数"""
    # 可配置参数
    server = HighPerformanceTCPServer(
        host='127.0.0.1',      # 监听地址
        port=8888,             # 监听端口
        max_connections=1000,  # 最大并发连接数
        buffer_size=4096,      # 缓冲区大小
        timeout=300            # 超时时间(秒)
    )
    
    await server.start_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
