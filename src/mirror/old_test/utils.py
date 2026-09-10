
"""工具模块"""
import logging, logging.handlers


class Logger(logging.Logger):
    """日志记录器类"""
    FORMATTER = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def __init__(self, name:str, debug:bool=True):
        super().__init__(name=name)
        self.setLevel(logging.DEBUG if debug else logging.INFO)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(self.FORMATTER)
        self.addHandler(stream_handler)
        file_handler = logging.FileHandler(name+".log")
        file_handler.setFormatter(self.FORMATTER)
        self.addHandler(file_handler)

