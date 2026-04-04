"""
modelchain_example 模块展示了 windpowerlib 库的简单用法。

本模块使用 ModelChain 类来计算风力发电机的功率输出。
ModelChain（模型链）是 windpowerlib 的核心概念，它将多个计算步骤串联起来，
形成完整的功率计算流程。

ModelChain 的工作原理：
========================
ModelChain 是一个高级接口，它自动组合了风力发电计算所需的所有步骤：

1. 风速修正（wind_speed_model）：
   将测量高度的风速修正到轮毂高度
   - 'logarithmic': 对数风廓线模型（默认）
   - 'hellman': Hellman 指数模型
   - 'interpolation_extrapolation': 插值外推法

2. 密度计算（density_model）：
   计算空气密度，影响功率输出
   - 'barometric': 气压计公式（默认）
   - 'ideal_gas': 理想气体定律
   - 'interpolation_extrapolation': 插值外推法

3. 温度修正（temperature_model）：
   将温度修正到轮毂高度
   - 'linear_gradient': 线性温度梯度（默认）
   - 'interpolation_extrapolation': 插值外推法

4. 功率输出计算（power_output_model）：
   - 'power_curve': 使用功率曲线（默认）
   - 'power_coefficient_curve': 使用功率系数曲线

5. 密度修正（density_correction）：
   是否根据空气密度变化修正功率输出

使用 ModelChain 的三个主要步骤：
1. 导入气象数据（风速、温度、气压、粗糙度等）
2. 定义风力发电机参数（类型、轮毂高度、功率曲线等）
3. 调用 ModelChain 计算功率输出时间序列

安装依赖：
   pip install windpowerlib
   pip install matplotlib

SPDX-FileCopyrightText: 2019 oemof developer group <contact@oemof.org>
SPDX-License-Identifier: MIT
"""
import os
import pandas as pd
import requests
import logging
from windpowerlib import ModelChain, WindTurbine, create_power_curve

try:
    from matplotlib import pyplot as plt
except ImportError:
    plt = None


def get_weather_data(filename="weather.csv", start=None, end=None, **kwargs):
    r"""
    从文件导入气象数据。

    气象数据是风力发电计算的基础输入，包括：
    - 风速（wind_speed）：不同高度的测量值，单位 m/s
    - 气温（temperature）：不同高度的测量值，单位 K（开尔文）
    - 地表粗糙度长度（roughness_length）：影响风廓线，单位 m
    - 气压（pressure）：大气压力，单位 Pa

    数据格式说明：
    ==============
    DataFrame 使用 MultiIndex 作为列索引：
    - 第一层：变量名称（如 'wind_speed'）
    - 第二层：测量高度（如 10，表示 10 米高度）
    - 行索引：DateTimeIndex 时间序列

    如果本地没有气象数据文件，会自动从网络下载示例数据。

    Parameters
    ----------
    filename : str
        气象数据文件名。默认: 'weather.csv'。
    start : str or datetime-like, optional
        数据开始时间。支持多种格式：
        - 字符串: '2010-01-01', '2010-01-01 00:00:00'
        - pandas 时间戳: pd.Timestamp('2010-01-01')
        - None: 使用数据集的最早时间（默认）
    end : str or datetime-like, optional
        数据结束时间。支持多种格式：
        - 字符串: '2010-12-31', '2010-12-31 23:00:00'
        - pandas 时间戳: pd.Timestamp('2010-12-31')
        - None: 使用数据集的最晚时间（默认）

    Other Parameters
    ----------------
    datapath : str, optional
        气象数据文件存储路径。默认为本示例所在目录。

    Returns
    -------
    :pandas:`pandas.DataFrame<frame>`
        包含风速、温度、粗糙度和气压时间序列的 DataFrame。

    Examples
    --------
    获取完整数据集：
    >>> weather = get_weather_data("weather.csv")

    获取2010年1月的数据：
    >>> weather = get_weather_data("weather.csv", start='2010-01-01', end='2010-01-31')

    获取指定时间范围：
    >>> weather = get_weather_data("weather.csv",
    ...                            start='2010-06-01 00:00:00',
    ...                            end='2010-06-30 23:00:00')
    """

    if "datapath" not in kwargs:
        kwargs["datapath"] = os.path.dirname(__file__)

    file = os.path.join(kwargs["datapath"], filename)

    # 如果文件不存在，自动下载示例气象数据
    if not os.path.isfile(file):
        logging.debug("Download weather data for example.")
        req = requests.get("https://osf.io/59bqn/download")
        with open(file, "wb") as fout:
            fout.write(req.content)

    # 读取 CSV 文件
    # header=[0, 1] 表示使用前两行作为多级列索引
    weather_df = pd.read_csv(
        file,
        index_col=0,
        header=[0, 1],
        date_parser=lambda idx: pd.to_datetime(idx, utc=True),
    )

    # 转换时区为欧洲/柏林时区
    weather_df.index = weather_df.index.tz_convert("Europe/Berlin")

    # 根据开始和结束时间筛选数据
    if start is not None or end is not None:
        weather_df = weather_df.loc[start:end]

    return weather_df


