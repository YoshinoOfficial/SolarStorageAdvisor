function export_plot_data_csv(allResults, allData, outDir)
%EXPORT_PLOT_DATA_CSV Export plotting inputs/results to CSV files.
% The exported bundle is intentionally broad: aggregate hourly profiles,
% per-community hourly profiles, and convergence histories.

if nargin < 3 || isempty(outDir)
    outDir = 'plot_data_csv';
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

if isempty(allResults) || ~isstruct(allResults)
    return;
end
if nargin < 2 || isempty(allData) || ~isstruct(allData)
    allData = struct();
end

scenNames = fieldnames(allResults);
manifestRows = struct([]);

for s = 1:numel(scenNames)
    scenName = scenNames{s};
    R = allResults.(scenName);
    if isstruct(allData) && isfield(allData, scenName)
        D = allData.(scenName);
    else
        D = struct();
    end
    if ~isstruct(R)
        continue;
    end

    methodNames = fieldnames(R);
    for m = 1:numel(methodNames)
        methodName = methodNames{m};
        sol = R.(methodName);
        if ~isstruct(sol) || is_failed_solution(sol)
            continue;
        end

        [N, T] = infer_export_size(D, sol);
        if N <= 0 || T <= 0
            continue;
        end

        baseName = sprintf('%s_%s', safe_file_name(scenName), safe_file_name(methodName));
        aggregateFile = fullfile(outDir, sprintf('%s_hourly_aggregate.csv', baseName));
        communityFile = fullfile(outDir, sprintf('%s_community_hourly.csv', baseName));

        aggregateTable = build_hourly_aggregate_table(scenName, methodName, D, sol, N, T);
        communityTable = build_community_hourly_table(scenName, methodName, D, sol, N, T);
        scalarTable = build_solution_scalar_table(scenName, methodName, sol);
        scalarFile = fullfile(outDir, sprintf('%s_solution_scalars.csv', baseName));
        writetable(aggregateTable, aggregateFile);
        writetable(communityTable, communityFile);
        writetable(scalarTable, scalarFile);

        manifestRows = [manifestRows; make_manifest_row(scenName, methodName, 'hourly_aggregate', aggregateFile)]; %#ok<AGROW>
        manifestRows = [manifestRows; make_manifest_row(scenName, methodName, 'community_hourly', communityFile)]; %#ok<AGROW>
        manifestRows = [manifestRows; make_manifest_row(scenName, methodName, 'solution_scalars', scalarFile)]; %#ok<AGROW>

        convergenceTable = build_convergence_table(scenName, methodName, sol);
        if ~isempty(convergenceTable)
            convergenceFile = fullfile(outDir, sprintf('%s_convergence.csv', baseName));
            writetable(convergenceTable, convergenceFile);
            manifestRows = [manifestRows; make_manifest_row(scenName, methodName, 'convergence', convergenceFile)]; %#ok<AGROW>
        end
    end
end

if ~isempty(manifestRows)
    writetable(struct2table(manifestRows), fullfile(outDir, 'plot_data_manifest.csv'));
end
end

function TBL = build_hourly_aggregate_table(scenName, methodName, D, sol, N, T)
dataFields = {'Pload','Hload','H2load','Ppv','Pwind','PcompFixed'};
sumSolFields = {'Pgrid','Pch','Pdis','PpvUse','PpvCurt','PwindUse','PwindCurt', ...
    'Pchp','Hchp','Fgas','Peb','Heb','Pelec','H2prod','H2cons_fc','Pfc','Pcomp', ...
    'Hch','Hdis','H2ch','H2dis','H2short','Hdump','Qpv','Qes','QinjLocal','PinjLocal', ...
    'CarbonEmission_kg','CarbonQuota_kg','CarbonBuyMarket_kg','CarbonSellMarket_kg', ...
    'CarbonTradeWithCommunities_kg','CarbonUnusedAllowance_kg'};
meanSolFields = {'SOC_e','SOC_th','SOC_h2','V'};

