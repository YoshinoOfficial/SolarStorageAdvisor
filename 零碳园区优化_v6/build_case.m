function data = build_case(caseName, ddreScenarioId)
% BUILD_CASE 零碳园区多能流算例构建函数
% 输入: caseName - 算例名称, ddreScenarioId - DDRE场景ID
% 输出: data - 包含系统参数的结构体
% 功能:
%   - 光伏+风力发电
%   - 冷热电三联供(CHP)、电锅炉
%   - 电解水制氢+燃料电池+储氢系统
%   - 电/热/氢储能
%   - 电/热/氢负荷
%   - IEEE33节点辐射状配电网(DistFlow模型)

if nargin < 1
    caseName = 'ieee33_3comm_hetero_real';
end
if nargin < 2 || isempty(ddreScenarioId)
    ddreScenarioId = 1;
end

switch lower(caseName)
    case {'ieee33_3comm_hetero_real','ieee33_3comm_hetero'}
        data = build_ieee33_3comm_hetero_case(ddreScenarioId);
    otherwise
        error('未知的异构算例名称: %s', caseName);
end
end

function data = build_ieee33_3comm_hetero_case(ddreScenarioId)
% 构建IEEE33节点三社区异构图

%% 基本维度参数
B = 33;          % 节点数
rootBus = 1;      % 根节点
T = 24;           % 时间段数(24小时)
dt = 1;           % 时间步长(小时)
N = 3;            % 社区数量

%% IEEE33辐射状配电网(Baran-Wu)
branch_ohm = [ ...
    1  2  0.0922 0.0470;
    2  3  0.4930 0.2511;
    3  4  0.3660 0.1864;
    4  5  0.3811 0.1941;
    5  6  0.8190 0.7070;
    6  7  0.1872 0.6188;
    7  8  0.7114 0.2351;
    8  9  1.0300 0.7400;
    9  10 1.0440 0.7400;
    10 11 0.1966 0.0650;
    11 12 0.3744 0.1238;
    12 13 1.4680 1.1550;
    13 14 0.5416 0.7129;
    14 15 0.5910 0.5260;
    15 16 0.7463 0.5450;
    16 17 1.2890 1.7210;
    17 18 0.7320 0.5740;
    2  19 0.1640 0.1565;
    19 20 1.5042 1.3554;
    20 21 0.4095 0.4784;
    21 22 0.7089 0.9373;
    3  23 0.4512 0.3083;
    23 24 0.8980 0.7091;
    24 25 0.8960 0.7011;
    6  26 0.2030 0.1034;
    26 27 0.2842 0.1447;
    27 28 1.0590 0.9337;
    28 29 0.8042 0.7006;
    29 30 0.5075 0.2585;
    30 31 0.9744 0.9630;
    31 32 0.3105 0.3619;
    32 33 0.3410 0.5302];

branch = branch_ohm(:,1:2);
L = size(branch,1);

baseMVA = 100;
baseKV  = 12.66;
Zbase = baseKV^2 / baseMVA;
rline = branch_ohm(:,3) / Zbase;
xline = branch_ohm(:,4) / Zbase;

%% IEEE33标准负荷(MW/MVAr)
Pd_nom = [ ...
    0.000 0.100 0.090 0.120 0.060 0.060 0.200 0.200 0.060 0.060 0.045 ...
    0.060 0.060 0.120 0.060 0.060 0.060 0.090 0.090 0.090 0.090 0.090 ...
    0.090 0.420 0.420 0.060 0.060 0.060 0.120 0.200 0.150 0.210 0.060];

Qd_nom = [ ...
    0.000 0.060 0.040 0.080 0.030 0.020 0.100 0.100 0.020 0.020 0.030 ...
    0.035 0.035 0.080 0.010 0.020 0.020 0.040 0.040 0.040 0.040 0.040 ...
    0.050 0.200 0.200 0.025 0.025 0.020 0.070 0.600 0.070 0.100 0.040];

%% 三个社区位于代表性节点
commBus = [10; 18; 30];

