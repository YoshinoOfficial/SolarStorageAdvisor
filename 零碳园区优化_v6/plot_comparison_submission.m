function plot_comparison_submission(matFile, outDir)
%PLOT_RESULTS_APPLIED_ENERGY_SUBMISSION
% Submission plotting script for zero-carbon campus multi-energy model

    scriptPath = mfilename('fullpath');
    scriptDir = fileparts(scriptPath);
    if isempty(scriptDir)
        scriptDir = pwd;
    end

    if nargin < 1 || isempty(matFile)
        matFile = fullfile(scriptDir, 'comparison_results.mat');
    elseif ~is_absolute_path(matFile) && exist(fullfile(scriptDir, matFile), 'file')
        matFile = fullfile(scriptDir, matFile);
    end
    if nargin < 2 || isempty(outDir)
        outDir = fullfile(scriptDir, 'comparison_submission');
    elseif ~is_absolute_path(outDir)
        outDir = fullfile(scriptDir, outDir);
    end
    ensure_directory_exists(outDir);

    S = load(matFile);
    if ~isfield(S, 'allResults')
        error('Result file does not contain allResults');
    end
    allResults = S.allResults;
    if isfield(S, 'allData')
        allData = S.allData;
    else
        allData = struct();
    end
    scenNames = fieldnames(allResults);
    nScen = numel(scenNames);

    set_plot_defaults();

    draw_objective_comparison(allResults, scenNames, outDir);
    draw_grid_purchase_combined(allResults, scenNames, outDir);
    for k = 1:nScen
        R = allResults.(scenNames{k});
        if isstruct(allData) && isfield(allData, scenNames{k})
            D = allData.(scenNames{k});
        else
            D = struct();
        end
        % draw_cost_breakdown(R, scenNames{k}, outDir);
        % draw_convergence(R, scenNames{k}, outDir);
        draw_renewable_profiles(R, scenNames{k}, outDir, k);
        draw_soc_profiles(R, D, scenNames{k}, outDir);
        draw_chp_profiles(R, scenNames{k}, outDir);
        draw_energy_balance(R, scenNames{k}, outDir);
        draw_hydrogen_profiles(R, scenNames{k}, outDir);
        % draw_community_load_profiles(D, scenNames{k}, outDir);
    end

    fprintf('Done. Figures saved to: %s\n', outDir);
end

%% ========================= Figure functions =========================

function draw_objective_comparison(allResults, scenNames, outDir)
    nScen = numel(scenNames);
    objMat = nan(nScen,2);
    for k = 1:nScen
        R = allResults.(scenNames{k});
        if isfield(R, 'centralized') && is_solution_ok(R.centralized)
            objMat(k,1) = get_solution_objective(R.centralized);
        end
        if isfield(R, 'admm') && is_solution_ok(R.admm)
            objMat(k,2) = get_solution_objective(R.admm);
        end
    end
    methodNames = {'Centralized', 'ADMM'};
    validCols = any(~isnan(objMat), 1);
    objMat = objMat(:, validCols);
    methodNames = methodNames(validCols);
    if isempty(objMat) || ~any(~isnan(objMat(:))), return; end

    fig = create_figure([100 100 960 560]);
    ax = axes(fig);
    hb = bar(ax, objMat, 'grouped', 'LineWidth', 1.0);
    colors = [0.00 0.45 0.74; 0.85 0.33 0.10];
    for i = 1:numel(hb)
        hb(i).FaceColor = colors(i,:);
    end
    grid(ax,'on');
    ax.XTick=1:nScen; ax.XTickLabel=prettify_scenario_names(scenNames);
    ax.XTickLabelRotation=12; ylabel('Objective value (Yuan)');
    title('Fig. 1. Objective value comparison');
    legend(ax, methodNames, 'Location', 'best');
    finalize_axes(ax);
    export_dual(fig, outDir, 'Fig1_Objective_Comparison');
end

function draw_cost_breakdown(R, scenName, outDir)
    costMat = []; methodNames = {};
    labels = {'Grid','Carbon','Gas','Gas Carbon','PV curt','Wind curt','H2 short','Q support'};
    if isfield(R,'admm') && is_solution_ok(R.admm), costMat=[costMat; get_parts_vec(R.admm)]; methodNames{end+1}='ADMM'; end
    if isempty(costMat), return; end
    fig = create_figure();
    hb = bar(1:numel(methodNames), costMat, 'stacked', 'LineWidth',0.8); grid on;
    ax = gca; ax.XTick=1:numel(methodNames); ax.XTickLabel=methodNames;
    ylabel('Cost (Yuan)');
    title(sprintf('Fig. 2. Cost breakdown in %s', prettify_one_name(scenName)));
    legend(hb, labels, 'Location','eastoutside'); finalize_axes(ax);
    safeSceneName = strrep(prettify_one_name(scenName),' ','_');
    export_dual(fig, outDir, sprintf('Fig2_Cost_Breakdown_%s', safeSceneName));
end

