"""
Wind 模块 - 风力发电功率计算

本模块使用 windpowerlib 库计算风力发电机的功率输出曲线。
主要功能：
1. 获取气象数据（风速、温度、气压等）
2. 使用 ModelChain 计算风机功率输出
3. 将 1 小时间隔数据插值为 15 分钟间隔
"""
import sys
import os

current_file = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(current_file))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pandas as pd
import logging
from windpowerlib import ModelChain, WindTurbine

logging.getLogger().setLevel(logging.WARNING)


def get_weather_data(filename="weather.csv", start="2010-06-01", end="2010-06-01"):
    """
    从文件导入气象数据并筛选时间范围。

    气象数据包括：
    - 风速（wind_speed）：不同高度的测量值，单位 m/s
    - 气温（temperature）：不同高度的测量值，单位 K
    - 地表粗糙度长度（roughness_length）：影响风廓线，单位 m
    - 气压（pressure）：大气压力，单位 Pa

    Parameters
    ----------
    filename : str
        气象数据文件名。默认: 'weather.csv'。
    start : str or datetime-like, optional
        数据开始时间。
    end : str or datetime-like, optional
        数据结束时间。

    Returns
    -------
    pandas.DataFrame
        包含风速、温度、粗糙度和气压时间序列的 DataFrame。
    """
    datapath = os.path.dirname(__file__)
    file = os.path.join(datapath, filename)

    weather_df = pd.read_csv(
        file,
        index_col=0,
        header=[0, 1],
        date_parser=lambda idx: pd.to_datetime(idx, utc=True),
    )

    weather_df.index = weather_df.index.tz_convert("Europe/Berlin")

    if start is not None or end is not None:
        weather_df = weather_df.loc[start:end]

    return weather_df


def initialize_wind_turbine(turbine_type="E-126/4200", hub_height=135):
    """
    初始化风力发电机对象。

    使用 OpenEnergy Database (oedb) 涡轮机库中的数据。
    常用机型包括：
    - "E-126/4200": Enercon E126, 4.2MW, 轮毂高度通常 135m
    - "V90/2000": Vestas V90, 2MW
    - "SWT130/3600": Siemens SWT-130, 3.6MW

    查看所有可用机型：
        windpowerlib.wind_turbine.get_turbine_types()

    Parameters
    ----------
    turbine_type : str
        涡轮机型号，需与 oedb 数据库中的名称匹配。
    hub_height : float
        轮毂高度，单位：米。

    Returns
    -------
    WindTurbine
        风力发电机对象。
    """
    turbine_config = {
        "turbine_type": turbine_type,
        "hub_height": hub_height,
    }
    turbine = WindTurbine(**turbine_config)
    return turbine


def calculate_power_output(weather, turbine, modelchain_config=None):
    """
    使用 ModelChain 计算风力发电机的功率输出。

    ModelChain 封装了完整的功率计算流程：
    气象数据 → 风速修正 → 密度计算 → 温度修正 → 功率计算 → 输出

    Parameters
    ----------
    weather : pandas.DataFrame
        气象数据时间序列。
    turbine : WindTurbine
        风力发电机对象。
    modelchain_config : dict, optional
        ModelChain 配置参数。默认使用以下配置：
        - wind_speed_model: 'logarithmic' (对数风廓线)
        - density_model: 'ideal_gas' (理想气体定律)
        - temperature_model: 'linear_gradient' (线性温度梯度)
        - power_output_model: 'power_coefficient_curve' (功率系数曲线)
        - density_correction: True (密度修正)

    Returns
    -------
    pandas.Series
        功率输出时间序列，单位：W。
    """
    if modelchain_config is None:
        modelchain_config = {
            "wind_speed_model": "logarithmic",
            "density_model": "ideal_gas",
            "temperature_model": "linear_gradient",
            "power_output_model": "power_coefficient_curve",
            "density_correction": True,
            "obstacle_height": 0,
            "hellman_exp": None,
        }

    mc = ModelChain(turbine, **modelchain_config).run_model(weather)
    return mc.power_output


