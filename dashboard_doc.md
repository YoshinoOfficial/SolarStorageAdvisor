# 可视化平台开发文档

## 目录

- [1. 项目概述](#1-项目概述)
- [2. 技术架构](#2-技术架构)
- [3. 项目结构](#3-项目结构)
- [4. 核心功能模块](#4-核心功能模块)
  - [4.1 天气配置页](#41-天气配置页)
  - [4.2 设备配置页](#42-设备配置页)
  - [4.3 优化算法页](#43-优化算法页)
  - [4.4 Dashboard 监控大屏](#44-dashboard-监控大屏)
- [5. API接口文档](#5-api接口文档)
- [6. 前端架构](#6-前端架构)
- [7. 数据可视化](#7-数据可视化)
- [8. 响应式设计](#8-响应式设计)
- [9. 开发指南](#9-开发指南)
- [10. 后续开发建议](#10-后续开发建议)

---

## 1. 项目概述

本项目是一个零碳园区能源系统的可视化平台，提供能源设备配置管理、优化算法结果展示和实时运行监控功能。平台基于Flask后端 + 原生前端（HTML/CSS/JavaScript）+ Plotly图表库构建。

### 1.1 设计目标

- **设备配置管理**：光伏板、储能系统、风机的参数配置
- **优化结果展示**：ADMM算法收敛曲线、多场景对比分析
- **实时运行监控**：日运行仿真、年化运行分析、社区级详情
- **天气场景配置**：典型天气天数分配、风光功率曲线编辑
- **数据驱动**：基于后端API动态加载和更新数据

### 1.2 核心特性

1. **双页面架构**：配置页面（index）与监控大屏（dashboard）分离
2. **日/年双视图**：Dashboard 支持日运行监控和年化运行情况两种视角
3. **实时仿真**：支持导入 CSV 风光出力数据，一键运行 MILP 优化调度
4. **社区级下钻**：从园区总览到居民区/商业区/工业区的多层级详情
5. **节点电压可视化**：IEEE 33 节点拓扑图 + 电压偏差热力图
6. **天气配置内嵌**：Dashboard 内可直接编辑天气天数和功率曲线，无需跳转

---

## 2. 技术架构

### 2.1 技术栈

| 层级 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **后端** | Python + Flask | Flask 2.x | Web框架，提供REST API |
| **前端** | HTML5 + CSS3 + JavaScript | ES6+ | 原生前端，无框架依赖 |
| **图表** | Plotly.js | 2.27.0 | 交互式图表库 |
| **数据处理** | Pandas + NumPy | - | 后端数据分析 |
| **图表生成** | Matplotlib | - | 后端图表生成（转Base64） |
| **优化引擎** | MATLAB (可选) | - | ADMM/集中式优化算法 |

### 2.2 架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Browser)                        │
│  ┌──────────────────────┐  ┌──────────────────────────────┐ │
│  │   配置页面 (index)     │  │  监控大屏 (dashboard)         │ │
│  │  ┌─────┬─────┬─────┐ │  │  ┌──────────┬──────────────┐ │ │
│  │  │天气 │设备 │优化 │ │  │  │日运行监控 │ 年化运行情况  │ │ │
│  │  │配置 │配置 │算法 │ │  │  │          │  ┌─────┬────┐│ │ │
│  │  └─────┴─────┴─────┘ │  │  │          │  │总览 │典型││ │ │
│  └──────────────────────┘  │  └──────────┴──┴─────┴────┘│ │ │
│                             └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     后端 (Flask Server)                      │
│  ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │
│  │ 天气配置 │ │ 设备配置  │ │ 优化算法  │ │ 日调度引擎     │  │
│  │ Manager │ │ Manager  │ │ Manager  │ │ DailyDispatch  │  │
│  └─────────┘ └──────────┘ └──────────┘ └────────────────┘  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              数据层 (JSON + CSV)                     │    │
│  │  config/  零碳园区优化_v12/  data/  s4_ddre_batch_csv/│    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 数据流

```
用户操作 → JavaScript → fetch API → Flask路由 → 数据处理 → JSON/图片响应 → 前端渲染
     ↓
  配置修改 → POST/PUT请求 → 后端验证 → 保存到JSON文件 → 返回结果
```

### 2.4 双页面架构

| 页面 | URL | 文件 | 用途 |
|------|-----|------|------|
| **配置页面** | `/` | `index.html` | 天气配置、设备配置、优化算法查看 |
| **监控大屏** | `/dashboard` | `dashboard.html` | 日/年运行监控、实时仿真、社区详情 |

两个页面共享同一 Flask 后端和 API 体系，但各自有独立的 JS 逻辑和 CSS 样式。

---

## 3. 项目结构

```
web/
├── app.py                           # Flask后端主文件 (~3086行)
├── templates/
│   ├── index.html                   # 配置页面模板 (374行)
│   └── dashboard.html               # Dashboard监控大屏模板 (740行)
├── static/
│   ├── css/
│   │   ├── style.css                # 配置页面样式 (1088行)
│   │   └── dashboard.css            # Dashboard专用样式
│   └── js/
│       ├── app.js                   # 配置页面脚本 (1408行)
│       └── dashboard.js             # Dashboard脚本 (~3450行)
└── start_dashboard.bat              # 一键启动脚本
```

---

## 4. 核心功能模块

### 4.1 天气配置页

#### 4.1.1 年度典型天气天数配置

配置各天气类型在一年中的代表天数（总和必须为365天），直接影响 Dashboard 年化指标的计算。

| 参数 | 说明 |
|------|------|
| 天气场景 | 5种典型天气：晴天少风(116)、晴天多风(178)、多云中风(137)、阴天少风(183)、阴天多风(40) |
| 代表天数 | 每种天气在一年中的天数 |
| 占比 | 自动计算百分比 |

**功能**：
- 实时验证天数总和是否为365
- 保存后 Dashboard 的年运行成本、总新能源发电量、新能源利用率会根据新天数重新计算
- 支持重置为默认值

**API**: `GET/POST /api/weather/config`, `POST /api/weather/update`

#### 4.1.2 典型天气风光功率曲线配置

编辑各典型天气场景下4个节点的归一化风光出力曲线（0~1标幺值），支持两种编辑方式：

**CSV导入方式**：
- 上传CSV文件，支持96行（15分钟间隔）或24行（小时）格式
- 4列数据：`node_22_wind`, `node_25_wind`, `node_18_PV`, `node_33_PV`
- 导入前提供数据预览（前10行）
- 保存时自动扩展为15分钟分辨率写入场景文件

**填表法方式**：
- 直接在表格中编辑24个小时的功率值
- 4个节点可独立配置
- 实时预览功率曲线图表

**功能**：
- 选择天气场景后自动加载对应功率曲线
- 保存后自动更新场景文件
- 支持"保存配置并重新运算"一键触发MATLAB优化

**API**: `GET /api/scenario-power/<scenario_id>`, `POST /api/scenario-power/<scenario_id>`, `POST /api/scenario-power/import-csv`, `POST /api/scenario-power/save-and-rerun`

#### 4.1.3 MATLAB配置

配置MATLAB路径，用于触发型优化计算。

**API**: `GET/POST /api/matlab/config`

### 4.2 设备配置页

#### 4.2.1 光伏配置管理

- **社区选择**：选择光伏社区，切换后自动加载对应配置
- **光伏板数量配置**：配置每种光伏板的安装数量
- **社区光伏发电曲线**：按天气类型展示社区总光伏出力曲线（Plotly交互图表）
- **光伏板详细配置**：面积、倾角、方位角、经纬度、海拔、环境温度、风速等参数
- **新建/删除**：支持创建自定义光伏板配置

**API**: `GET /api/config`, `POST /api/panels/quantities`, `POST /api/panels/create`, `POST /api/panels/delete`, `POST /api/panels/update`, `GET /api/community/solar-curve`, `POST /api/communities/switch`

#### 4.2.2 风电配置管理

- **风电社区选择**：选择风电社区
- **风机台数配置**：配置各社区风机安装数量
- **社区风力发电曲线**：展示社区风电出力曲线
- **风机参数展示**：查看风机技术参数

**API**: `GET /api/wind/communities`, `POST /api/wind/communities/switch`, `POST /api/wind/coefficient`, `GET /api/community/wind-curve`

#### 4.2.3 储能配置管理

- **配置切换**：支持多套储能配置方案
- **参数配置**：
  - 容量 (kWh)
  - 最大充电/放电功率 (kW)
  - 充电/放电效率
  - 初始SOC、最小SOC、最大SOC
- **新建/删除**：支持创建和删除储能配置

**API**: `POST /api/storages/switch`, `POST /api/storages/create`, `POST /api/storages/delete`, `POST /api/storages/update`

### 4.3 优化算法页

#### 4.3.1 ADMM算法收敛曲线

展示四种场景下ADMM分布式优化算法的收敛过程：
- **原始残差收敛曲线**（对数尺度）
- **对偶残差收敛曲线**（对数尺度）

四种场景：
1. S1: 无碳交易无需求响应
2. S2: 无碳交易有需求响应
3. S3: 有碳交易无需求响应
4. S4: 有碳交易有需求响应

**API**: `GET /api/optimization/chart/centralized-convergence`

### 4.4 Dashboard 监控大屏

Dashboard 是平台的核心展示页面，提供日运行监控和年化运行情况两个维度的全景视图。

#### 4.4.1 顶部导航

- **标题**：零碳园区智慧能源监控平台
- **天气配置入口**：左上角齿轮图标，点击展开/收起天气配置面板
- **日/年切换**：切换"日运行监控"和"年化运行情况"两个视图
- **实时时钟**：右上角显示当前日期和时间

#### 4.4.2 日运行监控

实时仿真页面，支持导入实际风光出力数据运行 MILP 优化调度。

**实时仿真控制面板**：
- CSV 导入：上传风光出力曲线数据
- 一键运行：触发 MILP 优化调度引擎
- 状态指示：运行状态、计算耗时

**英雄区（Hero Section）**：
- **社区地图**：居民区、商业区、工业区三个可交互区域，点击切换社区详情
- **园区总功率曲线**：展示光伏、风电、负荷、储能的综合功率曲线（Plotly交互图表）

**KPI 指标栏**：
- 日运行成本（元）
- 日购电量（MWh）
- 日碳排放（tCO₂）
- 新能源消纳率（%）

**归一化出力曲线**：
- 光伏归一化出力 (p.u.)
- 风电归一化出力 (p.u.)

**详细图表区**：
- **氢气供需曲线**：氢气产量、需求、储氢SOC
- **需求响应功率曲线**：DR聚合功率、可调节负荷
- **节点电压**：IEEE 33 节点拓扑图 + 电压偏差可视化，点击拓扑节点查看详细电压曲线

**右侧面板**：
- **实时仿真核心指标**：总发电量、购电量、碳排放、储能充放电量等
- **日能源构成**：饼图展示各类能源占比
- **日运行成本构成**：购电成本、碳交易收益、需求响应收益等
- **容量配置规划**：当前设备容量配置汇总

**社区详情**（点击社区地图触发）：
- 供电侧/用电侧功率曲线
- 储能SOC曲线
- 氢气供需曲线
- 需求响应曲线
- 能源构成饼图
- 社区级核心指标

**天气配置面板**（可折叠）：
- 典型天气天数配置表
- 典型场景风光功率曲线编辑（CSV导入 + 填表法）
- MATLAB路径配置

**API**: `POST /api/daily-dispatch/run`, `GET /api/daily-dispatch/result/latest`, `GET /api/daily-dispatch/curve`, `POST /api/daily-dispatch/optimize-milp`, `GET /api/optimization/daily-kpis`, `GET /api/optimization/energy-summary`, `GET /api/optimization/chart/h2-power-data`, `GET /api/optimization/chart/dr-power-data`, `GET /api/optimization/chart/cost-breakdown`, `GET /api/optimization/chart/community-h2-dr-data`, `GET /api/optimization/chart/node-voltage-data`

#### 4.4.3 年化运行情况

分为"总览"和"典型日运行情况"两个子视图。

**总览视图**：
- **全年加权KPI**：年运行成本、年购电量、年碳排放、新能源利用率、年碳交易收益、年售电收益
- **储能SOC统计**：平均SOC、最低SOC、最高SOC

**典型日运行情况视图**：
- **场景选择器**：4个优化场景按钮切换（S1~S4）
- **社区卡片**：居民区、商业区、工业区 + 天气信息卡片，点击切换社区详情
- **园区总功率曲线**：光伏/风电/负荷/储能的综合功率曲线（Plotly交互图表）
- **KPI指标栏**：日运行成本、日购电量、日碳排放、新能源消纳率
- **氢气供需曲线**：氢气产量、需求、储氢SOC
- **需求响应功率曲线**：DR聚合功率、可调节负荷
- **节点电压**：IEEE 33 节点拓扑图 + 电压偏差可视化
- **年度成本构成分析**：购电成本、燃气成本、运维成本、碳交易收益等
- **能源构成**：各类能源占比饼图
- **典型天气权重概览**：各天气类型的天数和占比
- **容量配置规划**：光伏、风机、储能的容量配置汇总
- **典型数据表**：各场景下的关键指标数据

**API**: `GET /api/optimization/annual-summary`, `GET /api/optimization/s4-annual-kpis`, `GET /api/optimization/typical-scenarios`, `GET /api/optimization/scenario-metrics`, `GET /api/optimization/chart/renewable-utilization`, `GET /api/optimization/chart/hourly-power-data`, `GET /api/optimization/chart/community-power-data`, `GET /api/optimization/chart/carbon-analysis`, `GET /api/optimization/chart/economic-comparison`, `GET /api/optimization/chart/centralized-convergence`, `GET /api/planning/capacity`, `GET /api/planning/annual-cost-breakdown`

---

## 5. API接口文档

### 5.1 响应格式

所有API返回JSON格式：

```json
{
    "success": true,
    "data": { ... }
}
```

错误响应：

```json
{
    "success": false,
    "error": "错误信息"
}
```

### 5.2 核心API列表

| 方法 | 路径 | 说明 |
|------|------|------|
| **天气配置** | | |
| GET | `/api/weather/config` | 获取天气配置 |
| POST | `/api/weather/update` | 更新天气配置 |
| GET | `/api/scenario-power/<id>` | 获取场景功率曲线 |
| POST | `/api/scenario-power/<id>` | 保存场景功率曲线 |
| POST | `/api/scenario-power/import-csv` | CSV导入功率曲线 |
| POST | `/api/scenario-power/save-and-rerun` | 保存并重新运算 |
| GET/POST | `/api/matlab/config` | MATLAB配置 |
| **设备配置** | | |
| GET | `/api/config` | 获取系统配置 |
| POST | `/api/panels/quantities` | 批量更新光伏板数量 |
| POST | `/api/panels/create` | 创建光伏板配置 |
| POST | `/api/panels/delete` | 删除光伏板配置 |
| POST | `/api/panels/update` | 更新光伏板配置 |
| GET | `/api/communities` | 获取社区列表 |
| POST | `/api/communities/switch` | 切换社区 |
| GET | `/api/community/solar-curve` | 获取社区光伏曲线 |
| GET | `/api/wind/communities` | 获取风电社区列表 |
| POST | `/api/wind/communities/switch` | 切换风电社区 |
| POST | `/api/wind/coefficient` | 设置风电系数 |
| GET | `/api/community/wind-curve` | 获取社区风力曲线 |
| POST | `/api/storages/switch` | 切换储能配置 |
| POST | `/api/storages/create` | 创建储能配置 |
| POST | `/api/storages/delete` | 删除储能配置 |
| POST | `/api/storages/update` | 更新储能配置 |
| POST | `/api/electricity-price/update` | 更新电价配置 |
| POST | `/api/feed-in-price/update` | 更新上网电价 |
| **日调度** | | |
| GET | `/api/daily-dispatch/config` | 获取日调度配置 |
| PUT | `/api/daily-dispatch/config` | 更新日调度配置 |
| POST | `/api/daily-dispatch/run` | 运行日调度 |
| GET | `/api/daily-dispatch/result/latest` | 获取最新调度结果 |
| GET | `/api/daily-dispatch/curve` | 获取调度曲线 |
| POST | `/api/daily-dispatch/optimize-milp` | 运行MILP优化 |
| **优化结果** | | |
| GET | `/api/optimization/annual-summary` | 获取年度汇总 |
| GET | `/api/optimization/s4-annual-kpis` | S4年度KPI |
| GET | `/api/optimization/typical-scenarios` | 获取典型场景列表 |
| GET | `/api/optimization/typical-metrics` | 获取典型场景指标 |
| GET | `/api/optimization/daily-kpis` | 获取日KPI |
| GET | `/api/optimization/energy-summary` | 获取能源汇总 |
| GET | `/api/optimization/scenario-metrics` | 获取场景指标 |
| GET | `/api/optimization/chart/renewable-utilization` | 新能源消纳图 |
| GET | `/api/optimization/chart/hourly-power-data` | 小时功率数据 |
| GET | `/api/optimization/chart/community-power-data` | 社区功率数据 |
| GET | `/api/optimization/chart/carbon-analysis` | 碳排放分析图 |
| GET | `/api/optimization/chart/economic-comparison` | 经济性对比图 |
| GET | `/api/optimization/chart/centralized-convergence` | ADMM收敛曲线 |
| GET | `/api/optimization/chart/hourly-power` | 小时功率图 |
| GET | `/api/optimization/chart/h2-shortage` | 氢气短缺图 |
| GET | `/api/optimization/chart/h2-power-data` | 氢气功率数据 |
| GET | `/api/optimization/chart/dr-power-data` | 需求响应数据 |
| GET | `/api/optimization/chart/cost-breakdown` | 成本构成数据 |
| GET | `/api/optimization/chart/community-h2-dr-data` | 社区氢气/DR数据 |
| GET | `/api/optimization/chart/node-voltage-data` | 节点电压数据 |
| **容量规划** | | |
| GET | `/api/planning/capacity` | 获取容量配置 |
| GET | `/api/planning/annual-cost-breakdown` | 年度成本分解 |
| GET | `/api/planning/device-status` | 设备状态 |

### 5.3 图表数据格式

#### 功率数据格式

```json
{
    "success": true,
    "data": {
        "hours": [0, 1, 2, ...],
        "pv_power": [0, 0, 0.1, ...],
        "wind_power": [0.2, 0.3, 0.4, ...],
        "load_power": [100, 95, 90, ...],
        "storage_power": [-10, -5, 5, ...]
    }
}
```

#### 成本数据格式

```json
{
    "success": true,
    "data": {
        "categories": ["光伏", "风电", "储能", "电网购电"],
        "values": [1000, 500, 200, 800],
        "colors": ["#f39c12", "#3498db", "#2ecc71", "#e74c3c"]
    }
}
```

#### 图表图片格式（Base64）

```json
{
    "success": true,
    "data": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

## 6. 前端架构

### 6.1 文件结构

#### 配置页面
- **index.html**：配置页面主模板，包含天气配置、设备配置、优化算法三个Tab
- **style.css**：配置页面专用样式（1088行）
- **app.js**：配置页面交互逻辑（1408行），包括Tab切换、数据加载、表单处理、图表渲染

#### Dashboard 监控大屏
- **dashboard.html**：Dashboard主模板（740行），包含日/年两个视图
- **dashboard.css**：Dashboard专用样式（深色主题）
- **dashboard.js**：Dashboard交互逻辑（~3450行），包括日调度、年化分析、社区详情、电压拓扑

### 6.2 CSS类命名规范

| 前缀 | 说明 | 示例 |
|------|------|------|
| `.btn-*` | 按钮类 | `.btn-primary`, `.btn-secondary`, `.btn-danger` |
| `.form-*` | 表单类 | `.form-group`, `.form-row`, `.form-actions` |
| `.config-*` | 配置区域 | `.config-section`, `.config-form`, `.config-header` |
| `.chart-*` | 图表容器 | `.chart-container`, `.chart-container-hero`, `.chart-container-sm` |
| `.panel-*` | 面板卡片 | `.panel-card`, `.panel-header`, `.panel-badge` |
| `.metric-*` | 指标卡片 | `.metric-card`, `.metric-card.compact` |
| `.daily-*` | 日运行相关 | `.daily-kpi-bar`, `.daily-dispatch-panel` |
| `.annual-*` | 年化相关 | `.annual-typical-only`, `.annual-power-card` |
| `.community-*` | 社区相关 | `.community-map`, `.map-community` |
| `.weather-*` | 天气配置 | `.weather-config-table`, `.weather-panel` |
| `.voltage-*` | 电压相关 | `.voltage-panel`, `.voltage-topology` |

### 6.3 JavaScript函数命名规范

| 前缀 | 说明 | 示例 |
|------|------|------|
| `load*` | 加载数据 | `loadConfig()`, `loadOverviewData()` |
| `save*` | 保存数据 | `savePanelQuantities()`, `saveWeatherConfig()` |
| `render*` | 渲染图表 | `renderPowerOverviewChart()`, `renderDailyPowerChart()` |
| `update*` | 更新UI | `updateUI()`, `updateAnnualWeatherDays()` |
| `switch*` | 切换视图 | `switchCommunity()`, `switchDashboardWindow()` |
| `select*` | 选择操作 | `selectCommunity()`, `selectDailyCommunityView()` |
| `db*` | Dashboard内嵌天气配置 | `dbLoadWeatherConfig()`, `dbSaveScenarioPower()` |
| `daily*` | 日运行相关 | `runDailyDispatch()`, `renderDailyOverview()` |

### 6.4 Tab切换机制

配置页面使用HTML5 data属性实现Tab切换：

```html
<button class="tab-btn active" data-tab="weather">天气配置</button>
<div id="tab-weather" class="tab-pane active">
```

Dashboard使用窗口切换机制：

```html
<button class="dashboard-window-btn active" data-window="daily" onclick="switchDashboardWindow('daily')">日运行监控</button>
<button class="dashboard-window-btn" data-window="annual" onclick="switchDashboardWindow('annual')">年化运行情况</button>
```

### 6.5 模态框系统

```html
<div id="modal-overlay" class="modal-overlay">
    <div class="modal">
        <h3 id="modal-title">标题</h3>
        <div id="modal-content">内容</div>
    </div>
</div>
```

**使用方式**：

```javascript
// 显示模态框
showCreatePanelModal();

// 关闭模态框
closeModal();

// 确认操作
confirmModal();
```

---

## 7. 数据可视化

### 7.1 图表类型

| 图表类型 | 技术实现 | 应用场景 |
|----------|----------|----------|
| **交互式图表** | Plotly.js | 功率曲线、SOC曲线、社区详情 |
| **静态图片** | Matplotlib → Base64 | ADMM收敛曲线、经济性对比 |
| **拓扑图** | SVG + JavaScript | IEEE 33节点电压拓扑 |
| **热力图** | SVG填充色 | 电压偏差区域可视化 |
| **饼图** | Plotly.js | 能源构成、成本构成 |
| **KPI卡片** | HTML + CSS | 关键指标展示 |

### 7.2 图表容器尺寸

| 类名 | 尺寸 | 用途 |
|------|------|------|
| `.chart-container-hero` | 大尺寸 | 主功率曲线 |
| `.chart-container` | 标准尺寸 | 详细图表 |
| `.chart-container-sm` | 小尺寸 | 辅助图表 |

### 7.3 电压拓扑可视化

IEEE 33 节点配电系统拓扑图：
- 使用 SVG 多边形渲染节点区域
- 颜色映射：绿色（正常）→ 黄色（偏差中等）→ 红色（偏差严重）
- 支持点击节点查看详细电压时间序列
- 支持小时回放功能

---

## 8. 响应式设计

### 8.1 断点设置

```css
/* 移动端 */
@media (max-width: 768px) { ... }

/* 平板端 */
@media (max-width: 1024px) { ... }

/* 桌面端 */
@media (min-width: 1025px) { ... }
```

### 8.2 布局策略

- **桌面端**：多列网格布局，侧边栏 + 主内容区
- **平板端**：两列布局，部分模块堆叠
- **移动端**：单列布局，完全堆叠

---

## 9. 开发指南

### 9.1 添加新的配置表单

1. **HTML结构**：

```html
<div class="config-section">
    <h3>配置标题</h3>
    <div class="config-form">
        <div class="form-row">
            <div class="form-group">
                <label>参数名:</label>
                <input type="number" id="param-id" step="1">
            </div>
        </div>
        <div class="form-actions">
            <button onclick="saveConfig()" class="btn-primary">保存</button>
        </div>
    </div>
</div>
```

2. **JavaScript函数**：

```javascript
async function saveConfig() {
    const value = document.getElementById('param-id').value;
    const res = await fetchAPI('/api/config/update', 'POST', { param: value });
    if (res.success) {
        // 更新UI
    }
}
```

3. **Flask路由**：

```python
@app.route('/api/config/update', methods=['POST'])
def update_config():
    data = request.get_json()
    param = data.get('param')
    # 处理逻辑
    return jsonify({'success': True})
```

### 9.2 添加新的图表

1. **HTML容器**：

```html
<div class="panel-card chart-panel">
    <div class="panel-header">
        <h3>图表标题</h3>
    </div>
    <div id="chart-id" class="chart-container"></div>
</div>
```

2. **Plotly图表渲染**：

```javascript
async function loadChart() {
    const res = await fetchAPI('/api/chart/data');
    if (res.success) {
        Plotly.newPlot('chart-id', res.data.traces, res.data.layout);
    }
}
```

3. **静态图片渲染**：

```javascript
async function loadStaticChart() {
    const res = await fetchAPI('/api/chart/image');
    if (res.success) {
        document.getElementById('chart-id').innerHTML = 
            `<img src="data:image/png;base64,${res.data}" style="width:100%;">`;
    }
}
```

### 9.3 添加新的API端点

```python
@app.route('/api/new/endpoint', methods=['GET'])
def new_endpoint():
    try:
        # 业务逻辑
        data = process_data()
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

### 9.4 Dashboard 开发要点

- Dashboard 使用独立的 JS 文件 `dashboard.js` 和 CSS 文件 `dashboard.css`
- 日运行和年化视图通过 `switchDashboardWindow()` 切换，切换时触对应数据加载
- 天气配置面板通过 `toggleWeatherConfig()` 展开/收起，使用 `db*` 前缀函数独立管理
- 社区详情通过 `selectCommunity()` / `selectDailyCommunityView()` 触发，动态渲染下方图表区
- 电压拓扑图使用 SVG 绘制，需要计算节点坐标和连线关系

---

## 10. 后续开发建议

### 10.1 功能扩展

1. **实时数据接入**：接入物联网设备数据，实现真正的实时监控
2. **告警系统**：添加设备异常、能源不足等告警功能
3. **历史数据对比**：支持不同日期/场景的数据对比分析
4. **导出功能**：支持图表和报表导出为PDF/Excel
5. **用户权限管理**：多用户登录和权限控制
6. **典型日结果保存**：年化视图的典型日计算结果持久化，避免每次切换场景重新计算
7. **日调度历史记录**：保存历次实时仿真结果，支持回放和对比

### 10.2 性能优化

1. **数据缓存**：对频繁访问的配置数据添加Redis缓存
2. **图表懒加载**：对非首屏图表实现懒加载
3. **API聚合**：合并多个小API减少请求次数
4. **图片压缩**：对Base64图片进行压缩优化
5. **WebSocket**：对实时仿真进度使用 WebSocket 推送替代轮询

### 10.3 代码优化

1. **组件化**：将重复的UI模式（指标卡片、图表面板等）抽象为可复用组件
2. **状态管理**：引入简单的状态管理机制，减少全局变量
3. **TypeScript**：考虑引入TypeScript提高代码质量
4. **单元测试**：为关键函数添加单元测试
5. **减少 JS 文件体积**：`dashboard.js` 已超过 3400 行，建议按功能模块拆分

---

## 附录

### A. 颜色方案

| 用途 | 颜色值 | 说明 |
|------|--------|------|
| 光伏 | `#f39c12` | 橙色 |
| 风电 | `#3498db` | 蓝色 |
| 储能充电 | `#2ecc71` | 绿色 |
| 储能放电 | `#e74c3c` | 红色 |
| 电网购电 | `#9b59b6` | 紫色 |
| 负荷 | `#e67e22` | 深橙色 |
| 碳排放 | `#e74c3c` | 红色 |
| 碳交易 | `#2ecc71` | 绿色 |

### B. 典型天气场景

| ID | 名称 | 说明 |
|----|------|------|
| 116 | 晴天少风 | 光伏出力高，风电出力低 |
| 178 | 晴天多风 | 光伏出力高，风电出力高 |
| 137 | 多云中风 | 光伏出力中等，风电出力中等 |
| 183 | 阴天少风 | 光伏出力低，风电出力低 |
| 40 | 阴天多风 | 光伏出力低，风电出力高 |

### C. 优化场景

| 场景 | 碳交易 | 需求响应 | 说明 |
|------|--------|----------|------|
| S1 | ❌ | ❌ | 基准场景 |
| S2 | ❌ | ✅ | 仅需求响应 |
| S3 | ✅ | ❌ | 仅碳交易 |
| S4 | ✅ | ✅ | 完整场景 |

### D. IEEE 33节点系统

Dashboard 中的节点电压可视化基于 IEEE 33 节点配电测试系统，包含：
- 33 个节点
- 37 条支路
- 额定电压 12.66 kV
- 总负荷 3.72 MW + 2.3 Mvar
