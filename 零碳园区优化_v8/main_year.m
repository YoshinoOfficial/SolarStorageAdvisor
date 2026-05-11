%% Zero-carbon campus multi-energy runner: typical scenarios + storage comparison
% 功能：
% 1) 构造多类典型天气/新能源场景（晴天少风、晴天多风、多云中风、阴天少风、阴天多风、高负荷低新能源）；
% 2) 每个典型场景均运行“有储能”和“无储能”两种方案；
% 3) 输出日运行指标、储能改善量，以及按代表天数折算的全年经济/减排效益。

% 如需同时运行ADMM，将 runFixedADMM 改为 1 即可。

yalmip('clear');
reset_optimizer_caches();

caseName = 'ieee33_3comm_hetero_real';
ddreScenarioId = 13;
runCentralized = 1;
runFixedADMM   = 1; 
usePreprocess  = 1;
generatePlots  = false;

admmRho = 50;
admmMaxIter = 1000;
admmTolPri = 1e-4;
admmTolDual = 5e-2;

% 原始基准场景系数：保持你前一版为了形成明显风光出力特征而使用的PV放大系数。
baseScenario = struct('name','BaseDay','name_cn','基准日', ...
    'pvScale',1.0,'windScale',1.00,'loadScale',1.05,'h2Scale',1.00,'days',0);

% 典型场景列表：先在baseScenario基础上二次缩放。
% 注意：最终光伏出力 = 原始Ppv × baseScenario.pvScale × typicalScenario.pvScale。
typicalScenarios = define_typical_scenarios();

allSummary = [];
allMetricRows = [];
allResults = struct();
allData    = struct();

% 只构建一次基础算例，后续每个场景从baseData复制，避免比例系数重复叠乘。
baseData0 = build_case(caseName, ddreScenarioId);
baseData0 = apply_scenario(baseData0, baseScenario);

% Use the same fixed S1 carbon quota baseline as main_run_comparison:
% S1 = normal renewable output (PV=3, Wind=3), no storage, no community
% carbon trading, no carbon-market sell.
fprintf('\n============================================================\n');
fprintf('Computing fixed S1 carbon quota baseline for annual typical scenarios...\n');
fprintf('S1 baseline: PV scale=3.000, Wind scale=3.000, Storage=0, CommunityCarbonTrading=0, MarketSell=0\n');
fprintf('============================================================\n');
baselineScenario = struct('name','S1_Normal_NoStorage_NoCarbon', ...
    'name_cn','S1_Normal_NoStorage_NoCarbon', ...
    'pvScale',3.0,'windScale',3.0,'loadScale',1.0,'h2Scale',1.0,'days',0);
baselineData = apply_scenario(baseData0, baselineScenario);
baselineData.storageEnabled = false;
baselineData.storageLabel = 'NoStorage';
baselineData.storageCase = 'NoStorage';
baselineData.pvScaleFinal = baseScenario.pvScale * baselineScenario.pvScale;
baselineData.windScaleFinal = baseScenario.windScale * baselineScenario.windScale;
baselineData.loadScaleFinal = baseScenario.loadScale * baselineScenario.loadScale;
baselineData.h2ScaleFinal = baseScenario.h2Scale * baselineScenario.h2Scale;
baselineData.carbonQuotaMode = 'baseline-scenario';
baselineData = disable_storage(baselineData);
baselineData = configure_carbon_trading(baselineData, struct( ...
    'enableCarbonQuota', true, ...
    'enableCommunityCarbonTrading', false, ...
    'allowCarbonMarketSell', false));
baselineCentral = solve_centralized(baselineData);
baselineCarbonQuota_kg = baselineCentral.CarbonQuota_kg;
fprintf('Fixed S1 carbon quota baseline total: %.4f kgCO2\n', sum(baselineCarbonQuota_kg(:)));
reset_optimizer_caches();

scenarioInfoRows = [];

