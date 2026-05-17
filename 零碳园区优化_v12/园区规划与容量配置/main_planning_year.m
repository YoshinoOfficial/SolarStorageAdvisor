%% MAIN_PLANNING_YEAR
% 年尺度园区容量规划主程序。
%
% 第一版功能：
%   1) 基于 main_year 的 5 类典型日和代表天数；
%   2) 以集中式方式联合优化：PV容量、风机容量、电储能容量、热储能容量、储氢容量；
%   3) 固定储能时长，自动得到储能功率容量；
%   4) 新能源装机容量与无功/视在容量同步变化；
%   5) 目标函数 = 年化投资成本 + 年固定运维成本 + 年运行成本 + 年碳排放惩罚。
%
% 使用方法：
%   在 MATLAB 当前目录切换到代码所在文件夹，运行：
%       main_planning_year
%
% 输出文件：
%   planning_capacity_result.csv
%   planning_cost_breakdown.csv
%   planning_typical_scenario_settings.csv
%   planning_typical_scenario_result.csv
%   planning_year_result.mat

clear; clc;
yalmip('clear');
reset_optimizer_caches();

caseName = 'ieee33_3comm_hetero_real';

% 读取一个基础算例，用于生成默认规划参数。
data0 = build_case(caseName, 1);
plan = configure_planning_params(data0);

% ===== 用户可在这里直接调整关键参数 =====
% 碳排放联合优化权重，单位 yuan/tCO2。
% 建议做灵敏度：0, 100, 300, 500, 800。
plan.lambdaCO2_yuan_per_tCO2 = 100;

% 是否额外加入原碳交易成本。
plan.includeCarbonTradingCost = 1;

% 固定储能时长。
plan.tauE_h  = 4.0;
plan.tauTh_h = 4.0;
plan.tauH2_h = 8.0;

% 如果你希望更高新能源上限，可改这里。
% plan.KpvMax_MW   = [8; 8; 8];
% plan.KwindMax_MW = [4; 5; 4];

fprintf('\n============================================================\n');
fprintf('Zero-carbon park annual capacity planning started.\n');
fprintf('Carbon weight lambdaCO2 = %.2f yuan/tCO2\n', plan.lambdaCO2_yuan_per_tCO2);
fprintf('Carbon trading cost included = %d\n', plan.includeCarbonTradingCost);
fprintf('============================================================\n');

[dataSet, scenarioSettingTable] = build_planning_dataset(caseName, plan);

try
    writetable(scenarioSettingTable, 'planning_typical_scenario_settings.csv');
catch ME
    warning('Failed to write scenario setting table: %s', ME.message);
end

res = solve_centralized_planning_year(dataSet, plan);

capacityTable = res.capacityTable;
costTable = res.costTable;
scenarioResultTable = res.scenarioTable;

fprintf('\n===== Optimal Capacity Configuration =====\n');
disp(capacityTable);

fprintf('\n===== Annual Cost Breakdown =====\n');
disp(costTable);

fprintf('\n===== Typical Scenario Annualized Results =====\n');
disp(scenarioResultTable);

fprintf('\n===== Key Annual Indicators =====\n');
fprintf('Total annual objective: %.2f yuan/year\n', res.cost.TotalAnnualObjective_Yuan);
fprintf('Annual investment cost: %.2f yuan/year\n', res.cost.AnnualInvestmentCost_Yuan);
fprintf('Annual fixed OM cost: %.2f yuan/year\n', res.cost.AnnualFixedOMCost_Yuan);
fprintf('Annual operation cost: %.2f yuan/year\n', res.cost.AnnualOperationCost_Yuan);
fprintf('Annual carbon penalty cost: %.2f yuan/year\n', res.cost.AnnualCarbonPenaltyCost_Yuan);
fprintf('Annual carbon emission: %.4f tCO2/year\n', res.annual.CarbonEmission_tCO2);
fprintf('Annual renewable use rate: %.2f %%\n', res.annual.RenewableUseRate_percent);
fprintf('Annual renewable curtailment rate: %.2f %%\n', res.annual.RenewableCurtailmentRate_percent);

try
    writetable(capacityTable, 'planning_capacity_result.csv');
    writetable(costTable, 'planning_cost_breakdown.csv');
    writetable(scenarioResultTable, 'planning_typical_scenario_result.csv');
catch ME
    warning('Failed to write planning CSV files: %s', ME.message);
end

try
    save('planning_year_result.mat', 'res', 'plan', 'dataSet', 'scenarioSettingTable', ...
        'capacityTable', 'costTable', 'scenarioResultTable', '-v7.3');
catch ME
    warning('Failed to save planning_year_result.mat: %s', ME.message);
end

reset_optimizer_caches();
try
    yalmip('clear');
catch
end

fprintf('\nPlanning finished. Results have been exported.\n');
