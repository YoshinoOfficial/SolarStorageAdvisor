# 零碳园区优化 v12 数据结构说明

本文档描述 `零碳园区优化_v12/` 目录下所有 CSV 结果文件的结构、列含义和场景定义。

---

## 一、场景定义

### 1.1 对比场景（comparison）：碳交易 x 需求响应 2x2 矩阵

| 场景 | 名称 | 碳交易 | 需求响应(DR) | 说明 |
|------|------|--------|-------------|------|
| S1 | S1_NoCarbon_NoDR | 无 | 无 | 基准场景 |
| S2 | S2_Normal_NoCarbon_DR | 无 | 有 | 仅启用DR |
| S3 | S3_Carbon_NoDR | 有 | 无 | 仅启用碳交易 |
| S4 | S4__Carbon_DR | 有 | 有 | 完整场景（注意名称含双下划线） |

每个场景均使用 **集中式优化（centralized）** 和 **ADMM分布式优化** 两种方法求解。

### 1.2 年度典型天气场景（year）：5种天气类型

| 天气场景 | 英文名 | 代表天数 | PV标签 | 风电标签 | DDRE场景ID |
|----------|--------|---------|--------|---------|-----------|
| 晴天少风 | Sunny_LowWind | 94天 | 0(晴) | 0(低) | 116 |
| 晴天多风 | Sunny_HighWind | 51天 | 0(晴) | 2(高) | 178 |
| 多云中风 | Cloudy_MidWind | 72天 | 1(多云) | 1(中) | 137 |
| 阴天少风 | Rainy_LowWind | 69天 | 2(阴) | 0(低) | 183 |
| 阴天多风 | Rainy_HighWind | 79天 | 2(阴) | 2(高) | 40 |

> 5种天气的代表天数之和 = 94+51+72+69+79 = **365天**（全年）

### 1.3 年度指标计算方式

年成本等年度参数 = **S4场景下各典型天气的日运行指标 x 该天气的代表天数，再求和**。

公式：`年指标 = Σ(日指标_weather_i × 代表天数_i)`，i = 1..5

- 年度运行使用 **S4场景（碳交易+DR均启用）** 的配置
- 容量配置来自 `园区规划与容量配置/planning_capacity_result.csv`（规划优化结果），PV放大5倍、风电放大5倍

---

## 二、根目录文件

根目录包含 5 个 CSV 结果文件和若干 MATLAB 源码/数据文件。

> **关于重复行**：部分 CSV 文件（`year_typical_scenario_metric_table.csv`、`year_annual_weighted_summary.csv`）每个场景/天气包含 2 行数据，分别对应**集中式优化（centralized）**和 **ADMM分布式优化**两种方法的结果。调用时只需取集中式结果，即每组的第一行。有 `Method` 列的文件（如 `comparison_metric_table.csv`）可通过 `Method.str.contains('centralized')` 筛选；无 `Method` 列的文件使用 `drop_duplicates(subset=['TypicalScenario'])` 去重。

### 2.1 comparison_metric_table.csv — 场景对比优化指标表

**用途**：4种场景 × 2种方法的优化目标和收敛指标对比

**行数**：8行（4场景 × 2方法）

**列（12列）**：

| 列名 | 含义 | 单位 |
|------|------|------|
| `Scenario` | 场景英文名 | - |
| `ScenarioCN` | 场景中文名 | - |
| `Method` | 优化方法 | - |
| `Status` | 求解状态（Solved） | - |
| `TotalObjective_Yuan` | 日总目标函数值 | 元 |
| `Iterations` | ADMM迭代次数（集中式为NaN） | 次 |
| `CarbonTradingCost_Yuan` | 碳交易成本（负值=碳交易收益） | 元 |
| `ADMMPrimalResidual` | ADMM原始残差（集中式为NaN） | - |
| `ADMMDualResidual` | ADMM对偶残差（集中式为NaN） | - |
| `MaxConsensusP_MW` | 有功功率最大共识偏差 | MW |
| `MaxConsensusQ_MVAr` | 无功功率最大共识偏差 | MVAr |
| `MaxConsensusCarbon_kg` | 碳排放最大共识偏差 | kg |

### 2.2 comparison_summary.csv — 场景对比详细汇总表