for k = 1:numel(typicalScenarios)
    sc = typicalScenarios(k);

    data = apply_scenario(baseData0, sc);
    data.typicalScenarioName = sc.name;
    data.typicalScenarioNameCN = sc.name_cn;
    data.representativeDays = sc.days;
    data.pvScaleFinal = baseScenario.pvScale * sc.pvScale;
    data.windScaleFinal = baseScenario.windScale * sc.windScale;
    data.loadScaleFinal = baseScenario.loadScale * sc.loadScale;
    data.h2ScaleFinal = baseScenario.h2Scale * sc.h2Scale;
    data.storageEnabled = true;
    data.storageLabel = '有储能';
    data.storageCase = 'WithStorage';
    data.scenarioName = matlab.lang.makeValidName(sc.name);
    data.fixedCarbonQuota_kg = baselineCarbonQuota_kg;
    data.carbonQuotaMode = 'fixed-baseline';
    carbonOpts = struct( ...
        'enableCarbonQuota', true, ...
        'enableCommunityCarbonTrading', true, ...
        'allowCarbonMarketSell', true);
    data = configure_carbon_trading(data, carbonOpts);
    data.admmRho = admmRho;
    data.admmMaxIter = admmMaxIter;
    data.admmTolPri = admmTolPri;
    data.admmTolDual = admmTolDual;
    data.preserveOptimizerCache = logical(runFixedADMM);

    scenarioInfoRows = [scenarioInfoRows; make_scenario_info_row(data)]; %#ok<AGROW>

        fprintf('\n============================================================\n');
        fprintf('Typical scenario: %s | Storage: %s\n', string(data.typicalScenarioNameCN), string(data.storageLabel));
        fprintf('Case: %s | DDRE-33 day scenario: %03d\n', caseName, ddreScenarioId);
        fprintf('PV scale(final)=%.3f, Wind scale(final)=%.3f, Load scale=%.3f, H2 scale=%.3f, Days=%d\n', ...
            data.pvScaleFinal, data.windScaleFinal, data.loadScaleFinal, data.h2ScaleFinal, data.representativeDays);
        fprintf('Internal scenario name: %s\n', data.scenarioName);
        fprintf('============================================================\n');

        if runCentralized
            fprintf('Running multi-energy centralized benchmark...\n');
            try
                central = solve_centralized(data);
                allResults.(data.scenarioName).centralized = central;
                fprintf('Centralized optimization cost: %.4f\n', central.obj);
                allSummary = [allSummary; make_row(data, central.method, central.obj, NaN, central.totalPVCurt, mean(min(central.V,[],1)), NaN, 'Solved', '')]; %#ok<AGROW>
                allMetricRows = [allMetricRows; make_metric_row(data, central.method, central)]; %#ok<AGROW>
            catch ME
                methodName = 'centralized-multi-energy-pq';
                warning('场景 %s 求解失败，已记录为 Failed 并继续运行后续场景：%s', data.scenarioName, ME.message);
                central = struct();
                central.method = methodName;
                central.obj = NaN;
                central.solveStatus = 'Failed';
                central.errorMessage = ME.message;
                allResults.(data.scenarioName).centralized = central;
                allSummary = [allSummary; make_failed_row(data, methodName, ME.message)]; %#ok<AGROW>
                allMetricRows = [allMetricRows; make_failed_metric_row(data, methodName, ME.message)]; %#ok<AGROW>
            end
        end

        if runFixedADMM
            fprintf('Running multi-energy fixed-rho ADMM...\n');
            try
                if usePreprocess
                    fprintf('Prebuilding ADMM optimizer cache for this scenario...\n');
                    tPreprocess = tic;
                    preprocess_optimizers(data, data.admmRho*ones(data.N,1));
                    data.optimizersPreprocessed = true;
                    fprintf('ADMM optimizer cache ready in %.2f s.\n', toc(tPreprocess));
                end
                admm = solve_admm_fixed(data);
                allResults.(data.scenarioName).admm = admm;
                allSummary = [allSummary; make_row(data, admm.method, admm.recoveredGlobalObjective, admm.finalLocalCost, admm.totalPVCurt, mean(min(admm.V,[],1)), numel(admm.hist_pri), 'Solved', '')]; %#ok<AGROW>
                allMetricRows = [allMetricRows; make_metric_row(data, admm.method, admm)]; %#ok<AGROW>
            catch ME
                methodName = 'fixed-rho-admm';
                warning('场景 %s 的 ADMM 求解失败，已记录为 Failed 并继续运行后续场景：%s', data.scenarioName, ME.message);
                admm = struct();
                admm.method = methodName;
                admm.solveStatus = 'Failed';
                admm.errorMessage = ME.message;
                allResults.(data.scenarioName).admm = admm;
                allSummary = [allSummary; make_failed_row(data, methodName, ME.message)]; %#ok<AGROW>
                allMetricRows = [allMetricRows; make_failed_metric_row(data, methodName, ME.message)]; %#ok<AGROW>
            end
        end

        allData.(data.scenarioName) = data;
end

