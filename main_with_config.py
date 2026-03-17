from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from config.config_manager import load_config
import pandas as pd
from plot_comparison import plot_comparison

# 加载配置（自动从示例创建）
config = load_config(auto_create=True)

# 从配置中获取参数
area = config['system']['area']
location_params = config['location']
time_params = config['time_range']
weather_params = config['weather']
system_params = config['system_config']
economics_params = config['economics']

# 调用 Solar 函数（使用配置参数）
Solar = area * getsolar(
    lat=location_params['lat'],
    lon=location_params['lon'],
    tz=location_params['tz'],
    altitude=location_params['altitude'],
    name=location_params['name'],
    start=time_params['start'],
    end=time_params['end'],
    freq=time_params['freq'],
    temp_air=weather_params['temp_air'],
    wind_speed=weather_params['wind_speed'],
    surface_tilt=system_params['surface_tilt'],
    surface_azimuth=system_params['surface_azimuth'],
    temp_a=system_params['temperature_model']['a'],
    temp_b=system_params['temperature_model']['b'],
    temp_deltaT=system_params['temperature_model']['deltaT']
) / 1000

# 获取用电数据
Consumption = getconsumption()

# 创建 DataFrame
data = pd.DataFrame({
    'Solar': Solar.values,
    'Consumption': Consumption.values,
    'Energy Balance': Consumption.values - Solar.values
}, index=Solar.index)

# 计算日成本
Electricity = data['Energy Balance'].clip(lower=0)
ElectricityPrice = economics_params['electricity_price']
cost = sum(Electricity * ElectricityPrice) / 4
print(f"成本为: {cost} 元/天")

# 绘制图表
plot_comparison(data)