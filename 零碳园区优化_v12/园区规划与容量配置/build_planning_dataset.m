function [dataSet, scenarioTable] = build_planning_dataset(caseName, plan)
%BUILD_PLANNING_DATASET Build annual typical-day dataset for planning.
% 将 main_year 中的典型日逻辑整理为规划层数据集。
%
% 输出：
%   dataSet{s}: 第 s 个典型日数据；所有典型日共享同一组容量变量；
%   scenarioTable: 典型日设置表。

if nargin < 1 || isempty(caseName)
    caseName = 'ieee33_3comm_hetero_real';
end
if nargin < 2
    plan = [];
end

scenarios = define_planning_typical_scenarios();
dataSet = cell(numel(scenarios), 1);
rows = repmat(make_empty_planning_scenario_row(), numel(scenarios), 1);

% 规划层中 pv/wind 容量由变量决定，所以这里不再使用 main_year 里的
% pvScale=5、windScale=5 去放大固定容量。天气差异由 DDRE 单位出力曲线体现。
baseScenario = struct('name','BasePlanningDay','name_cn','规划基准日', ...
    'pvScale',1.0,'windScale',1.0,'loadScale',1.0,'h2Scale',1.0,'days',0);

for s = 1:numel(scenarios)
    sc = scenarios(s);
    data = build_case(caseName, sc.ddreScenarioId);
    data = apply_scenario(data, baseScenario);
    data = apply_scenario(data, sc);

    data.typicalScenarioName = sc.name;
    data.typicalScenarioNameCN = sc.name_cn;
    data.representativeDays = sc.days;
    data.ddreScenarioId = sc.ddreScenarioId;
    data.pvLabel = sc.pvLabel;
    data.windLabel = sc.windLabel;
    data.ddreSourceCount = sc.sourceCount;
    data.ddreSelectionRule = sc.selectionRule;
    data.pvScaleFinal = baseScenario.pvScale * sc.pvScale;
    data.windScaleFinal = baseScenario.windScale * sc.windScale;
    data.loadScaleFinal = baseScenario.loadScale * sc.loadScale;
    data.h2ScaleFinal = baseScenario.h2Scale * sc.h2Scale;
    data.scenarioName = matlab.lang.makeValidName(sc.name);
    data.storageEnabled = true;
    data.storageLabel = '容量规划';
    data.storageCase = 'Planning';

    % 保存单位容量风光曲线。build_case 新版会直接提供；若旧版没有，
    % 则尽量由固定容量数据反推，保证兼容。
    data.pvProfilePU = get_profile_compat(data, 'pv');
    data.windProfilePU = get_profile_compat(data, 'wind');

    % 规划版默认只使用实际碳排放联合目标，不强制启用碳交易约束。
    carbonOpts = struct( ...
        'enableCarbonQuota', false, ...
        'enableCommunityCarbonTrading', false, ...
        'allowCarbonMarketSell', false, ...
        'carbonBuyPrice', 150, ...
        'carbonSellPrice', 100, ...
        'zetaE', 1080, ...
        'zetaH', 324, ...
        'chiE', 728, ...
        'chiH', 367.2, ...
        'ceh', 1.6667, ...
        'QtradeMax_tCO2', 1.6);
    if isstruct(plan) && isfield(plan, 'includeCarbonTradingCost') && plan.includeCarbonTradingCost
        carbonOpts.enableCarbonQuota = true;
        carbonOpts.enableCommunityCarbonTrading = false;
        carbonOpts.allowCarbonMarketSell = logical(get_plan_field(plan, 'allowCarbonMarketSell', false));
        carbonOpts.carbonBuyPrice = get_plan_field(plan, 'carbonBuyPrice', 150);
        carbonOpts.carbonSellPrice = get_plan_field(plan, 'carbonSellPrice', 100);
    end
    data = configure_carbon_trading(data, carbonOpts);

    dataSet{s} = data;
    rows(s) = make_planning_scenario_row(data);
end

scenarioTable = struct2table(rows);
end

