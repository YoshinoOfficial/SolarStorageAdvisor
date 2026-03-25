import requests
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config.config_manager import (
    save_storage_config,
    save_electricity_price,
    load_storage_config,
    load_electricity_price,
    list_available_storages,
    list_available_panels,
    create_new_storage_config,
    create_new_panel_config
)

def load_llm_config():
    """
    加载LLM配置文件
    
    Returns:
        dict: LLM配置字典
    """
    config_manager_path = os.path.abspath(__file__)
    project_root = os.path.dirname(config_manager_path)
    config_path = os.path.join(project_root, 'config', 'model', 'llm_config.json')
    
    if not os.path.exists(config_path):
        example_path = config_path + '.example'
        if os.path.exists(example_path):
            import shutil
            shutil.copy2(example_path, config_path)
            print(f"已从示例创建配置文件: {config_path}")
        else:
            raise FileNotFoundError(f"LLM配置文件不存在: {config_path}")
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

LLM_CONFIG = load_llm_config()

SYSTEM_PROMPT = """你是一个储能系统配置助手。用户会用自然语言描述配置需求，你需要理解用户意图并调用相应的函数。

## 可用操作

### 储能配置
- 修改储能参数：调用 modify_storage_config 函数
- 查询储能配置：调用 get_storage_config 函数
- 创建新储能：调用 create_storage_config 函数
- 列出所有储能：调用 list_storages 函数

### 电价配置
- 修改电价：调用 modify_electricity_price 函数
- 查询电价：调用 get_electricity_price 函数

### 光伏板配置
- 列出所有光伏板：调用 list_panels 函数

---

## 函数参数详解

### create_storage_config（创建新储能）

必填参数：
- storage_id: 储能系统ID，英文标识，如 "storage_custom"
- name: 储能系统名称，如 "工厂A储能系统"
- description: 描述，如 "适用于中型工商业"
- capacity: 储能容量（kWh）
- max_charge_power: 最大充电功率（kW）
- max_discharge_power: 最大放电功率（kW）

可选参数（有默认值，用户不指定时使用默认值）：
- charge_efficiency: 充电效率，默认 0.95（95%）
- discharge_efficiency: 放电效率，默认 0.95（95%）
- initial_soc: 初始SOC，默认 0.5（50%）
- min_soc: 最小SOC，默认 0.1（10%）
- max_soc: 最大SOC，默认 0.9（90%）

### modify_storage_config（修改储能配置）

所有参数可选，只传用户指定的：
- capacity: 储能容量（kWh）
- max_charge_power: 最大充电功率（kW）
- max_discharge_power: 最大放电功率（kW）
- charge_efficiency: 充电效率（0-1）
- discharge_efficiency: 放电效率（0-1）
- initial_soc: 初始SOC（0-1）
- min_soc: 最小SOC（0-1）
- max_soc: 最大SOC（0-1）

### modify_electricity_price（修改电价）

必填参数：
- price: 电价（元/kWh）

---

## 参数不完整时的处理规则

当用户想要执行某个操作但缺少必填参数时，**不要调用函数**，而是直接追问用户：

1. 明确告知用户缺少哪些信息
2. 一次只问 1-2 个问题，不要一次性问太多
3. 使用友好的语气，可以给出建议值或示例
4. 当用户表示迷茫或不确定时，主动提供默认值作为参考

### 示例对话

用户: 新建一个储能配置
助手: 好的，我来帮您创建储能配置。请提供以下信息：
1. 储能系统名称？（如：工厂A储能系统）
2. 储能容量是多少 kWh？

用户: 名称叫测试储能，容量500度，其他不知道怎么填
助手: 没问题！我来帮您补充其他参数：

**必填参数还需要：**
- 最大充电功率（kW）：建议设为容量的 0.2 倍，即 100 kW
- 最大放电功率（kW）：建议与充电功率相同，即 100 kW
- 描述：如 "500kWh测试储能系统"

**可选参数（不填则使用默认值）：**
- 充电效率：默认 95%
- 放电效率：默认 95%
- 初始SOC：默认 50%
- 最小SOC：默认 10%
- 最大SOC：默认 90%

您觉得这些建议值可以吗？或者有需要调整的？

用户: 可以，就用建议值
助手: [调用 create_storage_config，使用建议值]

---

## 单位换算
- "度电" = kWh
- "千瓦" = kW
- 百分比需转换为 0-1 小数（如 95% → 0.95）

## 执行结果反馈
执行操作后，用简洁友好的语言告知用户结果，列出关键参数。"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "modify_storage_config",
            "description": "修改当前储能系统的配置参数",
            "parameters": {
                "type": "object",
                "properties": {
                    "capacity": {
                        "type": "number",
                        "description": "储能容量，单位为空"
                    },
                    "max_charge_power": {
                        "type": "number",
                        "description": "最大充电功率，单位为空"
                    },
                    "max_discharge_power": {
                        "type": "number",
                        "description": "最大放电功率，单位为空"
                    },
                    "charge_efficiency": {
                        "type": "number",
                        "description": "充电效率，0-1之间的小数，如0.95表示95%"
                    },
                    "discharge_efficiency": {
                        "type": "number",
                        "description": "放电效率，0-1之间的小数"
                    },
                    "initial_soc": {
                        "type": "number",
                        "description": "初始SOC，0-1之间的小数"
                    },
                    "min_soc": {
                        "type": "number",
                        "description": "最小SOC，0-1之间的小数"
                    },
                    "max_soc": {
                        "type": "number",
                        "description": "最大SOC，0-1之间的小数"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_storage_config",
            "description": "获取当前储能系统的配置信息",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_storage_config",
            "description": "创建新的储能系统配置",
            "parameters": {
                "type": "object",
                "properties": {
                    "storage_id": {
                        "type": "string",
                        "description": "储能系统ID，英文标识，如storage_custom"
                    },
                    "name": {
                        "type": "string",
                        "description": "储能系统名称"
                    },
                    "description": {
                        "type": "string",
                        "description": "储能系统描述"
                    },
                    "capacity": {
                        "type": "number",
                        "description": "储能容量（kWh）"
                    },
                    "max_charge_power": {
                        "type": "number",
                        "description": "最大充电功率（kW）"
                    },
                    "max_discharge_power": {
                        "type": "number",
                        "description": "最大放电功率（kW）"
                    },
                    "charge_efficiency": {
                        "type": "number",
                        "description": "充电效率，0-1之间小数，默认0.95"
                    },
                    "discharge_efficiency": {
                        "type": "number",
                        "description": "放电效率，0-1之间小数，默认0.95"
                    },
                    "initial_soc": {
                        "type": "number",
                        "description": "初始SOC，0-1之间小数，默认0.5"
                    },
                    "min_soc": {
                        "type": "number",
                        "description": "最小SOC，0-1之间小数，默认0.1"
                    },
                    "max_soc": {
                        "type": "number",
                        "description": "最大SOC，0-1之间小数，默认0.9"
                    }
                },
                "required": ["storage_id", "name", "description", "capacity", "max_charge_power", "max_discharge_power"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_storages",
            "description": "列出所有可用的储能系统",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "modify_electricity_price",
            "description": "修改电价配置",
            "parameters": {
                "type": "object",
                "properties": {
                    "price": {
                        "type": "number",
                        "description": "电价，单位为元/kWh"
                    }
                },
                "required": ["price"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_electricity_price",
            "description": "获取当前电价配置",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_panels",
            "description": "列出所有可用的光伏板配置",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]

FUNCTION_MAP = {
    "modify_storage_config": save_storage_config,
    "get_storage_config": load_storage_config,
    "create_storage_config": create_new_storage_config,
    "list_storages": list_available_storages,
    "modify_electricity_price": save_electricity_price,
    "get_electricity_price": load_electricity_price,
    "list_panels": list_available_panels
}

def call_llm_api(messages, tools=None, model=None, temperature=None):
    """
    调用LLM API
    
    Args:
        messages: 对话消息列表
        tools: 工具定义（可选）
        model: 模型名称（可选，默认使用配置文件中的模型）
        temperature: 温度参数（可选，默认使用配置文件中的值）
        
    Returns:
        dict: API响应
    """
    url = LLM_CONFIG.get('base_url', LLM_CONFIG['providers'][LLM_CONFIG['provider']]['base_url'])
    api_key = LLM_CONFIG['api_key']
    model = model or LLM_CONFIG.get('model', LLM_CONFIG['providers'][LLM_CONFIG['provider']]['models'][0])
    temperature = temperature if temperature is not None else LLM_CONFIG.get('temperature', 0.7)

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json"
    }

    data = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    if tools:
        data["tools"] = tools

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"API调用失败: {response.status_code}, {response.text}")

def execute_function(function_name, arguments):
    """
    执行配置管理函数
    
    Args:
        function_name: 函数名称
        arguments: 函数参数字典
        
    Returns:
        执行结果
    """
    if function_name not in FUNCTION_MAP:
        return {"error": f"未知函数: {function_name}"}
    
    func = FUNCTION_MAP[function_name]
    
    try:
        if function_name == "modify_storage_config":
            save_storage_config(**arguments)
            return {"success": True, "message": "储能配置已更新"}
        elif function_name == "get_storage_config":
            config = load_storage_config()
            return {"success": True, "data": config}
        elif function_name == "create_storage_config":
            create_new_storage_config(**arguments)
            return {"success": True, "message": f"已创建储能配置: {arguments['storage_id']}"}
        elif function_name == "list_storages":
            storages = list_available_storages()
            return {"success": True, "data": storages}
        elif function_name == "modify_electricity_price":
            save_electricity_price(arguments["price"])
            return {"success": True, "message": f"电价已更新为 {arguments['price']} 元/kWh"}
        elif function_name == "get_electricity_price":
            config = load_electricity_price()
            return {"success": True, "data": config}
        elif function_name == "list_panels":
            panels = list_available_panels()
            return {"success": True, "data": panels}
    except Exception as e:
        return {"error": str(e)}

def chat_with_config_assistant(user_message, conversation_history=None):
    """
    与配置助手进行对话，自动处理函数调用
    
    Args:
        user_message: 用户输入的消息
        conversation_history: 对话历史（可选）
        
    Returns:
        tuple: (助手回复, 更新后的对话历史)
    """
    if conversation_history is None:
        conversation_history = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
    
    conversation_history.append({"role": "user", "content": user_message})
    
    response = call_llm_api(conversation_history, tools=TOOLS)
    
    message = response["choices"][0]["message"]
    
    if "tool_calls" in message and message["tool_calls"]:
        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])
            
            print(f"[系统] 调用函数: {func_name}({func_args})")
            
            result = execute_function(func_name, func_args)
            
            conversation_history.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [tool_call]
            })
            conversation_history.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
                "tool_call_id": tool_call["id"]
            })
        
        follow_up_response = call_llm_api(conversation_history, tools=TOOLS)
        assistant_reply = follow_up_response["choices"][0]["message"]["content"]
        
        conversation_history.append({
            "role": "assistant",
            "content": assistant_reply
        })
        
        return assistant_reply, conversation_history
    
    assistant_reply = message.get("content", "")
    
    conversation_history.append({
        "role": "assistant",
        "content": assistant_reply
    })
    
    return assistant_reply, conversation_history

if __name__ == "__main__":
    print("=== 储能系统配置助手 ===")
    print("输入 'quit' 退出\n")
    
    history = None
    
    while True:
        user_input = input("用户: ").strip()
        
        if user_input.lower() == 'quit':
            print("再见！")
            break
        
        if not user_input:
            continue
        
        try:
            reply, history = chat_with_config_assistant(user_input, history)
            print(f"助手: {reply}\n")
        except Exception as e:
            print(f"错误: {e}\n")