def initialize_wind_turbines():
    r"""
    初始化三个 WindTurbine（风力发电机）对象。

    本函数展示了三种定义风力发电机的方法：

    方法一：使用 OpenEnergy Database (oedb) 涡轮机库
    ------------------------------------------------
    oedb 提供了大量商用风力发电机的参数数据，包括功率曲线和功率系数曲线。
    只需指定 turbine_type（型号）和 hub_height（轮毂高度）即可。

    方法二：自定义功率曲线
    ----------------------
    直接提供功率曲线数据，适用于：
    - 使用非标准型号的发电机
    - 需要精确控制功率曲线的情况

    方法三：从文件读取数据
    ----------------------
    从 CSV 等文件读取功率曲线数据，适用于批量处理多种机型。

    查看所有可用机型：
        windpowerlib.wind_turbine.get_turbine_types()

    Returns
    -------
    Tuple (:class:`~.wind_turbine.WindTurbine`,
           :class:`~.wind_turbine.WindTurbine`,
           :class:`~.wind_turbine.WindTurbine`)
        三个风力发电机对象
    """
    # ************************************************************************
    # **** 方法一：使用 oedb 涡轮机库中的数据 ********************************
    # 这种方法最简单，只需指定机型和轮毂高度
    # 数据库会自动加载该机型的功率曲线等参数

    enercon_e126 = {
        "turbine_type": "E-126/4200",  # 涡轮机型号（需与数据库中的名称匹配）
        "hub_height": 135,  # 轮毂高度，单位：米
    }
    e126 = WindTurbine(**enercon_e126)

    # ************************************************************************
    # **** 方法二：自定义功率曲线 ********************************************
    # 注意：功率值和额定功率必须以瓦特（W）为单位

    my_turbine = {
        "nominal_power": 3e6,  # 额定功率，单位：W（3 MW）
        "hub_height": 105,  # 轮毂高度，单位：m
        # 功率曲线：风速与输出功率的对应关系
        # power_curve 是一个 DataFrame，包含 'wind_speed' 和 'value' 两列
        "power_curve": pd.DataFrame(
            data={
                "value": [
                    p * 1000
                    for p in [0.0, 26.0, 180.0, 1500.0, 3000.0, 3000.0]
                ],  # 功率值，单位：W
                "wind_speed": [0.0, 3.0, 5.0, 10.0, 15.0, 25.0],  # 风速，单位：m/s
            }
        ),
    }
    my_turbine = WindTurbine(**my_turbine)

    # ************************************************************************
    # **** 方法三：从文件读取数据 *********************************************
    # 实际应用中，可以使用 pandas.read_csv() 从文件读取数据
    # >>> import pandas as pd
    # >>> my_data = pd.read_csv("path/to/my/data/file")
    # >>> my_power = my_data["my_power"]
    # >>> my_wind_speed = my_data["my_wind_speed"]

    # 这里使用示例数据模拟从文件读取
    my_power = pd.Series(
        [0.0, 39000.0, 270000.0, 2250000.0, 4500000.0, 4500000.0]
    )
    my_wind_speed = (0.0, 3.0, 5.0, 10.0, 15.0, 25.0)

    # 使用 create_power_curve 函数创建功率曲线
    my_turbine2 = {
        "nominal_power": 6e6,  # 额定功率，单位：W（6 MW）
        "hub_height": 115,  # 轮毂高度，单位：m
        "power_curve": create_power_curve(
            wind_speed=my_wind_speed, power=my_power
        ),
    }
    my_turbine2 = WindTurbine(**my_turbine2)

    return my_turbine, e126, my_turbine2


