from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from config.config_manager import (
    load_panel_by_id,
    list_available_panels,
    get_current_panel_id,
    set_current_panel_id,
    load_electricity_price
)
import pandas as pd
from plot_comparison import plot_comparison

# 示例 1: 列出所有可用的光伏板
print("=== 可用的光伏板 ===")
panels = list_available_panels()
for panel in panels:
    print(f"ID: {panel['id']}")
    print(f"名称: {panel['name']}")
    print(f"描述: {panel['description']}")
    print(f"文件: {panel['file']}")
    print("-" * 50)

# 示例 2: 获取当前使用的光伏板
print(f"\n=== 当前光伏板 ===")
current_panel_id = get_current_panel_id()
print(f"当前光伏板 ID: {current_panel_id}")

# 示例 3: 切换到不同的光伏板
print("\n=== 切换光伏板 ===")
new_panel_id = 'panel_trina'
set_current_panel_id(new_panel_id)

# 示例 4: 加载指定光伏板的配置
print("\n=== 加载光伏板配置 ===")
panel_config = load_panel_by_id(new_panel_id)
print(f"光伏板名称: {panel_config['name']}")
print(f"制造商: {panel_config['manufacturer']}")
print(f"型号: {panel_config['model']}")
print(f"系统面积: {panel_config['system']['area']} 平方米")

# 示例 5: 加载电价配置
print("\n=== 电价配置 ===")
economics_config = load_electricity_price()
print(f"电价: {economics_config['electricity_price']} 元/千瓦时")
print(f"最后更新: {economics_config['last_updated']}")

# 示例 6: 使用配置运行模拟
print("\n=== 运行模拟 ===")
area = panel_config['system']['area']
location_params = panel_config['location']
time_params = panel_config['time_range']
weather_params = panel_config['weather']
system_params = panel_config['system_config']

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

Consumption = getconsumption()

data = pd.DataFrame({
    'Solar': Solar.values,
    'Consumption': Consumption.values,
    'Energy Balance': Consumption.values - Solar.values
}, index=Solar.index)

Electricity = data['Energy Balance'].clip(lower=0)
ElectricityPrice = economics_config['electricity_price']
cost = sum(Electricity * ElectricityPrice) / 4
print(f"成本为: {cost} 元/天")

plot_comparison(data)