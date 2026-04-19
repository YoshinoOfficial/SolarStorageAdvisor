import sys
import os

current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
solar_dir = os.path.dirname(current_file)

# 注意顺序：solar_dir 在前，这样 import Solar 会找到 Solar.py 而不是 Solar 文件夹
if solar_dir not in sys.path:
    sys.path.insert(0, solar_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

import Solar
from config.config_manager import load_panel_by_id

_calculate_single_panel = Solar._calculate_single_panel
WEATHER_TYPES = Solar.WEATHER_TYPES


def calculate_power_density(panel_id='panel_canadian_solar'):
    """
    计算单块光伏板的功率密度（单位面积功率）
    
    Args:
        panel_id: 光伏板配置ID
        
    Returns:
        dict: 各天气类型的功率密度时间序列 {weather_type: power_density_series}
        float: 光伏板面积 (m²)
    """
    panel_config = load_panel_by_id(panel_id)
    area = panel_config['system']['area']
    
    power_density_dict = {}
    
    for weather_type in WEATHER_TYPES.keys():
        power = _calculate_single_panel(panel_config, weather_type=weather_type)
        power_density = power / area
        power_density_dict[weather_type] = power_density
    
    return power_density_dict, area


def visualize_power_density(power_density_dict, area, save_path=None):
    """
    可视化功率密度曲线
    
    Args:
        power_density_dict: 各天气类型的功率密度字典
        area: 光伏板面积
        save_path: 图片保存路径
    """
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    colors = plt.cm.Set1.colors
    
    # 上图：功率密度曲线
    ax1 = axes[0]
    for i, (weather_type, power_density) in enumerate(power_density_dict.items()):
        weather_name = WEATHER_TYPES.get(weather_type, weather_type)
        ax1.plot(power_density.index, power_density.values, 
                label=weather_name, color=colors[i % len(colors)], linewidth=2)
    
    ax1.set_title(f'单块光伏板功率密度日运行曲线 (面积: {area} m²)', fontsize=14)
    ax1.set_ylabel('功率密度 (kW/m²)', fontsize=12)
    ax1.set_xlabel('时间', fontsize=12)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 下图：日发电量密度对比
    ax2 = axes[1]
    weather_names = [WEATHER_TYPES.get(wt, wt) for wt in power_density_dict.keys()]
    daily_energy_density = [pd.sum() for pd in power_density_dict.values()]
    
    bars = ax2.bar(weather_names, daily_energy_density, color=colors[:len(weather_names)])
    ax2.set_title('不同天气类型日发电量密度对比', fontsize=14)
    ax2.set_ylabel('发电量密度 (kWh/m²)', fontsize=12)
    ax2.set_xlabel('天气类型', fontsize=12)
    
    for bar, energy in zip(bars, daily_energy_density):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, 
                f'{energy:.3f}', ha='center', va='bottom', fontsize=10)
    
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"图表已保存至 {save_path}")
    
    plt.show(block=False)
    plt.pause(2)
    plt.close()


def save_power_density_csv(power_density_dict, csv_path):
    """
    保存功率密度数据到CSV文件
    
    Args:
        power_density_dict: 各天气类型的功率密度字典
        csv_path: CSV文件保存路径
    """
    power_density_df = pd.DataFrame(power_density_dict)
    
    weather_labels = {wt: i for i, wt in enumerate(WEATHER_TYPES.keys())}
    power_density_df.columns = [weather_labels.get(wt, wt) for wt in power_density_df.columns]
    
    power_density_df.to_csv(csv_path, encoding='utf-8-sig', index_label='time')
    print(f"功率密度数据已保存至 {csv_path}")


if __name__ == '__main__':
    power_density_dict, area = calculate_power_density()
    
    save_path = os.path.join(os.path.dirname(__file__), 'power_density.png')
    visualize_power_density(power_density_dict, area, save_path)
    
    data_dir = os.path.join(project_root, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    csv_path = os.path.join(data_dir, 'power_density.csv')
    save_power_density_csv(power_density_dict, csv_path)
    
    print("\n各天气类型日发电量密度:")
    for weather_type, power_density in power_density_dict.items():
        weather_name = WEATHER_TYPES.get(weather_type, weather_type)
        daily_energy_density = power_density.sum()
        print(f"  {weather_name}: {daily_energy_density:.3f} kWh/m²")
