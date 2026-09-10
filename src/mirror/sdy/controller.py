
import asyncio, asyncssh
from dataclasses import dataclass, asdict
from mirror.mirror_control.utils import OCS_Logger


@dataclass(frozen=True)
class SSH_Config:
    port:int =  22
    username:str = "root"
    password:str = "deltatau"


class Controller:
    """运动控制器类"""
    SSH_CONN_TIMEOUT = 2.0
    GPA_RECV_TIMEOUT = 0.01
    SSH_LOGIN_PROMPT = ":/opt/ppmac#"
    GPA_LOGIN_CMD = "gpascii -2 -f"
    GPA_LOGIN_ACK = "\x06\r\n"
    GPA_LOGIN_PROMPT = "STDIN Open for ASCII Input"
    GPA_ECHO_MODE = "echo 7"
    GPA_CMD_ACK = "\x06\r\n\x06\r\n"
    GPA_SEP_PROMPT = "\r\n"



    def __init__(self, host, ctrl_id):
        self.host = host
        self.ctrl_id = ctrl_id
        self.conn = self.writer = self.stdout = self.stderr = None
        self.logger = OCS_Logger(f"Controller[{self.ctrl_id:d}]")
        self.logger.info(f"is starting up ...")

    @property
    def is_connected(self) -> bool:
        return (
                all([self.conn, self.writer, self.stdout, self.stderr])
                and not self.conn.is_closed()
                and not self.writer.is_closing()
        )

    async def disconnect(self):
        if (self.writer is not None) and (not self.writer.is_closing()):
            self.writer.close()
            await self.writer.wait_closed()
        if (self.conn is not None) and (not self.conn.is_closed()):
            self.conn.close()
            await self.conn.wait_closed()
        self.conn =  self.writer = self.stdout = self.stderr = None
        self.logger.info(f"connection is CLOSED")

    async def connect(self) -> bool:
        """建立连接"""
        if self.is_connected:
            await self.disconnect()
        try:
            # SSH连接
            self.conn = await asyncssh.connect(host=self.host, **asdict(SSH_Config()), options=asyncssh.SSHClientConnectionOptions(known_hosts=None))
            self.writer, self.stdout, self.stderr = await self.conn.open_session(term_type="vt100")
            await asyncio.wait_for(self.stdout.readuntil(self.SSH_LOGIN_PROMPT), timeout=self.SSH_CONN_TIMEOUT)
            # gpascii登录
            try:
                res = await self._exec_command(self.GPA_LOGIN_CMD, timeout=self.SSH_CONN_TIMEOUT, fin=self.GPA_LOGIN_ACK)
                if self.GPA_LOGIN_PROMPT not in res:
                    raise ConnectionError("gpascii login ERROR")
                res = await self._exec_command(self.GPA_ECHO_MODE, timeout=self.SSH_CONN_TIMEOUT)
                self.logger.info("Controller is CONNECTED")
                return True
            except Exception as err:
                self.logger.warning(f"gpascii logined FAILED: {err!r}")
        except Exception as err:
            self.logger.warning(f"SSH is failed: {err!r}")
        return False

    async def _exec_command(self, cmd:str, timeout:float=None, fin=None) -> None:
        """执行命令 -- 底层函数"""
        self.writer.write(cmd+self.GPA_SEP_PROMPT)
        await self.writer.drain()
        to = timeout if timeout else self.GPA_RECV_TIMEOUT
        fin = fin if fin else self.GPA_CMD_ACK
        res = await asyncio.wait_for(self.stdout.readuntil(fin), timeout=to)
        return [item for item in res.replace(fin, "").split(self.GPA_SEP_PROMPT) if item]




