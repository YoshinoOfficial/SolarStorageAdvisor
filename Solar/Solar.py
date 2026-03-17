import pvlib
import pandas as pd
from pvlib.location import Location
from pvlib.pvsystem import PVSystem, Array, FixedMount
from pvlib.modelchain import ModelChain

def getsolar(lat=39.9, lon=116.4, tz='Asia/Shanghai', altitude=44, name='Beijing', start='2024-06-21', end='2024-06-22', freq='15min',temp_air=30, wind_speed=2, surface_tilt=30, surface_azimuth=180, temp_a=-3.56, temp_b=-0.075, temp_deltaT=3):
    
    # --- 第一步：定义地理位置 (北京) ---
    #lat, lon = 39.9, 116.4
    #tz = 'Asia/Shanghai'
    #altitude = 44
    site = Location(latitude=lat, longitude=lon, tz=tz, altitude=altitude, name=name)
    
    # --- 第二步：构造“晴朗天空”时间序列 ---
    # 我们模拟 2024 年 6 月 21 日（夏至）这一天，每 15 分钟一个数据点
    times = pd.date_range(start=start, end=end, freq=freq, tz=tz)

    # 获取晴空辐射数据 (GHI, DNI, DHI)
    clearsky = site.get_clearsky(times)

    # 整合进 weather 数据库，并补上环境温度和风速
    weather = pd.DataFrame({
        'ghi': clearsky['ghi'],
        'dni': clearsky['dni'],
        'dhi': clearsky['dhi'],
        'temp_air': temp_air,    # 假设夏日气温 30°C
        'wind_speed': wind_speed    # 假设微风 2 m/s
    }, index=times)

    # --- 第三步：定义硬件 (组件和逆变器) ---
    # 从内置数据库随便“白嫖”两款经典型号
    sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
    module_params = sandia_modules['Canadian_Solar_CS5P_220M___2009_'] # 阿特斯 220W 组件

    cec_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
    inverter_params = cec_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_'] # ABB 微逆

    # --- 第四步：构建电站系统 ---
    # 支架设为 30 度倾角，面向正南 (180度)
    mount = FixedMount(surface_tilt=surface_tilt, surface_azimuth=surface_azimuth)
    array = Array(mount=mount, module_parameters=module_params, temperature_model_parameters={'a': temp_a, 'b': temp_b, 'deltaT': temp_deltaT})
    system = PVSystem(arrays=[array], inverter_parameters=inverter_params)

    # --- 第五步：运行模拟链 ---
    mc = ModelChain(system, site)
    mc.run_model(weather)

    # --- 第六步：查看结果并绘图 ---
    #print("模拟完成！当日最大 AC 输出功率为: ", mc.results.ac.max(), "W/平方米")

    # 绘图展示
    '''
    mc.results.ac.plot(figsize=(10, 6), title='Summer Solstice Clear Sky Power Output (Beijing)')
    plt.ylabel('AC Power Output (Watts)')
    plt.xlabel('Time of Day')
    plt.grid(True)
    plt.show(block=False)
    plt.pause(2)
    plt.close()
    '''
    return mc.results.ac