%% 电价和基础负荷曲线
ce_base = 1000 * [0.40 0.32 0.26 0.21 0.23 0.35 0.55 0.70 0.82 0.84 0.80 0.78 ...
           0.68 0.57 0.52 0.53 0.65 0.85 0.96 0.92 0.87 0.78 0.66 0.48];
shape_default = [0.56 0.54 0.53 0.52 0.54 0.62 0.73 0.83 0.90 0.94 0.96 0.97 ...
              0.98 0.97 0.96 0.96 0.98 1.00 0.98 0.93 0.86 0.78 0.69 0.61];

% 社区特定24小时负荷曲线
% 社区1: 工业区 - 白天生产,负荷最高
% 社区2: 商业区 - 午餐和晚餐高峰
% 社区3: 住宅区 - 早高峰和晚高峰

%% 读取DDRE数据文件
file_ddre_day = resolve_local_file_hetero('1-Day Scenarios');

%% 从DDRE-33获取光伏曲线
[ddrePpvPU, ddreMeta] = build_ddre33_day_pv_profiles_hetero(file_ddre_day, commBus, ddreScenarioId);

%% 从DDRE-33获取风电曲线
[ddrePwindPU] = build_ddre33_day_wind_profiles_hetero(file_ddre_day, commBus, ddreScenarioId);

%% 电价、基础负荷、光伏、风电
ce = zeros(N,T);
Ppv = zeros(N,T);
Pwind = zeros(N,T);
pvCap = [3.50; 4.00; 3.00];         % MW, 光伏装机容量(差异化)
windCap = [0.00; 2.50; 0];       % MW, 风电装机容量
PchMax  = [3.50; 3.20; 3.00];       % MW, 电储能充放功率
PdisMax = [2.50; 2.20; 2.00];       % MW
Emax    = 3.0 * PdisMax;            % MWh, 电储能容量
priceShift = [0; 0.000; 0];

% 放大基础电负荷,并根据功率因数重构无功负荷
for i = 1:N
    ce(i,:) = max(250, ce_base + priceShift(i));
    Ppv(i,:)   = pvCap(i) * ddrePpvPU(i,:);
    Pwind(i,:) = windCap(i) * ddrePwindPU(i,:);
end

%% 碳成本参数
carbonShape = [0.92 0.91 0.90 0.90 0.91 0.95 1.02 1.08 1.12 1.15 1.17 1.16 ...
               1.13 1.10 1.08 1.10 1.16 1.22 1.24 1.18 1.08 1.00 0.96 0.93];
carbonShape = carbonShape / mean(carbonShape);
efGridBase = 0.4419 * 1000;              % kgCO2/MWh, 电网排放因子
pCO2Base   = 62.36/1000;                  % 元/kgCO2, 碳价格
efGrid = zeros(N,T);
pCO2   = zeros(N,T);
for i = 1:N
    locCarbonScale = 1.00 + 0.03*(i-2);
    efGrid(i,:) = efGridBase * locCarbonScale * carbonShape;
    pCO2(i,:)   = pCO2Base * ones(1,T);
end
cCarbon = efGrid .* pCO2;

%% 热电联供(CHP)参数 - 中等园区规模
PchpRated = [1.20; 0.75; 0.60];      % MW, 电功率额定值
etaE_chp  = 0.35 * ones(N,1);          % 电效率
etaH_chp  = 0.45 * ones(N,1);          % 热效率
FgasMin   = zeros(N,1);                % 无最小出力限制(可关停)
FgasMax   = PchpRated ./ etaE_chp;     % 最大燃气输入(MW_th)
cGas      = (2.8 / 9.7) * 1000;       % 元/MWh_th (天然气约2.8元/m3, LHV约9.7 kWh/m3)
efGas     = 0.202 * 1000;             % kgCO2/MWh_th (IPCC天然气排放因子)

