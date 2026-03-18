import sys
import os

# 添加项目根目录到 Python 路径，确保能找到模块
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import matplotlib.pyplot as plt
from Consumption.IndustrialConsumption import get_industrial_consumption

def getconsumption(type='industry',totaldailyconsumption=100*24,start='2024-06-21', end='2024-06-22', freq='15min', tz='Asia/Shanghai', ifdraw=False):
    times = pd.date_range(start=start, end=end, freq=freq, tz=tz)

    # 恒定负荷数据
    if type == 'industry':
        Consumption = get_industrial_consumption(totaldailyconsumption,start, end, freq, tz)
    elif type == 'constant':
        Consumption = pd.Series(totaldailyconsumption/24, index=times)
    else:
        raise ValueError("type must be 'industry' or 'constant'")
    #print(consumption)

    # 绘图展示
    if ifdraw:
        Consumption.plot(figsize=(10, 6), title='Consumption (Beijing)')
        plt.ylabel('Consumption (kW)')
        plt.xlabel('Time of Day')
        plt.grid(True)
        plt.show(block=False)
        plt.pause(2)
        plt.savefig('consumption.png')
        plt.close()
    
    return Consumption

if __name__ == '__main__':
    getconsumption(ifdraw=True)