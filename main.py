from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from Storage.Storage import simulate_storage
from config.config_manager import load_electricity_price
import pandas as pd
from plot_comparison import plot_comparison

freconvert = 60 / 15  # 15分钟频率的折算因子

# 加载电价配置
economics_config = load_electricity_price()

# 调用 Solar 函数（自动从配置文件获取参数并计算）
Solar = getsolar()

# 获取用电数据
Consumption = getconsumption()

# 创建 DataFrame
data = pd.DataFrame({
    'Solar': Solar.values,
    'Consumption': Consumption.values,
    'Energy Balance': Consumption.values - Solar.values
}, index=Solar.index)

# 储能系统
storage_power, soc = simulate_storage(data['Energy Balance'], freq_minutes=15)
data['Storage Power'] = storage_power.values
data['SOC'] = soc.values

# 计算储能后的净负荷
data['Net Load'] = data['Energy Balance'] + data['Storage Power']

# 计算日成本（使用独立的电价配置）
Electricity = data['Net Load'].clip(lower=0)
ElectricityPrice = economics_config['electricity_price']
cost = sum(Electricity * ElectricityPrice) / freconvert
print(f"成本为: {cost} 元/天")

# 绘制图表
plot_comparison(data, ifsave=True)