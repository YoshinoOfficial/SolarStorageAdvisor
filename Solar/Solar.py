import sys
import os

# 添加项目根目录到 Python 路径，确保能找到 config 模块
current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pvlib
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.location import Location
from pvlib.pvsystem import PVSystem, Array, FixedMount
from pvlib.modelchain import ModelChain
from config.config_manager import load_panel_by_id, get_current_panel_id, get_panel_quantities, list_available_panels


def _calculate_single_panel(panel_config, lat=None, lon=None, tz=None, altitude=None, name=None, 
                            start=None, end=None, freq=None, temp_air=None, wind_speed=None, 
                            surface_tilt=None, surface_azimuth=None, temp_a=None, temp_b=None, 
                            temp_deltaT=None):
    """
    计算单块光伏板的功率输出
    
    Args:
        panel_config: 光伏板配置字典
        其他参数为可选覆盖项，如不提供则使用配置文件中的值
        
    Returns:
        pd.Series: 单块光伏板的功率时间序列 (kW)
    """
    # 从配置中获取位置参数
    location_params = panel_config['location']
    if lat is None:
        lat = location_params['lat']
    if lon is None:
        lon = location_params['lon']
    if tz is None:
        tz = location_params['tz']
    if altitude is None:
        altitude = location_params['altitude']
    if name is None:
        name = location_params['name']
    
    # 从配置中获取时间参数
    time_params = panel_config['time_range']
    if start is None:
        start = time_params['start']
    if end is None:
        end = time_params['end']
    if freq is None:
        freq = time_params['freq']
    
    # 从配置中获取天气参数
    weather_params = panel_config['weather']
    if temp_air is None:
        temp_air = weather_params['temp_air']
    if wind_speed is None:
        wind_speed = weather_params['wind_speed']
    
    # 从配置中获取系统参数
    system_params = panel_config['system_config']
    if surface_tilt is None:
        surface_tilt = system_params['surface_tilt']
    if surface_azimuth is None:
        surface_azimuth = system_params['surface_azimuth']
    
    # 温度模型参数
    temp_model_params = system_params['temperature_model']
    if temp_a is None:
        temp_a = temp_model_params['a']
    if temp_b is None:
        temp_b = temp_model_params['b']
    if temp_deltaT is None:
        temp_deltaT = temp_model_params['deltaT']
    
    # 获取面积参数
    area = panel_config['system']['area']
    
    # --- 第一步：定义地理位置 ---
    site = Location(latitude=lat, longitude=lon, tz=tz, altitude=altitude, name=name)
    
    # --- 第二步：构造"晴朗天空"时间序列 ---
    times = pd.date_range(start=start, end=end, freq=freq, tz=tz)

    # 获取晴空辐射数据 (GHI, DNI, DHI)
    clearsky = site.get_clearsky(times)

    # 整合进 weather 数据库，并补上环境温度和风速
    weather = pd.DataFrame({
        'ghi': clearsky['ghi'],
        'dni': clearsky['dni'],
        'dhi': clearsky['dhi'],
        'temp_air': temp_air,    # 环境温度
        'wind_speed': wind_speed # 风速
    }, index=times)

    # --- 第三步：定义硬件 (组件和逆变器) ---
    # 从内置数据库获取经典型号
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    module_params = sandia_modules['Canadian_Solar_CS5P_220M___2009_']  # 阿特斯 220W 组件

    cec_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
    inverter_params = cec_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']  # ABB 微逆

    # --- 第四步：构建电站系统 ---
    mount = FixedMount(surface_tilt=surface_tilt, surface_azimuth=surface_azimuth)
    array = Array(mount=mount, module_parameters=module_params, temperature_model_parameters={'a': temp_a, 'b': temp_b, 'deltaT': temp_deltaT})
    system = PVSystem(arrays=[array], inverter_parameters=inverter_params)

    # --- 第五步：运行模拟链 ---
    mc = ModelChain(system, site)
    mc.run_model(weather)
    
    # 返回单块光伏板的功率 (kW)
    return area * mc.results.ac / 1000


def getsolar(panel_quantities=None, lat=None, lon=None, tz=None, altitude=None, name=None, 
             start=None, end=None, freq=None, temp_air=None, wind_speed=None, 
             surface_tilt=None, surface_azimuth=None, temp_a=None, temp_b=None, 
             temp_deltaT=None, panel_id=None, ifdraw=False):
    """
    计算光伏系统的总功率输出（支持多种光伏板叠加）
    
    Args:
        panel_quantities: 光伏板数量字典，如 {"panel_canadian_solar": 10, "panel_trina": 5}
                         如不提供，则从配置文件读取
        panel_id: 单独计算某一种光伏板时使用（向后兼容）
        ifdraw: 是否绘制功率曲线图
        其他参数为可选覆盖项，如不提供则使用配置文件中的值
        
    Returns:
        pd.Series: 总功率时间序列 (kW)
    """
    # 如果没有传入 panel_quantities，从配置文件读取
    if panel_quantities is None:
        panel_quantities = get_panel_quantities()
    
    # 向后兼容：如果指定了 panel_id，只计算该光伏板
    if panel_id is not None:
        panel_quantities = {panel_id: 1}
    
    panel_powers = {}
    total_power = None
    
    # 遍历所有光伏板，计算并累加功率
    for pid, quantity in panel_quantities.items():
        if quantity <= 0:
            continue
        
        # 加载该光伏板配置
        panel_config = load_panel_by_id(pid)
        
        # 计算单块光伏板的功率
        single_power = _calculate_single_panel(
            panel_config, lat, lon, tz, altitude, name, start, end, freq, 
            temp_air, wind_speed, surface_tilt, surface_azimuth, 
            temp_a, temp_b, temp_deltaT
        )
        
        # 乘以数量，得到该类型光伏板的总功率
        panel_powers[pid] = single_power * quantity
        
        # 累加到总功率
        if total_power is None:
            total_power = panel_powers[pid].copy()
        else:
            total_power = total_power + panel_powers[pid]
    
    if total_power is None:
        return pd.Series()
    
    # 绘图展示
    if ifdraw:
        _draw_power_curves(panel_powers, total_power, panel_quantities)
    
    return total_power


def _draw_power_curves(panel_powers, total_power, panel_quantities):
    """
    绘制各光伏板功率曲线和总功率曲线
    
    Args:
        panel_powers: 各光伏板功率字典 {panel_id: power_series}
        total_power: 总功率时间序列
        panel_quantities: 光伏板数量字典
    """
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    plt.figure(figsize=(12, 7))
    
    colors = plt.cm.tab10.colors
    
    # 获取光伏板名称映射
    panel_names = {p['id']: p['name'] for p in list_available_panels()}
    
    # 绘制各光伏板的功率曲线
    for i, (pid, power) in enumerate(panel_powers.items()):
        label = f"{panel_names.get(pid, pid)} (x{panel_quantities.get(pid, 0)})"
        power.plot(label=label, color=colors[i % len(colors)], alpha=0.7, linewidth=1.5)
    
    # 绘制总功率曲线
    total_power.plot(label='总功率', color='black', linewidth=2.5, linestyle='--')
    
    plt.title('光伏板功率输出曲线', fontsize=14)
    plt.ylabel('功率 (kW)', fontsize=12)
    plt.xlabel('时间', fontsize=12)
    plt.legend(loc='upper right', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig('solar.png', dpi=150)
    print("图表已保存至 solar.png")
    plt.show(block=False)
    plt.pause(2)
    plt.close()


if __name__ == '__main__':
    getsolar(ifdraw=True)
