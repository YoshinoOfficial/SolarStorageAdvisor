园区规划第一版代码说明
======================

新增/修改文件：
1. main_planning_year.m
   年尺度容量规划主程序。直接运行该文件即可。

2. configure_planning_params.m
   设置规划参数，包括投资成本、寿命、CRF折现率、固定储能时长、容量上下限、碳排放权重等。

3. build_planning_dataset.m
   复用 main_year 的 5 类典型日设置，构造 dataSet{s}。
   注意：规划层中风光容量是变量，因此不再使用 main_year 中 pvScale=5/windScale=5 放大固定容量。

4. solve_centralized_planning_year.m
   核心规划模型。一次性建立所有典型日的集中式联合优化模型。
   目标函数：
      年化投资成本 + 年固定运维成本 + 年运行成本 + 年碳排放惩罚
   规划变量：
      Kpv, Kwind, Ebat, Eth, EH2
   固定储能时长：
      Pbat = Ebat/tauE, Hth = Eth/tauTh, H2Power = EH2/tauH2

5. build_case.m
   已做最小补丁：新增保存 pvCap0、windCap0、ddrePpvPU、ddrePwindPU、pvProfilePU、windProfilePU。
   原有 solve_centralized.m 与 main_year.m 不需要依赖这些新增字段，因此不影响旧版运行。

运行方法：
1. 确认 MATLAB 当前目录为代码文件夹。
2. 确认 YALMIP 与 Gurobi/CPLEX/MOSEK 可用。
3. 运行：
      main_planning_year

输出文件：
- planning_capacity_result.csv：最优容量配置
- planning_cost_breakdown.csv：年成本分解
- planning_typical_scenario_settings.csv：典型日设置
- planning_typical_scenario_result.csv：各典型日运行指标
- planning_year_result.mat：完整结果

建议的灵敏度分析：
在 main_planning_year.m 中修改：
   plan.lambdaCO2_yuan_per_tCO2 = 0 / 100 / 300 / 500 / 800;
观察光伏、风机、储能、储氢容量与年碳排放、年成本之间的变化。

重要建模说明：
- 第一版默认 plan.includeCarbonTradingCost = false。
  这表示目标函数中只加入实际碳排放惩罚项，不额外加入碳交易买卖成本。
  这样可以避免“碳交易成本 + 碳排放权重”重复计价。
- 若你确实需要保留碳交易成本，可在 main_planning_year.m 中设为 true，
  但论文中需说明 lambdaCO2 是低碳偏好权重，不是碳市场价格。