% CHP增强运行参数(与元/MWh目标函数数值同步)
uChp0       = zeros(N,1);
PchpMin     = 0.30 * PchpRated;        % 最小出力
RampUpCHP   = 0.35 * PchpRated;        % MW/时段, 爬坡速率
RampDnCHP   = 0.35 * PchpRated;        % MW/时段
StartUpCHP  = 80  * ones(N,1);         % 元/次, 启动成本
ShutDnCHP   = 20  * ones(N,1);         % 元/次, 停机成本
MinUpCHP    = 2   * ones(N,1);         % 时段, 最小运行时间
MinDnCHP    = 2   * ones(N,1);         % 时段, 最小停机时间
cOM_CHP     = 8   * ones(N,1);         % 元/MWh_el, 运维成本
cRampCHP    = 2   * ones(N,1);         % 元/MW-change, 爬坡成本
lambdaHdump = 200 * ones(N,1);         % 元/MWh_th, 余热惩罚成本

%% 电锅炉
PebMax = [2.50; 2.00; 1.50];           % MW
etaEb  = 0.97 * ones(N,1);              % 效率


%% 电解水制氢(PEM)
PelecMax = [1.00; 0.80; 1.20];         % MW
etaElec  = 20.0 * ones(N,1);           % kgH2/MWh (约50 kWh/kg, 典型PEM电解槽)

%% 燃料电池(PEM)
H2fcMax  = [30.0; 25.0; 40.0];         % kg/h, 最大耗氢量
etaFc    = 0.018 * ones(N,1);          % MW/(kg/h) = 18 kWh/kgH2 (典型PEM燃料电池)

%% 电储能(现有)
SOC0_e   = 0.50 * Emax;
etaCh_e  = 0.95 * ones(N,1);
etaDis_e = 0.95 * ones(N,1);

%% 热储能
HchMax   = [2.50; 2.00; 1.80];         % MW
HdisMax  = [2.50; 2.00; 1.80];         % MW
EthMax   = [10.0; 8.0; 6.0];           % MWh
SOC0_th  = 0.50 * EthMax;
etaCh_th = 0.95 * ones(N,1);
etaDis_th= 0.95 * ones(N,1);

%% 储氢系统
H2chMax  = [60.0; 50.0; 80.0];         % kg/h
H2disMax = [60.0; 50.0; 80.0];         % kg/h
EH2Max   = [30.0; 25.0; 40.0];      % kg
SOC0_h2  = 0.20 * EH2Max;

%% 典型日负荷曲线
% 社区类型:
%   1) 住宅区
%   2) 工业区
%   3) 商业区
% 假设: 冬季供暖季

% 固定电负荷(MW)
Pload = [ ...
    0.22 0.20 0.28 0.27 0.29 0.38 0.40 0.42 0.50 0.54 0.60 0.58 ...
    0.56 0.55 0.56 0.60 0.68 0.78 0.86 0.92 0.78 0.76 0.42 0.30;   % 社区1: 住宅区

    0.85 0.82 0.80 0.79 0.82 0.92 1.10 1.32 1.48 1.60 1.68 1.72 ...
    1.74 1.74 1.72 1.70 1.68 1.65 1.58 1.50 1.38 1.22 1.05 0.95;   % 社区2: 工业区

    0.30 0.28 0.27 0.26 0.28 0.35 0.50 0.82 0.83 0.85 0.98 0.99 ...
    0.96 1.00 0.82 0.78 0.88 0.90 1.12 1.10 0.98 0.86 0.72 0.64];  % 社区3: 商业区

% 保持基础电负荷同步
Pbase = Pload;

% 根据功率因数重构无功负荷
% 住宅区: 较高功率因数
% 工业区: 因电机设备功率因数较低
% 商业区: 中高功率因数
pfComm = [0.98; 0.93; 0.96];
Qbase = zeros(N,T);
for i = 1:N
    Qbase(i,:) = Pbase(i,:) * tan(acos(pfComm(i)));
end

