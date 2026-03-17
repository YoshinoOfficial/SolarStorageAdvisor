import pandas as pd

def getconsumption(start='2024-06-21', end='2024-06-22', freq='15min', tz='Asia/Shanghai'):
    times = pd.date_range(start=start, end=end, freq=freq, tz=tz)
    Consumption = pd.Series(100, index=times)
    #print(consumption)
    # 绘图展示
    '''
    Consumption.plot(figsize=(10, 6), title='Consumption (Beijing)')
    plt.ylabel('Consumption (kW)')
    plt.xlabel('Time of Day')
    plt.grid(True)
    plt.show(block=False)
    plt.pause(2)
    plt.close()
    '''
    return Consumption
