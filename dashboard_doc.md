# 零碳园区智慧能源可视化平台

## 1. 简介

本平台是面向零碳园区多能互补能源系统的可视化监控与配置管理平台，基于 Flask + Plotly.js 构建，提供场景对比、天气切换、社区详情、容量配置等功能。平台采用深空蓝暗色主题，针对 2560x1440 大屏适配。

平台包含两个页面：
- **配置管理页**（`/`）— 设备参数配置、光伏/风电/储能管理
- **监控大屏**（`/dashboard`）— 优化结果可视化、运行监控

---

## 2. 快速上手

### 2.1 环境依赖

需要 Python 3.8+，安装以下库：

```bash
pip install flask pandas matplotlib
```

| 库 | 用途 | 版本建议 |
|----|------|---------|
| Flask | Web 服务器 | >= 2.0 |
| Pandas | CSV 数据读取 | >= 1.5 |
| Matplotlib | 静态图表生成 | >= 3.5 |

> Plotly.js 通过 CDN 前端加载，无需安装 Python 包。

### 2.2 启动步骤

```bash
# 1. 进入项目目录
cd C:\Code\SolarStorageAdvisor

# 2. 启动 Flask 服务器
python web/app.py

# 3. 浏览器打开
#    配置管理页：http://localhost:5000/
#    监控大屏：  http://localhost:5000/dashboard
```

启动后终端会显示 `Running on http://0.0.0.0:5000`，保持终端窗口不要关闭。按 `Ctrl+C` 停止服务。

---

## 3. 监控大屏功能说明

监控大屏（`/dashboard`）是平台的核心页面，包含 **总览视图** 和 **社区详情视图** 两个层级。

### 3.1 数据维度切换

页面顶部提供两种数据查看维度，通过切换按钮选择：

| 维度 | 数据来源 | 选项 |
|------|---------|------|
| **场景**（碳交易×需求响应） | `comparison_plot_data_csv/` | S1（基准）、S2（仅DR）、S3（仅碳交易）、S4（完整） |
| **天气** | `year_plot_data_csv/` | 晴天少风、晴天多风、多云中风、阴天少风、阴天多风 |

切换后，功率曲线、氢气供需、需求响应、能源构成、日核心指标等所有图表同步更新。

### 3.2 总览视图布局

总览视图采用 **主内容区 + 右侧边栏** 的两栏布局。

#### 主内容区

**第一行：社区地图 + 园区总功率曲线**
- 左侧三个社区卡片（居民区、商业区、工业区），点击进入社区详情
- 右侧功率曲线含三个子图：供电侧堆叠图、用电侧堆叠图、储能SOC曲线

**日核心指标栏**
- 4 个指标卡，随场景/天气切换实时更新（带数值过渡动画）：
  - 日运行成本（元）
  - 日购电量（MWh）
  - 日碳排放（tCO₂）
  - 新能源消纳率（%）

**交互图表行**
- 氢气供需曲线 — 供需平衡堆叠图 + 氢储能SOC
- 需求响应功率曲线 — 负荷对比图 + DR动作图 + 汇总指标栏
- 年度成本构成 — 投资/运维/运行/碳交易等成本环形图

**静态分析图表行**
- 经济性对比、可再生能源利用、碳排放分析、氢气短缺分析

**设备状态栏**
- 设备状态（光伏/风电/储能/负荷）、储能SOC仪表盘、今日告警

#### 右侧边栏

- **核心指标** — 总发电量、年总成本、年碳排放、新能源利用率
- **辅助指标** — 全年购电量、购气量、碳配额、碳交易收益、弃风弃光、氢气短缺
- **能源构成** — 各电源占比环形图（随场景/天气切换）
- **典型场景数据** — 5种天气场景的天数、成本、碳排放、新能源率汇总表
- **容量配置规划** — 3个社区的PV/风电/电池/热储/氢储容量表

### 3.3 社区详情视图

点击总览视图中的社区卡片进入。顶部有独立的场景/天气切换器，与总览视图联动。

**容量指标栏（7列）**

| 指标 | 数据来源 |
|------|---------|
| 光伏（MW） | `planning_capacity_result.csv` |
| 风电（MW） | 同上 |
| 电储能（MWh） | 同上 |
| 热储能（MWh） | 同上 |
| 氢储能（kg） | 同上 |
| 储能功率（MW） | 同上 |
| 日发电量（MWh） | 从图表数据实时计算 |

**图表区域（3×2 网格）**
- 供电侧、用电侧、储能SOC（全宽）、氢气供需、需求响应、能源构成
- 所有图表均支持场景/天气切换

---

## 4. 配置管理页

配置管理页（`/`）提供设备参数的可视化配置与风光功率曲线编辑，包含三个标签页：

### 4.1 天气配置

包含两个子标签页：

**天数配置**
- 编辑 5 种典型天气场景的代表天数（总和必须为 365 天）
- 修改后 dashboard 的年运行成本、总新能源发电量等指标会根据新天数重新计算

**典型场景风光功率曲线配置**
- 选择天气场景（晴天少风/晴天多风/多云中风/阴天少风/阴天多风）
- 三种编辑方式（通过子标签页切换）：
  - **CSV 导入** — 上传 CSV 文件直接导入，支持 96 行（15分钟）或 24 行（小时）格式，自动识别并保存
  - **曲线拖拽法** — Plotly 交互图表，点击选中节点后上下拖拽调整标幺值，松手自动更新
  - **填表法** — 24 行可编辑表格，直接输入各节点各时刻的标幺值