**用途**：4种场景 × 2种方法的能源平衡与碳排放详细指标

**行数**：8行（4场景 × 2方法）

**列（20列）**：

| 列名 | 含义 | 单位 |
|------|------|------|
| `Scenario` | 场景英文名 | - |
| `ScenarioCN` | 场景中文名 | - |
| `Method` | 优化方法 | - |
| `Status` | 求解状态 | - |
| `TotalObjective_Yuan` | 日总目标函数值 | 元 |
| `GridEnergy_MWh` | 日购电量 | MWh |
| `GasEnergy_MWhth` | 日燃气消耗量（热值） | MWh_th |
| `CarbonEmission_kg` | 日碳排放量 | kg |
| `CarbonQuota_kg` | 日碳配额 | kg |
| `CarbonSurplusBeforeTrade_kg` | 碳交易前碳盈余（正=盈余） | kg |
| `CarbonBuyMarket_kg` | 从碳市场购买量 | kg |
| `CarbonSellMarket_kg` | 向碳市场出售量 | kg |
| `CarbonTradeAbs_kg` | 碳交易总量绝对值 | kg |
| `CarbonUnusedAllowance_kg` | 未使用碳配额 | kg |
| `RenewableAvailable_MWh` | 可用新能源发电量 | MWh |
| `RenewableUse_MWh` | 实际新能源消纳量 | MWh |
| `RenewableCurtailment_MWh` | 新能源弃电量 | MWh |
| `RenewableUseRate_percent` | 新能源消纳率 | % |
| `AvgMinimumVoltage_pu` | 平均最低电压 | p.u. |
| `GridVoltageDeviation_pu` | 电网电压偏差 | p.u. |

### 2.3 year_typical_scenario_metric_table.csv — 年度典型天气指标表

**用途**：5种天气场景 × 2种方法的日运行与年化指标（基于S4场景+规划容量）

**行数**：10行（5天气 × 2方法）

**列（42列）**：

| 列名 | 含义 | 单位 |
|------|------|------|
| `TypicalScenario` | 天气场景英文名 | - |
| `TypicalScenarioCN` | 天气场景中文名 | - |
| `DDREScenarioId` | 1-Day Scenarios中的场景编号 | - |
| `PVLabel` | PV天气标签（0晴/1多云/2阴） | - |
| `WindLabel` | 风电标签（0低/1中/2高） | - |
| `RepresentativeDays` | 该天气的年代表天数 | 天 |
| `TotalObjective_Yuan` | 日总目标函数值 | 元 |
| `AnnualObjective_Yuan` | 年化目标函数值（日值×代表天数） | 元 |
| `GridEnergy_MWh` | 日购电量 | MWh |
| `AnnualGridEnergy_MWh` | 年化购电量 | MWh |
| `GridPeak_MW` | 日电网功率峰值 | MW |
| `GridPeakValleyDiff_MW` | 日电网峰谷差 | MW |
| `GasEnergy_MWhth` | 日燃气消耗量 | MWh_th |
| `AnnualGasEnergy_MWhth` | 年化燃气消耗量 | MWh_th |
| `CarbonEmission_tCO2` | 日碳排放量 | tCO₂ |
| `AnnualCarbonEmission_tCO2` | 年化碳排放量 | tCO₂ |
| `CarbonQuota_tCO2` | 日碳配额 | tCO₂ |
| `AnnualCarbonQuota_tCO2` | 年化碳配额 | tCO₂ |
| `CarbonSurplusBeforeTrade_tCO2` | 碳交易前碳盈余 | tCO₂ |
| `AnnualCarbonSurplusBeforeTrade_tCO2` | 年化碳交易前碳盈余 | tCO₂ |
| `CarbonBuyMarket_tCO2` | 日碳市场购买量 | tCO₂ |
| `AnnualCarbonBuyMarket_tCO2` | 年化碳市场购买量 | tCO₂ |
| `CarbonSellMarket_tCO2` | 日碳市场出售量 | tCO₂ |
| `AnnualCarbonSellMarket_tCO2` | 年化碳市场出售量 | tCO₂ |
| `CarbonTradeAbs_tCO2` | 日碳交易总量 | tCO₂ |
| `AnnualCarbonTradeAbs_tCO2` | 年化碳交易总量 | tCO₂ |
| `CarbonUnusedAllowance_tCO2` | 日未使用碳配额 | tCO₂ |
| `AnnualCarbonUnusedAllowance_tCO2` | 年化未使用碳配额 | tCO₂ |
| `RenewableAvailable_MWh` | 日可用新能源发电量 | MWh |
| `RenewableUse_MWh` | 日新能源消纳量 | MWh |
| `RenewableUseRate_percent` | 新能源消纳率 | % |
| `RenewableCurtailment_MWh` | 日弃电量 | MWh |
| `AnnualRenewableCurtailment_MWh` | 年化弃电量 | MWh |
| `RenewableCurtailmentRate_percent` | 弃电率 | % |
| `H2Shortage_kg` | 日氢气短缺量 | kg |
| `AnnualH2Shortage_kg` | 年化氢气短缺量 | kg |
| `HeatDump_MWh` | 日弃热量 | MWh |
| `StorageCharge_MWh` | 日储能充电量 | MWh |
| `StorageDischarge_MWh` | 日储能放电量 | MWh |
| `StorageSOCSwing_MWh` | 日储能SOC波动幅度 | MWh |
| `AvgMinimumVoltage_pu` | 平均最低电压 | p.u. |
| `GridVoltageDeviation_pu` | 电网电压偏差 | p.u. |

