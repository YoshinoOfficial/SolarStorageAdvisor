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
import numpy as np
from pvlib.location import Location
from pvlib.pvsystem import PVSystem, Array, FixedMount
from pvlib.modelchain import ModelChain
from config.config_manager import load_panel_by_id, get_current_panel_id, get_panel_quantities, list_available_panels


WEATHER_TYPES = {
    'clear': '晴天',
    'partly_cloudy': '多云',
    'overcast': '阴天',
    'rainy': '雨天',
    'foggy': '雾天/霾天'
}


def _adjust_partly_cloudy(clearsky, location, times, cloud_factor=0.7, variability=0.3):
    n = len(clearsky)
    np.random.seed(42)
    noise = np.random.randn(n)
    window = 30
    smoothed_noise = np.convolve(noise, np.ones(window)/window, mode='same')
    
    dni_factor = cloud_factor + variability * smoothed_noise
    dni_factor = np.clip(dni_factor, 0.2, 1.0)
    
    cloudy = clearsky.copy()
    cloudy['dni'] = clearsky['dni'] * dni_factor
    
    dhi_enhancement = 1.5 - 0.5 * dni_factor
    cloudy['dhi'] = clearsky['dhi'] * dhi_enhancement
    
    solar_position = location.get_solarposition(times)
    cloudy['ghi'] = cloudy['dni'] * np.cos(np.radians(solar_position['zenith'])) + cloudy['dhi']
    cloudy['ghi'] = cloudy['ghi'].clip(lower=0)
    
    return cloudy


def _adjust_overcast(clearsky, location, times, thickness_factor=0.3):
    overcast = clearsky.copy()
    overcast['dni'] = clearsky['dni'] * 0.05
    overcast['dhi'] = clearsky['ghi'] * thickness_factor
    
    solar_position = location.get_solarposition(times)
    overcast['ghi'] = overcast['dni'] * np.cos(np.radians(solar_position['zenith'])) + overcast['dhi']
    overcast['ghi'] = overcast['ghi'].clip(lower=0)
    
    return overcast


def _adjust_rainy(clearsky, location, times, intensity_factor=0.1):
    rainy = clearsky.copy()
    rainy['dni'] = clearsky['dni'] * 0.02
    rainy['dhi'] = clearsky['ghi'] * intensity_factor
    
    solar_position = location.get_solarposition(times)
    rainy['ghi'] = rainy['dni'] * np.cos(np.radians(solar_position['zenith'])) + rainy['dhi']
    rainy['ghi'] = rainy['ghi'].clip(lower=0)
    
    return rainy


def _adjust_foggy(clearsky, location, times, visibility_factor=0.4):
    foggy = clearsky.copy()
    foggy['dni'] = clearsky['dni'] * visibility_factor * 0.5
    foggy['dhi'] = clearsky['ghi'] * visibility_factor * 0.8
    
    solar_position = location.get_solarposition(times)
    foggy['ghi'] = foggy['dni'] * np.cos(np.radians(solar_position['zenith'])) + foggy['dhi']
    foggy['ghi'] = foggy['ghi'].clip(lower=0)
    
    return foggy


def _adjust_weather_irradiance(clearsky, location, times, weather_type):
    """
    根据天气类型调整辐射数据
    
    Args:
        clearsky: 晴天辐射数据DataFrame
        location: Location对象
        times: 时间序列
        weather_type: 天气类型，可选值：
            - 'clear': 晴天（不调整，返回原始数据）
            - 'partly_cloudy': 多云
            - 'overcast': 阴天
            - 'rainy': 雨天
            - 'foggy': 雾天/霾天
    
    Returns:
        调整后的辐射数据DataFrame
    """
    if weather_type == 'clear':
        return clearsky.copy()
    elif weather_type == 'partly_cloudy':
        return _adjust_partly_cloudy(clearsky, location, times)
    elif weather_type == 'overcast':
        return _adjust_overcast(clearsky, location, times)
    elif weather_type == 'rainy':
        return _adjust_rainy(clearsky, location, times)
    elif weather_type == 'foggy':
        return _adjust_foggy(clearsky, location, times)
    else:
        return clearsky.copy()