rows = struct([]);
for t = 1:T
    row = struct();
    row.Scenario = string(scenName);
    row.Method = string(methodName);
    row.TimeSlot = t;

    for k = 1:numel(dataFields)
        name = dataFields{k};
        M = get_matrix(D, name, N, T);
        row.(sprintf('DataSum_%s', name)) = sum(M(:,t));
    end

    for k = 1:numel(sumSolFields)
        name = sumSolFields{k};
        M = get_matrix(sol, name, N, T);
        row.(sprintf('Sum_%s', name)) = sum(M(:,t));
    end

    for k = 1:numel(meanSolFields)
        name = meanSolFields{k};
        M = get_matrix(sol, name, N, T);
        row.(sprintf('Mean_%s', name)) = mean(M(:,t));
    end

    row.TotalRenewableAvailable_MW = row.DataSum_Ppv + row.DataSum_Pwind;
    row.TotalRenewableUsed_MW = row.Sum_PpvUse + row.Sum_PwindUse;
    row.TotalRenewableCurtailment_MW = row.Sum_PpvCurt + row.Sum_PwindCurt;
    rows = append_struct_row(rows, row);
end
TBL = struct2table(rows);
end

function TBL = build_community_hourly_table(scenName, methodName, D, sol, N, T)
dataFields = {'Pload','Hload','H2load','Ppv','Pwind','PcompFixed'};
solFields = {'Pgrid','Pch','Pdis','SOC_e','PpvUse','PpvCurt','PwindUse','PwindCurt', ...
    'Pchp','Hchp','Fgas','Peb','Heb','Pelec','H2prod','H2cons_fc','Pfc','Pcomp', ...
    'Hch','Hdis','SOC_th','H2ch','H2dis','SOC_h2','H2short','Hdump', ...
    'Qpv','Qes','QinjLocal','PinjLocal','V', ...
    'CarbonEmission_kg','CarbonQuota_kg','CarbonBuyMarket_kg','CarbonSellMarket_kg', ...
    'CarbonTradeWithCommunities_kg','CarbonUnusedAllowance_kg'};
capFields = {'Emax','SOC0_e','EthMax','SOC0_th','EH2Max','SOC0_h2'};

rows = struct([]);
idx = 0;
for i = 1:N
    for t = 1:T
        idx = idx + 1;
        row = struct();
        row.Scenario = string(scenName);
        row.Method = string(methodName);
        row.Community = i;
        row.TimeSlot = t;

        for k = 1:numel(dataFields)
            name = dataFields{k};
            M = get_matrix(D, name, N, T);
            row.(sprintf('Data_%s', name)) = M(i,t);
        end

        for k = 1:numel(solFields)
            name = solFields{k};
            M = get_matrix(sol, name, N, T);
            row.(name) = M(i,t);
        end

        for k = 1:numel(capFields)
            name = capFields{k};
            row.(sprintf('Data_%s', name)) = get_vector_value(D, name, i);
        end

        rows = append_struct_row(rows, row);
    end
end
TBL = struct2table(rows);
end

function TBL = build_convergence_table(scenName, methodName, sol)
histPri = get_vector(sol, 'hist_pri');
histDual = get_vector(sol, 'hist_dual');
n = max(numel(histPri), numel(histDual));
if n == 0
    TBL = table();
    return;
end

rows = struct([]);
for k = 1:n
    row = struct();
    row.Scenario = string(scenName);
    row.Method = string(methodName);
    row.Iteration = k;
    row.PrimalResidual = get_index_or_nan(histPri, k);
    row.DualResidual = get_index_or_nan(histDual, k);
    rows = append_struct_row(rows, row);
end
TBL = struct2table(rows);
end

function TBL = build_solution_scalar_table(scenName, methodName, sol)
row = struct();
row.Scenario = string(scenName);
row.Method = string(methodName);
row.Objective_Yuan = first_scalar(sol, {'TotalObjective_Yuan','recoveredGlobalObjective','obj'}, NaN);
row.LocalObjective_Yuan = first_scalar(sol, {'finalLocalCost'}, NaN);
row.Iterations = get_iteration_count(sol);
row.FinalPrimalResidual = first_scalar(sol, {'finalPrimalResidual'}, NaN);
row.FinalDualResidual = first_scalar(sol, {'finalDualResidual'}, NaN);
row.MaxConsensusP_MW = first_scalar(sol, {'maxConsensusP'}, NaN);
row.MaxConsensusQ_MVAr = first_scalar(sol, {'maxConsensusQ'}, NaN);
row.MaxConsensusCarbon_kg = first_scalar(sol, {'maxConsensusCarbon'}, NaN);
row.TotalPVCurt_MWh = first_scalar(sol, {'totalPVCurt'}, NaN);
row.TotalWindCurt_MWh = first_scalar(sol, {'totalWindCurt'}, NaN);
row.TotalH2Shortage_kg = first_scalar(sol, {'totalH2short'}, NaN);