function draw_convergence(R, scenName, outDir)
    if ~isfield(R,'admm') || ~is_solution_ok(R.admm) || ~isfield(R.admm,'hist_pri'), return; end
    fig = create_figure(); hold on; grid on;
    plot(log10(R.admm.hist_pri),'-','LineWidth',1.8,'DisplayName','ADMM primal');
    plot(log10(R.admm.hist_dual),'--','LineWidth',1.8,'DisplayName','ADMM dual');
    xlabel('Iteration'); ylabel('Residual');
    title(sprintf('Fig. 3. Convergence in %s', prettify_one_name(scenName)));
    legend('Location','southwest');
    ax = gca; ax.YTick=[-4,-2,0,2]; ax.YTickLabel={'10^{-4}','10^{-2}','10^{0}','10^{2}'};
    ax.XLim=[0 ceil(max(numel(R.admm.hist_pri),numel(R.admm.hist_dual))*1.05)];
    finalize_axes(ax);
    safeSceneName = strrep(prettify_one_name(scenName),' ','_');
    export_dual(fig, outDir, sprintf('Fig3_Convergence_%s', safeSceneName));
end

function draw_grid_purchase_combined(allResults, scenNames, outDir)
    hasAny = false;
    fig = create_figure([100 100 980 520]);
    ax = axes(fig);
    hold(ax,'on');
    grid(ax,'on');

    colors = [0.00 0.45 0.74;
              0.85 0.33 0.10;
              0.47 0.67 0.19;
              0.49 0.18 0.56;
              0.30 0.75 0.93;
              0.64 0.08 0.18];
    markers = {'o','s','^','d','v','p'};
    maxT = 0;

    for k = 1:numel(scenNames)
        sol = get_admm_solution(allResults.(scenNames{k}));
        if isempty(sol) || ~has_numeric_field(sol,'Pgrid')
            fprintf('Skip grid purchase curve for %s: no solved Pgrid field.\n', scenNames{k});
            continue;
        end
        y = sum(sol.Pgrid, 1);
        T = numel(y);
        maxT = max(maxT, T);
        [tPlot, yPlot, markerIdx] = smooth_curve_for_display(1:T, y);
        plot(ax, tPlot, yPlot, '-', ...
            'Color', colors(mod(k-1,size(colors,1))+1,:), ...
            'LineWidth', 2.0, ...
            'Marker', markers{mod(k-1,numel(markers))+1}, ...
            'MarkerIndices', markerIdx, ...
            'MarkerSize', 5.0, ...
            'MarkerFaceColor', 'w', ...
            'MarkerEdgeColor', colors(mod(k-1,size(colors,1))+1,:), ...
            'DisplayName', sprintf('case%d', k));
        hasAny = true;
    end

    if ~hasAny
        close(fig);
        fprintf('Skip combined grid purchase plot: no solved Pgrid fields.\n');
        return;
    end

    if maxT > 0
        xlim(ax, [1 maxT]);
        if maxT <= 24
            xticks(ax, 1:maxT);
        else
            xticks(ax, 1:4:maxT);
        end
    end
    xlabel(ax, 'Time slot');
    ylabel(ax, 'Grid purchase (MW)');
    title(ax, 'Fig. 4. Grid purchase comparison across scenarios');
    legend(ax, 'Location','northoutside', 'Orientation','horizontal', ...
        'NumColumns', min(numel(scenNames), 4), 'Box','on');
    finalize_axes(ax);
    export_dual(fig, outDir, 'Fig4_Grid_Purchase_Comparison_ADMM');
end

function draw_renewable_profiles(R, scenName, outDir, caseIdx)
    if nargin < 4 || isempty(caseIdx)
        caseIdx = 1;
    end
    sol = get_admm_solution(R);
    if isempty(sol)
        return;
    end

    hasPV = has_numeric_field(sol,'PpvUse');
    hasWind = has_numeric_field(sol,'PwindUse');
    hasPVCurt = has_numeric_field(sol,'PpvCurt');
    hasWindCurt = has_numeric_field(sol,'PwindCurt');
    if ~hasPV && ~hasWind && ~hasPVCurt && ~hasWindCurt
        return;
    end

    [N, T] = infer_matrix_size(sol, struct(), {'PpvUse','PwindUse','PpvCurt','PwindCurt'}, '');
    if N == 0 || T == 0
        return;
    end

    pvUse = sum(get_matrix_or_zeros(sol, 'PpvUse', N, T), 1);
    windUse = sum(get_matrix_or_zeros(sol, 'PwindUse', N, T), 1);
    renewableCurt = sum(get_matrix_or_zeros(sol, 'PpvCurt', N, T) + ...
        get_matrix_or_zeros(sol, 'PwindCurt', N, T), 1);
    t = 1:T;

    fig = create_figure([100 100 920 500]);
    ax = axes(fig);
    hold(ax,'on');
    grid(ax,'on');

    if hasPV
        plot(ax, t, pvUse, '-o', 'Color', [0.85 0.33 0.10], ...
            'LineWidth', 1.9, 'MarkerSize', 4.8, ...
            'MarkerFaceColor', 'w', 'DisplayName', 'PV used');
    end
    if hasWind
        plot(ax, t, windUse, '-s', 'Color', [0.00 0.45 0.74], ...
            'LineWidth', 1.9, 'MarkerSize', 4.8, ...
            'MarkerFaceColor', 'w', 'DisplayName', 'Wind used');
    end
    if hasPVCurt || hasWindCurt
        plot(ax, t, renewableCurt, '-^', 'Color', [0.49 0.18 0.56], ...
            'LineWidth', 1.9, 'MarkerSize', 4.8, ...
            'MarkerFaceColor', 'w', 'DisplayName', 'Curtailment');
    end

    xlim(ax, [1 T]);
    if T <= 24
        xticks(ax, 1:T);
    else
        xticks(ax, 1:4:T);
    end
    xlabel(ax, 'Time slot');
    ylabel(ax, 'Power (MW)');
    title(ax, sprintf('Renewable utilization and curtailment in case%d', caseIdx));
    legend(ax, 'Location','northoutside', 'Orientation','horizontal', ...
        'NumColumns', 3, 'Box','on');
    finalize_axes(ax);

    safeSceneName = strrep(prettify_one_name(scenName),' ','_');
    export_dual(fig, outDir, sprintf('Fig5_Renewable_Profiles_%s', safeSceneName));
