%% Four-scenario energy-carbon comparison runner
% S1: normal renewable output, with storage, no carbon trading, no demand response
% S2: normal renewable output, with storage, no carbon trading
% S3: normal renewable output, with storage, with carbon trading
% S4: high renewable output, with storage, with carbon trading

yalmip('clear');
reset_optimizer_caches();

caseName = 'ieee33_3comm_hetero_real';
ddreScenarioId = 12;
runCentralized = 1;
runFixedADMM = 1;
admmRhoPQ = 200;    % P/Q feeder-consensus ADMM penalty
admmRhoC  = 100;     % carbon-consensus ADMM penalty, tCO2-scale carbon variables
admmMaxIter = 1000;
admmTolPri = 5e-4;
admmTolDual = 5e-3;

baseData = build_case(caseName, ddreScenarioId);
scenarios = define_comparison_scenarios();

allResults = struct();
allData = struct();
summaryRows = [];
metricRows = [];
baselineCarbonQuota_kg = [];

for k = 1:numel(scenarios)
    sc = scenarios(k);
    data = prepare_comparison_data(baseData, sc, admmMaxIter, admmTolPri, admmTolDual);
    data.admmRhoPQ = admmRhoPQ;
    data.admmRhoC  = admmRhoC;
    data.preserveOptimizerCache = logical(runFixedADMM);

    % Carbon-quota baseline handling:
    %   Scenario 1 is the baseline scenario. Centralized and ADMM must solve
    %   the same model, so Scenario 1 must NOT use fixedCarbonQuota_kg.
    %   After both methods of Scenario 1 are solved, the Scenario-1 quota is
    %   stored and then applied only to subsequent scenarios.
    pendingBaselineCarbonQuota_kg = [];
    if ~isempty(baselineCarbonQuota_kg)
        data.fixedCarbonQuota_kg = baselineCarbonQuota_kg;
        data.carbonQuotaMode = 'fixed-baseline';
    else
        if isfield(data, 'fixedCarbonQuota_kg')
            data = rmfield(data, 'fixedCarbonQuota_kg');
        end
        data.carbonQuotaMode = 'baseline-scenario';
    end

    fprintf('\n============================================================\n');
    fprintf('%s | %s\n', data.comparisonScenario, data.comparisonScenarioCN);
    fprintf('PV scale=%.3f, Wind scale=%.3f, Storage=%d, DemandResponse=%d, CarbonTrading=%d, rhoPQ=%.3f, rhoC=%.3f\n', ...
        data.pvScaleFinal, data.windScaleFinal, data.storageEnabled, data.demandResponseEnabled, data.enableCarbonTrading, data.admmRhoPQ, data.admmRhoC);
    fprintf('============================================================\n');

    allData.(data.scenarioName) = data;

    if runCentralized
        methodName = 'centralized-multi-energy-pq';
        try
            fprintf('Running centralized solver...\n');
            central = solve_centralized(data);
            allResults.(data.scenarioName).centralized = central;
            if isempty(baselineCarbonQuota_kg) && isfield(central, 'CarbonQuota_kg') && ~isempty(central.CarbonQuota_kg)
                pendingBaselineCarbonQuota_kg = central.CarbonQuota_kg;
            end
            summaryRows = [summaryRows; make_summary_row(data, central.method, central, central.Status, '')]; %#ok<AGROW>
            metricRows = [metricRows; make_metric_row(data, central.method, central, central.Status, '')]; %#ok<AGROW>
        catch ME
            warning('Centralized failed for %s: %s', data.scenarioName, ME.message);
            allResults.(data.scenarioName).centralized = make_failed_result(methodName, ME.message);
            summaryRows = [summaryRows; make_summary_row(data, methodName, [], 'Failed', ME.message)]; %#ok<AGROW>
            metricRows = [metricRows; make_metric_row(data, methodName, [], 'Failed', ME.message)]; %#ok<AGROW>
        end
    end

    if runFixedADMM
        methodName = 'admm-fixed-multi-energy-pq-carbon';
        try
            fprintf('Running ADMM solver...\n');
            fprintf('Prebuilding ADMM optimizer cache for this scenario...\n');
            tPreprocess = tic;
            preprocess_optimizers(data, data.admmRhoPQ*ones(data.N,1), data.admmRhoC*ones(data.N,1));
            data.optimizersPreprocessed = true;
            fprintf('ADMM optimizer cache ready in %.2f s.\n', toc(tPreprocess));
            admm = solve_admm_fixed(data);
            allResults.(data.scenarioName).admm = admm;
            if isempty(baselineCarbonQuota_kg) && isempty(pendingBaselineCarbonQuota_kg) && isfield(admm, 'CarbonQuota_kg') && ~isempty(admm.CarbonQuota_kg)
                % Fallback only: normally the fixed baseline should come from
                % the centralized Scenario-1 result. This branch is used only
                % when the centralized solver is disabled or fails.
                pendingBaselineCarbonQuota_kg = admm.CarbonQuota_kg;
            end
            summaryRows = [summaryRows; make_summary_row(data, admm.method, admm, admm.Status, '')]; %#ok<AGROW>
            metricRows = [metricRows; make_metric_row(data, admm.method, admm, admm.Status, '')]; %#ok<AGROW>
        catch ME
            warning('ADMM failed for %s: %s', data.scenarioName, ME.message);
            allResults.(data.scenarioName).admm = make_failed_result(methodName, ME.message);
            summaryRows = [summaryRows; make_summary_row(data, methodName, [], 'Failed', ME.message)]; %#ok<AGROW>
            metricRows = [metricRows; make_metric_row(data, methodName, [], 'Failed', ME.message)]; %#ok<AGROW>
        end
    end

    if isempty(baselineCarbonQuota_kg) && ~isempty(pendingBaselineCarbonQuota_kg)
        baselineCarbonQuota_kg = pendingBaselineCarbonQuota_kg;
        fprintf('Stored Scenario-1 fixed carbon quota baseline for later scenarios: %.4f kgCO2.\n', ...
            sum(baselineCarbonQuota_kg(:)));
    end

