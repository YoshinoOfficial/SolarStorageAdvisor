import json
import os
import shutil
import pandas as pd

def load_config(config_path='config/solar_config.json', auto_create=True):
    """
    加载配置文件，支持自动从示例创建
    
    Args:
        config_path: 配置文件路径
        auto_create: 如果配置文件不存在，是否自动从示例创建
        
    Returns:
        dict: 配置字典
    """
    # 自动调整相对路径
    if not os.path.isabs(config_path):
        # 获取项目根目录
        config_manager_path = os.path.abspath(__file__)
        config_dir = os.path.dirname(config_manager_path)
        project_root = os.path.dirname(config_dir)
        config_path = os.path.join(project_root, config_path)
    
    # 配置文件存在，直接加载
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"已加载配置文件: {config_path}")
        return config
    
    print(f"配置文件不存在: {config_path}")
    
    # 配置文件不存在，处理示例文件
    example_path = config_path.replace('.json', '.json.example')
    
    if not os.path.exists(example_path):
        raise FileNotFoundError(f"示例文件不存在: {example_path}")
    
    # 自动从示例创建配置
    if auto_create:
        return create_config_from_example(config_path)
    
    # 不自动创建，抛出异常
    raise FileNotFoundError(
        f"配置文件不存在: {config_path}\n"
        f"提示: 从示例文件创建配置: create_config_from_example('{config_path}')"
    )

def save_config(config, config_path='config/solar_config.json'):
    """
    保存配置文件
    
    Args:
        config: 配置字典
        config_path: 配置文件路径
    """
    # 自动调整相对路径
    if not os.path.isabs(config_path):
        # 获取项目根目录
        config_manager_path = os.path.abspath(__file__)
        config_dir = os.path.dirname(config_manager_path)
        project_root = os.path.dirname(config_dir)
        config_path = os.path.join(project_root, config_path)
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"配置已保存到: {config_path}")

def create_config_from_example(config_path='config/solar_config.json'):
    """
    从示例文件创建配置文件
    
    Args:
        config_path: 目标配置文件路径
        
    Returns:
        dict: 创建的配置字典
    """
    example_path = config_path.replace('.json', '.json.example')
    
    if not os.path.exists(example_path):
        raise FileNotFoundError(f"示例文件不存在: {example_path}")
    
    if os.path.exists(config_path):
        print(f"警告: 配置文件已存在，将被覆盖: {config_path}")
    
    shutil.copy2(example_path, config_path)
    print(f"已从示例创建配置文件: {config_path}")
    
    # 加载并返回创建的配置
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    return config

def load_panel_by_id(panel_id):
    """
    通过板子 ID 加载光伏板配置
    
    Args:
        panel_id: 光伏板 ID
        
    Returns:
        dict: 光伏板配置字典
    """
    panels_list = load_config('config/solar/panels_list.json')
    
    panel_info = None
    for panel in panels_list['available_panels']:
        if panel['id'] == panel_id:
            panel_info = panel
            break
    
    if not panel_info:
        raise ValueError(f"光伏板 ID 不存在: {panel_id}")
    # print(panel_info)
    return load_config(panel_info['file'])

def list_available_panels():
    """
    列出所有可用的光伏板
    
    Returns:
        list: 光伏板信息列表
    """
    panels_list = load_config('config/solar/panels_list.json')
    return panels_list['available_panels']

def get_panel_quantities():
    """
    获取所有光伏板的数量配置
    
    Returns:
        dict: 光伏板ID到数量的映射，如 {"panel_canadian_solar": 10, "panel_trina": 5}
    """
    panels_list = load_config('config/solar/panels_list.json')
    return panels_list.get('panel_quantities', {})

