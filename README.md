# 零碳园区能源系统 (SolarStorageAdvisor)

**项目目标**：结合用户特点，提供光伏发电和储能成本可行性分析，为用户提供"零碳园区"的建设依据。

**关键词**：光伏发电能力、风力发电、储能、负荷曲线、峰谷电价套利、碳证交易、优化算法

---

## 项目流程

本项目采用三阶段流程实现零碳园区的能源管理与优化：

### 阶段一：新能源出力计算
使用专业物理模型计算园区的新能源发电能力

| 模块 | 技术 | 说明 |
|------|------|------|
| 光伏发电 | pvlib | 支持晴天/多云/阴天/雨天/雾天等多种天气类型 |
| 风力发电 | windpowerlib | ModelChain功率曲线计算 |
| 负荷预测 | 统计分析 | 工业/商业/居民负荷 |

**光伏计算流程图：**

![光伏出力pvlib流程图](Solar/光伏出力pvlib流程图.png)

### 阶段二：优化控制策略
使用 MATLAB 实现的高级优化算法

| 算法 | 说明 |
|------|------|
| 集中式优化 | 全局最优控制策略 |
| ADMM分散式优化 | 分布式协同优化 |
| 储能控制 | 考虑充放电效率和老化的储能策略 |
| 碳交易 | 碳排放核算与碳证交易 |

**支持200+个日场景的优化分析**

### 阶段三：可视化平台
基于 Flask 的 Web 可视化系统

- **配置管理**：天气场景配置、光伏/风电/储能设备参数管理
- **日运行监控**：实时仿真优化、社区级功率曲线、节点电压拓扑
- **年化运行分析**：全年加权KPI、典型日场景对比、成本构成分析
- **经济性分析**：成本收益计算、碳交易收益

**Dashboard 监控大屏：**

![日运行监控](可视化平台截图/日运行1.png)

![年化运行情况-总览](可视化平台截图/年化典型日1.png)

![年化运行情况-典型日](可视化平台截图/年化典型日2.png)

---

## 项目结构

```
SolarStorageAdvisor/
├── Solar/                      # 光伏计算模块
│   ├── Solar.py               # pvlib光伏功率计算
│   ├── Solar_auto.py          # 自动光伏配置
│   └── pvlib_guide.md         # pvlib使用指南
│
├── Wind/                       # 风电计算模块
│   ├── Wind.py                # windpowerlib风力发电计算
│   ├── modelchain_example.py  # ModelChain使用示例
│   └── weather.csv            # 气象数据
│
├── Consumption/               # 负荷计算模块
│   ├── Consumption.py         # 基础负荷
│   └── IndustrialConsumption.py # 工业负荷
│
├── Storage/                    # 储能模拟模块
│   └── Storage.py             # 储能充放电模拟
│
├── web/                       # Web可视化平台
│   ├── app.py                # Flask应用 (~3000行)
│   ├── templates/
│   │   ├── index.html        # 配置页面
│   │   └── dashboard.html    # Dashboard监控大屏
│   └── static/
│       ├── css/
│       │   ├── style.css     # 配置页样式
│       │   └── dashboard.css # Dashboard样式
│       └── js/
│           ├── app.js        # 配置页脚本
│           └── dashboard.js  # Dashboard脚本
│
├── 零碳园区优化_v8/           # MATLAB优化算法
│   ├── build_case.m         # 构建优化问题
│   ├── solve_centralized.m  # 集中式求解器
│   ├── solve_admm_fixed.m   # ADMM分散式求解器
│   ├── carbon_accounting.m  # 碳排放核算
│   ├── comparison_metric_table.csv # 对比指标表
│   └── 1-Day Scenarios/      # 日场景数据(200个)
│
├── config/                    # 配置文件
│   ├── config_manager.py     # 配置管理
│   └── Storage/configs/      # 储能配置
│
└── main.py                   # 主程序入口
```

---

## 技术栈

### 后端
- **Python 3.x**：核心计算语言
- **pvlib**：光伏系统仿真
- **windpowerlib**：风力发电仿真
- **Flask**：Web框架
- **MATLAB**：优化算法实现

### 前端
- **HTML5**：页面结构（配置页 + Dashboard双页面）
- **CSS3**：响应式设计、深色主题Dashboard
- **JavaScript (ES6+)**：交互逻辑、异步API调用
- **Plotly.js**：交互式数据可视化
- **SVG**：IEEE 33节点拓扑图渲染

### 优化算法
- **MATLAB**：优化问题建模与求解
- **ADMM**：交替方向乘子法
- **集中式/分散式**：两种优化架构

---

## 快速开始

### 1. 安装依赖

```bash
pip install pvlib windpowerlib flask pandas numpy matplotlib
```

### 2. 运行新能源计算

```python
from Solar.Solar import getsolar
from Wind.Wind import getwind

# 计算光伏出力
solar = getsolar(community="community1", start="2010-06-01", end="2010-06-02")

# 计算风电出力
wind = getwind(start="2010-06-01", end="2010-06-01", community="community1")
```

### 3. 启动Web服务

**方式一：一键启动（推荐）**

双击项目根目录的 `start_dashboard.bat`，自动启动 Flask 服务并打开浏览器。

**方式二：手动启动**

```bash
python web/app.py
```

然后在浏览器中访问 `http://localhost:5000`

- 配置页面：`http://localhost:5000/`
- Dashboard 监控大屏：`http://localhost:5000/dashboard`

---

## 功能特点

1. **多能源互补**：光伏+风电+储能+氢能的多能互补系统
2. **多场景分析**：支持200+个典型日场景的优化分析（ADMM分散式 + 集中式）
3. **实时仿真优化**：导入实际风光数据运行MILP调度优化
4. **灵活配置**：支持光伏板、储能、风机的多种配置方案
5. **社区级监控**：居民区/商业区/工业区多层级详情下钻
6. **节点电压分析**：IEEE 33节点拓扑可视化 + 电压偏差热力图
7. **碳交易与需求响应**：碳排放核算、碳证交易、DR聚合优化
8. **经济性优化**：考虑电价套利、碳交易、售电收益等经济因素
9. **可视化展示**：日/年双视图Dashboard、交互式Plotly图表

---

## 计算板块

1. **负荷曲线**：日/年负荷曲线，置信区间
2. **光伏出力**：一次成本、可变成本、波动性、老化
3. **储能**：一次成本、可变成本、充放电效率、老化
4. **生命周期成本及碳证书成本**：运营维护、碳证价格

最终结合工业电价计算总成本，目标是使得成本最低（回本周期最短），从而实现提供"零碳园区"的建设依据。

---

## 后续改进方向

### 1. 日收益计算模块
- 实现每日收益的精确计算
- 区分峰谷电价收益
- 考虑余电上网收益

### 2. 投资回报分析
- **设备一次投资成本**：
  - 光伏组件投资成本
  - 风力发电机投资成本
  - 储能系统投资成本
  - 配套设施投资成本

- **折旧成本计算**：
  - 光伏组件25年折旧
  - 风机20年折旧
  - 储能系统10年折旧

- **回报率分析**：
  - 内部收益率(IRR)
  - 净现值(NPV)
  - 投资回报率(ROI)

- **回本周期计算**：
  - 静态回本周期
  - 动态回本周期（考虑资金时间价值）

### 3. 经济性优化目标扩展
```
目标函数 = min(年化总成本 - 年化新能源收益 - 年化碳证收益 - 年化补贴)

约束条件：
- 功率平衡约束
- 储能SOC约束
- 设备容量约束
- 电网接入约束
```

