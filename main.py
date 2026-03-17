from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
import pandas as pd
from plot_comparison import plot_comparison

# 定义系统参数
area = 1000  # 假设系统面积为 1000 平方米
Solar = area * getsolar() / 1000  # 转换为 kW/平方米，再乘上面积
#print(Solar.values)

Consumption = getconsumption()
#print(Consumption)

# 创建 DataFrame
data = pd.DataFrame({
    'Solar': Solar.values,
    'Consumption': Consumption.values,
    'Energy Balance': Consumption.values - Solar.values  # 能量差额：正值需要购电，负值可售电
}, index=Solar.index)

# 计算日成本
Electricity = data['Energy Balance'].clip(lower=0)  # 只保留正值，负值设为0
ElectricityPrice = 1  # 假设电价为 1 元/千瓦时
cost = sum(Electricity * ElectricityPrice)/4 # 计算成本,除以4是因为15分钟间隔
print("成本为: ", cost, "元/天")



plot_comparison(data)