% 固定热负荷(MW)
Hload = [ ...
   0.625 0.610 0.600 0.590 0.610 0.690 0.780 0.860 0.830 0.750 0.680 0.640 ...
   0.610 0.600 0.610 0.640 0.700 0.790 0.870 0.930 0.950 0.890 0.790 0.690;   % 社区1: 住宅区

    1.45 1.42 1.40 1.40 1.42 1.48 1.58 1.68 1.76 1.82 1.86 1.88 ...
    1.88 1.86 1.84 1.82 1.80 1.76 1.70 1.62 1.56 1.52 1.48 1.46;   % 社区2: 工业区

    0.210 0.200 0.190 0.190 0.200 0.240 0.325 0.475 0.640 0.790 0.890 0.950 ...
    0.980 1.000 1.010 0.990 0.940 0.840 0.700 0.550 0.410 0.310 0.250 0.230];  % 社区3: 商业区

% 氢气负荷: 仅工业区有氢气需求
H2load = zeros(N,T);
H2load(2,:) = [4 4 8 8 9 10 12 14 16 18 20 20 20 20 19 19 18 17 16 14 12 10 9 8 ];

PgridMax = zeros(N,1);
for i = 1:N
    PgridMax(i) = 1.5 * (max(Pbase(i,:)) + PchpRated(i) + windCap(i) + PchMax(i));
end

% Soften CHP trajectories so hour-to-hour output is less abrupt in Fig. 8.
PchpMin     = [0.22; 0.40; 0.40] .* PchpRated;
RampUpCHP   = [0.28; 0.18; 0.18] .* PchpRated;
RampDnCHP   = [0.28; 0.18; 0.18] .* PchpRated;
StartUpCHP  = [70; 150; 150];
ShutDnCHP   = [25; 60; 60];
MinUpCHP    = [2; 4; 4];
MinDnCHP    = [2; 3; 3];
cRampCHP    = [4; 12; 12];

%% 配电网运行参数
Vmin = 0.95 * ones(B,1);
Vmax = 1.05 * ones(B,1);
Vslack = 1.05;
PsubMax = 20.0 * ones(1,T);            % MW, 中等园区规模
PijMax  = 12.0 * ones(L,1);            % MW
QijMax  = 8.0 * ones(L,1);             % MVAr
PijMax(1:4)   = 12.0;  QijMax(1:4)   = 8.0;
PijMax(5:17)  = 8.0;   QijMax(5:17)  = 5.5;
PijMax(18:21) = 6.0;   QijMax(18:21) = 4.0;
PijMax(22:24) = 6.0;   QijMax(22:24) = 4.0;
PijMax(25:27) = 5.5;   QijMax(25:27) = 3.5;
PijMax(28:32) = 4.0;   QijMax(28:32) = 2.5;

%% 背景配电网负荷
PbusBase = zeros(B,T);
QbusBase = zeros(B,T);
for bidx = 2:B
    if ~ismember(bidx, commBus)
        PbusBase(bidx,:) = Pd_nom(bidx) * shape_default;
        QbusBase(bidx,:) = Qd_nom(bidx) * shape_default;
    end
end

%% 惩罚系数
lambdaPVCurt  = 230 * ones(N,1);        % 元/MWh
lambdaWindCurt= 200 * ones(N,1);       % 元/MWh
lambdaH2Short = 30 * ones(N,1);       % 元/kg
lambdaQpv     = 5.0 * ones(N,1);      % 元/(MVAr^2*h)
lambdaQes     = 5.0 * ones(N,1);      % 元/(MVAr^2*h)

QcompCoeff = [0.032; 0.033; 0.032];
QpvMax     = 1.05 * pvCap(:) + 0.08;
QesMax     = 1.10 * PdisMax(:) + 0.08;
PcompFixed = zeros(N,T);         
QinjMax    = max(Qbase,[],2) + QcompCoeff(:).*PcompFixed(:,1) + 0.05;
QinjMin    = min(Qbase,[],2) - QpvMax(:) - QesMax(:) - 0.05;

%% 拓扑辅助结构
[bus_has_comm, bus_to_comm, out_lines] = build_network_helpers_struct_hetero(B, branch, commBus, N);

%% 封装参数
data.caseName = 'ieee33_3comm_hetero_real';
data.networkName = 'IEEE33';
data.modelType = 'zero_carbon_campus_multi_energy';
data.N = N; data.T = T; data.B = B; data.L = L; data.dt = dt;

data.commBus = commBus(:);
data.rootBus = rootBus;
data.branch = branch;

