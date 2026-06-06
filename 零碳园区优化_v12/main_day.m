%% Zero-carbon campus multi-energy runner: single scenario (S4-style)
% 参考 main_run_comparison 的 S4 场景，只运行一个典型日场景。
% 可配置 ddreScenarioId、pvScale、windScale。

yalmip('clear');
reset_optimizer_caches();

% ===================== Configuration =====================
caseName = 'ieee33_3comm_hetero_real';
ddreScenarioId = 13;   % 1-Day Scenario 编号（可切换：116, 178, 137, 183, 40 等）
pvScale = 5;           % 光伏出力/容量倍率
windScale = 5;         % 风电出力/容量倍率
loadScale = 1.0;
h2Scale = 1.00;

runCentralized = 1;
runFixedADMM   = 0;
usePreprocess  = 1;
generatePlots  = 0;

admmRhoPQ = 200;    % P/Q feeder-consensus ADMM penalty
admmRhoC  = 100;    % carbon-consensus ADMM penalty
admmMaxIter = 300;
admmTolPri = 5e-4;
admmTolDual = 5e-3;

% ===================== Data Preparation =====================
data = build_case(caseName, ddreScenarioId);

scenarioDef = struct('name', 'SingleScenario', 'name_cn', '单场景', ...
    'pvScale', pvScale, 'windScale', windScale, ...
    'loadScale', loadScale, 'h2Scale', h2Scale, 'days', 365);
data = apply_scenario(data, scenarioDef);

data.typicalScenarioName = 'SingleScenario';
data.typicalScenarioNameCN = '单场景';
data.representativeDays = 365;
data.ddreScenarioId = ddreScenarioId;
data.pvScaleFinal = pvScale;
data.windScaleFinal = windScale;
data.loadScaleFinal = loadScale;
data.h2ScaleFinal = h2Scale;
data.storageEnabled = true;
data.storageLabel = '有储能';
data.storageCase = 'WithStorage';
data.scenarioName = matlab.lang.makeValidName('SingleScenario');

% Paper benchmark carbon allowance
baselineCarbonQuota_kg = [];
fprintf('\n============================================================\n');
fprintf('Using paper benchmark-based carbon allowance mechanism.\n');
fprintf('No fixed S1/no-storage carbon quota baseline is computed.\n');
fprintf('Quota mode: baseline-scenario; carbon market buy/sell = 200/100 yuan per tCO2.\n');
fprintf('============================================================\n');

if isfield(data, 'fixedCarbonQuota_kg')
    data = rmfield(data, 'fixedCarbonQuota_kg');
end
data.carbonQuotaMode = 'baseline-scenario';
carbonOpts = struct( ...
    'enableCarbonQuota', true, ...
    'enableCommunityCarbonTrading', true, ...
    'allowCarbonMarketSell', true, ...
    'carbonBuyPrice', 150, ...
    'carbonSellPrice', 100, ...
    'zetaE', 1080, ...
    'zetaH', 324, ...
    'chiE', 728, ...
    'chiH', 367.2, ...
    'ceh', 1.6667, ...
    'QtradeMax_tCO2', 1.6);
data = configure_carbon_trading(data, carbonOpts);
data.admmRhoPQ = admmRhoPQ;
data.admmRhoC  = admmRhoC;
data.admmMaxIter = admmMaxIter;
data.admmTolPri = admmTolPri;
data.admmTolDual = admmTolDual;
data.preserveOptimizerCache = logical(runFixedADMM);

fprintf('\n============================================================\n');
fprintf('Single scenario: ddreScenarioId=%03d | pvScale=%.3f | windScale=%.3f\n', ...
    ddreScenarioId, pvScale, windScale);
fprintf('Load scale=%.3f, H2 scale=%.3f, Days=%d\n', ...
    loadScale, h2Scale, 365);
fprintf('============================================================\n');

% ===================== Solve =====================
allResults = struct();
allData    = struct();
summaryRows = [];
metricRows  = [];

if runCentralized
    fprintf('Running multi-energy centralized benchmark...\n');
    try
        central = solve_centralized(data);
        allResults.(data.scenarioName).centralized = central;
        fprintf('Centralized optimization cost: %.4f\n', central.obj);
        summaryRows = [summaryRows; make_row(data, central.method, central.obj, NaN, central.totalPVCurt, mean(min(central.V,[],1)), NaN, 'Solved', '')];
        metricRows = [metricRows; make_metric_row(data, central.method, central)];
    catch ME
        methodName = 'centralized-multi-energy-pq';
        warning('场景求解失败：%s', ME.message);
        central = struct();
        central.method = methodName;
        central.obj = NaN;
        central.solveStatus = 'Failed';
        central.errorMessage = ME.message;
        allResults.(data.scenarioName).centralized = central;
        summaryRows = [summaryRows; make_failed_row(data, methodName, ME.message)];
        metricRows = [metricRows; make_failed_metric_row(data, methodName, ME.message)];
    end
