# pvlib 库使用指南

## 简介

pvlib 是一个用于光伏系统建模和仿真的 Python 库，提供了完整的太阳能发电系统模拟功能，包括辐射计算、组件性能建模、温度模型等。

## 快速开始 - 使用封装函数

本项目提供了两个封装好的函数，可以快速进行太阳能发电模拟：

### 1. getsolar() - 使用 Array 对象（需要指定温度模型参数）

```python
from Solar.Solar import getsolar

# 使用默认参数
Solar = getsolar()

# 自定义参数
Solar = getsolar(
    lat=39.9,                    # 纬度
    lon=116.4,                   # 经度
    tz='Asia/Shanghai',          # 时区
    altitude=44,                 # 海拔（米）
    name='Beijing',              # 位置名称
    start='2024-06-21',          # 开始日期
    end='2024-06-22',            # 结束日期
    freq='15min',                # 时间频率
    temp_air=30,                 # 环境温度（°C）
    wind_speed=2,                # 风速（m/s）
    surface_tilt=30,             # 倾角（度）
    surface_azimuth=180,          # 方位角（度，180=正南）
    temp_a=-3.56,                # 温度模型参数 a
    temp_b=-0.075,               # 温度模型参数 b
    temp_deltaT=3                # 温度模型参数 deltaT
)
```

### 2. getsolar_auto() - 自动推断温度模型（推荐）

```python
from Solar.Solar_auto import getsolar_auto

# 使用默认参数
Solar_auto = getsolar_auto()

# 自定义参数
Solar_auto = getsolar_auto(
    lat=39.9,                    # 纬度
    lon=116.4,                   # 经度
    tz='Asia/Shanghai',          # 时区
    altitude=44,                 # 海拔（米）
    name='Beijing',              # 位置名称
    start='2024-06-21',          # 开始日期
    end='2024-06-22',            # 结束日期
    freq='15min',                # 时间频率
    temp_air=30,                 # 环境温度（°C）
    wind_speed=2,                # 风速（m/s）
    surface_tilt=30,             # 倾角（度）
    surface_azimuth=180,          # 方位角（度，180=正南）
    racking_model='open_rack',   # 支架类型
    module_type='glass_polymer'   # 组件类型
)
```

### 两个函数的区别

- **getsolar()**: 使用 `Array` 对象构建系统，需要手动指定温度模型参数（`temp_a`, `temp_b`, `temp_deltaT`）
- **getsolar_auto()**: 直接在 `PVSystem` 上设置，通过 `racking_model` 和 `module_type` 自动推断温度模型（推荐使用）

两个函数的计算结果相同，但 `getsolar_auto()` 更简洁，无需手动指定温度模型参数。

### 函数返回值

两个函数都返回 `mc.results.ac`，即交流输出功率的时间序列数据（pandas Series）。

## 需要的数据

### 1. 地理位置数据
- **纬度** (latitude): 地理纬度，单位：度
- **经度** (longitude): 地理经度，单位：度  
- **时区** (timezone): 时区标识符，如 'Asia/Shanghai'
- **海拔** (altitude): 海拔高度，单位：米

### 2. 气象数据
- **GHI** (Global Horizontal Irradiance): 水平面总辐射，单位：W/m²
- **DNI** (Direct Normal Irradiance): 法向直接辐射，单位：W/m²
- **DHI** (Diffuse Horizontal Irradiance): 水平面散射辐射，单位：W/m²
- **环境温度** (temp_air): 环境温度，单位：°C
- **风速** (wind_speed): 风速，单位：m/s

> **提示**: 如果使用晴空模型 (clearsky)，可以通过 `site.get_clearsky(times)` 方法自动获取 GHI、DNI、DHI 数据，无需手动提供。

### 3. 光伏组件参数
- 从 SAM 数据库获取或使用厂商提供的参数
- 包括：开路电压、短路电流、最大功率点电压/电流等

### 4. 逆变器参数
- 从 SAM 数据库获取或使用厂商提供的参数
- 包括：最大交流功率、效率曲线等

## 基本使用步骤

### 步骤 1: 定义地理位置

```python
from pvlib.location import Location

site = Location(
    latitude=39.9,           # 北京纬度
    longitude=116.4,         # 北京经度
    tz='Asia/Shanghai',      # 时区
    altitude=44,             # 海拔
    name='Beijing'          # 位置名称
)
```

### 步骤 2: 准备时间序列和天气数据

```python
import pandas as pd

# 创建时间序列
times = pd.date_range(
    start='2024-06-21', 
    end='2024-06-22', 
    freq='15min', 
    tz='Asia/Shanghai'
)

# 获取晴空辐射数据
clearsky = site.get_clearsky(times)

# 构建天气数据
weather = pd.DataFrame({
    'ghi': clearsky['ghi'],
    'dni': clearsky['dni'],
    'dhi': clearsky['dhi'],
    'temp_air': 30,        # 环境温度
    'wind_speed': 2        # 风速
}, index=times)
```

### 步骤 3: 获取组件和逆变器参数

```python
import pvlib

# 从 SAM 数据库获取组件参数
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module_params = sandia_modules['Canadian_Solar_CS5P_220M___2009_']

# 从 SAM 数据库获取逆变器参数
cec_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
inverter_params = cec_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']
```

### 步骤 4: 构建光伏系统

#### 方法 1: 直接在 PVSystem 上设置（推荐，可自动推断温度模型）