### 2.4 year_annual_weighted_summary.csv — 年度加权汇总表

**用途**：将5种天气的日指标按代表天数加权求和，得到全年总指标。2行分别对应集中式和ADMM方法。

**行数**：2行（2种方法）

**列（14列）**：

| 列名 | 含义 | 单位 |
|------|------|------|
| `TotalRepresentativeDays` | 总代表天数（=365） | 天 |
| `AnnualObjective_Yuan` | 年总目标函数值 | 元 |
| `AnnualGridEnergy_MWh` | 年购电量 | MWh |
| `AnnualGasEnergy_MWhth` | 年燃气消耗量 | MWh_th |
| `AnnualCarbonEmission_tCO2` | 年碳排放量 | tCO₂ |
| `AnnualCarbonQuota_tCO2` | 年碳配额 | tCO₂ |
| `AnnualCarbonBuyMarket_tCO2` | 年碳市场购买量 | tCO₂ |
| `AnnualCarbonSellMarket_tCO2` | 年碳市场出售量 | tCO₂ |
| `AnnualCarbonTradeAbs_tCO2` | 年碳交易总量 | tCO₂ |
| `AnnualRenewableAvailable_MWh` | 年可用新能源发电量 | MWh |
| `AnnualRenewableUse_MWh` | 年新能源消纳量 | MWh |
| `AnnualRenewableCurtailment_MWh` | 年弃电量 | MWh |
| `AnnualRenewableUseRate_percent` | 年新能源消纳率 | % |
| `AnnualH2Shortage_kg` | 年氢气短缺量 | kg |

### 2.5 year_typical_scenario_settings.csv — 年度典型天气配置表

**用途**：5种典型天气场景的输入参数配置

**行数**：5行（5种天气）

**列（17列）**：

| 列名 | 含义 | 单位 |
|------|------|------|
| `TypicalScenario` | 天气场景英文名 | - |
| `TypicalScenarioCN` | 天气场景中文名 | - |
| `DDREScenarioId` | 1-Day Scenarios中的场景编号 | - |
| `PVLabel` | PV天气标签 | - |
| `WindLabel` | 风电标签 | - |
| `DDRESourceCount` | 该天气类型包含的原始场景数 | 个 |
| `DDRESelectionRule` | 代表日选取规则（median-representative） | - |
| `RepresentativeDays` | 年代表天数 | 天 |
| `PVScaleFinal` | PV容量放大倍数（规划结果=5） | 倍 |
| `WindScaleFinal` | 风电容量放大倍数（规划结果=5） | 倍 |
| `LoadScaleFinal` | 负荷放大倍数 | 倍 |
| `H2ScaleFinal` | 氢负荷放大倍数 | 倍 |
| `AvailablePV_MWh` | 日可用PV发电量（放大后） | MWh |
| `AvailableWind_MWh` | 日可用风电发电量（放大后） | MWh |
| `TotalElectricLoad_MWh` | 日总电负荷 | MWh |
| `TotalHeatLoad_MWh` | 日总热负荷 | MWh |
| `TotalH2Load_kg` | 日总氢负荷 | kg |