def calculate_power_output(weather, my_turbine, e126, my_turbine2):
    r"""
    使用 ModelChain 计算风力发电机的功率输出。

    ModelChain 是 windpowerlib 的核心类，它封装了完整的功率计算流程：

    计算流程图：
    ============
    气象数据 → 风速修正 → 密度计算 → 温度修正 → 功率计算 → 输出

    ModelChain 的关键参数：
    ======================
    wind_speed_model : str
        风速修正模型，将测量高度的风速转换到轮毂高度
        - 'logarithmic': 对数风廓线（默认），适用于中性大气条件
        - 'hellman': Hellman 幂律模型，简单但精度较低
        - 'interpolation_extrapolation': 多高度测量值插值

    density_model : str
        空气密度计算模型
        - 'barometric': 气压计公式（默认）
        - 'ideal_gas': 理想气体状态方程
        - 'interpolation_extrapolation': 插值法

    temperature_model : str
        温度修正模型
        - 'linear_gradient': 线性温度递减率（默认，约-6.5K/km）
        - 'interpolation_extrapolation': 插值法

    power_output_model : str
        功率输出计算方法
        - 'power_curve': 直接使用功率曲线（默认）
        - 'power_coefficient_curve': 使用功率系数曲线计算

    density_correction : bool
        是否根据空气密度变化修正功率输出
        - False: 不修正（默认）
        - True: 根据实际密度修正（推荐用于高精度计算）

    obstacle_height : float
        障碍物高度，用于风速修正，单位：m

    hellman_exp : float
        Hellman 指数，用于 Hellman 风速模型

    Parameters
    ----------
    weather : :pandas:`pandas.DataFrame<frame>`
        气象数据时间序列
    my_turbine : :class:`~.wind_turbine.WindTurbine`
        自定义功率曲线的风力发电机
    e126 : :class:`~.wind_turbine.WindTurbine`
        使用 oedb 数据库的 Enercon E126 风机
    my_turbine2 : :class:`~.wind_turbine.WindTurbine`
        从文件数据创建的风力发电机
    """

    # ************************************************************************
    # **** ModelChain 示例一：自定义所有参数 **********************************
    # 这里展示了如何配置 ModelChain 的各个参数
    modelchain_data = {
        # 风速模型：使用对数风廓线模型
        # 对数模型考虑了地表粗糙度，是较精确的风速修正方法
        "wind_speed_model": "logarithmic",  # 可选: 'logarithmic'(默认), 'hellman', 'interpolation_extrapolation'

        # 密度模型：使用理想气体定律
        # 空气密度影响风能密度，进而影响功率输出
        "density_model": "ideal_gas",  # 可选: 'barometric'(默认), 'ideal_gas', 'interpolation_extrapolation'

        # 温度模型：线性梯度
        # 温度随高度变化，影响空气密度计算
        "temperature_model": "linear_gradient",  # 可选: 'linear_gradient'(默认), 'interpolation_extrapolation'

        # 功率输出模型：使用功率系数曲线
        # 功率系数曲线描述了风机效率随风速的变化
        "power_output_model": "power_coefficient_curve",  # 可选: 'power_curve'(默认), 'power_coefficient_curve'

        # 密度修正：开启
        # 根据实际空气密度修正功率输出，提高计算精度
        "density_correction": True,  # 默认 False

        # 障碍物高度：0米（无障碍物影响）
        "obstacle_height": 0,  # 默认: 0

        # Hellman 指数：使用默认值
        # 仅当 wind_speed_model='hellman' 时有效
        "hellman_exp": None,  # 默认: None
    }

    # 初始化 ModelChain 并运行模型
    # ModelChain 的构造函数接受 WindTurbine 对象和配置参数
    # run_model() 方法执行完整的计算流程
    mc_e126 = ModelChain(e126, **modelchain_data).run_model(weather)

    # 将计算得到的功率输出保存到 WindTurbine 对象
    # power_output 是一个时间序列，单位为瓦特（W）
    e126.power_output = mc_e126.power_output

    # ************************************************************************
    # **** ModelChain 示例二：使用默认参数 ************************************
    # 默认配置适用于大多数标准计算场景
    # 默认使用: logarithmic风速模型 + barometric密度模型 + power_curve功率曲线
    mc_my_turbine = ModelChain(my_turbine).run_model(weather)
    my_turbine.power_output = mc_my_turbine.power_output

    # ************************************************************************
    # **** ModelChain 示例三：仅修改部分参数 **********************************
    # 可以只指定需要修改的参数，其他使用默认值
    # 这里仅修改风速模型为 Hellman 模型
    mc_example_turbine = ModelChain(
        my_turbine2, wind_speed_model="hellman"
    ).run_model(weather)
    my_turbine2.power_output = mc_example_turbine.power_output

    return


