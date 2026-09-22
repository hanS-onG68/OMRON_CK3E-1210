import asyncio
from mirror.amplifier.domestic_amplifier import Amplifier as amp
from contextlib import AsyncExitStack
import numpy as np
from importlib import resources

amp_file = resources.files("mirror.mirror_control").joinpath("settings/Domestic_Amplifier_Mapping.csv") 
data = np.loadtxt(amp_file, delimiter=',', dtype=str, skiprows=1, comments='#')
# dev_data = np.zeros(len(data), dtype=str)
# print(f"data = {data}-{data.shape}, dev_data = {dev_data}-{dev_data.shape}")
dev_id = np.char.strip(data[:, 0]).astype(int)
dev_ip = np.char.strip(data[:, 1])
# dev_id, dev_ip = data.T
print(f"dev_id = {dev_id}-{dev_id.shape}, dev_ip = {dev_ip}-{dev_ip.shape}")
dev_data = np.zeros(dev_id.max() + 1, dtype='<U15')
dev_data[dev_id.astype(int)] = dev_ip

print(f"dev_data = {dev_data}-{dev_data.shape}")
i= dev_data.tolist()
print(f"i = {i}-{len(i)}")