end

function draw_soc_profiles(R, D, scenName, outDir)
    sol = get_admm_solution(R);
    if isempty(sol), return; end
    safeSceneName = strrep(prettify_one_name(scenName),' ','_');

    % Electric storage: charge/discharge power bars with SOC curve.
    if has_numeric_field(sol,'SOC_e') && has_numeric_field(sol,'Pch') && has_numeric_field(sol,'Pdis')
        [powerStackE, labelsE, colorsE] = build_electric_power_stack(sol, D);
        fig = draw_storage_power_soc_profile(powerStackE, labelsE, colorsE, sol.SOC_e, ...
            get_field_or_empty(D,'Emax'), get_field_or_empty(D,'SOC0_e'), ...
            sprintf('Electric storage operation in %s', prettify_one_name(scenName)), ...
            'Electric power', 'Power (MW)', [0.49 0.18 0.56]);
        export_dual(fig, outDir, sprintf('Fig7a_SOC_Electric_%s', safeSceneName));
    end

    % Thermal storage: heat charge/discharge bars with SOC curve.
    if has_numeric_field(sol,'SOC_th') && has_numeric_field(sol,'Hch') && has_numeric_field(sol,'Hdis')
        [powerStackTh, labelsTh, colorsTh] = build_thermal_power_stack(sol, D);
        fig = draw_storage_power_soc_profile(powerStackTh, labelsTh, colorsTh, sol.SOC_th, ...
            get_field_or_empty(D,'EthMax'), get_field_or_empty(D,'SOC0_th'), ...
            sprintf('Thermal storage operation in %s', prettify_one_name(scenName)), ...
            'Thermal power', 'Thermal power (MW)', [0.64 0.08 0.18]);
        export_dual(fig, outDir, sprintf('Fig7b_SOC_Thermal_%s', safeSceneName));
    end
end

function [powerStack, labels, colors] = build_electric_power_stack(sol, D)
    [N, T] = infer_matrix_size(sol, D, {'Pgrid','PpvUse','PwindUse','Pchp','Pfc','Pdis','Pch','Peb','Pelec'}, 'Pload');
    powerStack = zeros(N, T, 0);
    labels = {};
    colors = zeros(0,3);

    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Pgrid', N, T), 'Grid purchase', [0.00 0.45 0.74]);

    renewable = get_matrix_or_zeros(sol, 'PpvUse', N, T) + get_matrix_or_zeros(sol, 'PwindUse', N, T);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, renewable, 'Renewable output', [0.47 0.67 0.19]);

    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Pchp', N, T), 'CHP electric', [0.93 0.69 0.13]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Pfc', N, T), 'Fuel cell', [0.30 0.75 0.93]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Pdis', N, T), 'Battery discharge', [0.49 0.18 0.56]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(D, 'Pload', N, T), 'Electric load', [0.55 0.55 0.55]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(sol, 'Pch', N, T), 'Battery charge', [0.85 0.33 0.10]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(sol, 'Peb', N, T), 'E-boiler power', [0.64 0.08 0.18]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(sol, 'Pelec', N, T), 'Electrolyzer power', [0.75 0.52 0.10]);
end

function [tPlot, yPlot, markerIdx] = smooth_curve_for_display(t, y)
    t = double(t(:).');
    y = double(y(:).');
    if numel(t) < 4 || numel(t) ~= numel(y)
        tPlot = t;
        yPlot = y;
        markerIdx = 1:numel(tPlot);
        return;
    end

    pointsPerInterval = 12;
    tPlot = linspace(t(1), t(end), (numel(t)-1)*pointsPerInterval + 1);
    yPlot = interp1(t, y, tPlot, 'pchip');
    yPlot = max(yPlot, 0);
    markerIdx = 1:pointsPerInterval:numel(tPlot);
end

function [powerStack, labels, colors] = build_thermal_power_stack(sol, D)
    [N, T] = infer_matrix_size(sol, D, {'Hchp','Heb','Hdis','Hch','Hdump'}, 'Hload');
    powerStack = zeros(N, T, 0);
    labels = {};
    colors = zeros(0,3);

    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Hchp', N, T), 'CHP heat', [0.93 0.69 0.13]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Heb', N, T), 'E-boiler heat', [0.00 0.45 0.74]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, get_matrix_or_zeros(sol, 'Hdis', N, T), 'Thermal discharge', [0.47 0.67 0.19]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(D, 'Hload', N, T), 'Thermal load', [0.55 0.55 0.55]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(sol, 'Hch', N, T), 'Thermal charge', [0.85 0.33 0.10]);
    [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, -get_matrix_or_zeros(sol, 'Hdump', N, T), 'Dumped heat', [0.64 0.08 0.18]);