def plot_or_print(my_turbine, e126, my_turbine2):
    r"""
    绘制或打印功率输出和功率曲线。

    本函数展示如何访问 WindTurbine 对象的计算结果：
    - power_output: 功率输出时间序列
    - power_curve: 功率曲线（风速-功率关系）
    - power_coefficient_curve: 功率系数曲线

    Parameters
    ----------
    my_turbine : :class:`~.wind_turbine.WindTurbine`
        自定义功率曲线的风力发电机
    e126 : :class:`~.wind_turbine.WindTurbine`
        使用 oedb 数据库的 Enercon E126 风机
    my_turbine2 : :class:`~.wind_turbine.WindTurbine`
        从文件数据创建的风力发电机
    """

    # 绘制或打印功率输出时间序列
    if plt:
        # 使用 matplotlib 绘制三条功率曲线
        e126.power_output.plot(legend=True, label="Enercon E126")
        my_turbine.power_output.plot(legend=True, label="myTurbine")
        my_turbine2.power_output.plot(legend=True, label="myTurbine2")
        plt.xlabel("Time")
        plt.ylabel("Power in W")
        plt.show()
    else:
        # 如果没有 matplotlib，直接打印数据
        print(e126.power_output)
        print(my_turbine.power_output)
        print(my_turbine2.power_output)

    # 绘制或打印功率曲线
    # 功率曲线显示了风速与输出功率的关系
    if plt:
        if e126.power_curve is not False:
            e126.power_curve.plot(
                x="wind_speed",
                y="value",
                style="*",
                title="Enercon E126 power curve",
            )
            plt.xlabel("Wind speed in m/s")
            plt.ylabel("Power in W")
            plt.show()
        if my_turbine.power_curve is not False:
            my_turbine.power_curve.plot(
                x="wind_speed",
                y="value",
                style="*",
                title="myTurbine power curve",
            )
            plt.xlabel("Wind speed in m/s")
            plt.ylabel("Power in W")
            plt.show()
        if my_turbine2.power_curve is not False:
            my_turbine2.power_curve.plot(
                x="wind_speed",
                y="value",
                style="*",
                title="myTurbine2 power curve",
            )
            plt.xlabel("Wind speed in m/s")
            plt.ylabel("Power in W")
            plt.show()
    else:
        if e126.power_coefficient_curve is not False:
            print(e126.power_coefficient_curve)
        if e126.power_curve is not False:
            print(e126.power_curve)


def run_example(start=None, end=None):
    r"""
    运行完整示例。

    执行流程：
    1. 配置日志级别
    2. 获取气象数据
    3. 初始化风力发电机
    4. 计算功率输出
    5. 显示结果

    Parameters
    ----------
    start : str or datetime-like, optional
        数据开始时间。例如: '2010-01-01'
        默认为 None，使用数据集的最早时间。
    end : str or datetime-like, optional
        数据结束时间。例如: '2010-12-31'
        默认为 None，使用数据集的最晚时间。

    Examples
    --------
    运行完整数据集：
    >>> run_example()

    运行2010年1月的数据：
    >>> run_example(start='2010-01-01', end='2010-01-31')

    运行指定时间范围：
    >>> run_example(start='2010-06-01', end='2010-06-30')
    """
    # 配置日志级别以获取 windpowerlib 的运行信息
    # logging.DEBUG -> 详细调试信息
    # logging.INFO -> 关键信息
    logging.getLogger().setLevel(logging.DEBUG)

    # 步骤1：获取气象数据（可指定时间范围）
    weather = get_weather_data("weather.csv", start=start, end=end)

    # 打印数据时间范围信息
    print(f"数据时间范围: {weather.index[0]} 至 {weather.index[-1]}")
    print(f"数据点数量: {len(weather)}")

    # 步骤2：初始化风力发电机
    my_turbine, e126, my_turbine2 = initialize_wind_turbines()

    # 步骤3：使用 ModelChain 计算功率输出
    calculate_power_output(weather, my_turbine, e126, my_turbine2)

    # 步骤4：显示结果
    plot_or_print(my_turbine, e126, my_turbine2)


if __name__ == "__main__":
    # 示例：计算2010年6月的功率输出
    # 修改下面的时间范围来计算不同时期的数据
    # run_example()  # 使用完整数据集
    run_example(start='2010-06-01', end='2010-06-01')  # 使用指定时间范围