end

summaryTable = struct2table(summaryRows);
metricTable = struct2table(metricRows);
summaryTable = normalize_csv_text_columns(summaryTable);
metricTable = normalize_csv_text_columns(metricTable);
allResults = strip_yalmip_objects(allResults);
allData = make_clean_saved_data(allData);

try
    write_utf8_bom_table(summaryTable, 'comparison_summary.csv');
    write_utf8_bom_table(metricTable, 'comparison_metric_table.csv');
catch ME
    warning('Writing comparison CSV summary tables failed: %s', ME.message);
end

save('comparison_results.mat', 'allResults', 'allData', 'summaryTable', 'metricTable', 'scenarios', ...
    'admmRhoPQ', 'admmRhoC', 'admmMaxIter', 'admmTolPri', 'admmTolDual', '-v7.3');
write_results_loader('comparison_results.m');

try
    export_plot_data_csv(allResults, allData, 'comparison_plot_data_csv');
catch ME
    warning('Exporting comparison plotting CSV data failed: %s', ME.message);
end

disp(' ');
disp('===== Four-Scenario Energy-Carbon Summary =====');
disp(summaryTable);
disp(' ');
disp('===== Four-Scenario Energy-Carbon Metrics =====');
disp(metricTable);

reset_optimizer_caches();
try
    yalmip('clear');
catch
end

%% ============================ Local functions ============================

function scenarios = define_comparison_scenarios()
scenarios = struct( ...
    'name', {'S1_NoCarbon_NoDR', 'S2_Normal_NoCarbon_DR', ...
             'S3_Carbon_NoDR', 'S4__Carbon_DR'}, ...
    'name_cn', {'Scenario 1 - No carbon trading - No demand response', ...
                'Scenario 2 - No carbon trading - With demand response', ...
                'Scenario 3 - With carbon trading - No demand response', ...
                'Scenario 4 - With carbon trading - With demand response'}, ...
    'pvScale', {5.5, 5.5, 5.5, 5.5}, ...
    'windScale', {5.5, 5.5, 5.5, 5.5}, ...
    'enableStorage', {1, 1, 1, 1}, ...
    'enableDemandResponse', {0, 1, 0, 1}, ...
    'enableCarbonQuota', {1, 1, 1, 1}, ...
    'enableCommunityCarbonTrading', {0, 0, 1, 1}, ...
    'allowCarbonMarketSell', {0, 0, 1, 1});