---

## 三、comparison_plot_data_csv/ — 场景对比时序数据

**用途**：存储4种对比场景（S1~S4）在**同一天气条件**下的逐时运行曲线数据。

**天气条件**：使用 `1-Day Scenarios` 中的场景 12（ddreScenarioId=12），对应 **晴天+中等风力**（pv_label=0, wind_label=1）。

**目录结构**：扁平结构，所有CSV直接位于目录下。

**文件命名规则**：`{场景名}_{方法}_{数据类型}.csv`

**包含的场景**：
- S1_NoCarbon_NoDR
- S2_Normal_NoCarbon_DR
- S3_Carbon_NoDR
- S4__Carbon_DR

**包含的方法**：`centralized`、`admm`

### 文件类型与列定义

#### A. hourly_aggregate — 园区逐时汇总（63列）

每场景每方法1个文件，24行（TimeSlot 1~24）。

| 列名 | 含义 | 单位 |
|------|------|------|
| `Scenario` | 场景名 | - |
| `Method` | 方法名 | - |
| `TimeSlot` | 时刻（1~24） | h |
| `DataSum_Pload` | 园区总电负荷 | MW |
| `DataSum_PloadFixed` | 固定电负荷（不可调节） | MW |
| `DataSum_PdrShiftBase` | DR可转移负荷基线 | MW |
| `DataSum_PdrShiftMax` | DR最大可转移量 | MW |
| `DataSum_PdrCutEmax` | DR最大可削减电负荷 | MW |
| `DataSum_Hload` | 园区总热负荷 | MW_th |
| `DataSum_HdrCutMax` | DR最大可削减热负荷 | MW_th |
| `DataSum_H2load` | 园区总氢负荷 | kg/h |
| `DataSum_H2drCutMax` | DR最大可削减氢负荷 | kg/h |
| `DataSum_Ppv` | PV总出力 | MW |
| `DataSum_Pwind` | 风电总出力 | MW |
| `DataSum_PcompFixed` | 固定压缩机负荷 | MW |
| `Sum_Pgrid` | 电网购电功率 | MW |
| `Sum_Pch` | 储能总充电功率 | MW |
| `Sum_Pdis` | 储能总放电功率 | MW |
| `Sum_PpvUse` | PV消纳功率 | MW |
| `Sum_PpvCurt` | PV弃光功率 | MW |
| `Sum_PwindUse` | 风电消纳功率 | MW |
| `Sum_PwindCurt` | 风电弃风功率 | MW |
| `Sum_Pchp` | CHP发电功率 | MW |
| `Sum_Hchp` | CHP供热功率 | MW_th |
| `Sum_Fgas` | 燃气消耗功率 | MW |
| `Sum_Peb` | 电锅炉电功率 | MW |
| `Sum_Heb` | 电锅炉热功率 | MW_th |
| `Sum_Pelec` | 电解槽电功率 | MW |
| `Sum_H2prod` | 电解槽产氢量 | kg/h |
| `Sum_H2cons_fc` | 燃料电池耗氢量 | kg/h |
| `Sum_Pfc` | 燃料电池发电功率 | MW |
| `Sum_Pcomp` | 压缩机电功率 | MW |
| `Sum_Hch` | 储热充电功率 | MW_th |
| `Sum_Hdis` | 储热放电功率 | MW_th |
| `Sum_H2ch` | 储氢充氢量 | kg/h |
| `Sum_H2dis` | 储氢放氢量 | kg/h |
| `Sum_H2short` | 氢气短缺量 | kg/h |
| `Sum_Hdump` | 弃热量 | MW_th |
| `Sum_PdrShift` | DR实际转移负荷 | MW |
| `Sum_PdrShiftDev` | DR转移偏差 | MW |
| `Sum_PdrCutE` | DR实际削减电负荷 | MW |
| `Sum_HdrCut` | DR实际削减热负荷 | MW_th |
| `Sum_H2drCut` | DR实际削减氢负荷 | kg/h |
| `Sum_PloadDR` | DR后实际电负荷 | MW |
| `Sum_HloadDR` | DR后实际热负荷 | MW_th |
| `Sum_H2loadDR` | DR后实际氢负荷 | kg/h |
| `Sum_Qpv` | PV无功功率 | MVAr |
| `Sum_Qwind` | 风电无功功率 | MVAr |
| `Sum_Qes` | 储能无功功率 | MVAr |
| `Sum_QinjLocal` | 本地注入无功 | MVAr |
| `Sum_PinjLocal` | 本地注入有功 | MW |
| `Sum_CarbonEmission_kg` | 时碳排放量 | kg |
| `Sum_CarbonQuota_kg` | 时碳配额 | kg |
| `Sum_CarbonBuyMarket_kg` | 时碳市场购买量 | kg |
| `Sum_CarbonSellMarket_kg` | 时碳市场出售量 | kg |
| `Sum_CarbonTradeWithCommunities_kg` | 社区间碳交易量 | kg |
| `Sum_CarbonUnusedAllowance_kg` | 时未使用碳配额 | kg |
| `Mean_SOC_e` | 平均电储能SOC | - |
| `Mean_SOC_th` | 平均储热SOC | - |
| `Mean_SOC_h2` | 平均储氢SOC | - |
| `Mean_V` | 平均电压 | p.u. |
| `TotalRenewableAvailable_MW` | 总可用新能源出力 | MW |
| `TotalRenewableUsed_MW` | 总新能源消纳出力 | MW |
| `TotalRenewableCurtailment_MW` | 总弃电功率 | MW |