partNames = {'gridCost','carbonTradingCost','gasCost','gasCarbonCost','pvCurtCost','windCurtCost','h2ShortCost','qSupportCost'};
for k = 1:numel(partNames)
    row.(sprintf('Part_%s', partNames{k})) = get_part_scalar(sol, partNames{k});
end
TBL = struct2table(row);
end

function row = make_manifest_row(scenName, methodName, dataType, fileName)
row = struct();
row.Scenario = string(scenName);
row.Method = string(methodName);
row.DataType = string(dataType);
row.FileName = string(fileName);
end

function rows = append_struct_row(rows, row)
if isempty(rows)
    rows = row;
else
    rows(end+1, 1) = row;
end
end

function [N, T] = infer_export_size(D, sol)
N = get_scalar_int(D, 'N', 0);
T = get_scalar_int(D, 'T', 0);
fields = {'Pload','Hload','H2load','Ppv','Pwind','Pgrid','PpvUse','PwindUse','SOC_e','SOC_th','SOC_h2','Heb','Hchp'};
for k = 1:numel(fields)
    if N > 0 && T > 0
        break;
    end
    [n1, t1] = field_size(D, fields{k});
    if n1 == 0 || t1 == 0
        [n1, t1] = field_size(sol, fields{k});
    end
    if N <= 0
        N = n1;
    end
    if T <= 0
        T = t1;
    end
end
end

function M = get_matrix(s, name, N, T)
M = zeros(N, T);
if ~isstruct(s) || ~isfield(s, name) || isempty(s.(name)) || ~isnumeric(s.(name))
    return;
end
x = double(s.(name));
if isscalar(x)
    M(:,:) = x;
elseif ismatrix(x)
    [r, c] = size(x);
    if r == N && c == T
        M = x;
    elseif r == T && c == N
        M = x.';
    elseif r == 1 && c == T
        M = repmat(x, N, 1);
    elseif r == N && c == 1
        M = repmat(x, 1, T);
    elseif numel(x) == N*T
        M = reshape(x, N, T);
    end
end
end

function v = get_vector(s, name)
if isstruct(s) && isfield(s, name) && isnumeric(s.(name))
    v = double(s.(name)(:));
else
    v = [];
end
end

function val = get_vector_value(s, name, idx)
val = NaN;
v = get_vector(s, name);
if isempty(v)
    return;
end
if numel(v) == 1
    val = v;
elseif idx <= numel(v)
    val = v(idx);
end
end

function val = get_index_or_nan(v, idx)
if idx <= numel(v)
    val = v(idx);
else
    val = NaN;
end
end

function val = first_scalar(s, names, defaultValue)
val = defaultValue;
if ~isstruct(s)
    return;
end
for k = 1:numel(names)
    name = names{k};
    if isfield(s, name) && isnumeric(s.(name)) && isscalar(s.(name))
        val = double(s.(name));
        return;
    end
end
end

function n = get_iteration_count(sol)
n = first_scalar(sol, {'Iterations'}, NaN);
if ~isnan(n)
    return;
end
histPri = get_vector(sol, 'hist_pri');
histDual = get_vector(sol, 'hist_dual');
n = max(numel(histPri), numel(histDual));
if n == 0
    n = NaN;
end
end

function val = get_part_scalar(sol, name)
val = NaN;
if isstruct(sol) && isfield(sol, 'parts') && isstruct(sol.parts) && ...
        isfield(sol.parts, name) && isnumeric(sol.parts.(name)) && isscalar(sol.parts.(name))
    val = double(sol.parts.(name));
end
end

function tf = is_failed_solution(sol)
tf = false;
statusFields = {'Status','solveStatus'};
for k = 1:numel(statusFields)
    name = statusFields{k};
    if isfield(sol, name)
        statusText = lower(string(sol.(name)));
        if contains(statusText, "fail")
            tf = true;
            return;
        end
    end
end
end

function name = safe_file_name(name)
name = char(string(name));
name = regexprep(name, '[^\w\-]+', '_');
name = regexprep(name, '_+', '_');
name = regexprep(name, '^_|_$', '');
if isempty(name)
    name = 'unnamed';
end
end

function n = get_scalar_int(s, name, defaultValue)
n = defaultValue;
if isstruct(s) && isfield(s, name) && isnumeric(s.(name)) && isscalar(s.(name))
    n = round(double(s.(name)));
end
end

function [N, T] = field_size(s, name)
N = 0;
T = 0;
if ~isstruct(s) || ~isfield(s, name) || isempty(s.(name)) || ~isnumeric(s.(name))
    return;
end
x = s.(name);
if ismatrix(x)
    [N, T] = size(x);
end
end