end

function data = prepare_comparison_data(baseData, sc, admmMaxIter, admmTolPri, admmTolDual)
data = baseData;
data = apply_scenario(data, sc);
data.scenarioName = matlab.lang.makeValidName(sc.name);
data.scenarioNameCN = sc.name_cn;
data.comparisonScenario = sc.name;
data.comparisonScenarioCN = sc.name_cn;
data.pvScaleFinal = sc.pvScale;
data.windScaleFinal = sc.windScale;
data.storageEnabled = logical(sc.enableStorage);
data.demandResponseEnabled = logical(sc.enableDemandResponse);
data.admmMaxIter = admmMaxIter;
data.admmTolPri = admmTolPri;
data.admmTolDual = admmTolDual;
data.carbonQuotaMode = 'baseline-scenario';
carbonOpts = struct( ...
    'enableCarbonQuota', sc.enableCarbonQuota, ...
    'enableCommunityCarbonTrading', sc.enableCommunityCarbonTrading, ...
    'allowCarbonMarketSell', sc.allowCarbonMarketSell);
data = configure_carbon_trading(data, carbonOpts);
if ~data.storageEnabled
    data = disable_storage(data);
end
if ~data.demandResponseEnabled
    data = disable_demand_response(data);
end
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

function data = disable_demand_response(data)
z = zeros(data.N, data.T);
data.PloadFixed = data.Pload;
data.PdrShiftBase = z;
data.PdrShiftMax = z;
data.PdrCutEmax = z;
data.HdrCutMax = z;
data.H2drCutMax = z;
end

function row = make_summary_row(data, method, res, status, ~)
row = struct();
row.Scenario = string(data.comparisonScenario);
row.ScenarioCN = string(data.comparisonScenarioCN);
row.Method = string(method);
row.Status = string(status);
if ~isempty(res) && ~strcmp(status, 'Failed')
    row.TotalObjective_Yuan = get_objective(res);
    row.Iterations = get_iterations(res);
    row.CarbonTradingCost_Yuan = get_scalar_field(res, 'CarbonTradingCost_Yuan', get_part(res, 'carbonTradingCost'));
    row.ADMMPrimalResidual = get_scalar_field(res, 'finalPrimalResidual', NaN);
    row.ADMMDualResidual = get_scalar_field(res, 'finalDualResidual', NaN);
    row.MaxConsensusP_MW = get_scalar_field(res, 'maxConsensusP', NaN);
    row.MaxConsensusQ_MVAr = get_scalar_field(res, 'maxConsensusQ', NaN);
    row.MaxConsensusCarbon_kg = get_scalar_field(res, 'maxConsensusCarbon', NaN);
else
    row.TotalObjective_Yuan = NaN;
    row.Iterations = NaN;
    row.CarbonTradingCost_Yuan = NaN;
    row.ADMMPrimalResidual = NaN;
    row.ADMMDualResidual = NaN;
    row.MaxConsensusP_MW = NaN;
    row.MaxConsensusQ_MVAr = NaN;
    row.MaxConsensusCarbon_kg = NaN;
end
end

function row = make_metric_row(data, method, res, status, ~)
row = struct();
row.Scenario = string(data.comparisonScenario);
row.ScenarioCN = string(data.comparisonScenarioCN);
row.Method = string(method);
row.Status = string(status);

if isempty(res) || strcmp(status, 'Failed')
    row.TotalObjective_Yuan = NaN;
    row.GridEnergy_MWh = NaN;
    row.GasEnergy_MWhth = NaN;
    row.CarbonEmission_kg = NaN;
    row.CarbonQuota_kg = NaN;
    row.CarbonSurplusBeforeTrade_kg = NaN;
    row.CarbonBuyMarket_kg = NaN;
    row.CarbonSellMarket_kg = NaN;
    row.CarbonTradeAbs_kg = NaN;
    row.CarbonUnusedAllowance_kg = NaN;
    row.RenewableAvailable_MWh = NaN;
    row.RenewableUse_MWh = NaN;
    row.RenewableCurtailment_MWh = NaN;
    row.RenewableUseRate_percent = NaN;
    row.AvgMinimumVoltage_pu = NaN;
    row.GridVoltageDeviation_pu = NaN;
    return;