#### B. community_hourly — 分社区逐时数据（66列）

每场景每方法1个文件，24行 × 3社区 = 72行。

与 `hourly_aggregate` 相同的列（去掉 `Sum_` 前缀变为单社区值），额外增加：

| 额外列名 | 含义 | 单位 |
|----------|------|------|
| `Community` | 社区编号（1/2/3） | - |
| `Data_Emax` | 电储能容量 | MWh |
| `Data_SOC0_e` | 电储能初始SOC | - |
| `Data_EthMax` | 储热容量 | MWh_th |
| `Data_SOC0_th` | 储热初始SOC | - |
| `Data_EH2Max` | 储氢容量 | kg |
| `Data_SOC0_h2` | 储氢初始SOC | - |

#### C. solution_scalars — 求解标量结果（26列）

每场景每方法1个文件，1行数据。

| 列名 | 含义 | 单位 |
|------|------|------|
| `Scenario` | 场景名 | - |
| `Method` | 方法名 | - |
| `Objective_Yuan` | 日目标函数值 | 元 |
| `LocalObjective_Yuan` | 各社区本地目标之和 | 元 |
| `Iterations` | ADMM迭代次数 | 次 |
| `FinalPrimalResidual` | 最终原始残差 | - |
| `FinalDualResidual` | 最终对偶残差 | - |
| `MaxConsensusP_MW` | 有功最大共识偏差 | MW |
| `MaxConsensusQ_MVAr` | 无功最大共识偏差 | MVAr |
| `MaxConsensusCarbon_kg` | 碳排放最大共识偏差 | kg |
| `TotalPVCurt_MWh` | 日总弃光量 | MWh |
| `TotalWindCurt_MWh` | 日总弃风量 | MWh |
| `TotalH2Shortage_kg` | 日总氢气短缺量 | kg |
| `TotalPdrShiftDeviation_MWh` | 日DR转移偏差总量 | MWh |
| `TotalElectricCurtailmentDR_MWh` | 日DR电削减量 | MWh |
| `TotalHeatCurtailmentDR_MWh` | 日DR热削减量 | MWh |
| `TotalHydrogenCurtailmentDR_kg` | 日DR氢削减量 | kg |
| `Part_gridCost` | 购电成本分项 | 元 |
| `Part_carbonTradingCost` | 碳交易成本分项 | 元 |
| `Part_gasCost` | 燃气成本分项 | 元 |
| `Part_gasCarbonCost` | 燃气碳排放成本分项 | 元 |
| `Part_pvCurtCost` | 弃光惩罚成本分项 | 元 |
| `Part_windCurtCost` | 弃风惩罚成本分项 | 元 |
| `Part_h2ShortCost` | 氢短缺惩罚成本分项 | 元 |
| `Part_demandResponseCost` | 需求响应成本分项 | 元 |
| `Part_qSupportCost` | 无功支撑成本分项 | 元 |