summaryTable = struct2table(allSummary);
metricTable = struct2table(allMetricRows);
scenarioTable = struct2table(scenarioInfoRows);
annualTable = make_annual_weather_table(metricTable);
dropOutputColumns = {'StorageCase','StorageEnabled','Scenario','Method','Status','ErrorMessage'};
summaryTable = drop_table_columns(summaryTable, dropOutputColumns);
metricTable = drop_table_columns(metricTable, dropOutputColumns);
annualTable = drop_table_columns(annualTable, dropOutputColumns);

try
    writetable(scenarioTable, 'year_typical_scenario_settings.csv');
    writetable(metricTable, 'year_typical_scenario_metric_table.csv');
    writetable(annualTable, 'year_annual_weighted_summary.csv');
catch ME
    warning('写出CSV结果表失败：%s', ME.message);
end

disp(' ');
disp('===== Typical Scenario Settings =====');
disp(scenarioTable);
disp(' ');
disp('===== Zero-Carbon Campus Multi-Energy Summary =====');
disp(summaryTable);
disp(' ');
disp('===== Key Metrics by Typical Weather Scenario =====');
disp(metricTable);
disp(' ');
disp('===== Annual Weighted Summary =====');
disp(annualTable);

allResults = strip_yalmip_objects(allResults);
allData    = make_clean_saved_data(allData);
summaryTable = strip_yalmip_objects(summaryTable);
metricTable = strip_yalmip_objects(metricTable);
scenarioTable = strip_yalmip_objects(scenarioTable);
annualTable = strip_yalmip_objects(annualTable);

reset_optimizer_caches();
try
    yalmip('clear');
catch
end

save('year_typical_scenario_results.mat', ...
     'allResults', 'allData', 'scenarioTable', 'summaryTable', 'metricTable', 'annualTable', ...
     'baselineCarbonQuota_kg', 'admmRho', 'admmMaxIter', 'admmTolPri', 'admmTolDual', '-v7.3');

try
    export_plot_data_csv(allResults, allData, 'year_plot_data_csv');
catch ME
    warning('Exporting annual plotting CSV data failed: %s', ME.message);
end

if generatePlots
    plot_year_submission('year_typical_scenario_results.mat', 'year_submission');
end

%% ============================ Local functions ============================

function scenarios = define_typical_scenarios()
%DEFINE_TYPICAL_SCENARIOS 典型天气/新能源场景。
% days用于将典型日结果加权折算成年运行效益；可按当地实际气象统计进一步修改。
%
% 采用一次性 struct 构造，保证所有元素字段完全一致，避免 MATLAB 报错：
% “在不同结构体之间进行下标赋值”。

scenarios = struct( ...
    'name',      {'Sunny_LowWind', 'Sunny_HighWind', 'Cloudy_MidWind', 'Rainy_LowWind', 'Rainy_HighWind'}, ...
    'name_cn',   {'晴天少风',      '晴天多风',       '多云中风',       '阴天少风',      '阴天多风',      }, ...
    'pvScale',   {3.30,            3.30,             3.0,             2.70,            2.30,      }, ...
    'windScale', {2.70,            3.30,             3.0,             2.70,            3.30,        }, ...
    'loadScale', {1.00,            1.00,             1.00,             1.00,            1.00,        }, ...
    'h2Scale',   {1.00,            1.00,             1.00,             1.00,            1.00,         }, ...
    'days',      {85,              60,               100,               80,              40,         } ...
);
end

function row = make_scenario_info_row(data)
row = struct();
row.TypicalScenario = string(data.typicalScenarioName);
row.TypicalScenarioCN = string(data.typicalScenarioNameCN);
row.RepresentativeDays = data.representativeDays;
row.PVScaleFinal = data.pvScaleFinal;
row.WindScaleFinal = data.windScaleFinal;
row.LoadScaleFinal = data.loadScaleFinal;
row.H2ScaleFinal = data.h2ScaleFinal;
row.AvailablePV_MWh = sum(data.Ppv(:))*data.dt;
row.AvailableWind_MWh = sum(data.Pwind(:))*data.dt;
row.TotalElectricLoad_MWh = sum(data.Pload(:))*data.dt;
row.TotalHeatLoad_MWh = sum(data.Hload(:))*data.dt;
row.TotalH2Load_kg = sum(data.H2load(:))*data.dt;
end