data.ce = ce;
data.efGrid = efGrid;
data.pCO2 = pCO2;
data.cCarbon = cCarbon;
data.Pbase = Pbase;
data.Qbase = Qbase;
data.Ppv = Ppv;
data.Pwind = Pwind;

% 多能流设备
data.PchpRated = PchpRated(:);
data.etaE_chp = etaE_chp(:);
data.etaH_chp = etaH_chp(:);
data.FgasMin = FgasMin(:);
data.FgasMax = FgasMax(:);
data.cGas = cGas;
data.efGas = efGas;

data.uChp0 = uChp0(:);
data.PchpMin = PchpMin(:);
data.RampUpCHP = RampUpCHP(:);
data.RampDnCHP = RampDnCHP(:);
data.StartUpCHP = StartUpCHP(:);
data.ShutDnCHP = ShutDnCHP(:);
data.MinUpCHP = MinUpCHP(:);
data.MinDnCHP = MinDnCHP(:);
data.cOM_CHP = cOM_CHP(:);
data.cRampCHP = cRampCHP(:);
data.lambdaHdump = lambdaHdump(:);

data.PebMax = PebMax(:);
data.etaEb = etaEb(:);

data.PelecMax = PelecMax(:);
data.etaElec = etaElec(:);

data.H2fcMax = H2fcMax(:);
data.etaFc = etaFc(:);

% 电储能
data.PchMax = PchMax(:);
data.PdisMax = PdisMax(:);
data.Emax = Emax(:);
data.SOC0_e = SOC0_e(:);
data.etaCh_e = etaCh_e(:);
data.etaDis_e = etaDis_e(:);

% 热储能
data.HchMax = HchMax(:);
data.HdisMax = HdisMax(:);
data.EthMax = EthMax(:);
data.SOC0_th = SOC0_th(:);
data.etaCh_th = etaCh_th(:);
data.etaDis_th = etaDis_th(:);

% 储氢
data.H2chMax = H2chMax(:);
data.H2disMax = H2disMax(:);
data.EH2Max = EH2Max(:);
data.SOC0_h2 = SOC0_h2(:);

% 负荷
data.Pload = Pload;
data.Hload = Hload;
data.H2load = H2load;

data.PcompFixed = PcompFixed;
data.QcompCoeff = QcompCoeff(:);

data.PgridMax = PgridMax(:);

data.baseMVA = baseMVA;
data.rline = rline(:);
data.xline = xline(:);
data.Vmin = Vmin(:);
data.Vmax = Vmax(:);
data.Vslack = Vslack;
data.PsubMax = PsubMax;
data.PijMax = PijMax(:);
data.QijMax = QijMax(:);

data.PbusBase = PbusBase;
data.QbusBase = QbusBase;

data.lambdaPVCurt = lambdaPVCurt(:);
data.lambdaWindCurt = lambdaWindCurt(:);
data.lambdaH2Short = lambdaH2Short(:);
data.lambdaQpv = lambdaQpv(:);
data.lambdaQes = lambdaQes(:);

data.QpvMax = QpvMax(:);
data.QesMax = QesMax(:);
data.QinjMin = QinjMin(:);
data.QinjMax = QinjMax(:);

% 周期末端状态目标(日前调度)
data.termSOC_e  = data.SOC0_e;
data.termSOC_th = data.SOC0_th;
data.termSOC_h2 = data.SOC0_h2;
data.bus_has_comm = bus_has_comm;
data.bus_to_comm = bus_to_comm;
data.out_lines = out_lines;

% 元数据
data.ieee33_Pd_nom = Pd_nom(:);
data.ieee33_Qd_nom = Qd_nom(:);
data.solarSourceFile = file_ddre_day;
data.ddreMeta = ddreMeta;
data.ddreScenarioId = ddreScenarioId;
data.carbonModelNotes = {'电网购电和燃气消耗的线性时变碳成本'};
end

%% ========================================================================
function [pvProfiles, meta] = build_ddre33_day_pv_profiles_hetero(sourcePath, commBus, scenarioId)
% 从DDRE-33数据构建光伏曲线