end

dt = data.dt;
Pgrid = get_res_field(res, 'Pgrid');
Fgas = get_res_field(res, 'Fgas');
PpvUse = get_res_field(res, 'PpvUse');
PpvCurt = get_res_field(res, 'PpvCurt');
PwindUse = get_res_field(res, 'PwindUse');
PwindCurt = get_res_field(res, 'PwindCurt');
V = get_res_field(res, 'V');
carbon = carbon_accounting(data, get_res_field(res, 'Pgrid'), get_res_field(res, 'Pchp'), get_res_field(res, 'Hchp'), get_res_field(res, 'Fgas'));

renAvail = (sum(data.Ppv(:)) + sum(data.Pwind(:))) * dt;
renUse = (sum(PpvUse(:)) + sum(PwindUse(:))) * dt;
renCurt = (sum(PpvCurt(:)) + sum(PwindCurt(:))) * dt;

row.TotalObjective_Yuan = get_objective(res);
row.GridEnergy_MWh = sum(Pgrid(:))*dt;
row.GasEnergy_MWhth = sum(Fgas(:))*dt;
row.CarbonEmission_kg = sum(carbon.emission(:));
row.CarbonQuota_kg = sum(carbon.quota(:));
row.CarbonSurplusBeforeTrade_kg = sum(carbon.quota(:) - carbon.emission(:));
row.CarbonBuyMarket_kg = sum(get_res_field(res, 'CarbonBuyMarket_kg'), 'all');
row.CarbonSellMarket_kg = sum(get_res_field(res, 'CarbonSellMarket_kg'), 'all');
row.CarbonTradeAbs_kg = sum(abs(get_res_field(res, 'CarbonTradeWithCommunities_kg')), 'all')/2;
row.CarbonUnusedAllowance_kg = sum(get_res_field(res, 'CarbonUnusedAllowance_kg'), 'all');
row.RenewableAvailable_MWh = renAvail;
row.RenewableUse_MWh = renUse;
row.RenewableCurtailment_MWh = renCurt;
row.RenewableUseRate_percent = safe_pct(renUse, renAvail);
if isempty(V)
    row.AvgMinimumVoltage_pu = NaN;
    row.GridVoltageDeviation_pu = NaN;
else
    voltagePu = sqrt(max(0, V));
    row.AvgMinimumVoltage_pu = mean(min(voltagePu, [], 1));
    row.GridVoltageDeviation_pu = mean(abs(voltagePu(:) - 1.0));
end
end

function out = make_failed_result(methodName, errMsg)
out = struct('method', methodName, 'Status', 'Failed', 'solveStatus', 'Failed', 'errorMessage', errMsg);
end

function x = get_res_field(res, name)
if isstruct(res) && isfield(res, name) && ~isempty(res.(name))
    x = res.(name);
else
    x = 0;
end
end

function val = get_objective(res)
if isfield(res, 'TotalObjective_Yuan')
    val = res.TotalObjective_Yuan;
elseif isfield(res, 'obj')
    val = res.obj;
elseif isfield(res, 'recoveredGlobalObjective')
    val = res.recoveredGlobalObjective;
else
    val = NaN;
end
end

function val = get_iterations(res)
if isfield(res, 'Iterations')
    val = res.Iterations;
elseif isfield(res, 'hist_pri')
    val = numel(res.hist_pri);
else
    val = NaN;
end
end

function val = get_scalar_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end

function val = get_part(res, name)
val = 0;
if isfield(res, 'parts') && isfield(res.parts, name)
    val = res.parts.(name);
end
end

function y = safe_pct(numerator, denominator)
if abs(denominator) < 1e-9
    y = NaN;
else
    y = numerator / denominator * 100;