function data = disable_storage(data)
z = zeros(data.N,1);
data.PchMax = z;
data.PdisMax = z;
data.Emax = z;
data.SOC0_e = z;
data.termSOC_e = z;
data.QesMax = z;
data.lambdaQes = z;
data.HchMax = z;
data.HdisMax = z;
data.EthMax = z;
data.SOC0_th = z;
data.termSOC_th = z;
data.H2chMax = z;
data.H2disMax = z;
data.EH2Max = z;
data.SOC0_h2 = z;
data.termSOC_h2 = z;
end

function row = make_row(data, method, globalObj, localObj, totalPVCurt, avgMinVoltageSq, iterations, status, errMsg)
if nargin < 8 || isempty(status)
    status = 'Solved';
end
if nargin < 9
    errMsg = '';
end
row = struct('TypicalScenario', string(data.typicalScenarioName), ...
    'TypicalScenarioCN', string(data.typicalScenarioNameCN), ...
    'StorageCase', string(data.storageLabel), ...
    'Scenario', string(data.scenarioName), ...
    'Method', string(method), ...
    'GlobalObjective', globalObj, ...
    'LocalObjective', localObj, ...
    'TotalPVCurt', totalPVCurt, ...
    'AvgMinVoltageSq', avgMinVoltageSq, ...
    'Iterations', iterations, ...
    'Status', string(status), ...
    'ErrorMessage', string(errMsg));
end

function row = make_failed_row(data, method, errMsg)
%MAKE_FAILED_ROW 生成求解失败场景的summary占位行，保证后续场景不中断。
row = make_row(data, method, NaN, NaN, NaN, NaN, NaN, 'Failed', errMsg);
end

function row = make_metric_row(data, method, res)
%MAKE_METRIC_ROW Indicators for economic and emission-reduction comparison.
dt = data.dt;
Pgrid = get_res_field(res, 'Pgrid');
PpvUse = get_res_field(res, 'PpvUse');
PpvCurt = get_res_field(res, 'PpvCurt');
PwindUse = get_res_field(res, 'PwindUse');
PwindCurt = get_res_field(res, 'PwindCurt');
Fgas = get_res_field(res, 'Fgas');
Pchp = get_res_field(res, 'Pchp');
Hchp = get_res_field(res, 'Hchp');
H2short = get_res_field(res, 'H2short');
Hdump = get_res_field(res, 'Hdump');
Pch = get_res_field(res, 'Pch');
Pdis = get_res_field(res, 'Pdis');
SOCe = get_res_field(res, 'SOC_e');
V = get_res_field(res, 'V');

renTotal = sum(data.Ppv(:))*dt + sum(data.Pwind(:))*dt;
renUse = sum(PpvUse(:))*dt + sum(PwindUse(:))*dt;
renCurt = sum(PpvCurt(:))*dt + sum(PwindCurt(:))*dt;
if renTotal > 1e-9
    renUseRate = renUse / renTotal * 100;
    renCurtRate = renCurt / renTotal * 100;
else
    renUseRate = NaN;
    renCurtRate = NaN;
end

gridEnergy = sum(Pgrid(:))*dt;
gridPeak = max(sum(Pgrid,1));
gridValley = min(sum(Pgrid,1));
gridPeakValleyDiff = gridPeak - gridValley;
gasEnergy = sum(Fgas(:))*dt;
carbon = carbon_accounting(data, Pgrid, Pchp, Hchp, Fgas);
carbonEmissionKg = sum(carbon.emission(:));
carbonQuotaKg = sum(carbon.quota(:));
carbonEmissionTon = carbonEmissionKg / 1000;
carbonQuotaTon = carbonQuotaKg / 1000;
carbonBuyKg = sum(get_res_field(res, 'CarbonBuyMarket_kg'), 'all');
carbonSellKg = sum(get_res_field(res, 'CarbonSellMarket_kg'), 'all');
carbonTradeKg = sum(abs(get_res_field(res, 'CarbonTradeWithCommunities_kg')), 'all') / 2;
carbonUnusedKg = sum(get_res_field(res, 'CarbonUnusedAllowance_kg'), 'all');
if isfield(res,'obj')
    totalObjective = res.obj;
elseif isfield(res,'recoveredGlobalObjective')
    totalObjective = res.recoveredGlobalObjective;
else
    totalObjective = NaN;
end

