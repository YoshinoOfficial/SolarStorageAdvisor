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

from config.config_manager import (
    get_wind_coefficient, list_wind_communities, get_current_wind_community,
    get_wind_turbine_config
)

logging.getLogger().setLevel(logging.WARNING)

WIND_TYPES = {
    'high_wind': '多风',
    'medium_wind': '中风',
    'low_wind': '少风'
}

WIND_SPEED_SCALES = {
    'high_wind': 1.25,
    'medium_wind': 1.0,
    'low_wind': 0.6
}


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

    power_15min = power_15min[0:-1]  # 去掉后一天0点数据

    return power_15min


def getwind(start=None, end=None, community=None, coefficient=None, wind_type=None,
            turbine_type="E-126/4200", hub_height=135, 
            nominal_power_kw=4200, ifdraw=False, save_csv=False):
    """
    获取风力发电功率曲线（15分钟间隔），支持社区系数缩放和风况类型。

    这是 Wind 模块的主函数，整合了气象数据获取、功率计算和插值功能。

    Parameters
    ----------
    start : str, optional
        数据开始时间。例如: '2010-01-01'
    end : str, optional
        数据结束时间。例如: '2010-01-01'
    community : str, optional
        社区ID（如 'industrial', 'commercial', 'residential'），
        指定后从配置读取系数自动缩放功率。
    coefficient : float, optional
        手动指定功率系数，优先级高于 community 参数。
        社区总功率 = 单台风机功率 * coefficient
    wind_type : str, optional
        风况类型（如 'high_wind', 'medium_wind', 'low_wind'），
        指定后对风速列乘以对应缩放系数再计算功率。
    turbine_type : str
        涡轮机型号。默认: "E-126/4200"
    hub_height : float
        轮毂高度，单位：米。默认: 135
    nominal_power_kw : float
        额定功率，单位：kW。默认: 4200
    ifdraw : bool
        是否绘制功率曲线图。默认: False
    save_csv : bool
        是否保存功率曲线到CSV文件。默认: False

    Returns
    -------
    pandas.Series
        风力发电功率时间序列，单位：kW，时间间隔 15 分钟。
    """
    if coefficient is None and community is not None:
        coefficient = get_wind_coefficient(community=community)

    weather = get_weather_data("weather.csv", start=start, end=end)

    if wind_type is not None and wind_type in WIND_SPEED_SCALES:
        scale = WIND_SPEED_SCALES[wind_type]
        wind_speed_cols = [col for col in weather.columns if col[0] == 'wind_speed']
        for col in wind_speed_cols:
            weather[col] = weather[col] * scale
        wind_type_name = WIND_TYPES.get(wind_type, wind_type)
        print(f"  风速缩放系数: {scale} ({wind_type_name})")

    turbine = initialize_wind_turbine(
        turbine_type=turbine_type,
        hub_height=hub_height
    )

    power_output_w = calculate_power_output(weather, turbine)

    power_15min_w = interpolate_to_15min(power_output_w)

    power_15min_kw = power_15min_w / 1000

    if coefficient is not None:
        power_15min_kw = power_15min_kw * coefficient

    power_15min_kw.name = 'Wind'

    data_dir = os.path.join(project_root, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

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
        
        date_str = start if start else power_15min_kw.index[0].strftime('%Y-%m-%d')
        png_filename = f'wind_power_{date_str}.png'
        png_path = os.path.join(data_dir, png_filename)
        plt.savefig(png_path, dpi=300, bbox_inches='tight')
        plt.close()

    if save_csv:        
        date_str = start if start else power_15min_kw.index[0].strftime('%Y-%m-%d')
        csv_filename = f'wind_power_{date_str}.csv'
        csv_path = os.path.join(data_dir, csv_filename)
        
        df_to_save = pd.DataFrame({
            'datetime': power_15min_kw.index.strftime('%Y-%m-%d %H:%M:%S'),
            'power_kw': power_15min_kw.values
        })
        df_to_save.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"风电功率曲线已保存至: {csv_path}")
    
    return power_15min_kw