#### D. convergence — ADMM收敛曲线（5列）

仅ADMM方法有此文件，集中式无。

| 列名 | 含义 | 单位 |
|------|------|------|
| `Scenario` | 场景名 | - |
| `Method` | 方法名 | - |
| `Iteration` | 迭代编号 | - |
| `PrimalResidual` | 原始残差 | - |
| `DualResidual` | 对偶残差 | - |

#### E. plot_data_manifest.csv — 文件清单（4列）

| 列名 | 含义 |
|------|------|
| `Scenario` | 场景名 |
| `Method` | 方法名 |
| `DataType` | 数据类型（hourly_aggregate / community_hourly / solution_scalars / convergence） |
| `FileName` | 对应文件名 |

---

## 四、year_plot_data_csv/ — 年度时序数据

**用途**：存储 **S4场景（碳交易+DR）** 在5种不同天气下的逐时运行曲线数据。

**目录结构**：扁平结构，所有CSV直接位于目录下。

**文件命名规则**：`{天气场景名}_{方法}_{数据类型}.csv`

**包含的天气场景**：Sunny_LowWind、Sunny_HighWind、Cloudy_MidWind、Rainy_LowWind、Rainy_HighWind

**包含的方法**：`centralized`、`admm`

**CSV列结构**：与 `comparison_plot_data_csv/` 完全相同（见第三节），共4种文件类型：
- `hourly_aggregate`（63列）
- `community_hourly`（66列）
- `solution_scalars`（26列）
- `convergence`（5列，仅ADMM有）

---

## 五、1-Day Scenarios/ — 原始逐日场景数据

**用途**：200个合成的日风光出力场景，作为优化问题的输入数据源。

**文件清单**：
- `DATA_DESCRIPTION.txt` — 数据说明文件
- `scenario_labels.csv` — 场景分类标签
- `scenario_001.csv` ~ `scenario_200.csv` — 200个场景文件

### scenario_labels.csv（3列，200行）

| 列名 | 含义 |
|------|------|
| `scenario_index` | 场景编号（1~200） |
| `wind_label` | 风电标签：0=低, 1=中, 2=高 |
| `pv_label` | PV标签：0=晴/高, 1=多云/中, 2=阴/低 |

### scenario_xxx.csv（6列，96行）

每个文件为一个场景的24小时逐15分钟数据。

| 列名 | 含义 | 单位 |
|------|------|------|
| `scenario_id` | 场景编号 | - |
| `timestamp` | 时间戳（15分钟间隔） | - |
| `node_22_wind` | 节点22风电出力（归一化0~1） | p.u. |
| `node_25_wind` | 节点25风电出力（归一化0~1） | p.u. |
| `node_18_PV` | 节点18光伏出力（归一化0~1） | p.u. |
| `node_33_PV` | 节点33光伏出力（归一化0~1） | p.u. |

---

## 六、园区规划与容量配置/ — 容量规划优化结果

**用途**：独立的容量规划优化（规划层），决定各社区的最优设备容量配置。

> **注意**：此子目录的场景命名与根目录不同，沿用旧版命名（含储能/无储能维度）。其CSV文件结构与根目录同名文件**不完全相同**（列数不同）。

### 6.1 planning_capacity_result.csv — 最优容量配置（22列，3行）

每个社区1行，共3个社区。