row = struct();
row.TypicalScenario = string(data.typicalScenarioName);
row.TypicalScenarioCN = string(data.typicalScenarioNameCN);
row.StorageCase = string(data.storageLabel);
row.StorageEnabled = logical(data.storageEnabled);
row.Scenario = string(data.scenarioName);
row.Method = string(method);
row.Status = "Solved";
row.ErrorMessage = "";
row.RepresentativeDays = data.representativeDays;
row.TotalObjective_Yuan = totalObjective;
row.AnnualObjective_Yuan = totalObjective * data.representativeDays;
row.GridEnergy_MWh = gridEnergy;
row.AnnualGridEnergy_MWh = gridEnergy * data.representativeDays;
row.GridPeak_MW = gridPeak;
row.GridPeakValleyDiff_MW = gridPeakValleyDiff;
row.GasEnergy_MWhth = gasEnergy;
row.AnnualGasEnergy_MWhth = gasEnergy * data.representativeDays;
row.CarbonEmission_tCO2 = carbonEmissionTon;
row.AnnualCarbonEmission_tCO2 = carbonEmissionTon * data.representativeDays;
row.CarbonQuota_tCO2 = carbonQuotaTon;
row.AnnualCarbonQuota_tCO2 = carbonQuotaTon * data.representativeDays;
row.CarbonSurplusBeforeTrade_tCO2 = (carbonQuotaKg - carbonEmissionKg) / 1000;
row.AnnualCarbonSurplusBeforeTrade_tCO2 = row.CarbonSurplusBeforeTrade_tCO2 * data.representativeDays;
row.CarbonBuyMarket_tCO2 = carbonBuyKg / 1000;
row.AnnualCarbonBuyMarket_tCO2 = row.CarbonBuyMarket_tCO2 * data.representativeDays;
row.CarbonSellMarket_tCO2 = carbonSellKg / 1000;
row.AnnualCarbonSellMarket_tCO2 = row.CarbonSellMarket_tCO2 * data.representativeDays;
row.CarbonTradeAbs_tCO2 = carbonTradeKg / 1000;
row.AnnualCarbonTradeAbs_tCO2 = row.CarbonTradeAbs_tCO2 * data.representativeDays;
row.CarbonUnusedAllowance_tCO2 = carbonUnusedKg / 1000;
row.AnnualCarbonUnusedAllowance_tCO2 = row.CarbonUnusedAllowance_tCO2 * data.representativeDays;
row.RenewableAvailable_MWh = renTotal;
row.RenewableUse_MWh = renUse;
row.RenewableUseRate_percent = renUseRate;
row.RenewableCurtailment_MWh = renCurt;
row.AnnualRenewableCurtailment_MWh = renCurt * data.representativeDays;
row.RenewableCurtailmentRate_percent = renCurtRate;
row.H2Shortage_kg = sum(H2short(:))*dt;
row.AnnualH2Shortage_kg = row.H2Shortage_kg * data.representativeDays;
row.HeatDump_MWh = sum(Hdump(:))*dt;
row.StorageCharge_MWh = sum(Pch(:))*dt;
row.StorageDischarge_MWh = sum(Pdis(:))*dt;
row.StorageSOCSwing_MWh = max(SOCe(:)) - min(SOCe(:));
if isempty(V)
    row.AvgMinimumVoltage_pu = NaN;
    row.GridVoltageDeviation_pu = NaN;
else
    voltagePu = sqrt(max(0,V));
    row.AvgMinimumVoltage_pu = mean(min(voltagePu,[],1));
    row.GridVoltageDeviation_pu = mean(abs(voltagePu(:) - 1.0));
end
end

