import sys
import os

# 添加项目根目录到 Python 路径，确保能找到 config 模块
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import numpy as np
from config.config_manager import load_storage_config

def simulate_storage(energy_balance, freq_minutes=15, config=None):
    """
    储能系统运行
    
    Args:
        energy_balance: pd.Series, 能量平衡（负荷-光伏），正值表示需要用电，负值表示多余光伏
        freq_minutes: int, 时间间隔（分钟）
        config: dict, 储能配置，如果为None则自动加载
    
    Returns:
        tuple: (storage_power, soc)
            storage_power: pd.Series, 储能功率（kW），正为充电，负为放电
            soc: pd.Series, 储能荷电状态（百分比）
    """
    if config is None:
        config = load_storage_config()
    
    # 获取储能参数
    capacity = config['capacity']  # kWh
    max_charge_power = config['max_charge_power']  # kW
    max_discharge_power = config['max_discharge_power']  # kW
    charge_efficiency = config['charge_efficiency']
    discharge_efficiency = config['discharge_efficiency']
    initial_soc = config['initial_soc']
    min_soc = config['min_soc']
    max_soc = config['max_soc']
    
    # 时间间隔转换为小时
    time_interval = freq_minutes / 60.0
    
    # 初始化
    n = len(energy_balance)
    storage_power = np.zeros(n)
    soc = np.zeros(n)
    current_soc = initial_soc
    
    for i in range(n):
        balance = energy_balance.iloc[i]
        
        # 当前可用能量
        current_energy = current_soc * capacity
        min_energy = min_soc * capacity
        max_energy = max_soc * capacity
        
        if balance > 0:
            # 需要用电，尝试放电
            # 理论放电功率
            desired_discharge = balance
            
            # 考虑放电效率：实际放电功率 = 需要的功率
            # 从储能取出的能量 = 需要的功率 / 放电效率
            required_energy_from_storage = desired_discharge / discharge_efficiency
            
            # 限制：最大功率、最小SOC
            max_possible_discharge = min(
                max_discharge_power,
                (current_energy - min_energy) / time_interval * discharge_efficiency
            )
            
            actual_discharge = min(desired_discharge, max_possible_discharge)
            
            if actual_discharge > 0:
                storage_power[i] = -actual_discharge  # 放电为负
                # 更新SOC
                energy_drawn = actual_discharge / discharge_efficiency * time_interval
                current_soc -= energy_drawn / capacity
        
        elif balance < 0:
            # 多余光伏，尝试充电
            # 理论充电功率（负值）
            desired_charge = -balance
            
            # 考虑充电效率：实际充电功率 = 充电功率 * 充电效率
            # 储能增加的能量 = 充电功率 * 充电效率 * 时间
            max_possible_charge = min(
                max_charge_power,
                (max_energy - current_energy) / time_interval / charge_efficiency
            )
            
            actual_charge = min(desired_charge, max_possible_charge)
            
            if actual_charge > 0:
                storage_power[i] = actual_charge  # 充电为正
                # 更新SOC
                energy_stored = actual_charge * charge_efficiency * time_interval
                current_soc += energy_stored / capacity
        
        # 确保SOC在合理范围内
        current_soc = np.clip(current_soc, min_soc, max_soc)
        soc[i] = current_soc
    
    # 转换为Series
    storage_power = pd.Series(storage_power, index=energy_balance.index)
    soc = pd.Series(soc, index=energy_balance.index)
    
    return storage_power, soc

if __name__ == '__main__':
    # 测试代码
    times = pd.date_range(start='2024-06-21', end='2024-06-22', freq='15min', tz='Asia/Shanghai')
    
    # 能量平衡：白天光伏多，晚上负荷大
    energy_balance = pd.Series(0, index=times)
    for i, time in enumerate(times):
        hour = time.hour
        if 8 <= hour <= 17:
            energy_balance.iloc[i] = -50  # 多余光伏
        else:
            energy_balance.iloc[i] = 30  # 需要用电
    
    storage_power, soc = simulate_storage(energy_balance)
    
    print(f"储能功率范围: {storage_power.min():.2f} kW 到 {storage_power.max():.2f} kW")
    print(f"SOC范围: {soc.min():.2%} 到 {soc.max():.2%}")
    print(f"总放电量: {-storage_power[storage_power < 0].sum() * 0.25:.2f} kWh")
    print(f"总充电量: {storage_power[storage_power > 0].sum() * 0.25:.2f} kWh")