def calculate_all_wind_communities(start=None, end=None):
    """
    计算所有三个社区（工业区、商业区、居民区）在所有风况类型下的风力发电功率曲线，
    并将每个社区的功率曲线保存为单独的CSV文件（包含所有风况列）到 data/ 目录

    Args:
        start: 开始时间
        end: 结束时间

    Returns:
        dict: 社区ID到{风况类型: 功率时间序列}的映射
    """
    communities = list_wind_communities()
    community_powers = {}

    data_dir = os.path.join(project_root, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    for comm in communities:
        cid = comm['id']
        cname = comm['name']
        coeff = comm['coefficient']
        print(f"\n正在计算 {cname} 的风电功率 (系数: {coeff})...")

        comm_wind_powers = {}

        for wt in WIND_TYPES.keys():
            wt_name = WIND_TYPES[wt]
            print(f"  风况: {wt_name}")
            power = getwind(start=start, end=end, community=cid, wind_type=wt)
            comm_wind_powers[wt] = power
            if not power.empty:
                print(f"    日发电量: {power.sum():.2f} kWh")

        community_powers[cid] = comm_wind_powers

        if comm_wind_powers and not list(comm_wind_powers.values())[0].empty:
            power_df = pd.DataFrame({
                WIND_TYPES[wt]: comm_wind_powers[wt]
                for wt in WIND_TYPES.keys()
                if wt in comm_wind_powers and not comm_wind_powers[wt].empty
            })

            csv_filename = f"wind_{cid}.csv"
            csv_path = os.path.join(data_dir, csv_filename)
            power_df.to_csv(csv_path, encoding='utf-8-sig', index_label='time')
            print(f"  {cname} 功率曲线（含所有风况）已保存至 {csv_path}")

    _draw_wind_community_comparison(community_powers, communities)

    return community_powers


def _draw_wind_community_comparison(community_powers, communities):
    """
    绘制所有社区的风电功率对比图

    Args:
        community_powers: 社区ID到{风况类型: 功率时间序列}的映射
        communities: 社区信息列表
    """
    import matplotlib.pyplot as plt
    import matplotlib as mpl
    mpl.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
    mpl.rcParams['axes.unicode_minus'] = False

    n_communities = len(communities)
    fig, axes = plt.subplots(n_communities + 1, 1, figsize=(14, 5 * (n_communities + 1)))
    colors = plt.cm.Set1.colors

    for idx, comm in enumerate(communities):
        cid = comm['id']
        cname = comm['name']
        ax = axes[idx]
        comm_data = community_powers.get(cid, {})

        for i, wt in enumerate(WIND_TYPES.keys()):
            wt_name = WIND_TYPES[wt]
            if wt in comm_data and not comm_data[wt].empty:
                comm_data[wt].plot(ax=ax, label=wt_name, color=colors[i % len(colors)], linewidth=2)

        ax.set_title(f'{cname} 不同风况功率曲线对比', fontsize=14)
        ax.set_ylabel('功率 (kW)', fontsize=12)
        ax.legend(loc='upper right', fontsize=10)
        ax.grid(True, alpha=0.3)

    ax_bar = axes[-1]
    bar_width = 0.25
    x_pos = range(len(communities))

    for i, wt in enumerate(WIND_TYPES.keys()):
        wt_name = WIND_TYPES[wt]
        energies = []
        for comm in communities:
            comm_data = community_powers.get(comm['id'], {})
            if wt in comm_data and not comm_data[wt].empty:
                energies.append(comm_data[wt].sum())
            else:
                energies.append(0)
        offset = (i - 1) * bar_width
        bars = ax_bar.bar([x + offset for x in x_pos], energies, bar_width,
                          label=wt_name, color=colors[i % len(colors)])
        for bar, energy in zip(bars, energies):
            ax_bar.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.5,
                        f'{energy:.0f}', ha='center', va='bottom', fontsize=8, rotation=45)

    ax_bar.set_title('各社区各风况日发电量对比', fontsize=14)
    ax_bar.set_ylabel('发电量 (kWh)', fontsize=12)
    ax_bar.set_xticks(x_pos)
    ax_bar.set_xticklabels([comm['name'] for comm in communities])
    ax_bar.legend(fontsize=10)
    ax_bar.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    data_dir = os.path.join(project_root, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    save_path = os.path.join(data_dir, 'wind_all_communities.png')
    plt.savefig(save_path, dpi=150)
    print(f"\n社区风电对比图已保存至 {save_path}")
    plt.close()


if __name__ == '__main__':
    print("=" * 60)
    print("计算所有社区在所有风况下的风力发电功率曲线")
    print("=" * 60)

    community_powers = calculate_all_wind_communities(start='2010-06-01', end='2010-06-01')

    print(f"\n{'=' * 60}")
    print("各社区各风况日发电量汇总:")
    print(f"{'=' * 60}")
    for cid, wind_powers in community_powers.items():
        print(f"\n{cid}:")
        for wt, power in wind_powers.items():
            if not power.empty:
                wt_name = WIND_TYPES.get(wt, wt)
                print(f"  {wt_name}: {power.sum():.2f} kWh")

    print(f"\n所有社区风电功率曲线已保存到 data/ 目录")