if nargin < 3 || isempty(scenarioId)
    scenarioId = 1;
end

sourcePath = char(sourcePath);
scenarioName = sprintf('scenario_%03d.csv', scenarioId);
scenarioPath = '';

if exist(sourcePath, 'dir') == 7
    candidate = fullfile(sourcePath, scenarioName);
    if exist(candidate, 'file') == 2
        scenarioPath = candidate;
    end
elseif exist(sourcePath, 'file') == 2
    [~,~,ext] = fileparts(sourcePath);
    if strcmpi(ext, '.zip')
        tmpBase = fullfile(tempdir, 'ddre33_1day_scenarios');
        if exist(fullfile(tmpBase, '1-Day Scenarios'), 'dir') ~= 7
            mkdir(tmpBase);
            unzip(sourcePath, tmpBase);
        end
        candidate1 = fullfile(tmpBase, '1-Day Scenarios', scenarioName);
        candidate2 = fullfile(tmpBase, scenarioName);
        if exist(candidate1, 'file') == 2
            scenarioPath = candidate1;
        elseif exist(candidate2, 'file') == 2
            scenarioPath = candidate2;
        end
    end
end

if isempty(scenarioPath)
    error('未找到DDRE-33场景文件: %s', scenarioName);
end

tbl = read_ddre33_scenario_table_hetero(scenarioPath);
req = {'node_18_PV','node_33_PV'};
for c = 1:numel(req)
    if ~any(strcmp(tbl.Properties.VariableNames, req{c}))
        error('缺少必需的DDRE-33 PV列: %s', req{c});
    end
end

pv18_15 = max(0, min(1, double(tbl.node_18_PV(:))));
pv33_15 = max(0, min(1, double(tbl.node_33_PV(:))));
if numel(pv18_15) ~= 96 || numel(pv33_15) ~= 96
    error('DDRE-33 1天场景应有96个15分钟点。');
end

pv18 = mean(reshape(pv18_15, 4, 24), 1);
pv33 = mean(reshape(pv33_15, 4, 24), 1);
pvAvg = 0.5 * (pv18 + pv33);

N = numel(commBus);
pvProfiles = zeros(N, 24);
for i = 1:N
    if commBus(i) == 18
        pvProfiles(i,:) = pv18;
    elseif commBus(i) >= 28
        pvProfiles(i,:) = pv33;
    else
        pvProfiles(i,:) = pvAvg;
    end
end

meta.scenarioId = scenarioId;
meta.scenarioPath = scenarioPath;
meta.sourceBusPV = [18 33];
meta.pv18_hourly = pv18;
meta.pv33_hourly = pv33;
end

%% ========================================================================
function [windProfiles] = build_ddre33_day_wind_profiles_hetero(sourcePath, commBus, scenarioId)
% 从DDRE-33数据构建风电曲线

if nargin < 3 || isempty(scenarioId)
    scenarioId = 1;
end

sourcePath = char(sourcePath);
scenarioName = sprintf('scenario_%03d.csv', scenarioId);
scenarioPath = '';

if exist(sourcePath, 'dir') == 7
    candidate = fullfile(sourcePath, scenarioName);
    if exist(candidate, 'file') == 2
        scenarioPath = candidate;
    end
elseif exist(sourcePath, 'file') == 2
    [~,~,ext] = fileparts(sourcePath);
    if strcmpi(ext, '.zip')
        tmpBase = fullfile(tempdir, 'ddre33_1day_scenarios');
        if exist(fullfile(tmpBase, '1-Day Scenarios'), 'dir') ~= 7
            mkdir(tmpBase);
            unzip(sourcePath, tmpBase);
        end
        candidate1 = fullfile(tmpBase, '1-Day Scenarios', scenarioName);
        candidate2 = fullfile(tmpBase, scenarioName);
        if exist(candidate1, 'file') == 2
            scenarioPath = candidate1;
        elseif exist(candidate2, 'file') == 2
            scenarioPath = candidate2;
        end
    end
end

if isempty(scenarioPath)
    error('未找到DDRE-33场景文件: %s', scenarioName);
end