| 列名 | 含义 | 单位 |
|------|------|------|
| `Community` | 社区编号 | - |
| `PVExisting_MW` | 已有PV容量 | MW |
| `PVNew_MW` | 新增PV容量 | MW |
| `PV_MW` | PV总容量 | MW |
| `WindExisting_MW` | 已有风电容量 | MW |
| `WindNew_MW` | 新增风电容量 | MW |
| `Wind_MW` | 风电总容量 | MW |
| `BatteryExisting_MWh` | 已有电储能容量 | MWh |
| `BatteryNew_MWh` | 新增电储能容量 | MWh |
| `BatteryEnergy_MWh` | 电储能总容量 | MWh |
| `BatteryPower_MW` | 电储能额定功率 | MW |
| `ThermalStorageExisting_MWh` | 已有储热容量 | MWh |
| `ThermalStorageNew_MWh` | 新增储热容量 | MWh |
| `ThermalStorage_MWh` | 储热总容量 | MWh |
| `ThermalStoragePower_MW` | 储热额定功率 | MW |
| `HydrogenStorageExisting_kg` | 已有储氢容量 | kg |
| `HydrogenStorageNew_kg` | 新增储氢容量 | kg |
| `HydrogenStorage_kg` | 储氢总容量 | kg |
| `HydrogenStoragePower_kg_h` | 储氢额定充放速率 | kg/h |
| `PVInverter_MVA` | PV逆变器容量 | MVA |
| `WindConverter_MVA` | 风电变流器容量 | MVA |
| `ESReactiveCapability_Mvar` | 储能无功支撑能力 | MVar |

### 6.2 planning_cost_breakdown.csv — 年成本分解（2列，17行）

键值对格式，`CostItem` 为成本项名称，`Value_Yuan` 为金额（元/年）。

| CostItem | 含义 |
|----------|------|
| `TotalAnnualObjective_Yuan` | 年总目标函数值（=以下各项之和） |
| `AnnualInvestmentCost_Yuan` | 年化投资成本 |
| `AnnualFixedOMCost_Yuan` | 年固定运维成本 |
| `AnnualOperationCost_Yuan` | 年运行成本（购电+燃气+碳交易等） |
| `AnnualCarbonTradingCost_Yuan` | 年碳交易成本 |
| `AnnualCarbonPenaltyCost_Yuan` | 年碳排放惩罚成本 |
| `InvPV_YuanPerYear` | PV年化投资（已有设备=0） |
| `InvWind_YuanPerYear` | 风电年化投资（已有设备=0） |
| `InvBat_YuanPerYear` | 电储能年化投资（已有设备=0） |
| `InvTh_YuanPerYear` | 储热年化投资 |
| `InvH2_YuanPerYear` | 储氢年化投资 |
| `FixOMPV_YuanPerYear` | PV固定运维费 |
| `FixOMWind_YuanPerYear` | 风电固定运维费 |
| `FixOMBat_YuanPerYear` | 电储能固定运维费 |
| `FixOMTh_YuanPerYear` | 储热固定运维费 |
| `FixOMH2_YuanPerYear` | 储氢固定运维费 |

### 6.3 planning_typical_scenario_result.csv — 规划层典型天气运行指标（14列，5行）

每种天气1行。注意：此表的场景命名来自旧版（含储能/无储能），但数据内容与根目录 `year_typical_scenario_metric_table.csv` 对应。

| 列名 | 含义 | 单位 |
|------|------|------|
| `TypicalScenario` | 天气场景英文名 | - |
| `TypicalScenarioCN` | 天气场景中文名 | - |
| `RepresentativeDays` | 年代表天数 | 天 |
| `DailyOpCost_Yuan` | 日运行成本 | 元 |
| `AnnualOpCost_Yuan` | 年运行成本（日值×代表天数） | 元 |
| `DailyEmission_tCO2` | 日碳排放量 | tCO₂ |
| `AnnualEmission_tCO2` | 年碳排放量 | tCO₂ |
| `RenAvail_MWh` | 日可用新能源发电量 | MWh |
| `RenUse_MWh` | 日新能源消纳量 | MWh |
| `RenCurt_MWh` | 日弃电量 | MWh |
| `RenUseRate_percent` | 新能源消纳率 | % |
| `RenCurtRate_percent` | 弃电率 | % |
| `AvgMinVoltage_pu` | 平均最低电压 | p.u. |
| `GridVoltageDeviation_pu` | 电网电压偏差 | p.u. |

### 6.4 planning_typical_scenario_settings.csv — 规划层天气配置（12列，5行）

| 列名 | 含义 | 单位 |
|------|------|------|
| `TypicalScenario` | 天气场景英文名 | - |
| `TypicalScenarioCN` | 天气场景中文名 | - |
| `DDREScenarioId` | 1-Day Scenarios中的场景编号 | - |
| `PVLabel` | PV天气标签 | - |
| `WindLabel` | 风电标签 | - |
| `RepresentativeDays` | 年代表天数 | 天 |
| `AvailablePVUnit_MWh_per_MW` | 单位PV容量可用发电量 | MWh/MW |
| `AvailableWindUnit_MWh_per_MW` | 单位风电容量可用发电量 | MWh/MW |
| `TotalElectricLoad_MWh` | 日总电负荷 | MWh |
| `TotalHeatLoad_MWh` | 日总热负荷 | MWh |
| `TotalH2Load_kg` | 日总氢负荷 | kg |

