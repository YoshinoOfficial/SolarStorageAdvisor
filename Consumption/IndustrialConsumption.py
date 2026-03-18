import sys
import os

# 添加项目根目录到 Python 路径
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def get_industrial_consumption(
    total_daily_kwh=1000,
    start='2024-06-21',
    end='2024-06-22',
    freq='15min',
    tz='Asia/Shanghai',
    ifdraw=False
):
    """
    生成工业典型日负荷曲线
    
    Args:
        total_daily_kwh: 一天总用电量（kWh）
        start: 开始时间
        end: 结束时间
        freq: 时间频率
        tz: 时区
        ifdraw: 是否绘制曲线
    
    Returns:
        pd.Series: 负荷曲线（kW），以times为索引
    """
    times = pd.date_range(start=start, end=end, freq=freq, tz=tz)
    
    # 定义工业负荷典型比例模式（基于时间点的小时数）
    # 工业负荷特点：白天工作时段高，夜间低，可能有多个峰值
    hourly_pattern = {
        0: 0.30,   # 00:00-01:00 深夜低负荷
        1: 0.25,   # 01:00-02:00 深夜最低
        2: 0.25,   # 02:00-03:00 深夜最低
        3: 0.25,   # 03:00-04:00 深夜最低
        4: 0.30,   # 04:00-05:00 逐渐上升
        5: 0.40,   # 05:00-06:00 早班准备
        6: 0.60,   # 06:00-07:00 早班开始
        7: 0.80,   # 07:00-08:00 早高峰
        8: 1.00,   # 08:00-09:00 工作高峰
        9: 1.00,   # 09:00-10:00 工作高峰
        10: 0.95,  # 10:00-11:00 工作时段
        11: 0.90,  # 11:00-12:00 午餐前
        12: 0.70,  # 12:00-13:00 午休
        13: 0.85,  # 13:00-14:00 午后恢复
        14: 1.00,  # 14:00-15:00 工作高峰
        15: 1.00,  # 15:00-16:00 工作高峰
        16: 0.95,  # 16:00-17:00 工作时段
        17: 0.90,  # 17:00-18:00 晚班前
        18: 0.80,  # 18:00-19:00 晚班开始
        19: 0.75,  # 19:00-20:00 晚班时段
        20: 0.70,  # 20:00-21:00 晚班时段
        21: 0.60,  # 21:00-22:00 晚班结束
        22: 0.45,  # 22:00-23:00 收尾
        23: 0.35   # 23:00-00:00 夜间
    }
    
    # 为每个时间点分配对应的负荷比例
    load_ratios = []
    for time in times:
        hour = time.hour
        load_ratios.append(hourly_pattern[hour])
    
    load_ratios = np.array(load_ratios)
    
    # 计算总比例权重
    total_ratio = np.sum(load_ratios) * (15 / 60)  # 15分钟间隔转换为小时
    
    # 计算基准功率（kW）
    base_power = total_daily_kwh / total_ratio
    
    # 生成负荷曲线（kW）
    consumption = pd.Series(base_power * load_ratios, index=times)
    
    # 绘图展示
    if ifdraw:
        consumption.plot(figsize=(12, 6), title=f'Industrial Consumption (Total: {total_daily_kwh} kWh)')
        plt.ylabel('Consumption (kW)')
        plt.xlabel('Time of Day')
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(2)
        plt.savefig('industrial_consumption.png')
        plt.close()
    
    return consumption

if __name__ == '__main__':
    result = get_industrial_consumption(total_daily_kwh=1000, ifdraw=True)
    print(f"总用电量: {result.sum() * (15/60):.2f} kWh")
    print(f"最大功率: {result.max():.2f} kW")
    print(f"平均功率: {result.mean():.2f} kW")