def _calculate_single_panel(panel_config, lat=None, lon=None, tz=None, altitude=None, name=None, 
                            start=None, end=None, freq=None, temp_air=None, wind_speed=None, 
                            surface_tilt=None, surface_azimuth=None, temp_a=None, temp_b=None, 
                            temp_deltaT=None, weather_type='clear'):
    """
    计算单块光伏板的功率输出
    
    Args:
        panel_config: 光伏板配置字典
        weather_type: 天气类型，可选值：
            - 'clear': 晴天（默认）
            - 'partly_cloudy': 多云
            - 'overcast': 阴天
            - 'rainy': 雨天
            - 'foggy': 雾天/霾天
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
    
    # 根据天气类型调整辐射数据
    adjusted_sky = _adjust_weather_irradiance(clearsky, site, times, weather_type)

    # 整合进 weather 数据库，并补上环境温度和风速
    weather = pd.DataFrame({
        'ghi': adjusted_sky['ghi'],
        'dni': adjusted_sky['dni'],
        'dhi': adjusted_sky['dhi'],
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
             temp_deltaT=None, panel_id=None, weather_type='clear', ifdraw=False):
    """
    计算光伏系统的总功率输出（支持多种光伏板叠加）
    
    Args:
        panel_quantities: 光伏板数量字典，如 {"panel_canadian_solar": 10, "panel_trina": 5}
                         如不提供，则从配置文件读取
        panel_id: 单独计算某一种光伏板时使用（向后兼容）
        weather_type: 天气类型，可选值：
            - 'clear': 晴天（默认）
            - 'partly_cloudy': 多云
            - 'overcast': 阴天
            - 'rainy': 雨天
            - 'foggy': 雾天/霾天
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
            temp_a, temp_b, temp_deltaT, weather_type
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
        _draw_power_curves(panel_powers, total_power, panel_quantities, weather_type)
    
    return total_power


def _draw_power_curves(panel_powers, total_power, panel_quantities, weather_type='clear'):
    """
    绘制各光伏板功率曲线和总功率曲线
    
    Args:
        panel_powers: 各光伏板功率字典 {panel_id: power_series}
        total_power: 总功率时间序列
        panel_quantities: 光伏板数量字典
        weather_type: 天气类型
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
    
    weather_name = WEATHER_TYPES.get(weather_type, weather_type)
    plt.title(f'光伏板功率输出曲线 ({weather_name})', fontsize=14)
    plt.ylabel('功率 (kW)', fontsize=12)
    plt.xlabel('时间', fontsize=12)
    plt.legend(loc='upper right', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(f'solar_{weather_type}.png', dpi=150)
    print(f"图表已保存至 solar_{weather_type}.png")
    plt.show(block=False)
    plt.pause(2)
    plt.close()


def _draw_all_weather_comparison(weather_powers):
    """
    绘制所有天气类型的功率对比图
    
    Args:
        weather_powers: 各天气类型的功率字典 {weather_type: total_power}
    """
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    plt.rcParams['axes.unicode_minus'] = False
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    
    colors = plt.cm.Set1.colors
    
    # 上图：所有天气类型的功率曲线对比
    ax1 = axes[0]
    for i, (weather_type, power) in enumerate(weather_powers.items()):
        weather_name = WEATHER_TYPES.get(weather_type, weather_type)
        power.plot(ax=ax1, label=weather_name, color=colors[i % len(colors)], linewidth=2)
    
    ax1.set_title('不同天气类型功率输出对比', fontsize=14)
    ax1.set_ylabel('功率 (kW)', fontsize=12)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.grid(True, alpha=0.3)
    
    # 下图：柱状图对比日发电量
    ax2 = axes[1]
    weather_names = [WEATHER_TYPES.get(wt, wt) for wt in weather_powers.keys()]
    daily_energy = [power.sum() for power in weather_powers.values()]
    
    bars = ax2.bar(weather_names, daily_energy, color=colors[:len(weather_names)])
    ax2.set_title('不同天气类型日发电量对比', fontsize=14)
    ax2.set_ylabel('发电量 (kWh)', fontsize=12)
    ax2.set_xlabel('天气类型', fontsize=12)
    
    for bar, energy in zip(bars, daily_energy):
        ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                f'{energy:.1f}', ha='center', va='bottom', fontsize=10)
    
    ax2.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig('solar_weather_comparison.png', dpi=150)
    print("对比图已保存至 solar_weather_comparison.png")
    plt.show(block=False)
    plt.pause(2)
    plt.close()


if __name__ == '__main__':
    weather_powers = {}
    
    for weather_type in WEATHER_TYPES.keys():
        print(f"\n正在计算 {WEATHER_TYPES[weather_type]} 的功率...")
        power = getsolar(weather_type=weather_type, ifdraw=False)
        weather_powers[weather_type] = power
        print(f"{WEATHER_TYPES[weather_type]} 日发电量: {power.sum():.2f} kWh")
    
    _draw_all_weather_comparison(weather_powers)