tbl = read_ddre33_scenario_table_hetero(scenarioPath);
req = {'node_22_wind','node_25_wind'};
for c = 1:numel(req)
    if ~any(strcmp(tbl.Properties.VariableNames, req{c}))
        error('缺少必需的DDRE-33风电列: %s', req{c});
    end
end

w22_15 = max(0, min(1, double(tbl.node_22_wind(:))));
w25_15 = max(0, min(1, double(tbl.node_25_wind(:))));
if numel(w22_15) ~= 96 || numel(w25_15) ~= 96
    error('DDRE-33 1天场景应有96个15分钟点。');
end

w22 = mean(reshape(w22_15, 4, 24), 1);
w25 = mean(reshape(w25_15, 4, 24), 1);
wAvg = 0.5 * (w22 + w25);

N = numel(commBus);
windProfiles = zeros(N, 24);
for i = 1:N
    if commBus(i) == 10
        windProfiles(i,:) = w22;
    elseif commBus(i) >= 28
        windProfiles(i,:) = w25;
    else
        windProfiles(i,:) = wAvg;
    end
end
end

%% ========================================================================
function filePath = resolve_local_file_hetero(fileName)
% 解析本地数据文件路径

if isstring(fileName), fileName = char(fileName); end
cand = cell(0,1);

cand{end+1} = fullfile(pwd, fileName);

thisFile = mfilename('fullpath');
if ~isempty(thisFile)
    thisDir = fileparts(thisFile);
    projectRoot = thisDir;
    cand{end+1} = fullfile(thisDir, fileName);
    cand{end+1} = fullfile(projectRoot, fileName);
    cand{end+1} = fullfile(projectRoot, 'alibaba', fileName);
    cand{end+1} = fullfile(projectRoot, '1-Day Scenarios', fileName);
end

cand{end+1} = fullfile('/mnt/data', fileName);
cand{end+1} = fullfile('/mnt/data', 'alibaba', fileName);
cand{end+1} = fullfile('/mnt/data', '1-Day Scenarios', fileName);

filePath = '';
for k = 1:numel(cand)
    if exist(cand{k}, 'file') == 2 || exist(cand{k}, 'dir') == 7
        filePath = cand{k};
        return;
    end
end

error('未找到所需的数据文件/文件夹: %s', fileName);
end

%% ========================================================================
function tbl = read_ddre33_scenario_table_hetero(scenarioPath)
% Read DDRE-33 scenario CSV without relying on datetime auto-detection.

try
    opts = detectImportOptions(scenarioPath, 'FileType', 'text');
    if any(strcmp(opts.VariableNames, 'timestamp'))
        opts = setvartype(opts, 'timestamp', 'char');
    end
    tbl = readtable(scenarioPath, opts);
catch
    fid = fopen(scenarioPath, 'r');
    if fid < 0
        error('Cannot open DDRE-33 scenario file: %s', scenarioPath);
    end
    cleanupObj = onCleanup(@() fclose(fid));
    raw = textscan(fid, '%f%s%f%f%f%f', ...
        'Delimiter', ',', ...
        'HeaderLines', 1, ...
        'Whitespace', '');
    if numel(raw) < 6 || isempty(raw{1})
        error('Cannot parse DDRE-33 scenario file: %s', scenarioPath);
    end
    tbl = table(raw{1}, raw{2}, raw{3}, raw{4}, raw{5}, raw{6}, ...
        'VariableNames', {'scenario_id','timestamp','node_22_wind','node_25_wind','node_18_PV','node_33_PV'});
end
end

%% ========================================================================
function [bus_has_comm, bus_to_comm, out_lines] = build_network_helpers_struct_hetero(B, branch, commBus, N)
% 构建网络辅助结构

L = size(branch,1);
bus_has_comm = false(B,1);
bus_to_comm = zeros(B,1);

for i = 1:N
    bus_has_comm(commBus(i)) = true;
    bus_to_comm(commBus(i)) = i;
end

out_lines = cell(B,1);
for l = 1:L
    from = branch(l,1);
    out_lines{from} = [out_lines{from}, l];
end
end
