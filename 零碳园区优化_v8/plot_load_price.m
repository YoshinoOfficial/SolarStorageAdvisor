function plot_load_price(dataSource, scenarioName, outDir)
%PLOT_LOAD_HEAT_RENEWABLE_PROFILES Draw price and community profile figures.
%   This combined plotting entry produces:
%   1) time-of-use electricity price curves;
%   2) electric load, heat load, wind and PV output curves.
%
%   plot_load_heat_renewable_profiles()
%   plot_load_heat_renewable_profiles('build_case','S3_Normal_WithStorage_Carbon')
%   plot_load_heat_renewable_profiles('comparison_results.mat','S3_Normal_WithStorage_Carbon')

if nargin < 1 || isempty(dataSource)
    dataSource = 'build_case';
end
if nargin < 2
    scenarioName = '';
end
if nargin < 3 || isempty(outDir)
    outDir = 'figures_submission';
end
if ~exist(outDir, 'dir')
    mkdir(outDir);
end

data = load_profile_data(dataSource, scenarioName);
fontCN = pick_cjk_font_local();

draw_electricity_price_profile(data, outDir, fontCN);
draw_load_heat_renewable_profile(data, outDir, fontCN);
end

function draw_electricity_price_profile(data, outDir, fontCN)
if ~isfield(data, 'ce') || isempty(data.ce)
    return;
end

ce = data.ce(1,:) / 1000;
T = numel(ce);
t = 1:T;

fig = figure('Color', 'w', 'Units', 'pixels', 'Position', [120 120 860 430]);
ax = axes(fig);
hold(ax, 'on');
box(ax, 'on');
grid(ax, 'on');
ax.XMinorTick = 'on';
ax.YMinorTick = 'on';
ax.TickDir = 'in';
ax.Layer = 'top';
ax.FontName = 'Times New Roman';
ax.FontSize = 13;
ax.LineWidth = 0.8;
ax.GridAlpha = 0.22;
ax.MinorGridAlpha = 0.12;

tFine = linspace(1, T, 240);
ceFine = interp1(t, ce, tFine, 'pchip');
plot(ax, tFine, ceFine, '-', ...
    'Color', [0.0000 0.4470 0.7410], 'LineWidth', 2.0, ...
    'DisplayName', '分时电价');
plot(ax, t, ce, 'o', ...
    'Color', [0.0000 0.4470 0.7410], 'LineWidth', 1.2, 'MarkerSize', 5.5, ...
    'MarkerFaceColor', 'w', 'HandleVisibility', 'off');

xlim(ax, [1 T]);
xticks(ax, 1:T);
ylim(ax, [0, 1.15 * max(max(ce(:)), 1e-3)]);
xlabel(ax, '时间 (h)', 'FontName', fontCN, 'FontSize', 16, 'Interpreter', 'none');
ylabel(ax, '电价 (元/kWh)', 'FontName', fontCN, 'FontSize', 16, 'Interpreter', 'none');
title(ax, '分时电价曲线', 'FontName', fontCN, 'FontSize', 17, ...
    'FontWeight', 'normal', 'Interpreter', 'none');

lgd = legend(ax, 'Location', 'northoutside', 'Orientation', 'horizontal', ...
    'Interpreter', 'none', 'Box', 'on');
lgd.FontName = fontCN;
lgd.FontSize = 11;
lgd.NumColumns = 1;
try
    lgd.ItemTokenSize = [24, 12];
catch
end

fileBase = fullfile(outDir, 'Fig3_2_Electricity_Price_Curve');
export_figure(fig, fileBase);
fprintf('Saved figure to:\n  %s.png\n  %s.eps\n', fileBase, fileBase);
end

function draw_load_heat_renewable_profile(data, outDir, fontCN)
T = size(data.Pload, 2);
t = 1:T;
N = min(3, size(data.Pload, 1));

Ppv = zeros(size(data.Pload));
Pwind = zeros(size(data.Pload));
if isfield(data, 'Ppv') && ~isempty(data.Ppv)
    Ppv = data.Ppv;
end
if isfield(data, 'Pwind') && ~isempty(data.Pwind)
    Pwind = data.Pwind;
end

fig = figure('Color', 'w', 'Units', 'pixels', 'Position', [80 40 860 1180]);
tl = tiledlayout(fig, N, 1, 'TileSpacing', 'loose', 'Padding', 'loose');