def set_panel_quantities(quantities_dict):
    """
    设置光伏板数量配置
    
    Args:
        quantities_dict: 光伏板ID到数量的映射字典
    """
    panels_list = load_config('config/solar/panels_list.json')
    
    valid_ids = {panel['id'] for panel in panels_list['available_panels']}
    for panel_id in quantities_dict:
        if panel_id not in valid_ids:
            raise ValueError(f"光伏板 ID 不存在: {panel_id}")
    
    panels_list['panel_quantities'] = quantities_dict
    save_config(panels_list, 'config/solar/panels_list.json')
    print(f"已设置光伏板数量配置")

def set_panel_quantity(panel_id, quantity):
    """
    设置单个光伏板的数量
    
    Args:
        panel_id: 光伏板 ID
        quantity: 数量（块数）
    """
    panels_list = load_config('config/solar/panels_list.json')
    
    panel_exists = False
    for panel in panels_list['available_panels']:
        if panel['id'] == panel_id:
            panel_exists = True
            break
    
    if not panel_exists:
        raise ValueError(f"光伏板 ID 不存在: {panel_id}")
    
    if 'panel_quantities' not in panels_list:
        panels_list['panel_quantities'] = {}
    
    panels_list['panel_quantities'][panel_id] = quantity
    save_config(panels_list, 'config/solar/panels_list.json')
    print(f"已设置光伏板 {panel_id} 数量为: {quantity}")

def get_current_panel_id():
    """
    获取当前使用的光伏板 ID（已废弃，保留向后兼容）
    
    Returns:
        str: 光伏板 ID
    """
    panels_list = load_config('config/solar/panels_list.json')
    return panels_list.get('current_panel', list(panels_list.get('panel_quantities', {}).keys())[0] if panels_list.get('panel_quantities') else None)

def set_current_panel_id(panel_id):
    """
    设置当前使用的光伏板 ID（已废弃，保留向后兼容）
    
    Args:
        panel_id: 光伏板 ID
    """
    panels_list = load_config('config/solar/panels_list.json')
    
    panel_exists = False
    for panel in panels_list['available_panels']:
        if panel['id'] == panel_id:
            panel_exists = True
            break
    
    if not panel_exists:
        raise ValueError(f"光伏板 ID 不存在: {panel_id}")
    
    panels_list['current_panel'] = panel_id
    save_config(panels_list, 'config/solar/panels_list.json')
    print(f"已设置当前光伏板: {panel_id}")

def load_electricity_price():
    """
    加载电价配置
    
    Returns:
        dict: 电价配置字典
    """
    return load_config('config/economics/electricity_price.json')