def interpolate_to_15min(power_output):
    """
    将 1 小时间隔的功率数据插值为 15 分钟间隔。

    使用线性插值方法，保持功率曲线的连续性。
    插值范围从原始数据的起点到终点+1小时，确保覆盖完整的一天。

    Parameters
    ----------
    power_output : pandas.Series
        1 小时间隔的功率数据，单位：W。

    Returns
    -------
    pandas.Series
        15 分钟间隔的功率数据，单位：W。
    """
    start_time = power_output.index[0]
    end_time = power_output.index[-1] + pd.Timedelta(hours=1)

    new_index = pd.date_range(
        start=start_time,
        end=end_time,
        freq='15min'
    )

    extended_index = power_output.index.union([end_time])
    power_extended = power_output.reindex(extended_index)
    power_extended.iloc[-1] = power_output.iloc[-1]

    power_15min = power_extended.reindex(
        extended_index.union(new_index)
    ).interpolate(method='linear').reindex(new_index)

    return power_15min


def getwind(start=None, end=None, turbine_type="E-126/4200", hub_height=135, 
            nominal_power_kw=4200, ifdraw=False):
    """
    获取风力发电功率曲线（15分钟间隔）。

    这是 Wind 模块的主函数，整合了气象数据获取、功率计算和插值功能。

    Parameters
    ----------
    start : str, optional
        数据开始时间。例如: '2010-01-01'
        默认使用气象数据集的最早时间。
    end : str, optional
        数据结束时间。例如: '2010-01-01'
        默认使用气象数据集的最晚时间。
    turbine_type : str
        涡轮机型号。默认: "E-126/4200" (Enercon E126, 4.2MW)
    hub_height : float
        轮毂高度，单位：米。默认: 135
    nominal_power_kw : float
        额定功率，单位：kW。用于归一化输出。
        默认: 4200 (对应 E-126/4200 的 4.2MW)
    ifdraw : bool
        是否绘制功率曲线图。默认: False

    Returns
    -------
    pandas.Series
        风力发电功率时间序列，单位：kW，时间间隔 15 分钟。

    Examples
    --------
    获取默认时间范围的风电功率：
    >>> wind_power = getwind()

    获取指定日期的风电功率：
    >>> wind_power = getwind(start='2010-06-01', end='2010-06-01')

    使用不同风机型号：
    >>> wind_power = getwind(turbine_type="V90/2000", hub_height=80, nominal_power_kw=2000)
    """
    weather = get_weather_data("weather.csv", start=start, end=end)

    turbine = initialize_wind_turbine(
        turbine_type=turbine_type,
        hub_height=hub_height
    )

    power_output_w = calculate_power_output(weather, turbine)

    power_15min_w = interpolate_to_15min(power_output_w)

    power_15min_kw = power_15min_w / 1000

    power_15min_kw.name = 'Wind'

    if ifdraw:
        import matplotlib.pyplot as plt
        import matplotlib as mpl
        mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
        mpl.rcParams['axes.unicode_minus'] = False

        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(power_15min_kw.index, power_15min_kw.values, 
                label='Wind Power', color='#17becf', linewidth=2)
        ax.axhline(y=nominal_power_kw, color='r', linestyle='--', 
                   label=f'额定功率 ({nominal_power_kw} kW)')
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('功率', fontsize=12)
        ax.set_title(f'风力发电功率曲线 - {turbine_type}', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show(block=False)
        plt.pause(3)
        plt.savefig('wind.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    return power_15min_kw


if __name__ == '__main__':
    wind_power = getwind(start='2010-06-01', end='2010-06-01', ifdraw=True)
    print(f"风电功率数据点数: {len(wind_power)}")
    print(f"时间范围: {wind_power.index[0]} 至 {wind_power.index[-1]}")
    print(f"最大功率: {wind_power.max():.2f} kW")