for i = 1:N
    ax = nexttile(tl, i);
    hold(ax, 'on');
    box(ax, 'on');
    grid(ax, 'on');
    ax.XMinorTick = 'on';
    ax.YMinorTick = 'on';
    ax.TickDir = 'in';
    ax.Layer = 'top';
    ax.FontName = 'Times New Roman';
    ax.FontSize = 13;
    ax.LineWidth = 0.8;
    ax.GridAlpha = 0.22;
    ax.MinorGridAlpha = 0.12;

    plot(ax, t, data.Pload(i,:), '-^', ...
        'Color', [0.0000 0.4470 0.7410], ...
        'LineWidth', 1.5, 'MarkerSize', 5.8, ...
        'MarkerFaceColor', 'w', 'DisplayName', '电负荷');
    plot(ax, t, data.Hload(i,:), '-s', ...
        'Color', [0.8500 0.3250 0.0980], ...
        'LineWidth', 1.5, 'MarkerSize', 5.2, ...
        'MarkerFaceColor', 'w', 'DisplayName', '热负荷');
    plot(ax, t, Pwind(i,:), '-o', ...
        'Color', [0.4660 0.6740 0.1880], ...
        'LineWidth', 1.5, 'MarkerSize', 5.5, ...
        'MarkerFaceColor', 'w', 'DisplayName', '风电');
    plot(ax, t, Ppv(i,:), '-d', ...
        'Color', [0.4940 0.1840 0.5560], ...
        'LineWidth', 1.5, 'MarkerSize', 5.2, ...
        'MarkerFaceColor', 'w', 'DisplayName', '光伏');

    xlim(ax, [1 T]);
    xticks(ax, 1:T);
    ymax = max([data.Pload(i,:), data.Hload(i,:), Pwind(i,:), Ppv(i,:)]);
    ylim(ax, [0, 1.18 * max(ymax, 0.1)]);

    xlabel(ax, '时间 (h)', 'FontName', fontCN, 'FontSize', 16, 'Interpreter', 'none');
    ylabel(ax, '功率 (MW)', 'FontName', fontCN, 'FontSize', 16, 'Interpreter', 'none');
    title(ax, sprintf('社区 %d', i), 'FontName', fontCN, 'FontSize', 17, ...
        'FontWeight', 'normal', 'Interpreter', 'none');

    lgd = legend(ax, 'Location', 'northoutside', 'Orientation', 'horizontal', ...
        'Interpreter', 'none', 'Box', 'on');
    lgd.FontName = fontCN;
    lgd.FontSize = 11;
    lgd.NumColumns = 4;
    try
        lgd.ItemTokenSize = [24, 12];
    catch
    end
end

caption = '图 3-3 电负荷、热负荷、风电和光伏出力曲线';
annotation(fig, 'textbox', [0.06 0.004 0.88 0.035], 'String', caption, ...
    'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
    'EdgeColor', 'none', 'FontName', fontCN, 'FontSize', 18, ...
    'Interpreter', 'none');

fileBase = fullfile(outDir, 'Fig3_3_Load_Heat_Renewable_Profiles');
export_figure(fig, fileBase);
fprintf('Saved figure to:\n  %s.png\n  %s.eps\n', fileBase, fileBase);
end

function data = load_profile_data(dataSource, scenarioName)
if strcmpi(dataSource, 'build_case')
    data = build_case('ieee33_3comm_hetero_real', 13);
    data = apply_profile_scenario_scale(data, scenarioName);
    return;
end

if exist(dataSource, 'file') == 2
    S = load(dataSource);
    if isfield(S, 'allData') && isstruct(S.allData) && ~isempty(fieldnames(S.allData))
        names = fieldnames(S.allData);
        if isempty(scenarioName)
            preferred = {'S3_Normal_WithStorage_Carbon', 'S2_Normal_WithStorage_NoCarbon', names{1}};
            scenarioName = preferred{find(cellfun(@(x) isfield(S.allData, x), preferred), 1, 'first')};
        end
        if isfield(S.allData, scenarioName)
            data = S.allData.(scenarioName);
            return;
        end
        error('Scenario "%s" was not found in %s.', scenarioName, dataSource);
    end
end

data = build_case('ieee33_3comm_hetero_real', 13);
data = apply_profile_scenario_scale(data, scenarioName);
end

function data = apply_profile_scenario_scale(data, scenarioName)
if isempty(scenarioName)
    return;
end
switch char(scenarioName)
    case {'S1_Normal_NoStorage_NoCarbon', 'S2_Normal_WithStorage_NoCarbon', 'S3_Normal_WithStorage_Carbon'}
        pvScale = 3.0;
        windScale = 3.0;
    case 'S4_HighRE_WithStorage_Carbon'
        pvScale = 3.3;
        windScale = 3.3;
    otherwise
        return;
end
data.Ppv = data.Ppv * pvScale;
data.Pwind = data.Pwind * windScale;
end

function export_figure(fig, fileBase)
if exist('exportgraphics', 'file') == 2
    exportgraphics(fig, [fileBase '.png'], 'Resolution', 400);
    exportgraphics(fig, [fileBase '.eps'], 'ContentType', 'vector');
else
    saveas(fig, [fileBase '.png']);
    saveas(fig, [fileBase '.eps'], 'epsc');
end
end

function fontName = pick_cjk_font_local()
candidates = {'Microsoft YaHei', 'SimHei', 'SimSun', 'PingFang SC', 'Heiti SC', ...
              'Noto Sans CJK SC', 'WenQuanYi Zen Hei', 'Arial Unicode MS'};
fontName = 'Microsoft YaHei';
try
    fonts = listfonts;
    for k = 1:numel(candidates)
        if any(strcmpi(fonts, candidates{k}))
            fontName = candidates{k};
            return;
        end
    end
catch
end
end