function scenarios = define_planning_typical_scenarios()
% 与 main_year 保持一致的 5 类典型日。
scenarios = struct( ...
    'name',          {'Sunny_LowWind', 'Sunny_HighWind', 'Cloudy_MidWind', 'Rainy_LowWind', 'Rainy_HighWind'}, ...
    'name_cn',       {'晴天少风',      '晴天多风',       '多云中风',       '阴天少风',      '阴天多风'}, ...
    'ddreScenarioId',{116,             178,              137,              183,             40}, ...
    'pvLabel',       {0,               0,                1,                2,               2}, ...
    'windLabel',     {0,               2,                1,                0,               2}, ...
    'sourceCount',   {26,              14,               20,               19,              22}, ...
    'selectionRule', {'median-representative', 'median-representative', 'median-representative', 'median-representative', 'median-representative'}, ...
    'pvScale',       {1.00,            1.00,             1.00,             1.00,            1.00}, ...
    'windScale',     {1.00,            1.00,             1.00,             1.00,            1.00}, ...
    'loadScale',     {1.00,            1.00,             1.00,             1.00,            1.00}, ...
    'h2Scale',       {1.00,            1.00,             1.00,             1.00,            1.00}, ...
    'days',          {94,              51,               72,               69,              79} ...
);
end

function profile = get_profile_compat(data, kind)
N = data.N; T = data.T;
switch lower(kind)
    case 'pv'
        if isfield(data, 'pvProfilePU') && ~isempty(data.pvProfilePU)
            profile = data.pvProfilePU;
        elseif isfield(data, 'ddrePpvPU') && ~isempty(data.ddrePpvPU)
            profile = data.ddrePpvPU;
        elseif isfield(data, 'pvCap0') && all(data.pvCap0(:) > 1e-8)
            profile = data.Ppv ./ repmat(data.pvCap0(:), 1, T);
        else
            profile = zeros(N,T);
        end
    case 'wind'
        if isfield(data, 'windProfilePU') && ~isempty(data.windProfilePU)
            profile = data.windProfilePU;
        elseif isfield(data, 'ddrePwindPU') && ~isempty(data.ddrePwindPU)
            profile = data.ddrePwindPU;
        elseif isfield(data, 'windCap0') && any(data.windCap0(:) > 1e-8)
            cap = max(data.windCap0(:), 1e-8);
            profile = data.Pwind ./ repmat(cap, 1, T);
        else
            profile = zeros(N,T);
        end
    otherwise
        profile = zeros(N,T);
end
profile = max(0, min(1.2, profile));
end

function row = make_planning_scenario_row(data)
row = struct();
row.TypicalScenario = string(data.typicalScenarioName);
row.TypicalScenarioCN = string(data.typicalScenarioNameCN);
row.DDREScenarioId = data.ddreScenarioId;
row.PVLabel = data.pvLabel;
row.WindLabel = data.windLabel;
row.RepresentativeDays = data.representativeDays;
row.AvailablePVUnit_MWh_per_MW = sum(data.pvProfilePU(:))*data.dt;
row.AvailableWindUnit_MWh_per_MW = sum(data.windProfilePU(:))*data.dt;
row.TotalElectricLoad_MWh = sum(data.Pload(:))*data.dt;
row.TotalHeatLoad_MWh = sum(data.Hload(:))*data.dt;
row.TotalH2Load_kg = sum(data.H2load(:))*data.dt;
end

function row = make_empty_planning_scenario_row()
row = struct();
row.TypicalScenario = "";
row.TypicalScenarioCN = "";
row.DDREScenarioId = NaN;
row.PVLabel = NaN;
row.WindLabel = NaN;
row.RepresentativeDays = NaN;
row.AvailablePVUnit_MWh_per_MW = NaN;
row.AvailableWindUnit_MWh_per_MW = NaN;
row.TotalElectricLoad_MWh = NaN;
row.TotalHeatLoad_MWh = NaN;
row.TotalH2Load_kg = NaN;
end

function val = get_plan_field(plan, name, defaultVal)
if isstruct(plan) && isfield(plan, name) && ~isempty(plan.(name))
    val = plan.(name);
else
    val = defaultVal;
end
end