### 6.5 其他文件

此目录还包含与根目录同名但结构不同的文件：
- `comparison_metric_table.csv` — 旧版场景对比（21列，含GridEnergy/Carbon/Renewable等详细指标）
- `comparison_summary.csv` — 旧版场景对比汇总（12列）
- `year_typical_scenario_metric_table.csv` — 旧版年度指标（39列，与根目录42列版本结构不同）
- `year_annual_weighted_summary.csv` — 旧版年度汇总（14列，与根目录结构相同）
- `year_typical_scenario_settings.csv` — 旧版天气配置（17列，与根目录结构相同）

> **旧版场景命名**（规划子目录中）：S1_Normal_NoStorage_NoCarbon、S2_Normal_WithStorage_NoCarbon、S3_Normal_WithStorage_Carbon、S4_HighRE_WithStorage_Carbon

---

## 七、year_submission/ — 论文投稿图表

仅包含 `.png` 和 `.eps` 格式的论文图表（共60个文件），无CSV数据。

图表类型包括：Renewable_Profiles、SOC_Electric、SOC_Thermal、CHP_Profiles、Energy_Balance、Hydrogen_Profiles，每种覆盖5种天气场景。

---

## 八、目录结构总览

```
零碳园区优化_v12/
├── comparison_metric_table.csv          # 场景对比-优化指标（12列×8行）
├── comparison_summary.csv               # 场景对比-详细汇总（20列×8行）
├── year_typical_scenario_metric_table.csv # 年度天气指标（42列×10行）
├── year_annual_weighted_summary.csv      # 年度加权汇总（14列×2行）
├── year_typical_scenario_settings.csv    # 年度天气配置（17列×5行）
├── *.m / *.mat                          # MATLAB源码与数据文件
│
├── comparison_plot_data_csv/             # S1~S4场景对比时序数据
│   ├── S1_*_{aggregate,community,scalars,convergence}.csv
│   ├── S2_*_*.csv
│   ├── S3_*_*.csv
│   ├── S4_*_*.csv
│   └── plot_data_manifest.csv
│
├── year_plot_data_csv/                   # S4场景×5天气的时序数据
│   ├── Sunny_LowWind_*_*.csv
│   ├── Sunny_HighWind_*_*.csv
│   ├── Cloudy_MidWind_*_*.csv
│   ├── Rainy_LowWind_*_*.csv
│   ├── Rainy_HighWind_*_*.csv
│   └── plot_data_manifest.csv
│
├── 1-Day Scenarios/                      # 200个原始日风光场景
│   ├── DATA_DESCRIPTION.txt
│   ├── scenario_labels.csv              # 场景标签（200行）
│   └── scenario_001.csv ~ scenario_200.csv  # 每场景96行（15分钟）
│
├── 园区规划与容量配置/                    # 容量规划优化结果
│   ├── planning_capacity_result.csv     # 最优容量（22列×3社区）
│   ├── planning_cost_breakdown.csv      # 年成本分解（17项）
│   ├── planning_typical_scenario_result.csv  # 天气运行指标（14列×5行）
│   ├── planning_typical_scenario_settings.csv # 天气配置（12列×5行）
│   ├── comparison_metric_table.csv      # 旧版场景对比（21列×8行）
│   ├── comparison_summary.csv           # 旧版场景汇总（12列×8行）
│   ├── year_typical_scenario_metric_table.csv # 旧版年度指标（39列×10行）
│   ├── year_annual_weighted_summary.csv  # 旧版年度汇总（14列×2行）
│   ├── year_typical_scenario_settings.csv # 旧版天气配置（17列×5行）
│   ├── README_planning_year.txt
│   ├── *.m / *.mat
│   └── 1-Day Scenarios/                 # 与根目录相同的200个场景
│
└── year_submission/                      # 论文投稿图表（png/eps，无CSV）
```