```python
from pvlib.pvsystem import PVSystem

system = PVSystem(
    surface_tilt=30,                    # 倾角
    surface_azimuth=180,               # 方位角（180度=正南）
    module_parameters=module_params,
    inverter_parameters=inverter_params,
    racking_model='open_rack',         # 支架类型
    module_type='glass_polymer'        # 组件类型
)
```

#### 方法 2: 使用 Array 对象（需要显式指定温度模型）

```python
from pvlib.pvsystem import PVSystem, Array, FixedMount

mount = FixedMount(surface_tilt=30, surface_azimuth=180)
array = Array(
    mount=mount,
    module_parameters=module_params,
    temperature_model_parameters={'a': -3.56, 'b': -0.075, 'deltaT': 3}
)
system = PVSystem(arrays=[array], inverter_parameters=inverter_params)
```

### 步骤 5: 创建并运行模拟链

```python
from pvlib.modelchain import ModelChain

# 创建模拟链
mc = ModelChain(system, site)

# 运行模拟
mc.run_model(weather)
```

### 步骤 6: 获取和分析结果

```python
# 获取交流输出功率
ac_power = mc.results.ac

# 查看最大输出功率
max_power = ac_power.max()
print(f"当日最大 AC 输出功率为: {max_power} W")

# 绘制功率曲线
import matplotlib.pyplot as plt
ac_power.plot(figsize=(10, 6), title='Power Output')
plt.ylabel('AC Power Output (Watts)')
plt.xlabel('Time of Day')
plt.grid(True)
plt.show()
```

## 计算结果

### 主要输出数据

1. **AC 输出功率** (`mc.results.ac`): 逆变器输出的交流功率
2. **DC 输出功率** (`mc.results.dc`): 光伏组件产生的直流功率
3. **组件温度** (`mc.results.cell_temperature`): 光伏组件的工作温度
4. **有效辐照度** (`mc.results.effective_irradiance`): 组件表面的有效辐照度

### 其他可用结果

- `mc.results.aoi_modifier`: 入射角修正因子
- `mc.results.spectral_mismatch`: 光谱失配因子
- `mc.results.losses`: 各种损失因子

## 温度模型说明

### 自动推断（推荐）
当使用方法 1（直接在 PVSystem 上设置）时，通过指定 `racking_model` 和 `module_type`，pvlib 会自动选择合适的温度模型参数。

**可用的 racking_model 值:**
- `'open_rack'`: 开放式支架
- `'close_mount'`: 紧贴安装
- `'insulated_back'`: 绝缘背面

**可用的 module_type 值:**
- `'glass_polymer'`: 玻璃聚合物组件
- `'glass_glass'`: 双玻璃组件
- `'other'`: 其他类型

### 显式指定
当使用方法 2（Array 对象）时，需要手动指定温度模型参数：

```python
temperature_model_parameters = {
    'a': -3.56,      # 热损失系数
    'b': -0.075,     # 风速影响系数
    'deltaT': 3      # 温度修正值
}
```

## 实际应用示例

### 完整示例代码

```python
import pvlib
import pandas as pd
import matplotlib.pyplot as plt
from pvlib.location import Location
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain

# 1. 定义位置
site = Location(latitude=39.9, longitude=116.4, tz='Asia/Shanghai', altitude=44, name='Beijing')

# 2. 准备天气数据
times = pd.date_range(start='2024-06-21', end='2024-06-22', freq='15min', tz='Asia/Shanghai')
clearsky = site.get_clearsky(times)
weather = pd.DataFrame({
    'ghi': clearsky['ghi'],
    'dni': clearsky['dni'],
    'dhi': clearsky['dhi'],
    'temp_air': 30,
    'wind_speed': 2
}, index=times)

# 3. 获取硬件参数
sandia_modules = pvlib.pvsystem.retrieve_sam('SandiaMod')
module_params = sandia_modules['Canadian_Solar_CS5P_220M___2009_']
cec_inverters = pvlib.pvsystem.retrieve_sam('cecinverter')
inverter_params = cec_inverters['ABB__MICRO_0_25_I_OUTD_US_208__208V_']

# 4. 构建系统
system = PVSystem(
    surface_tilt=30,
    surface_azimuth=180,
    module_parameters=module_params,
    inverter_parameters=inverter_params,
    racking_model='open_rack',
    module_type='glass_polymer'
)

# 5. 运行模拟
mc = ModelChain(system, site)
mc.run_model(weather)

# 6. 分析结果
print(f"当日最大 AC 输出功率为: {mc.results.ac.max()} W")
mc.results.ac.plot(figsize=(10, 6), title='Summer Solstice Clear Sky Power Output (Beijing)')
plt.ylabel('AC Power Output (Watts)')
plt.xlabel('Time of Day')
plt.grid(True)
plt.show()
```

## 常见问题

### 1. 如何获取真实天气数据？
- 可以使用气象站数据
- 使用卫星数据服务（如 NASA、PVGIS）
- 使用 pvlib 的 iotools 模块读取各种格式数据

### 2. 如何处理多云天气？
- 使用实际观测的 GHI、DNI、DHI 数据
- 或者使用云量数据修正晴空模型

### 3. 如何模拟多组件阵列？
- 使用 Array 对象创建多个阵列
- 或者调整模块参数中的数量

### 4. 温度模型参数如何选择？
- 优先使用厂商提供的参数
- 或者使用标准值（如示例中的参数）

## 参考资料

- pvlib 官方文档: https://pvlib-python.readthedocs.io/
- SAM 数据库: https://sam.nrel.gov/
- PVGIS: https://re.jrc.ec.europa.eu/pvg_tools/en/