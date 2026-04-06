# 配置管理使用指南

## 目录

- [文件结构](#文件结构)
- [config_manager.py 功能介绍](#config_managerpy-功能介绍)
- [基础配置管理](#基础配置管理)
- [光伏板管理](#光伏板管理)
- [电价管理](#电价管理)
- [储能管理](#储能管理)
- [完整示例](#完整示例)

---

## 文件结构

```
config/
├── config_manager.py                    # 配置管理工具
├── economics/                          # 经济相关文件夹
│   ├── electricity_price.json           # 电价配置
│   └── electricity_price.json.example   # 电价配置示例
├── solar/                             # 光伏相关文件夹
│   ├── panels_list.json                 # 光伏板列表索引
│   ├── panels_list.json.example         # 光伏板列表示例
│   └── panels/                         # 各个光伏板的配置
│       ├── panel_canadian_solar.json   # 板子 1: Canadian Solar
│       ├── panel_trina.json            # 板子 2: Trina Solar
│       └── panel_jinko.json            # 板子 3: Jinko Solar
└── Storage/                           # 储能相关文件夹
    ├── storage_list.json               # 储能列表索引
    ├── storage_list.json.example       # 储能列表示例
    └── configs/                        # 储能配置文件夹
        ├── storage_small.json          # 小型储能配置
        ├── storage_small.json.example  # 小型储能配置示例
        ├── storage_medium.json         # 中型储能配置
        ├── storage_medium.json.example # 中型储能配置示例
        ├── storage_large.json          # 大型储能配置
        └── storage_large.json.example  # 大型储能配置示例
```

### 文件说明

| 文件 | 说明 | 是否提交到 Git |
|------|------|---------------|
| `config_manager.py` | 配置管理工具，提供加载、保存等功能 | ✅ 是 |
| `economics/electricity_price.json` | 电价配置文件 | ❌ 否 |
| `economics/electricity_price.json.example` | 电价配置示例 | ✅ 是 |
| `solar/panels_list.json` | 光伏板列表索引 | ❌ 否 |
| `solar/panels_list.json.example` | 光伏板列表示例 | ✅ 是 |
| `solar/panels/*.json` | 各个光伏板的详细配置 | ❌ 否 |
| `Storage/storage_list.json` | 储能列表索引 | ❌ 否 |
| `Storage/storage_list.json.example` | 储能列表示例 | ✅ 是 |
| `Storage/configs/*.json` | 各个储能系统的详细配置 | ❌ 否 |

---

## config_manager.py 功能介绍

### 基础函数

#### `load_config(config_path='config/solar_config.json', auto_create=True)`

加载配置文件，支持自动从示例创建。

**参数**:
- `config_path`: 配置文件路径
- `auto_create`: 如果配置文件不存在，是否自动从示例创建

**返回**:
- `dict`: 配置字典

**示例**:
```python
from config.config_manager import load_config

# 加载默认配置
config = load_config()

# 加载指定配置
config = load_config('config/solar/panels/panel_canadian_solar.json')

# 不自动创建配置
config = load_config('config/solar/panels/panel_canadian_solar.json', auto_create=False)
```

---

#### `save_config(config, config_path='config/solar_config.json')`

保存配置文件。

**参数**:
- `config`: 配置字典
- `config_path`: 配置文件路径

**示例**:
```python
from config.config_manager import save_config

config = {
    'system': {'area': 1000},
    'location': {'lat': 39.9, 'lon': 116.4}
}

save_config(config, 'config/my_config.json')
```

---

#### `create_config_from_example(config_path='config/solar_config.json')`

从示例文件创建配置文件。

**参数**:
- `config_path`: 目标配置文件路径

**返回**:
- `dict`: 创建的配置字典

**示例**:
```python
from config.config_manager import create_config_from_example

# 从示例创建配置
config = create_config_from_example('config/solar/panels/panel_new.json')
```

---

### 光伏板管理函数

#### `load_panel_by_id(panel_id)`

通过板子 ID 加载光伏板配置。

**参数**:
- `panel_id`: 光伏板 ID

**返回**:
- `dict`: 光伏板配置字典

**示例**:
```python
from config.config_manager import load_panel_by_id

# 加载指定光伏板
panel_config = load_panel_by_id('panel_canadian_solar')
print(f"光伏板名称: {panel_config['name']}")
print(f"系统面积: {panel_config['system']['area']} 平方米")
```

---

#### `list_available_panels()`

列出所有可用的光伏板。

**返回**:
- `list`: 光伏板信息列表

**示例**:
```python
from config.config_manager import list_available_panels

# 列出所有光伏板
panels = list_available_panels()
for panel in panels:
    print(f"ID: {panel['id']}")
    print(f"名称: {panel['name']}")
    print(f"描述: {panel['description']}")
    print(f"文件: {panel['file']}")
    print("-" * 50)
```

---

#### `get_panel_quantities()`

获取所有光伏板的数量配置。

**返回**:
- `dict`: 光伏板ID到数量的映射，如 `{"panel_canadian_solar": 10, "panel_trina": 5}`

**示例**:
```python
from config.config_manager import get_panel_quantities

# 获取光伏板数量配置
quantities = get_panel_quantities()
for panel_id, quantity in quantities.items():
    print(f"{panel_id}: {quantity} 块")
```

---

#### `set_panel_quantities(quantities_dict)`

批量设置光伏板数量配置。

**参数**:
- `quantities_dict`: 光伏板ID到数量的映射字典

**示例**:
```python
from config.config_manager import set_panel_quantities

# 批量设置光伏板数量
set_panel_quantities({
    "panel_canadian_solar": 20,
    "panel_trina": 10,
    "panel_jinko": 5
})
```

---

#### `set_panel_quantity(panel_id, quantity)`

设置单个光伏板的数量。

**参数**:
- `panel_id`: 光伏板 ID
- `quantity`: 数量（块数）

**示例**:
```python
from config.config_manager import set_panel_quantity

# 设置单个光伏板数量
set_panel_quantity("panel_canadian_solar", 15)
```

---

#### `get_current_panel_id()` （已废弃）

获取当前使用的光伏板 ID。

> **注意**: 此函数已废弃，保留仅为向后兼容。推荐使用 `get_panel_quantities()` 获取光伏板配置。

**返回**:
- `str`: 光伏板 ID

**示例**:
```python
from config.config_manager import get_current_panel_id

# 获取当前光伏板（已废弃）
current_id = get_current_panel_id()
print(f"当前光伏板 ID: {current_id}")
```

---

#### `set_current_panel_id(panel_id)` （已废弃）

设置当前使用的光伏板 ID。

> **注意**: 此函数已废弃，保留仅为向后兼容。推荐使用 `set_panel_quantity()` 或 `set_panel_quantities()` 设置光伏板数量。

**参数**:
- `panel_id`: 光伏板 ID

**示例**:
```python
from config.config_manager import set_current_panel_id

# 切换到不同的光伏板（已废弃）
set_current_panel_id('panel_trina')
```

---

### 电价管理函数

#### `load_electricity_price()`

加载电价配置。

**返回**:
- `dict`: 电价配置字典

**示例**:
```python
from config.config_manager import load_electricity_price

# 加载电价配置
economics_config = load_electricity_price()
print(f"电价: {economics_config['electricity_price']} 元/千瓦时")
print(f"最后更新: {economics_config['last_updated']}")
```

---

#### `save_electricity_price(electricity_price)`

保存电价配置。

**参数**:
- `electricity_price`: 电价（元/千瓦时）

**示例**:
```python
from config.config_manager import save_electricity_price

# 修改电价
save_electricity_price(1.2)  # 设置电价为 1.2 元/千瓦时
```

---

### 储能管理函数

#### `load_storage_config()`

加载当前储能配置。

**返回**:
- `dict`: 储能配置字典

**示例**:
```python
from config.config_manager import load_storage_config

# 加载当前储能配置
storage_config = load_storage_config()
print(f"储能容量: {storage_config['capacity']} kWh")
print(f"最大充电功率: {storage_config['max_charge_power']} kW")
print(f"最大放电功率: {storage_config['max_discharge_power']} kW")
print(f"充电效率: {storage_config['charge_efficiency']}")
print(f"放电效率: {storage_config['discharge_efficiency']}")
```

---

#### `load_storage_by_id(storage_id)`

通过储能 ID 加载储能配置。

**参数**:
- `storage_id`: 储能 ID

**返回**:
- `dict`: 储能配置字典

**示例**:
```python
from config.config_manager import load_storage_by_id

# 加载指定储能配置
storage_config = load_storage_by_id('storage_medium')
print(f"储能容量: {storage_config['capacity']} kWh")
```

---

#### `list_available_storages()`

列出所有可用的储能系统。

**返回**:
- `list`: 储能系统信息列表

**示例**:
```python
from config.config_manager import list_available_storages

# 列出所有储能系统
storages = list_available_storages()
for storage in storages:
    print(f"ID: {storage['id']}")
    print(f"名称: {storage['name']}")
    print(f"描述: {storage['description']}")
    print(f"文件: {storage['file']}")
    print("-" * 50)
```

---

#### `get_current_storage_id()`

获取当前使用的储能 ID。

**返回**:
- `str`: 储能 ID

**示例**:
```python
from config.config_manager import get_current_storage_id

# 获取当前储能
current_id = get_current_storage_id()
print(f"当前储能 ID: {current_id}")
```

---

#### `set_current_storage_id(storage_id)`

设置当前使用的储能 ID。

**参数**:
- `storage_id`: 储能 ID

**示例**:
```python
from config.config_manager import set_current_storage_id

# 切换到不同的储能系统
set_current_storage_id('storage_medium')
```

---

#### `save_storage_config(capacity=None, max_charge_power=None, max_discharge_power=None, charge_efficiency=None, discharge_efficiency=None, initial_soc=None, min_soc=None, max_soc=None)`

保存当前储能配置（只更新提供的参数）。

**参数**:
- `capacity`: 储能容量
- `max_charge_power`: 最大充电功率
- `max_discharge_power`: 最大放电功率
- `charge_efficiency`: 充电效率（0-1）
- `discharge_efficiency`: 放电效率（0-1）
- `initial_soc`: 初始SOC（0-1）
- `min_soc`: 最小SOC（0-1）
- `max_soc`: 最大SOC（0-1）

**示例**:
```python
from config.config_manager import save_storage_config

# 修改储能容量和功率
save_storage_config(
    capacity=200,  # 200 kWh
    max_charge_power=100,  # 100 kW
    max_discharge_power=100  # 100 kW
)

# 只修改效率
save_storage_config(
    charge_efficiency=0.98,
    discharge_efficiency=0.98
)

# 修改SOC范围
save_storage_config(
    initial_soc=0.6,
    min_soc=0.15,
    max_soc=0.95
)
```

---

## 基础配置管理

### 加载配置文件

```python
from config.config_manager import load_config

# 加载默认配置
config = load_config()

# 访问配置参数
area = config['system']['area']
lat = config['location']['lat']
```

### 保存配置文件

```python
from config.config_manager import save_config

# 创建配置字典
config = {
    'system': {
        'area': 1000,
        'description': '太阳能系统面积（平方米）'
    },
    'location': {
        'lat': 39.9,
        'lon': 116.4,
        'tz': 'Asia/Shanghai',
        'altitude': 44,
        'name': 'Beijing'
    }
}

# 保存配置
save_config(config, 'config/my_config.json')
```

### 从示例创建配置

```python
from config.config_manager import create_config_from_example

# 从示例创建配置
config = create_config_from_example('config/solar/panels/panel_new.json')
```

---

## 光伏板管理

### 列出所有可用光伏板

```python
from config.config_manager import list_available_panels

panels = list_available_panels()
for panel in panels:
    print(f"{panel['id']}: {panel['name']} - {panel['description']}")
```

**输出示例**:
```
panel_canadian_solar: Canadian Solar CS5P-220M - 高效率单晶硅组件
panel_trina: Trina Solar TSM-250 - 性价比多晶硅组件
panel_jinko: Jinko Solar JKM300 - 大功率单晶硅组件
```

### 加载指定光伏板配置

```python
from config.config_manager import load_panel_by_id

# 加载光伏板配置
panel_config = load_panel_by_id('panel_canadian_solar')

# 访问配置参数
print(f"光伏板名称: {panel_config['name']}")
print(f"制造商: {panel_config['manufacturer']}")
print(f"型号: {panel_config['model']}")
print(f"系统面积: {panel_config['system']['area']} 平方米")
print(f"纬度: {panel_config['location']['lat']}")
print(f"经度: {panel_config['location']['lon']}")
```

### 设置光伏板数量

光伏系统支持同时使用多种光伏板，每种光伏板可以设置不同的数量。系统会自动计算所有光伏板的功率总和。

```python
from config.config_manager import get_panel_quantities, set_panel_quantities, set_panel_quantity

# 获取当前光伏板数量配置
quantities = get_panel_quantities()
print("当前光伏板配置:")
for panel_id, quantity in quantities.items():
    print(f"  {panel_id}: {quantity} 块")

# 方式1: 设置单个光伏板数量
set_panel_quantity("panel_canadian_solar", 20)

# 方式2: 批量设置所有光伏板数量
set_panel_quantities({
    "panel_canadian_solar": 20,
    "panel_trina": 10,
    "panel_jinko": 5
})
```

### 切换当前光伏板（已废弃）

> **注意**: 此方式已废弃，推荐使用上述"设置光伏板数量"方法。

```python
from config.config_manager import set_current_panel_id, get_current_panel_id

# 获取当前光伏板（已废弃）
current_id = get_current_panel_id()
print(f"当前光伏板: {current_id}")

# 切换到新的光伏板（已废弃）
set_current_panel_id('panel_trina')
print(f"已切换到: {get_current_panel_id()}")
```

### 添加新的光伏板

**步骤 1**: 创建新的光伏板配置文件

```python
from config.config_manager import save_config

# 创建新光伏板配置
new_panel = {
    "name": "New Panel Model",
    "manufacturer": "New Manufacturer",
    "model": "NP-300",
    "system": {
        "area": 1000,
        "description": "太阳能系统面积（平方米）"
    },
    "location": {
        "lat": 39.9,
        "lon": 116.4,
        "tz": "Asia/Shanghai",
        "altitude": 44,
        "name": "Beijing"
    },
    "time_range": {
        "start": "2024-06-21",
        "end": "2024-06-22",
        "freq": "15min"
    },
    "weather": {
        "temp_air": 30,
        "wind_speed": 2
    },
    "system_config": {
        "surface_tilt": 30,
        "surface_azimuth": 180,
        "temperature_model": {
            "a": -3.56,
            "b": -0.075,
            "deltaT": 3
        },
        "auto_model": {
            "racking_model": "open_rack",
            "module_type": "glass_polymer"
        }
    }
}

# 保存新光伏板配置
save_config(new_panel, 'config/solar/panels/panel_new.json')
```

**步骤 2**: 更新光伏板列表

```python
from config.config_manager import load_config, save_config

# 加载光伏板列表
panels_list = load_config('config/solar/panels_list.json')

# 添加新光伏板
panels_list['available_panels'].append({
    "id": "panel_new",
    "name": "New Panel Model",
    "file": "panels/panel_new.json",
    "description": "新添加的光伏板"
})

# 保存更新后的列表
save_config(panels_list, 'config/solar/panels_list.json')
```

---

## 电价管理

### 加载电价配置

```python
from config.config_manager import load_electricity_price

# 加载电价配置
economics_config = load_electricity_price()

# 访问电价
price = economics_config['electricity_price']
print(f"当前电价: {price} 元/千瓦时")
```

### 修改电价

```python
from config.config_manager import save_electricity_price

# 修改电价
new_price = 1.2  # 1.2 元/千瓦时
save_electricity_price(new_price)
print(f"电价已更新为: {new_price} 元/千瓦时")
```

---

## 储能管理

### 列出所有可用储能系统

```python
from config.config_manager import list_available_storages

storages = list_available_storages()
for storage in storages:
    print(f"{storage['id']}: {storage['name']} - {storage['description']}")
```

**输出示例**:
```
storage_small: 小型储能系统 - 适用于小型工商业，100kWh容量
storage_medium: 中型储能系统 - 适用于中型工商业，500kWh容量
storage_large: 大型储能系统 - 适用于大型工商业，1000kWh容量
```

### 加载储能配置

```python
from config.config_manager import load_storage_config, load_storage_by_id

# 加载当前储能配置
storage_config = load_storage_config()

# 加载指定储能配置
storage_config = load_storage_by_id('storage_medium')

# 访问储能参数
print(f"储能容量: {storage_config['capacity']} kWh")
print(f"最大充电功率: {storage_config['max_charge_power']} kW")
print(f"最大放电功率: {storage_config['max_discharge_power']} kW")
print(f"充电效率: {storage_config['charge_efficiency']}")
print(f"放电效率: {storage_config['discharge_efficiency']}")
print(f"初始SOC: {storage_config['initial_soc']}")
print(f"SOC范围: {storage_config['min_soc']} - {storage_config['max_soc']}")
```

### 切换当前储能系统

```python
from config.config_manager import set_current_storage_id, get_current_storage_id

# 获取当前储能
current_id = get_current_storage_id()
print(f"当前储能: {current_id}")

# 切换到新的储能系统
set_current_storage_id('storage_medium')
print(f"已切换到: {get_current_storage_id()}")
```

### 修改储能配置

```python
from config.config_manager import save_storage_config

# 修改储能容量和功率
save_storage_config(
    capacity=200,  # 200 kWh
    max_charge_power=100,  # 100 kW
    max_discharge_power=100  # 100 kW
)

# 只修改效率
save_storage_config(
    charge_efficiency=0.98,
    discharge_efficiency=0.98
)

# 修改SOC范围
save_storage_config(
    initial_soc=0.6,
    min_soc=0.15,
    max_soc=0.95
)
```

### 添加新的储能系统

**步骤 1**: 创建新的储能配置文件

```python
from config.config_manager import save_config

# 创建新储能配置
new_storage = {
    "capacity": 2000,
    "max_charge_power": 1000,
    "max_discharge_power": 1000,
    "charge_efficiency": 0.95,
    "discharge_efficiency": 0.95,
    "initial_soc": 0.5,
    "min_soc": 0.1,
    "max_soc": 0.9,
    "description": "超大型储能系统配置参数",
    "units": {
        "capacity": "kWh",
        "max_charge_power": "kW",
        "max_discharge_power": "kW",
        "charge_efficiency": "百分比",
        "discharge_efficiency": "百分比",
        "initial_soc": "百分比",
        "min_soc": "百分比",
        "max_soc": "百分比"
    }
}

# 保存新储能配置
save_config(new_storage, 'config/Storage/configs/storage_xlarge.json')
```

**步骤 2**: 更新储能列表

```python
from config.config_manager import load_config, save_config

# 加载储能列表
storage_list = load_config('config/Storage/storage_list.json')

# 添加新储能
storage_list['available_storages'].append({
    "id": "storage_xlarge",
    "name": "超大型储能系统",
    "file": "config/Storage/configs/storage_xlarge.json",
    "description": "适用于超大型工商业，2000kWh容量"
})

# 保存更新后的列表
save_config(storage_list, 'config/Storage/storage_list.json')
```

---

## 完整示例

### 示例 1: 使用光伏板配置运行模拟

```python
from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from config.config_manager import (
    get_panel_quantities,
    load_electricity_price
)
import pandas as pd
from plot_comparison import plot_comparison

# 获取光伏板数量配置
panel_quantities = get_panel_quantities()
print("光伏板配置:")
for pid, qty in panel_quantities.items():
    if qty > 0:
        print(f"  {pid}: {qty} 块")

# 加载电价配置
economics_config = load_electricity_price()

# 运行模拟（自动累加所有光伏板功率）
Solar = getsolar(ifdraw=True)

# 计算成本
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

# 绘制图表
plot_comparison(data)
```

### 示例 2: 自定义光伏板数量运行模拟

```python
from Solar.Solar import getsolar
from config.config_manager import load_electricity_price

# 自定义光伏板数量
custom_quantities = {
    "panel_canadian_solar": 30,
    "panel_trina": 15,
    "panel_jinko": 10
}

# 运行模拟并绘制曲线
Solar = getsolar(panel_quantities=custom_quantities, ifdraw=True)

print(f"最大功率: {Solar.max():.2f} kW")
print(f"总发电量: {Solar.sum() / 4:.2f} kWh")
```

### 示例 3: 比较不同光伏板的性能

```python
from Solar.Solar import getsolar
from config.config_manager import list_available_panels
import pandas as pd

# 列出所有光伏板
panels = list_available_panels()

# 比较每个光伏板单块的输出功率
results = []
for panel in panels:
    # 单独计算该光伏板（1块）
    Solar = getsolar(panel_id=panel['id'])
    
    max_power = Solar.max()
    total_energy = Solar.sum() / 4  # 转换为 kWh
    
    results.append({
        'name': panel['name'],
        'max_power': max_power,
        'total_energy': total_energy
    })

# 显示结果
results_df = pd.DataFrame(results)
print(results_df)
```

### 示例 3: 批量修改电价并分析成本

```python
from Solar.Solar import getsolar
from Consumption.Consumption import getconsumption
from config.config_manager import (
    load_panel_by_id,
    get_current_panel_id,
    save_electricity_price,
    load_electricity_price
)
import pandas as pd

# 加载当前光伏板配置
panel_config = load_panel_by_id(get_current_panel_id())

# 运行模拟（只需运行一次）
Solar = panel_config['system']['area'] * getsolar(
    lat=panel_config['location']['lat'],
    lon=panel_config['location']['lon'],
    tz=panel_config['location']['tz'],
    altitude=panel_config['location']['altitude'],
    name=panel_config['location']['name'],
    start=panel_config['time_range']['start'],
    end=panel_config['time_range']['end'],
    freq=panel_config['time_range']['freq'],
    temp_air=panel_config['weather']['temp_air'],
    wind_speed=panel_config['weather']['wind_speed'],
    surface_tilt=panel_config['system_config']['surface_tilt'],
    surface_azimuth=panel_config['system_config']['surface_azimuth'],
    temp_a=panel_config['system_config']['temperature_model']['a'],
    temp_b=panel_config['system_config']['temperature_model']['b'],
    temp_deltaT=panel_config['system_config']['temperature_model']['deltaT']
) / 1000

Consumption = getconsumption()
data = pd.DataFrame({
    'Solar': Solar.values,
    'Consumption': Consumption.values,
    'Energy Balance': Consumption.values - Solar.values
}, index=Solar.index)

# 测试不同电价
electricity_prices = [0.8, 1.0, 1.2, 1.5, 2.0]
costs = []

for price in electricity_prices:
    Electricity = data['Energy Balance'].clip(lower=0)
    cost = sum(Electricity * price) / 4
    costs.append(cost)
    
    print(f"电价 {price} 元/千瓦时: 成本 {cost:.2f} 元/天")

# 保存最优电价
optimal_price = electricity_prices[costs.index(min(costs))]
save_electricity_price(optimal_price)
print(f"\n最优电价: {optimal_price} 元/千瓦时")
```

---

## 配置文件格式说明

### 光伏板配置文件格式

```json
{
    "name": "光伏板名称",
    "manufacturer": "制造商",
    "model": "型号",
    "system": {
        "area": 1000,
        "description": "太阳能系统面积（平方米）"
    },
    "location": {
        "lat": 39.9,
        "lon": 116.4,
        "tz": "Asia/Shanghai",
        "altitude": 44,
        "name": "Beijing"
    },
    "time_range": {
        "start": "2024-06-21",
        "end": "2024-06-22",
        "freq": "15min"
    },
    "weather": {
        "temp_air": 30,
        "wind_speed": 2
    },
    "system_config": {
        "surface_tilt": 30,
        "surface_azimuth": 180,
        "temperature_model": {
            "a": -3.56,
            "b": -0.075,
            "deltaT": 3,
            "description": "温度模型参数（用于getsolar函数）"
        },
        "auto_model": {
            "racking_model": "open_rack",
            "module_type": "glass_polymer",
            "description": "自动推断温度模型参数（用于getsolar_auto函数）"
        }
    }
}
```

### 电价配置文件格式

```json
{
    "electricity_price": 1,
    "description": "电价（元/千瓦时）",
    "last_updated": "2024-06-21"
}
```

### 储能配置文件格式

```json
{
    "capacity": 100,
    "max_charge_power": 50,
    "max_discharge_power": 50,
    "charge_efficiency": 0.95,
    "discharge_efficiency": 0.95,
    "initial_soc": 0.5,
    "min_soc": 0.1,
    "max_soc": 0.9,
    "description": "储能系统配置参数",
    "units": {
        "capacity": "kWh",
        "max_charge_power": "kW",
        "max_discharge_power": "kW",
        "charge_efficiency": "百分比",
        "discharge_efficiency": "百分比",
        "initial_soc": "百分比",
        "min_soc": "百分比",
        "max_soc": "百分比"
    }
}
```

### 储能列表文件格式

```json
{
    "available_storages": [
        {
            "id": "storage_small",
            "name": "小型储能系统",
            "file": "config/Storage/configs/storage_small.json",
            "description": "适用于小型工商业，100kWh容量"
        }
    ],
    "current_storage": "storage_small"
}
```

**注意**：`file` 字段使用相对于项目根目录的路径，需要包含 `config/` 前缀。

### 光伏板列表文件格式

```json
{
    "available_panels": [
        {
            "id": "panel_canadian_solar",
            "name": "Canadian Solar CS5P-220M",
            "file": "config/solar/panels/panel_canadian_solar.json",
            "description": "高效率单晶硅组件"
        },
        {
            "id": "panel_trina",
            "name": "Trina Solar TSM-250",
            "file": "config/solar/panels/panel_trina.json",
            "description": "性价比多晶硅组件"
        }
    ],
    "panel_quantities": {
        "panel_canadian_solar": 10,
        "panel_trina": 5,
        "panel_jinko": 0
    }
}
```

> **说明**: `panel_quantities` 字段定义了每种光伏板的数量（块数）。系统会自动计算所有光伏板的功率总和。数量为 0 表示不使用该类型光伏板。

---

## 常见问题

### Q1: 如何添加新的光伏板？

1. 创建新的光伏板配置文件（参考现有格式）
2. 更新 `solar/panels_list.json`，添加新光伏板信息到 `available_panels` 列表
3. 在 `panel_quantities` 中设置该光伏板的数量

### Q2: 如何备份当前配置？

```python
from config.config_manager import load_config, save_config
from datetime import datetime

# 加载当前配置
config = load_config('config/solar/panels/panel_canadian_solar.json')

# 保存备份
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
save_config(config, f'config/solar/panels/panel_canadian_solar_backup_{timestamp}.json')
```

### Q3: 如何恢复默认配置？

```python
from config.config_manager import create_config_from_example

# 从示例重新创建配置
config = create_config_from_example('config/solar/panels/panel_canadian_solar.json')
```

### Q4: 配置文件会被提交到 Git 吗？

不会。根据 `.gitignore` 配置：
- `config/*.json` - 不提交
- `config/solar/*.json` - 不提交
- `config/solar/panels/*.json` - 不提交
- `config/Storage/*.json` - 不提交
- `config/Storage/configs/*.json` - 不提交

只有 `.example` 文件会被提交到 Git。

---

## 总结

- 使用 `load_panel_by_id()` 加载光伏板配置
- 使用 `list_available_panels()` 查看所有光伏板
- 使用 `get_panel_quantities()` 获取光伏板数量配置
- 使用 `set_panel_quantity()` 设置单个光伏板数量
- 使用 `set_panel_quantities()` 批量设置光伏板数量
- 使用 `load_electricity_price()` 和 `save_electricity_price()` 管理电价
- 使用 `load_storage_config()` 加载当前储能配置
- 使用 `load_storage_by_id()` 加载指定储能配置
- 使用 `list_available_storages()` 查看所有储能系统
- 使用 `set_current_storage_id()` 切换储能系统
- 使用 `save_storage_config()` 修改当前储能配置
- 所有配置文件都有对应的 `.example` 文件作为模板