- 支持"保存配置并重新运算"：保存所有 5 个场景的功率数据后，自动调用 MATLAB 运行 `main_year.m` 重新优化
- MATLAB 可执行文件路径可在页面底部配置（首次使用需设置）

### 4.2 设备配置

三个子标签页：

- **光伏配置** — 选择社区、配置光伏板数量、查看光伏发电曲线、编辑光伏板详细参数（面积、倾角、方位角等）
- **风电配置** — 选择社区、配置风机台数、查看风力发电曲线
- **储能配置** — 切换/新建/删除储能配置，编辑容量、充放电功率、效率、SOC 上下限等参数

### 4.3 优化算法

展示 ADMM 分布式优化算法的收敛曲线（原始残差和对偶残差随迭代次数的下降过程）。

---

## 5. API 接口

### 5.1 优化结果接口

| 方法 | 路径 | 说明 | 支持 mode 参数 |
|------|------|------|---------------|
| GET | `/api/optimization/annual-summary` | 年度加权汇总 | - |
| GET | `/api/optimization/daily-kpis` | 日核心指标（成本/购电/碳排/消纳率） | scenario / weather |
| GET | `/api/optimization/energy-summary` | 能源构成汇总 | scenario / weather |
| GET | `/api/optimization/chart/hourly-power-data` | 24h 功率数据 | scenario / weather |
| GET | `/api/optimization/chart/community-power-data` | 社区级功率数据 | scenario / weather |
| GET | `/api/optimization/chart/h2-power-data` | 氢气供需数据 | scenario / weather |
| GET | `/api/optimization/chart/dr-power-data` | 需求响应数据 | scenario / weather |
| GET | `/api/optimization/chart/community-h2-dr-data` | 社区级氢气/DR | scenario / weather |
| GET | `/api/optimization/chart/cost-breakdown` | 成本构成 | scenario |
| GET | `/api/optimization/typical-metrics` | 典型场景指标 | - |
| GET | `/api/optimization/typical-scenarios` | 典型场景配置 | - |

**mode 参数说明：**

```
# 场景模式（默认）
GET /api/optimization/chart/hourly-power-data?scenario=S4

# 天气模式
GET /api/optimization/chart/hourly-power-data?mode=weather&weather=Sunny_LowWind
```

### 5.2 规划配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/planning/capacity` | 分社区容量配置（PV/风电/储能/热储/氢储） |
| GET | `/api/planning/device-status` | 设备状态汇总 |
| GET | `/api/planning/annual-cost-breakdown` | 年成本分解 |

### 5.3 静态图表接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/optimization/chart/economic-comparison` | 经济性对比（Matplotlib PNG） |
| GET | `/api/optimization/chart/renewable-utilization` | 可再生能源利用 |
| GET | `/api/optimization/chart/carbon-analysis` | 碳排放分析 |
| GET | `/api/optimization/chart/h2-shortage` | 氢气短缺分析 |
| GET | `/api/optimization/chart/admm-convergence` | ADMM 收敛曲线 |

### 5.4 风光功率配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/scenario-power/list` | 获取 5 个典型天气场景列表 |
| GET | `/api/scenario-power/<id>` | 获取指定场景的 24h 风光功率数据 |
| POST | `/api/scenario-power/<id>` | 保存指定场景的 24h 风光功率数据（自动扩展为 15 分钟） |
| POST | `/api/scenario-power/import-csv` | CSV 文件导入（支持 96 行或 24 行，自动识别） |
| POST | `/api/scenario-power/save-and-rerun` | 保存全部 5 个场景并调用 MATLAB 重新优化 |
| GET | `/api/matlab/config` | 获取 MATLAB 可执行文件路径 |
| POST | `/api/matlab/config` | 设置 MATLAB 可执行文件路径 |

### 5.5 天气配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/weather/config` | 获取 5 种天气的代表天数 |
| POST | `/api/weather/update` | 更新代表天数（校验总和=365） |

### 5.6 设备配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/config` | 获取完整配置 |
| POST | `/api/calculate` | 触发模拟计算 |
| GET/POST | `/api/panels/*` | 光伏板 CRUD |
| POST | `/api/storages/*` | 储能配置 CRUD |
| POST | `/api/communities/switch` | 切换当前社区 |
| POST | `/api/communities/quantities` | 更新光伏板数量 |
| GET | `/api/community/solar-curve` | 光伏发电曲线 |
| GET | `/api/community/wind-curve` | 风力发电曲线 |
| POST | `/api/wind/coefficient` | 更新风机台数 |

---

## 6. 目录结构

```
web/
├── app.py                    # Flask 后端，API 路由与数据处理
├── templates/
│   ├── index.html            # 配置管理页
│   └── dashboard.html        # 监控大屏
└── static/
    ├── css/
    │   ├── style.css          # 配置管理页样式
    │   └── dashboard.css      # 监控大屏样式（深空蓝主题）
    └── js/
        ├── app.js             # 配置管理页逻辑
        └── dashboard.js       # 监控大屏逻辑
```
