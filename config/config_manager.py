import json
import os
import shutil

def load_config(config_path='config/solar_config.json', auto_create=True):
    """
    加载配置文件，支持自动从示例创建
    
    Args:
        config_path: 配置文件路径
        auto_create: 如果配置文件不存在，是否自动从示例创建
        
    Returns:
        dict: 配置字典
    """
    # 配置文件存在，直接加载
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"已加载配置文件: {config_path}")
        return config
    
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