end

function fig = draw_storage_power_soc_profile(powerStack, barLabels, barColors, socRaw, cap, soc0, ...
        titleText, tilePrefix, powerLabel, socColor)
    socPct = build_soc_series_percent(socRaw, cap, soc0);
    nComm = size(socRaw, 1);
    T = size(socRaw, 2);
    t = 1:T;
    tSoc = 0:T;

    fig = create_figure([100 60 1120 860]);
    tl = tiledlayout(fig, nComm, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    for i = 1:nComm
        ax = nexttile(tl);
        hold(ax, 'on');
        grid(ax, 'on');

        yyaxis(ax, 'left');
        plotStack = squeeze(powerStack(i,:,:));
        if size(plotStack, 1) ~= T
            plotStack = plotStack.';
        end
        barHandles = bar(ax, t, plotStack, 'stacked', 'BarWidth', 0.74, 'LineWidth', 0.45);
        for k = 1:numel(barHandles)
            barHandles(k).FaceColor = barColors(k,:);
            barHandles(k).EdgeColor = [0.20 0.20 0.20];
        end
        yline(ax, 0, '-', 'Color', [0.15 0.15 0.15], 'LineWidth', 0.8, ...
            'HandleVisibility', 'off');
        ylabel(ax, powerLabel);
        ax.YColor = [0.10 0.10 0.10];

        posStack = sum(max(plotStack, 0), 2);
        negStack = sum(min(plotStack, 0), 2);
        yMin = min(negStack);
        yMax = max(posStack);
        if isempty(yMin) || isempty(yMax) || ~isfinite(yMin) || ~isfinite(yMax) || yMax <= yMin
            yMin = -1;
            yMax = 1;
        end
        yPad = max(0.18 * (yMax - yMin), 0.08);
        ylim(ax, [yMin - yPad, yMax + yPad]);

        yyaxis(ax, 'right');
        socHandle = plot(ax, tSoc, socPct(i,:), '-o', 'Color', socColor, ...
            'LineWidth', 1.9, 'MarkerSize', 4.2, ...
            'MarkerFaceColor', 'w', 'MarkerEdgeColor', socColor);
        ylabel(ax, 'SOC (%)');
        ax.YColor = [0.10 0.10 0.10];
        ylim(ax, [0 105]);
        yticks(ax, 0:20:100);

        yyaxis(ax, 'left');
        xlim(ax, [-0.5, T + 1.2]);
        if T <= 24
            xticks(ax, 0:T);
        else
            xticks(ax, 0:4:T);
        end
        ax.XMinorGrid = 'off';
        ax.YMinorGrid = 'off';
        ax.Color = [0.995 0.995 0.995];
        ax.GridColor = [0.86 0.88 0.91];
        ax.GridAlpha = 0.55;
        ax.TickDir = 'in';
        ax.Layer = 'bottom';
        title(ax, sprintf('%s - Community %d', tilePrefix, i), 'FontWeight', 'normal');

        if i == nComm
            xlabel(ax, 'Time (h)');
        end

        if i == 1
            lgd = legend(ax, [barHandles(:); socHandle], [barLabels, {'SOC'}], ...
                'Location', 'northoutside', 'Orientation', 'horizontal', ...
                'NumColumns', min(numel(barLabels) + 1, 5), 'Box', 'on');
            try
                lgd.ItemTokenSize = [30, 14];
            catch
            end
        end
        finalize_axes(ax);
    end

    title(tl, titleText, 'FontWeight', 'bold');
end

function [powerStack, labels, colors] = add_stack_layer(powerStack, labels, colors, values, label, color)
    if isempty(values) || ~any(abs(values(:)) > 1e-9)
        return;
    end
    powerStack(:,:,end+1) = values;
    labels{end+1} = label;
    colors(end+1,:) = color;
end

function [N, T] = infer_matrix_size(sol, D, solFields, dataField)
    N = 0;
    T = 0;
    for k = 1:numel(solFields)
        if isstruct(sol) && isfield(sol, solFields{k}) && isnumeric(sol.(solFields{k})) && ~isempty(sol.(solFields{k}))
            [N, T] = size(sol.(solFields{k}));
            return;
        end
    end
    if nargin >= 4 && ~isempty(dataField) && isstruct(D) && ...
            isfield(D, dataField) && isnumeric(D.(dataField)) && ~isempty(D.(dataField))
        [N, T] = size(D.(dataField));
    end
end

function X = get_matrix_or_zeros(S, fieldName, N, T)
    X = zeros(N, T);
    if nargin < 4 || isempty(S) || ~isstruct(S) || ~isfield(S, fieldName)
        return;
    end
    V = S.(fieldName);
    if ~isnumeric(V) || isempty(V)
        return;
    end
    rows = min(N, size(V,1));
    cols = min(T, size(V,2));
    X(1:rows, 1:cols) = double(V(1:rows, 1:cols));
end

function socPct = build_soc_series_percent(socRaw, cap, soc0)
    socRaw = double(socRaw);
    socPctBody = soc_to_percent(socRaw, cap);
    nComm = size(socRaw, 1);

    if nargin >= 3 && ~isempty(soc0)
        soc0 = double(soc0(:));
        if numel(soc0) == 1
            soc0 = repmat(soc0, nComm, 1);
        end
        if nargin >= 2 && ~isempty(cap)
            cap = double(cap(:));
            if numel(cap) == 1
                cap = repmat(cap, nComm, 1);
            end
            if numel(cap) >= nComm && all(cap(1:nComm) > 0)
                soc0Pct = 100 * soc0(1:nComm) ./ cap(1:nComm);
            elseif max(abs(soc0(1:min(numel(soc0),nComm)))) <= 1.05
                soc0Pct = 100 * soc0(1:nComm);
            else
                soc0Pct = socPctBody(:,1);
            end
        elseif max(abs(soc0(1:min(numel(soc0),nComm)))) <= 1.05
            soc0Pct = 100 * soc0(1:nComm);
        else
            soc0Pct = socPctBody(:,1);
        end
    else
        soc0Pct = socPctBody(:,1);
    end

    socPct = [soc0Pct(:), socPctBody];
end

function draw_chp_profiles(R, scenName, outDir)
    sol = get_admm_solution(R);
    if isempty(sol) || ~has_numeric_field(sol,'Pchp'), return; end
    Pchp = double(sol.Pchp);
    [N, T] = size(Pchp);
    Hchp = get_matrix_or_zeros(sol, 'Hchp', N, T);
    hasHeat = any(abs(Hchp(:)) > 1e-9);
    t = 1:T;

    fig = create_figure([100 60 1040 760]);
    tl = tiledlayout(fig, N, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
    elecColor = [0.00 0.45 0.74];
    heatColor = [0.85 0.33 0.10];

    for i = 1:N
        ax = nexttile(tl);
        hold(ax, 'on');
        grid(ax, 'on');
        ax.Color = [0.995 0.995 0.995];
        ax.GridColor = [0.86 0.88 0.91];
        ax.GridAlpha = 0.55;
        ax.XMinorGrid = 'off';
        ax.YMinorGrid = 'off';
        ax.Layer = 'bottom';

        hElec = plot(ax, t, Pchp(i,:), '-o', ...
            'Color', elecColor, 'LineWidth', 1.9, ...
            'MarkerSize', 4.6, 'MarkerFaceColor', 'w', ...
            'MarkerEdgeColor', elecColor, ...
            'DisplayName', 'Electric output');
        if hasHeat
            hHeat = plot(ax, t, Hchp(i,:), '--s', ...
                'Color', heatColor, 'LineWidth', 1.9, ...
                'MarkerSize', 4.6, 'MarkerFaceColor', 'w', ...
                'MarkerEdgeColor', heatColor, ...
                'DisplayName', 'Thermal output');
        else
            hHeat = gobjects(0,1);
        end

        xlim(ax, [1 T]);
        if T <= 24
            xticks(ax, 1:T);
        else
            xticks(ax, 1:4:T);
        end
        yMax = max([Pchp(i,:), Hchp(i,:)]);
        ylim(ax, [0, 1.12 * max(yMax, 0.1)]);
        ylabel(ax, 'CHP output (MW)');
        title(ax, sprintf('Community %d', i), 'FontWeight', 'normal');

        if i == N
            xlabel(ax, 'Time slot');
        end
        if i == 1
            lgd = legend(ax, [hElec; hHeat], 'Location', 'northoutside', ...
                'Orientation', 'horizontal', 'NumColumns', 2, 'Box', 'on');
            try
                lgd.ItemTokenSize = [30, 14];
            catch
            end
        end
        finalize_axes(ax);
    end

    title(tl, sprintf('CHP electric and thermal output in %s', prettify_one_name(scenName)), ...
        'FontWeight', 'bold');
    safeSceneName = strrep(prettify_one_name(scenName),' ','_');
    export_dual(fig, outDir, sprintf('Fig8_CHP_Profiles_%s', safeSceneName));
end

function draw_energy_balance(R, scenName, outDir)
    sol = get_admm_solution(R);
    if isempty(sol), return; end
    fig = create_figure();
    tlo = tiledlayout(2,1,'TileSpacing','compact','Padding','compact');
    nexttile; hold on; grid on;
    if isfield(sol,'Heb')
        plot(sum(sol.Heb,1),'LineWidth',1.8,'DisplayName','E-boiler');
    end
    if isfield(sol,'Hchp')
        plot(sum(sol.Hchp,1),'--','LineWidth',1.8,'DisplayName','CHP heat');
    end
    ylabel('Thermal output (MW)'); title('Thermal');
    legend('Location','best'); finalize_axes(gca);
    title(tlo, sprintf('Fig. 9. Thermal balance in %s', prettify_one_name(scenName)));
    safeSceneName = strrep(prettify_one_name(scenName),' ','_');
    export_dual(fig, outDir, sprintf('Fig9_Energy_Balance_%s', safeSceneName));
end

function draw_hydrogen_profiles(R, scenName, outDir)
    sol = get_admm_solution(R);
    if isempty(sol) || ~has_numeric_field(sol,'H2prod'), return; end
    fig = create_figure(); hold on; grid on;
    ySeries = [];
    h2prod = sum(sol.H2prod,1);
    T = numel(h2prod);
    t = 1:T;
    ySeries = [ySeries, h2prod(:).'];
    [tPlot, yPlot, markerIdx] = smooth_curve_for_display(t, h2prod);
    plot(tPlot, yPlot, '-o', 'LineWidth', 1.8, ...
        'MarkerIndices', markerIdx, 'MarkerSize', 4.5, ...
        'MarkerFaceColor', 'w', 'DisplayName','H2 produced');
    if isfield(sol,'H2cons_fc')
        h2cons = sum(sol.H2cons_fc,1);
        ySeries = [ySeries, h2cons(:).'];
        [tPlot, yPlot, markerIdx] = smooth_curve_for_display(t, h2cons);
        plot(tPlot, yPlot, '--s', 'LineWidth', 1.8, ...
            'MarkerIndices', markerIdx, 'MarkerSize', 4.5, ...
            'MarkerFaceColor', 'w', 'DisplayName','H2 to FC');
    end
    if isfield(sol,'SOC_h2')
        h2soc = mean(sol.SOC_h2,1);
        ySeries = [ySeries, h2soc(:).'];
        [tPlot, yPlot, markerIdx] = smooth_curve_for_display(t, h2soc);
        plot(tPlot, yPlot, ':^', 'LineWidth', 1.8, ...
            'MarkerIndices', markerIdx, 'MarkerSize', 4.5, ...
            'MarkerFaceColor', 'w', 'DisplayName','H2 SOC');
    end
    xlabel('Time slot'); ylabel('Hydrogen (kg/h or kg)');
    title(sprintf('Fig. 10. Hydrogen system in %s', prettify_one_name(scenName)));
    xlim([1 T]);
    if T <= 24
        xticks(1:T);
    else
        xticks(1:4:T);
    end
    yMax = max(ySeries(isfinite(ySeries)));
    if isempty(yMax) || yMax <= 0
        yMax = 1;
    end
    ylim([0, 1.18 * yMax]);
    legend('Location','best'); finalize_axes(gca);
    safeSceneName = strrep(prettify_one_name(scenName),' ','_');
    export_dual(fig, outDir, sprintf('Fig10_Hydrogen_Profiles_%s', safeSceneName));
end

function draw_community_load_profiles(D, scenName, outDir)
    if isempty(D) || ~isstruct(D) || ~isfield(D,'Pload') || ~isfield(D,'Hload')
        return;
    end

    T = size(D.Pload, 2);
    t = 1:T;
    N = size(D.Pload, 1);
    fontCN = pick_cjk_font();

    for i = 1:N
        fig = create_figure([100 100 960 430]);
        ax = axes(fig); hold(ax,'on'); grid(ax,'on');
        ax.Color = [0.94 0.94 0.94];
        ax.GridColor = [0.82 0.82 0.82];
        ax.GridAlpha = 0.85;
        ax.MinorGridAlpha = 0.40;
        ax.XMinorTick = 'on';
        ax.YMinorTick = 'on';
        ax.Layer = 'top';

        h = gobjects(0,1);
        h(end+1) = plot(t, D.Pload(i,:), '-^', ...
            'LineWidth', 1.6, 'MarkerSize', 6, ...
            'MarkerFaceColor', 'w', 'DisplayName', '电负荷');
        h(end+1) = plot(t, D.Hload(i,:), '-s', ...
            'LineWidth', 1.6, 'MarkerSize', 5.5, ...
            'MarkerFaceColor', 'w', 'DisplayName', '热负荷');

        if isfield(D,'Pwind') && size(D.Pwind,1) >= i
            h(end+1) = plot(t, D.Pwind(i,:), '-o', ...
                'LineWidth', 1.6, 'MarkerSize', 6, ...
                'MarkerFaceColor', 'w', 'DisplayName', '风电');
        end

        if isfield(D,'Ppv') && size(D.Ppv,1) >= i
            h(end+1) = plot(t, D.Ppv(i,:), '-d', ...
                'LineWidth', 1.6, 'MarkerSize', 5.5, ...
                'MarkerFaceColor', 'w', 'DisplayName', '光伏');
        end

        xlabel(ax, '时间 (h)', 'FontName', fontCN, 'FontSize', 12, 'Interpreter', 'none');
        ylabel(ax, '功率 (MW)', 'FontName', fontCN, 'FontSize', 12, 'Interpreter', 'none');
        title(ax, sprintf('社区%d负荷与可再生出力曲线', i), 'FontName', fontCN, 'FontSize', 14, 'Interpreter', 'none');

        xlim([1, T]);
        if T <= 24
            xticks(1:T);
        else
            xticks(1:4:T);
        end

        yMax = max([D.Pload(i,:), D.Hload(i,:)]);
        if isfield(D,'Pwind') && size(D.Pwind,1) >= i
            yMax = max(yMax, max(D.Pwind(i,:)));
        end
        if isfield(D,'Ppv') && size(D.Ppv,1) >= i
            yMax = max(yMax, max(D.Ppv(i,:)));
        end
        ylim([0, 1.15*max(yMax, 0.1)]);

        lgd = legend(h, 'Location', 'northoutside', 'Orientation', 'horizontal', ...
            'Interpreter', 'none');
        lgd.Box = 'on';
        lgd.NumColumns = min(numel(h), 4);
        lgd.FontSize = 11;
        try
            lgd.FontName = fontCN;
            lgd.ItemTokenSize = [32, 14];
        catch
        end

        finalize_axes(ax);
        try
            ax.FontName = 'Times New Roman';
        catch
        end

        apply_cjk_font_to_axes(ax, fontCN);

        safeSceneName = strrep(prettify_one_name(scenName),' ','_');
        export_dual(fig, outDir, sprintf('Fig11_Comm%d_Load_Profiles_%s', i, safeSceneName));
    end
end

%% ========================= Utility functions =========================

function y = soc_to_percent(socRaw, cap)
    if isempty(socRaw)
        y = socRaw;
        return;
    end
    y = socRaw;

    if nargin >= 2 && ~isempty(cap)
        cap = cap(:);
        if numel(cap) == 1
            cap = repmat(cap, size(socRaw,1), 1);
        end
        if numel(cap) >= size(socRaw,1) && all(cap(1:size(socRaw,1)) > 0)
            y = 100 * socRaw ./ repmat(cap(1:size(socRaw,1)), 1, size(socRaw,2));
            return;
        end
    end

    % Fallback: if SOC was already stored in 0~1 fraction.
    if max(socRaw(:)) <= 1.05
        y = 100 * socRaw;
    end
end

function yl = auto_soc_ylim(socPct)
    vmax = max(socPct(:));
    if isempty(vmax) || ~isfinite(vmax)
        yl = [0 100];
        return;
    end
    upper = max(100, 5 * ceil(1.05 * vmax / 5));
    yl = [0 upper];
end

function v = get_field_or_empty(S, fieldName)
    v = [];
    if nargin < 2 || isempty(S) || ~isstruct(S)
        return;
    end
    if isfield(S, fieldName)
        v = S.(fieldName);
    end
end

function sol = get_admm_solution(R)
    sol = [];
    if nargin < 1 || isempty(R) || ~isstruct(R)
        return;
    end
    preferredFields = {'admm', 'centralized'};
    for i = 1:numel(preferredFields)
        fieldName = preferredFields{i};
        if isfield(R, fieldName) && is_solution_ok(R.(fieldName))
            sol = R.(fieldName);
            return;
        end
    end
end

function tf = is_solution_ok(sol)
    tf = false;
    if nargin < 1 || isempty(sol) || ~isstruct(sol)
        return;
    end
    if isfield(sol,'solveStatus')
        st = char(sol.solveStatus);
        if any(strcmpi(st, {'Failed','Infeasible_or_failed'}))
            return;
        end
    end
    tf = true;
end

function tf = has_numeric_field(S, fieldName)
    tf = false;
    if nargin < 2 || isempty(S) || ~isstruct(S) || ~isfield(S, fieldName)
        return;
    end
    v = S.(fieldName);
    tf = isnumeric(v) && ~isempty(v) && any(isfinite(v(:)));
end

function set_plot_defaults()
    set(groot,'defaultFigureColor','w');
    set(groot,'defaultAxesFontName','Times New Roman');
    set(groot,'defaultTextFontName','Times New Roman');
    set(groot,'defaultAxesFontSize',12);
    set(groot,'defaultTextFontSize',12);
    set(groot,'defaultAxesLineWidth',1.0);
    set(groot,'defaultLineLineWidth',1.5);
    set(groot,'defaultAxesBox','on');
end

function fig = create_figure(pos)
    if nargin<1||isempty(pos), pos=[100 100 860 620]; end
    if numel(pos)==2, pos=[100 100 pos(1) pos(2)]; end
    if numel(pos)~=4, pos=[100 100 860 620]; end
    fig = figure('Color','w','Position',pos);
end

function finalize_axes(ax)
    ax.TickDir='in'; ax.Box='on'; ax.LineWidth=1.0; ax.FontSize=12;
end

function apply_cjk_font_to_axes(ax, fontCN)
    if nargin < 2 || isempty(fontCN) || ~isgraphics(ax,'axes')
        return;
    end
    try
        if isgraphics(ax.XLabel), ax.XLabel.FontName = fontCN; ax.XLabel.Interpreter = 'none'; end
        if isgraphics(ax.YLabel), ax.YLabel.FontName = fontCN; ax.YLabel.Interpreter = 'none'; end
        if isgraphics(ax.Title),  ax.Title.FontName  = fontCN; ax.Title.Interpreter  = 'none'; end
    catch
    end
    try
        lgd = legend(ax);
        if isgraphics(lgd,'legend')
            lgd.FontName = fontCN;
            lgd.Interpreter = 'none';
        end
    catch
    end
end

function export_dual(fig, outDir, baseName)
    if nargin < 1 || isempty(fig) || ~ishandle(fig) || ~isgraphics(fig,'figure')
        warning('export_dual:invalidFigure', 'Invalid figure handle, skip export: %s', baseName);
        return;
    end

    ensure_directory_exists(outDir);

    pngFile = fullfile(outDir, [baseName '.png']);
    epsFile = fullfile(outDir, [baseName '.eps']);

    try
        drawnow;
    catch
    end
    try
        set(fig, 'PaperPositionMode', 'auto');
    catch
    end

    pngOK = false;
    if exist('exportgraphics','file') == 2
        try
            exportgraphics(fig, pngFile, 'Resolution', 400);
            pngOK = true;
        catch
            pngOK = false;
        end
    end
    if ~pngOK
        try
            figure(fig);
            print(fig, pngFile, '-dpng', '-r400');
        catch ME
            warning('PNG export failed for %s: %s', baseName, ME.message);
        end
    end

    epsOK = false;
    if exist('exportgraphics','file') == 2
        try
            exportgraphics(fig, epsFile, 'ContentType', 'vector');
            epsOK = true;
        catch
            epsOK = false;
        end
    end
    if ~epsOK
        try
            figure(fig);
            print(fig, epsFile, '-depsc', '-painters');
        catch ME
            warning('EPS export failed for %s: %s', baseName, ME.message);
        end
    end

    if ishandle(fig) && isgraphics(fig,'figure')
        close(fig);
    end
end

function ensure_directory_exists(outDir)
    if exist(outDir, 'dir')
        return;
    end
    [ok, msg] = mkdir(outDir);
    if ~ok
        error('Could not create output directory "%s": %s', outDir, msg);
    end
end

function tf = is_absolute_path(pathText)
    if isempty(pathText)
        tf = false;
        return;
    end
    pathText = char(pathText);
    tf = ~isempty(regexp(pathText, '^[A-Za-z]:[\\/]|^\\\\|^/', 'once'));
end

function names = prettify_scenario_names(scenNames)
    names = scenNames;
    for i=1:numel(names), names{i}=prettify_one_name(names{i}); end
end

function s = prettify_one_name(s)
    s = strrep(s,'_',' ');
    s = strrep(s,'S1 ','');
    s = strrep(s,'S2 ','');
    s = strrep(s,'S3 ','');
end

function vec = get_parts_vec(sol)
    vec = zeros(1,8);
    if ~isfield(sol,'parts'), return; end
    p = sol.parts;
    vec(1)=get_scalar_safe(p,'gridCost');
    vec(2)=get_scalar_safe(p,'carbonCost');
    vec(3)=get_scalar_safe(p,'gasCost');
    vec(4)=get_scalar_safe(p,'gasCarbonCost');
    vec(5)=get_scalar_safe(p,'pvCurtCost');
    vec(6)=get_scalar_safe(p,'windCurtCost');
    vec(7)=get_scalar_safe(p,'h2ShortCost');
    vec(8)=get_scalar_safe(p,'qSupportCost');
end

function v = get_solution_objective(sol)
    v = NaN;
    candidates = {'recoveredGlobalObjective', 'TotalObjective_Yuan', 'obj'};
    for i = 1:numel(candidates)
        f = candidates{i};
        if isfield(sol, f) && ~isempty(sol.(f))
            tmp = double(sol.(f));
            if isscalar(tmp) && isfinite(tmp)
                v = tmp;
                return;
            end
        end
    end
end

function v = get_scalar_safe(s, f)
    if isfield(s,f) && ~isempty(s.(f)), v=double(s.(f)); else v=0; end
end

function fontName = pick_cjk_font()
    % Pick a font that can actually render Chinese on the local machine.
    % Windows MATLAB usually has Microsoft YaHei / SimHei / SimSun.
    % macOS usually has PingFang SC / Heiti SC.
    % Linux may have Noto Sans CJK SC / WenQuanYi Zen Hei.
    candidates = {'Microsoft YaHei','SimHei','SimSun','PingFang SC','Heiti SC', ...
                  'Noto Sans CJK SC','WenQuanYi Zen Hei','Arial Unicode MS'};

    fontName = '';
    try
        allFonts = listfonts;
        for k = 1:numel(candidates)
            if any(strcmpi(allFonts, candidates{k}))
                fontName = candidates{k};
                return;
            end
        end
    catch
    end

    % Last-resort platform defaults.
    if ispc
        fontName = 'Microsoft YaHei';
    elseif ismac
        fontName = 'PingFang SC';
    else
        fontName = 'Noto Sans CJK SC';
    end
end