function row = make_failed_metric_row(data, method, errMsg)
%MAKE_FAILED_METRIC_ROW 生成求解失败场景的指标占位行。
% 该行保留场景与储能标签，指标填 NaN，便于导出表格后识别“无可行解”。
row = struct();
row.TypicalScenario = string(data.typicalScenarioName);
row.TypicalScenarioCN = string(data.typicalScenarioNameCN);
row.StorageCase = string(data.storageLabel);
row.StorageEnabled = logical(data.storageEnabled);
row.Scenario = string(data.scenarioName);
row.Method = string(method);
row.Status = "Failed";
row.ErrorMessage = string(errMsg);
row.RepresentativeDays = data.representativeDays;
row.TotalObjective_Yuan = NaN;
row.AnnualObjective_Yuan = NaN;
row.GridEnergy_MWh = NaN;
row.AnnualGridEnergy_MWh = NaN;
row.GridPeak_MW = NaN;
row.GridPeakValleyDiff_MW = NaN;
row.GasEnergy_MWhth = NaN;
row.AnnualGasEnergy_MWhth = NaN;
row.CarbonEmission_tCO2 = NaN;
row.AnnualCarbonEmission_tCO2 = NaN;
row.CarbonQuota_tCO2 = NaN;
row.AnnualCarbonQuota_tCO2 = NaN;
row.CarbonSurplusBeforeTrade_tCO2 = NaN;
row.AnnualCarbonSurplusBeforeTrade_tCO2 = NaN;
row.CarbonBuyMarket_tCO2 = NaN;
row.AnnualCarbonBuyMarket_tCO2 = NaN;
row.CarbonSellMarket_tCO2 = NaN;
row.AnnualCarbonSellMarket_tCO2 = NaN;
row.CarbonTradeAbs_tCO2 = NaN;
row.AnnualCarbonTradeAbs_tCO2 = NaN;
row.CarbonUnusedAllowance_tCO2 = NaN;
row.AnnualCarbonUnusedAllowance_tCO2 = NaN;
row.RenewableAvailable_MWh = NaN;
row.RenewableUse_MWh = NaN;
row.RenewableUseRate_percent = NaN;
row.RenewableCurtailment_MWh = NaN;
row.AnnualRenewableCurtailment_MWh = NaN;
row.RenewableCurtailmentRate_percent = NaN;
row.H2Shortage_kg = NaN;
row.AnnualH2Shortage_kg = NaN;
row.HeatDump_MWh = NaN;
row.StorageCharge_MWh = NaN;
row.StorageDischarge_MWh = NaN;
row.StorageSOCSwing_MWh = NaN;
row.AvgMinimumVoltage_pu = NaN;
row.GridVoltageDeviation_pu = NaN;
end

function T = drop_table_columns(T, names)
if isempty(T) || ~istable(T)
    return;
end
vars = intersect(names, T.Properties.VariableNames, 'stable');
if ~isempty(vars)
    T(:, vars) = [];
end
end

function annualTable = make_annual_weather_table(metricTable)
if isempty(metricTable)
    annualTable = table();
    return;
end
T = metricTable(metricTable.Status == "Solved", :);
if isempty(T)
    annualTable = table();
    return;
end

methods = unique(T.Method, 'stable');
rows = [];
for m = 1:numel(methods)
    sub = T(T.Method == methods(m), :);
    r = struct();
    r.Method = methods(m);
    r.TotalRepresentativeDays = sum(sub.RepresentativeDays);
    r.AnnualObjective_Yuan = sum_no_nan(sub.AnnualObjective_Yuan);
    r.AnnualGridEnergy_MWh = sum_no_nan(sub.AnnualGridEnergy_MWh);
    r.AnnualGasEnergy_MWhth = sum_no_nan(sub.AnnualGasEnergy_MWhth);
    r.AnnualCarbonEmission_tCO2 = sum_no_nan(sub.AnnualCarbonEmission_tCO2);
    r.AnnualCarbonQuota_tCO2 = sum_no_nan(sub.AnnualCarbonQuota_tCO2);
    r.AnnualCarbonBuyMarket_tCO2 = sum_no_nan(sub.AnnualCarbonBuyMarket_tCO2);
    r.AnnualCarbonSellMarket_tCO2 = sum_no_nan(sub.AnnualCarbonSellMarket_tCO2);
    r.AnnualCarbonTradeAbs_tCO2 = sum_no_nan(sub.AnnualCarbonTradeAbs_tCO2);
    r.AnnualRenewableAvailable_MWh = sum_no_nan(sub.RenewableAvailable_MWh .* sub.RepresentativeDays);
    r.AnnualRenewableUse_MWh = sum_no_nan(sub.RenewableUse_MWh .* sub.RepresentativeDays);
    r.AnnualRenewableCurtailment_MWh = sum_no_nan(sub.AnnualRenewableCurtailment_MWh);
    r.AnnualRenewableUseRate_percent = safe_pct(r.AnnualRenewableUse_MWh, r.AnnualRenewableAvailable_MWh);
    r.AnnualH2Shortage_kg = sum_no_nan(sub.AnnualH2Shortage_kg);
    rows = [rows; r]; %#ok<AGROW>
end
annualTable = struct2table(rows);
end

function benefitTable = make_storage_benefit_table(metricTable)
%MAKE_STORAGE_BENEFIT_TABLE Positive values mean storage improves the metric.
if isempty(metricTable) || height(metricTable) < 2
    benefitTable = table();
    return;