end
end

function write_results_loader(fileName)
fid = fopen(fileName, 'w');
if fid < 0
    warning('Unable to write %s.', fileName);
    return;
end
cleanup = onCleanup(@() fclose(fid));
fprintf(fid, '%% Auto-generated by main_run_comparison.m\n');
fprintf(fid, '%% Run this file to load the four-scenario comparison results.\n\n');
fprintf(fid, 'load(''comparison_results.mat'', ''allResults'', ''allData'', ''summaryTable'', ''metricTable'', ''scenarios'', ''admmRhoPQ'', ''admmRhoC'', ''admmMaxIter'', ''admmTolPri'', ''admmTolDual'');\n');
fprintf(fid, 'disp(''===== Four-Scenario Energy-Carbon Summary ====='');\n');
fprintf(fid, 'disp(summaryTable);\n');
fprintf(fid, 'disp(''===== Four-Scenario Energy-Carbon Metrics ====='');\n');
fprintf(fid, 'disp(metricTable);\n');
end

function tbl = normalize_csv_text_columns(tbl)
textVars = intersect({'Scenario','ScenarioCN','Method','Status'}, tbl.Properties.VariableNames, 'stable');
for k = 1:numel(textVars)
    name = textVars{k};
    if isstring(tbl.(name))
        tbl.(name) = cellstr(tbl.(name));
    end
end
end

function write_utf8_bom_table(tbl, fileName)
tmpName = [tempname, '.csv'];
writetable(tbl, tmpName, 'Encoding', 'UTF-8');
bytes = fileread_bytes(tmpName);
fid = fopen(fileName, 'w');
if fid < 0
    error('Unable to open %s for writing.', fileName);
end
cleanup = onCleanup(@() fclose(fid));
fwrite(fid, uint8([239 187 191]), 'uint8');
fwrite(fid, bytes, 'uint8');
delete(tmpName);
end

function bytes = fileread_bytes(fileName)
fid = fopen(fileName, 'r');
if fid < 0
    error('Unable to open %s for reading.', fileName);
end
cleanup = onCleanup(@() fclose(fid));
bytes = fread(fid, Inf, '*uint8');
end

function out = make_clean_saved_data(allData)
names = fieldnames(allData);
out = struct();
keep = {'scenarioName','scenarioNameCN','comparisonScenario','comparisonScenarioCN', ...
    'pvScaleFinal','windScaleFinal','storageEnabled','demandResponseEnabled','enableCarbonTrading', ...
    'admmRhoPQ','admmRhoC','admmMaxIter','admmTolPri','admmTolDual', ...
    'enableCarbonQuota','enableCommunityCarbonTrading','allowCarbonMarketSell','carbonQuotaMode','fixedCarbonQuota_kg', ...
    'N','T','dt','Pload','PloadFixed','PdrShiftBase','PdrShiftMax','PdrCutEmax', ...
    'Hload','HdrCutMax','H2load','H2drCutMax','Ppv','Pwind','PcompFixed','alphaCompH2','PcompMax','ce','PchpRated','etaE_chp','etaH_chp', ...
    'minChpHeatShare', ...
    'PchMax','PdisMax','Emax','SOC0_e','HchMax','HdisMax','EthMax','SOC0_th', ...
    'H2chMax','H2disMax','EH2Max','SOC0_h2','zetaE','zetaH','chiE','chiH','ceh', ...
    'RampUpEb','RampDnEb','cRampEb','RampUpElec','RampDnElec','cRampElec', ...
    'RampUpFc','RampDnFc','cRampFc','RampUpComp','RampDnComp','cRampComp', ...
    'quotaGridRatio','quotaGasRatio','carbonBuyPrice','carbonSellPrice', ...
    'lambdaQpv','lambdaQwind','lambdaQes','QpvMax','QwindMax','QesMax','QinjMin','QinjMax'};
for i = 1:numel(names)
    data = allData.(names{i});
    s = struct();
    for k = 1:numel(keep)
        if isfield(data, keep{k})
            s.(keep{k}) = data.(keep{k});
        end
    end
    out.(names{i}) = s;
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
