
import time
from datetime import datetime
from gsv86lib import gsv86


class Amplifier:
    """放大器数据采集类"""
    BAUDRATE = 115200

    def __init__(self, path:str, amp_id:int, data_rate:float=10.0):
        self.amp_id = amp_id
        self.data_rate = data_rate
        self.com = gsv86(path, baudrate=Amplifier.BAUDRATE)
        self.com.writeDataRate(self.data_rate)
        self.com.StartTransmission()
        #time.sleep(3.0/self.data_rate)  # 这个是我自己凑的经验公式，等待时间应该是采第一批数据的时间间隔，和datarate有关，datarate越快sleep越短

    def __del__(self):
        if self.com and self.com.transmissionIsRunning:
            self.com.StopTransmission()

    def read_data(self):
        """获取GSV8-DS的一组数据"""
        if not self.com or not self.com.transmissionIsRunning:
            raise RuntimeError(f"Group[{self.group_id}]: is not READY")
        data = self.com.ReadValue()
        values = []
        if not data.data:
            return (self.amp_id, datetime.now(), [])
        # data.data = [ str(timestamp), {'channel0': xxx, .... , 'channel7': xxx}, bool(isInputOverload), bool(isSixAxisError) ]
        timestamp = datetime.fromisoformat(data.data[0])
        values.append(data.getChannel1())
        values.append(data.getChannel2())
        values.append(data.getChannel3())
        values.append(data.getChannel4())
        values.append(data.getChannel5())
        values.append(data.getChannel6())
        values.append(data.getChannel7())
        values.append(data.getChannel8())
        result = (self.amp_id, timestamp, values)
        return result