def save_electricity_price(electricity_price, feed_in_price=None):
    """
    保存电价配置
    
    Args:
        electricity_price: 电价（元/千瓦时）
        feed_in_price: 上网电价/售电价（元/千瓦时），可选
    """
    config = load_electricity_price()
    config['electricity_price'] = electricity_price
    if feed_in_price is not None:
        config['feed_in_price'] = feed_in_price
    config['description'] = '电价（元/千瓦时），feed_in_price为上网电价（售电价）'
    config['last_updated'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    save_config(config, 'config/economics/electricity_price.json')

def save_feed_in_price(feed_in_price):
    """
    保存上网电价/售电价配置
    
    Args:
        feed_in_price: 上网电价/售电价（元/千瓦时）
    """
    config = load_electricity_price()
    config['feed_in_price'] = feed_in_price
    config['description'] = '电价（元/千瓦时），feed_in_price为上网电价（售电价）'
    config['last_updated'] = pd.Timestamp.now().strftime('%Y-%m-%d')
    save_config(config, 'config/economics/electricity_price.json')

def load_storage_config():
    """
    加载当前储能配置
    
    Returns:
        dict: 储能配置字典
    """
    storage_list = load_config('config/Storage/storage_list.json')
    current_id = storage_list['current_storage']
    return load_storage_by_id(current_id)

def load_storage_by_id(storage_id):
    """
    通过储能 ID 加载储能配置
    
    Args:
        storage_id: 储能 ID
        
    Returns:
        dict: 储能配置字典
    """
    storage_list = load_config('config/Storage/storage_list.json')
    
    storage_info = None
    for storage in storage_list['available_storages']:
        if storage['id'] == storage_id:
            storage_info = storage
            break
    
    if not storage_info:
        raise ValueError(f"储能 ID 不存在: {storage_id}")
    
    return load_config(storage_info['file'])

def list_available_storages():
    """
    列出所有可用的储能系统
    
    Returns:
        list: 储能系统信息列表
    """
    storage_list = load_config('config/Storage/storage_list.json')
    return storage_list['available_storages']

def get_current_storage_id():
    """
    获取当前使用的储能 ID
    
    Returns:
        str: 储能 ID
    """
    storage_list = load_config('config/Storage/storage_list.json')
    return storage_list['current_storage']

def set_current_storage_id(storage_id):
    """
    设置当前使用的储能 ID
    
    Args:
        storage_id: 储能 ID
    """
    storage_list = load_config('config/Storage/storage_list.json')
    
    storage_exists = False
    for storage in storage_list['available_storages']:
        if storage['id'] == storage_id:
            storage_exists = True
            break
    
    if not storage_exists:
        raise ValueError(f"储能 ID 不存在: {storage_id}")
    
    storage_list['current_storage'] = storage_id
    save_config(storage_list, 'config/Storage/storage_list.json')
    print(f"已设置当前储能系统: {storage_id}")

def save_storage_config(capacity=None, max_charge_power=None, max_discharge_power=None,
                        charge_efficiency=None, discharge_efficiency=None,
                        initial_soc=None, min_soc=None, max_soc=None):
    """
    保存当前储能配置（只更新提供的参数）
    
    Args:
        capacity: 储能容量（kWh）
        max_charge_power: 最大充电功率（kW）
        max_discharge_power: 最大放电功率（kW）
        charge_efficiency: 充电效率（0-1）
        discharge_efficiency: 放电效率（0-1）
        initial_soc: 初始SOC（0-1）
        min_soc: 最小SOC（0-1）
        max_soc: 最大SOC（0-1）
    """
    # 获取当前储能配置文件路径
    storage_list = load_config('config/Storage/storage_list.json')
    current_id = storage_list['current_storage']
    
    storage_info = None
    for storage in storage_list['available_storages']:
        if storage['id'] == current_id:
            storage_info = storage
            break
    
    if not storage_info:
        raise ValueError(f"当前储能 ID 不存在: {current_id}")
    
    # 加载当前配置
    config = load_config(storage_info['file'])
    
    if capacity is not None:
        config['capacity'] = capacity
    if max_charge_power is not None:
        config['max_charge_power'] = max_charge_power
    if max_discharge_power is not None:
        config['max_discharge_power'] = max_discharge_power
    if charge_efficiency is not None:
        config['charge_efficiency'] = charge_efficiency
    if discharge_efficiency is not None:
        config['discharge_efficiency'] = discharge_efficiency
    if initial_soc is not None:
        config['initial_soc'] = initial_soc
    if min_soc is not None:
        config['min_soc'] = min_soc
    if max_soc is not None:
        config['max_soc'] = max_soc
    
    save_config(config, storage_info['file'])
    print(f"储能配置已更新: {current_id}")

def create_new_storage_config(storage_id, name, description, capacity, max_charge_power, 
                               max_discharge_power, charge_efficiency=0.95, 
                               discharge_efficiency=0.95, initial_soc=0.5, 
                               min_soc=0.1, max_soc=0.9):
    """
    创建新的储能配置
    
    Args:
        storage_id: 储能 ID
        name: 储能名称
        description: 描述
        capacity: 储能容量（kWh）
        max_charge_power: 最大充电功率（kW）
        max_discharge_power: 最大放电功率（kW）
        charge_efficiency: 充电效率（0-1）
        discharge_efficiency: 放电效率（0-1）
        initial_soc: 初始SOC（0-1）
        min_soc: 最小SOC（0-1）
        max_soc: 最大SOC（0-1）
        
    Returns:
        dict: 创建的储能配置
    """
    storage_list = load_config('config/Storage/storage_list.json')
    
    for storage in storage_list['available_storages']:
        if storage['id'] == storage_id:
            raise ValueError(f"储能 ID 已存在: {storage_id}")
    
    config_file = f"config/Storage/configs/{storage_id}.json"
    
    new_config = {
        "capacity": capacity,
        "max_charge_power": max_charge_power,
        "max_discharge_power": max_discharge_power,
        "charge_efficiency": charge_efficiency,
        "discharge_efficiency": discharge_efficiency,
        "initial_soc": initial_soc,
        "min_soc": min_soc,
        "max_soc": max_soc,
        "description": description,
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
    
    save_config(new_config, config_file)
    
    storage_list['available_storages'].append({
        "id": storage_id,
        "name": name,
        "file": config_file,
        "description": description
    })
    save_config(storage_list, 'config/Storage/storage_list.json')
    
    print(f"已创建新储能配置: {storage_id}")
    return new_config

def delete_storage_config(storage_id):
    """
    删除储能配置
    
    Args:
        storage_id: 储能 ID
    """
    storage_list = load_config('config/Storage/storage_list.json')
    
    if storage_list['current_storage'] == storage_id:
        raise ValueError(f"无法删除当前正在使用的储能配置: {storage_id}")
    
    storage_info = None
    for storage in storage_list['available_storages']:
        if storage['id'] == storage_id:
            storage_info = storage
            break
    
    if not storage_info:
        raise ValueError(f"储能 ID 不存在: {storage_id}")
    
    config_file = storage_info['file']
    if not os.path.isabs(config_file):
        config_manager_path = os.path.abspath(__file__)
        config_dir = os.path.dirname(config_manager_path)
        project_root = os.path.dirname(config_dir)
        config_file = os.path.join(project_root, config_file)
    
    if os.path.exists(config_file):
        os.remove(config_file)
    
    storage_list['available_storages'] = [
        s for s in storage_list['available_storages'] if s['id'] != storage_id
    ]
    save_config(storage_list, 'config/Storage/storage_list.json')
    
    print(f"已删除储能配置: {storage_id}")

def create_new_panel_config(panel_id, name, description, area, lat=39.9, lon=116.4, 
                            tz='Asia/Shanghai', altitude=44, location_name='Beijing',
                            start='2024-06-21', end='2024-06-22', freq='15min',
                            temp_air=30, wind_speed=2, surface_tilt=30, surface_azimuth=180):
    """
    创建新的光伏板配置
    
    Args:
        panel_id: 光伏板 ID
        name: 光伏板名称
        description: 描述
        area: 面积（平方米）
        lat: 纬度
        lon: 经度
        tz: 时区
        altitude: 海拔
        location_name: 位置名称
        start: 开始时间
        end: 结束时间
        freq: 频率
        temp_air: 环境温度
        wind_speed: 风速
        surface_tilt: 倾角
        surface_azimuth: 方位角
        
    Returns:
        dict: 创建的光伏板配置
    """
    panels_list = load_config('config/solar/panels_list.json')
    
    for panel in panels_list['available_panels']:
        if panel['id'] == panel_id:
            raise ValueError(f"光伏板 ID 已存在: {panel_id}")
    
    config_file = f"config/solar/panels/{panel_id}.json"
    
    new_config = {
        "name": name,
        "manufacturer": "Custom",
        "model": name,
        "system": {
            "area": area,
            "description": "太阳能系统面积（平方米）"
        },
        "location": {
            "lat": lat,
            "lon": lon,
            "tz": tz,
            "altitude": altitude,
            "name": location_name
        },
        "time_range": {
            "start": start,
            "end": end,
            "freq": freq
        },
        "weather": {
            "temp_air": temp_air,
            "wind_speed": wind_speed
        },
        "system_config": {
            "surface_tilt": surface_tilt,
            "surface_azimuth": surface_azimuth,
            "temperature_model": {
                "a": -3.56,
                "b": -0.075,
                "deltaT": 3,
                "description": "温度模型参数"
            },
            "auto_model": {
                "racking_model": "open_rack",
                "module_type": "glass_polymer",
                "description": "自动推断温度模型参数"
            }
        }
    }
    
    save_config(new_config, config_file)
    
    panels_list['available_panels'].append({
        "id": panel_id,
        "name": name,
        "file": config_file,
        "description": description
    })
    save_config(panels_list, 'config/solar/panels_list.json')
    
    print(f"已创建新光伏板配置: {panel_id}")
    return new_config

def delete_panel_config(panel_id):
    """
    删除光伏板配置
    
    Args:
        panel_id: 光伏板 ID
    """
    panels_list = load_config('config/solar/panels_list.json')
    
    if panels_list['current_panel'] == panel_id:
        raise ValueError(f"无法删除当前正在使用的光伏板配置: {panel_id}")
    
    panel_info = None
    for panel in panels_list['available_panels']:
        if panel['id'] == panel_id:
            panel_info = panel
            break
    
    if not panel_info:
        raise ValueError(f"光伏板 ID 不存在: {panel_id}")
    
    config_file = panel_info['file']
    if not os.path.isabs(config_file):
        config_manager_path = os.path.abspath(__file__)
        config_dir = os.path.dirname(config_manager_path)
        project_root = os.path.dirname(config_dir)
        config_file = os.path.join(project_root, config_file)
    
    if os.path.exists(config_file):
        os.remove(config_file)
    
    panels_list['available_panels'] = [
        p for p in panels_list['available_panels'] if p['id'] != panel_id
    ]
    save_config(panels_list, 'config/solar/panels_list.json')
    
    print(f"已删除光伏板配置: {panel_id}")

def save_panel_config(panel_id, area=None, surface_tilt=None, surface_azimuth=None,
                      lat=None, lon=None, tz=None, altitude=None, location_name=None,
                      start=None, end=None, freq=None, temp_air=None, wind_speed=None):
    """
    保存光伏板配置（只更新提供的参数）
    
    Args:
        panel_id: 光伏板 ID
        area: 面积（平方米）
        surface_tilt: 倾角
        surface_azimuth: 方位角
        lat: 纬度
        lon: 经度
        tz: 时区
        altitude: 海拔
        location_name: 位置名称
        start: 开始时间
        end: 结束时间
        freq: 频率
        temp_air: 环境温度
        wind_speed: 风速
    """
    config = load_panel_by_id(panel_id)
    
    if area is not None:
        config['system']['area'] = area
    if surface_tilt is not None:
        config['system_config']['surface_tilt'] = surface_tilt
    if surface_azimuth is not None:
        config['system_config']['surface_azimuth'] = surface_azimuth
    if lat is not None:
        config['location']['lat'] = lat
    if lon is not None:
        config['location']['lon'] = lon
    if tz is not None:
        config['location']['tz'] = tz
    if altitude is not None:
        config['location']['altitude'] = altitude
    if location_name is not None:
        config['location']['name'] = location_name
    if start is not None:
        config['time_range']['start'] = start
    if end is not None:
        config['time_range']['end'] = end
    if freq is not None:
        config['time_range']['freq'] = freq
    if temp_air is not None:
        config['weather']['temp_air'] = temp_air
    if wind_speed is not None:
        config['weather']['wind_speed'] = wind_speed
    
    panels_list = load_config('config/solar/panels_list.json')
    panel_info = None
    for panel in panels_list['available_panels']:
        if panel['id'] == panel_id:
            panel_info = panel
            break
    
    if panel_info:
        save_config(config, panel_info['file'])
        print(f"光伏板配置已更新: {panel_id}")