end

if runFixedADMM
    fprintf('Running multi-energy fixed-rho ADMM...\n');
    try
        if usePreprocess
            fprintf('Prebuilding ADMM optimizer cache for this scenario...\n');
            tPreprocess = tic;
            preprocess_optimizers(data, data.admmRhoPQ*ones(data.N,1), data.admmRhoC*ones(data.N,1));
            data.optimizersPreprocessed = true;
            fprintf('ADMM optimizer cache ready in %.2f s.\n', toc(tPreprocess));
        end
        admm = solve_admm_fixed(data);
        allResults.(data.scenarioName).admm = admm;
        summaryRows = [summaryRows; make_row(data, admm.method, admm.recoveredGlobalObjective, admm.finalLocalCost, admm.totalPVCurt, mean(min(admm.V,[],1)), numel(admm.hist_pri), 'Solved', '')];
        metricRows = [metricRows; make_metric_row(data, admm.method, admm)];
    catch ME
        methodName = 'fixed-rho-admm';
        warning('ADMM 求解失败：%s', ME.message);
        admm = struct();
        admm.method = methodName;
        admm.solveStatus = 'Failed';
        admm.errorMessage = ME.message;
        allResults.(data.scenarioName).admm = admm;
        summaryRows = [summaryRows; make_failed_row(data, methodName, ME.message)];
        metricRows = [metricRows; make_failed_metric_row(data, methodName, ME.message)];
    end
end

allData.(data.scenarioName) = data;

% ===================== Output =====================
summaryTable = struct2table(summaryRows);
metricTable  = struct2table(metricRows);

dropOutputColumns = {'StorageCase','StorageEnabled','Scenario','Method','Status','ErrorMessage'};
summaryTable = drop_table_columns(summaryTable, dropOutputColumns);
metricTable  = drop_table_columns(metricTable, dropOutputColumns);

try
    writetable(metricTable, 'day_single_scenario_metric_table.csv');
catch ME
    warning('写出CSV结果表失败：%s', ME.message);
end

disp(' ');
disp('===== Zero-Carbon Campus Multi-Energy Summary =====');
disp(summaryTable);
disp(' ');
disp('===== Key Metrics =====');
disp(metricTable);

allResults = strip_yalmip_objects(allResults);
allData    = make_clean_saved_data(allData);
summaryTable = strip_yalmip_objects(summaryTable);
metricTable  = strip_yalmip_objects(metricTable);

reset_optimizer_caches();
try
    yalmip('clear');
catch
end

save('day_single_scenario_results.mat', ...
     'allResults', 'allData', 'summaryTable', 'metricTable', ...
     'baselineCarbonQuota_kg', 'admmRhoPQ', 'admmRhoC', 'admmMaxIter', 'admmTolPri', 'admmTolDual', '-v7.3');

try
    export_plot_data_csv(allResults, allData, 'day_single_plot_data_csv');
catch ME
    warning('Exporting plotting CSV data failed: %s', ME.message);
end

if generatePlots
    plot_year_submission('day_single_scenario_results.mat', 'day_single_submission');
end

%% ============================ Local functions ============================

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
    'DDREScenarioId', get_numeric_data_field(data, 'ddreScenarioId'), ...
    'PVLabel', get_numeric_data_field(data, 'pvLabel'), ...
    'WindLabel', get_numeric_data_field(data, 'windLabel'), ...
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
row = make_row(data, method, NaN, NaN, NaN, NaN, NaN, 'Failed', errMsg);
end

function row = make_metric_row(data, method, res)
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
row.DDREScenarioId = get_numeric_data_field(data, 'ddreScenarioId');
row.PVLabel = get_numeric_data_field(data, 'pvLabel');
row.WindLabel = get_numeric_data_field(data, 'windLabel');
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
row = struct();
row.TypicalScenario = string(data.typicalScenarioName);
row.TypicalScenarioCN = string(data.typicalScenarioNameCN);
row.DDREScenarioId = get_numeric_data_field(data, 'ddreScenarioId');
row.PVLabel = get_numeric_data_field(data, 'pvLabel');
row.WindLabel = get_numeric_data_field(data, 'windLabel');
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

function val = get_numeric_data_field(data, fieldName)
if isfield(data, fieldName) && ~isempty(data.(fieldName))
    val = data.(fieldName);
else
    val = NaN;
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
    'admmRhoPQ','admmRhoC','admmMaxIter','admmTolPri','admmTolDual', ...
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
    'lambdaPVCurt','lambdaWindCurt','lambdaH2Short','lambdaQpv','lambdaQwind','lambdaQes','QpvMax','QwindMax','QesMax','QcompCoeff', ...
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