end
methods = unique(metricTable.Method, 'stable');
scens = unique(metricTable.TypicalScenario, 'stable');
rows = [];
for m = 1:numel(methods)
    for s = 1:numel(scens)
        sub = metricTable(metricTable.Method == methods(m) & metricTable.TypicalScenario == scens(s), :);
        withIdx = sub.StorageEnabled == true;
        noIdx = sub.StorageEnabled == false;
        if ~any(withIdx) || ~any(noIdx)
            continue;
        end
        A = sub(find(withIdx,1), :); %#ok<FNDSB> % with storage
        B = sub(find(noIdx,1), :);   %#ok<FNDSB> % no storage
        r = struct();
        r.TypicalScenario = A.TypicalScenario;
        r.TypicalScenarioCN = A.TypicalScenarioCN;
        r.Method = methods(m);
        r.RepresentativeDays = A.RepresentativeDays;
        r.WithStorageStatus = A.Status;
        r.NoStorageStatus = B.Status;
        if A.Status ~= "Solved" || B.Status ~= "Solved"
            r.FeasibilityNote = "存在不可行/失败场景，改善量以 NaN 标记；可用于说明储能提升极端工况可行性。";
        else
            r.FeasibilityNote = "Both solved";
        end
        r.CostSaving_Yuan = B.TotalObjective_Yuan - A.TotalObjective_Yuan;
        r.CostSaving_percent = safe_pct(B.TotalObjective_Yuan - A.TotalObjective_Yuan, B.TotalObjective_Yuan);
        r.AnnualCostSaving_Yuan = r.CostSaving_Yuan * A.RepresentativeDays;
        r.GridEnergyReduction_MWh = B.GridEnergy_MWh - A.GridEnergy_MWh;
        r.AnnualGridEnergyReduction_MWh = r.GridEnergyReduction_MWh * A.RepresentativeDays;
        r.GridPeakReduction_MW = B.GridPeak_MW - A.GridPeak_MW;
        r.PeakValleyReduction_MW = B.GridPeakValleyDiff_MW - A.GridPeakValleyDiff_MW;
        r.CarbonReduction_tCO2 = B.CarbonEmission_tCO2 - A.CarbonEmission_tCO2;
        r.CarbonReduction_percent = safe_pct(B.CarbonEmission_tCO2 - A.CarbonEmission_tCO2, B.CarbonEmission_tCO2);
        r.AnnualCarbonReduction_tCO2 = r.CarbonReduction_tCO2 * A.RepresentativeDays;
        r.CurtailmentReduction_MWh = B.RenewableCurtailment_MWh - A.RenewableCurtailment_MWh;
        r.CurtailmentReduction_percent = safe_pct(B.RenewableCurtailment_MWh - A.RenewableCurtailment_MWh, B.RenewableCurtailment_MWh);
        r.AnnualCurtailmentReduction_MWh = r.CurtailmentReduction_MWh * A.RepresentativeDays;
        r.RenewableUseRateIncrease_pctpt = A.RenewableUseRate_percent - B.RenewableUseRate_percent;
        r.H2ShortageReduction_kg = B.H2Shortage_kg - A.H2Shortage_kg;
        r.AnnualH2ShortageReduction_kg = r.H2ShortageReduction_kg * A.RepresentativeDays;
        rows = [rows; r]; %#ok<AGROW>
    end
end
if isempty(rows)
    benefitTable = table();
else
    benefitTable = struct2table(rows);
end
end

function annualTable = make_annual_benefit_table(benefitTable)
if isempty(benefitTable)
    annualTable = table();
    return;
end
methods = unique(benefitTable.Method, 'stable');
rows = [];
for m = 1:numel(methods)
    sub = benefitTable(benefitTable.Method == methods(m), :);
    r = struct();
    r.Method = methods(m);
    r.TotalRepresentativeDays = sum(sub.RepresentativeDays);
    r.AnnualCostSaving_Yuan = sum_no_nan(sub.AnnualCostSaving_Yuan);
    r.AnnualCarbonReduction_tCO2 = sum_no_nan(sub.AnnualCarbonReduction_tCO2);
    r.AnnualCurtailmentReduction_MWh = sum_no_nan(sub.AnnualCurtailmentReduction_MWh);
    r.AnnualGridEnergyReduction_MWh = sum_no_nan(sub.AnnualGridEnergyReduction_MWh);
    r.AnnualH2ShortageReduction_kg = sum_no_nan(sub.AnnualH2ShortageReduction_kg);
    % 峰值类指标不能简单按天数加权，取各典型日改善量的最大值/平均值作为参考。
    r.MaxGridPeakReduction_MW = max(sub.GridPeakReduction_MW);
    r.AvgGridPeakReduction_MW = mean_no_nan(sub.GridPeakReduction_MW);
    r.AvgRenewableUseRateIncrease_pctpt = mean_no_nan(sub.RenewableUseRateIncrease_pctpt);
    rows = [rows; r]; %#ok<AGROW>
end
annualTable = struct2table(rows);
end

function s = sum_no_nan(x)
x = x(~isnan(x));
if isempty(x)
    s = NaN;
else
    s = sum(x);
end
end

function m = mean_no_nan(x)
x = x(~isnan(x));
if isempty(x)
    m = NaN;
else
    m = mean(x);
end
end

function x = get_res_field(res, name)
if isfield(res, name) && ~isempty(res.(name))
    x = res.(name);
else
    x = 0;
end
end

function y = safe_pct(numerator, denominator)
if abs(denominator) < 1e-9
    y = NaN;
else
    y = numerator / denominator * 100;
end
end

function out = make_clean_saved_data(allData)
scenNames = fieldnames(allData);
out = struct();

keep = { ...
    'scenarioName','typicalScenarioName','typicalScenarioNameCN','representativeDays', ...
    'pvScaleFinal','windScaleFinal','loadScaleFinal','h2ScaleFinal', ...
    'storageEnabled','storageLabel','storageCase','N','T','dt', ...
    'admmRho','admmMaxIter','admmTolPri','admmTolDual', ...
    'enableCarbonQuota','enableCarbonTrading','enableCommunityCarbonTrading','allowCarbonMarketSell', ...
    'carbonQuotaMode','fixedCarbonQuota_kg', ...
    'zetaE','zetaH','chiE','chiH','ceh','carbonBuyPrice','carbonSellPrice','minChpHeatShare', ...
    'Pload','Hload','H2load','Ppv','Pwind','PcompFixed','alphaCompH2','PcompMax', ...
    'ce','cCarbon','pCO2','efGrid','Pbase','Qbase', ...
    'PchpRated','etaE_chp','etaH_chp','FgasMin','FgasMax', ...
    'PchpMin','RampUpCHP','RampDnCHP','StartUpCHP','ShutDnCHP','MinUpCHP','MinDnCHP', ...
    'PebMax','etaEb','PelecMax','etaElec','H2fcMax','etaFc', ...
    'RampUpEb','RampDnEb','cRampEb','RampUpElec','RampDnElec','cRampElec', ...
    'RampUpFc','RampDnFc','cRampFc','RampUpComp','RampDnComp','cRampComp', ...
    'PchMax','PdisMax','Emax','SOC0_e','etaCh_e','etaDis_e', ...
    'HchMax','HdisMax','EthMax','SOC0_th','etaCh_th','etaDis_th', ...
    'H2chMax','H2disMax','EH2Max','SOC0_h2', ...
    'termSOC_e','termSOC_th','termSOC_h2', ...
    'PgridMax','QinjMin','QinjMax', ...
    'Vmin','Vmax','Vslack','rootBus','branch','rline','xline', ...
    'PijMax','QijMax','PsubMax','PbusBase','QbusBase','bus_has_comm','bus_to_comm','out_lines','baseMVA', ...
    'lambdaPVCurt','lambdaWindCurt','lambdaH2Short','lambdaQpv','lambdaQes','QpvMax','QesMax','QcompCoeff', ...
    'cGas','efGas' ...
    };

for s = 1:numel(scenNames)
    D = allData.(scenNames{s});
    S = struct();
    for k = 1:numel(keep)
        if isfield(D, keep{k})
            S.(keep{k}) = D.(keep{k});
        end
    end
    out.(scenNames{s}) = S;
end
end

function x = strip_yalmip_objects(x)
if isa(x,'sdpvar') || isa(x,'optimizer') || isa(x,'lmi') || isa(x,'constraint')
    x = [];
    return;
end

if isstruct(x)
    fn = fieldnames(x);
    for ii = 1:numel(x)
        for k = 1:numel(fn)
            x(ii).(fn{k}) = strip_yalmip_objects(x(ii).(fn{k}));
        end
    end
elseif iscell(x)
    for k = 1:numel(x)
        x{k} = strip_yalmip_objects(x{k});
    end
elseif istable(x)
    vars = x.Properties.VariableNames;
    for k = 1:numel(vars)
        x.(vars{k}) = strip_yalmip_objects(x.(vars{k}));
    end
end
end
