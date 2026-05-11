function data = build_case(caseName, ddreScenarioId)
% BUILD_CASE 闆剁⒊鍥尯澶氳兘娴佺畻渚嬫瀯寤哄嚱鏁?% 杈撳叆: caseName - 绠椾緥鍚嶇О, ddreScenarioId - DDRE鍦烘櫙ID
% 杈撳嚭: data - 鍖呭惈绯荤粺鍙傛暟鐨勭粨鏋勪綋
% 鍔熻兘:
%   - 鍏変紡+椋庡姏鍙戠數
%   - 鍐风儹鐢典笁鑱斾緵(CHP)銆佺數閿呯倝
%   - 鐢佃В姘村埗姘?鐕冩枡鐢垫睜+鍌ㄦ阿绯荤粺
%   - 鐢?鐑?姘㈠偍鑳?%   - 鐢?鐑?姘㈣礋鑽?%   - IEEE33鑺傜偣杈愬皠鐘堕厤鐢电綉(DistFlow妯″瀷)

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
        error('鏈煡鐨勫紓鏋勭畻渚嬪悕绉? %s', caseName);
end
end

function data = build_ieee33_3comm_hetero_case(ddreScenarioId)
% 鏋勫缓IEEE33鑺傜偣涓夌ぞ鍖哄紓鏋勫浘

%% 鍩烘湰缁村害鍙傛暟
B = 33;
rootBus = 1;
T = 24;
dt = 1;           % 鏃堕棿姝ラ暱(灏忔椂)
N = 3;            % 绀惧尯鏁伴噺

%% IEEE33杈愬皠鐘堕厤鐢电綉(Baran-Wu)
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

%% IEEE33鏍囧噯璐熻嵎(MW/MVAr)
Pd_nom = [ ...
    0.000 0.100 0.090 0.120 0.060 0.060 0.200 0.200 0.060 0.060 0.045 ...
    0.060 0.060 0.120 0.060 0.060 0.060 0.090 0.090 0.090 0.090 0.090 ...
    0.090 0.420 0.420 0.060 0.060 0.060 0.120 0.200 0.150 0.210 0.060];

Qd_nom = [ ...
    0.000 0.060 0.040 0.080 0.030 0.020 0.100 0.100 0.020 0.020 0.030 ...
    0.035 0.035 0.080 0.010 0.020 0.020 0.040 0.040 0.040 0.040 0.040 ...
    0.050 0.200 0.200 0.025 0.025 0.020 0.070 0.600 0.070 0.100 0.040];

%% Community buses
commBus = [10; 18; 30];

%% 鐢典环鍜屽熀纭€璐熻嵎鏇茬嚎
ce_base = 1000 * [0.40 0.32 0.26 0.21 0.23 0.35 0.55 0.70 0.82 0.84 0.80 0.78 ...
           0.68 0.57 0.52 0.53 0.65 0.85 0.96 0.92 0.87 0.78 0.66 0.48];
shape_default = [0.56 0.54 0.53 0.52 0.54 0.62 0.73 0.83 0.90 0.94 0.96 0.97 ...
              0.98 0.97 0.96 0.96 0.98 1.00 0.98 0.93 0.86 0.78 0.69 0.61];

% 绀惧尯鐗瑰畾24灏忔椂璐熻嵎鏇茬嚎
% 绀惧尯1: 宸ヤ笟鍖?- 鐧藉ぉ鐢熶骇,璐熻嵎鏈€楂?% 绀惧尯2: 鍟嗕笟鍖?- 鍗堥鍜屾櫄椁愰珮宄?% 绀惧尯3: 浣忓畢鍖?- 鏃╅珮宄板拰鏅氶珮宄?
%% 璇诲彇DDRE鏁版嵁鏂囦欢
file_ddre_day = resolve_local_file_hetero('1-Day Scenarios');

%% 浠嶥DRE-33鑾峰彇鍏変紡鏇茬嚎
[ddrePpvPU, ddreMeta] = build_ddre33_day_pv_profiles_hetero(file_ddre_day, commBus, ddreScenarioId);

%% 浠嶥DRE-33鑾峰彇椋庣數鏇茬嚎
[ddrePwindPU] = build_ddre33_day_wind_profiles_hetero(file_ddre_day, commBus, ddreScenarioId);

%% Price, load, PV and wind
ce = zeros(N,T);
Ppv = zeros(N,T);
Pwind = zeros(N,T);
pvCap = [3.50; 4.00; 3.00];         % MW, 鍏変紡瑁呮満瀹归噺(宸紓鍖?
windCap = [0.00; 2.50; 0];       % MW, 椋庣數瑁呮満瀹归噺
PchMax  = [3.50; 3.20; 3.00];       % MW
PdisMax = [2.50; 2.20; 2.00];       % MW
Emax    = 3.0 * PdisMax;            % MWh
priceShift = [0; 0.000; 0];

% Build price and renewable profiles by community.
for i = 1:N
    ce(i,:) = max(250, ce_base + priceShift(i));
    Ppv(i,:)   = pvCap(i) * ddrePpvPU(i,:);
    Pwind(i,:) = windCap(i) * ddrePwindPU(i,:);
end

%% Carbon cost parameters
carbonShape = [0.92 0.91 0.90 0.90 0.91 0.95 1.02 1.08 1.12 1.15 1.17 1.16 ...
               1.13 1.10 1.08 1.10 1.16 1.22 1.24 1.18 1.08 1.00 0.96 0.93];
carbonShape = carbonShape / mean(carbonShape);
efGridBase = 0.4419 * 1000;              % kgCO2/MWh, 鐢电綉鎺掓斁鍥犲瓙
pCO2Base   = 62.36/1000;                  % yuan/kgCO2
efGrid = zeros(N,T);
pCO2   = zeros(N,T);
for i = 1:N
    locCarbonScale = 1.00 + 0.03*(i-2);
    efGrid(i,:) = efGridBase * locCarbonScale * carbonShape;
    pCO2(i,:)   = pCO2Base * ones(1,T);
end
cCarbon = efGrid .* pCO2;

%% 鐑數鑱斾緵(CHP)鍙傛暟 - 涓瓑鍥尯瑙勬ā
PchpRated = [1.20; 0.75; 0.60];      % MW
etaE_chp  = 0.35 * ones(N,1);
etaH_chp  = 0.45 * ones(N,1);
FgasMin   = zeros(N,1);
FgasMax   = PchpRated ./ etaE_chp;     % 鏈€澶х噧姘旇緭鍏?MW_th)
cGas      = (2.8 / 9.7) * 1000;       % 鍏?MWh_th (澶╃劧姘旂害2.8鍏?m3, LHV绾?.7 kWh/m3)
efGas     = 0.202 * 1000;             % kgCO2/MWh_th (IPCC澶╃劧姘旀帓鏀惧洜瀛?

% CHP澧炲己杩愯鍙傛暟(涓庡厓/MWh鐩爣鍑芥暟鏁板€煎悓姝?
uChp0       = zeros(N,1);
PchpMin     = 0.30 * PchpRated;
RampUpCHP   = 0.35 * PchpRated;
RampDnCHP   = 0.35 * PchpRated;        % MW/鏃舵
StartUpCHP  = 80  * ones(N,1);         % 鍏?娆? 鍚姩鎴愭湰
ShutDnCHP   = 20  * ones(N,1);         % 鍏?娆? 鍋滄満鎴愭湰
MinUpCHP    = 2   * ones(N,1);
MinDnCHP    = 2   * ones(N,1);
cOM_CHP     = 8   * ones(N,1);
cRampCHP    = 2   * ones(N,1);         % 鍏?MW-change, 鐖潯鎴愭湰
lambdaHdump = 200 * ones(N,1);         % 鍏?MWh_th, 浣欑儹鎯╃綒鎴愭湰

%% Electric boiler
PebMax = [2.50; 2.00; 1.50];           % MW
etaEb  = 0.97 * ones(N,1);              % 鏁堢巼
RampUpEb = 0.60 * PebMax;
RampDnEb = 0.60 * PebMax;
cRampEb = 1.0 * ones(N,1);


%% 鐢佃В姘村埗姘?PEM)
PelecMax = [1.00; 0.80; 1.20];         % MW
etaElec  = 20.0 * ones(N,1);           % kgH2/MWh (绾?0 kWh/kg, 鍏稿瀷PEM鐢佃В妲?
RampUpElec = 0.50 * PelecMax;
RampDnElec = 0.50 * PelecMax;
cRampElec = 3.0 * ones(N,1);

%% 鐕冩枡鐢垫睜(PEM)
H2fcMax  = [30.0; 25.0; 40.0];         % kg/h
etaFc    = 0.018 * ones(N,1);          % MW/(kg/h) = 18 kWh/kgH2
RampUpFc = 0.50 * etaFc .* H2fcMax;
RampDnFc = 0.50 * etaFc .* H2fcMax;
cRampFc = 3.0 * ones(N,1);

%% 鐢靛偍鑳?鐜版湁)
SOC0_e   = 0.50 * Emax;
etaCh_e  = 0.95 * ones(N,1);
etaDis_e = 0.95 * ones(N,1);

%% Thermal storage
HchMax   = [2.50; 2.00; 1.80];         % MW
HdisMax  = [2.50; 2.00; 1.80];         % MW
EthMax   = [10.0; 8.0; 6.0];           % MWh
SOC0_th  = 0.50 * EthMax;
etaCh_th = 0.95 * ones(N,1);
etaDis_th= 0.95 * ones(N,1);

%% 鍌ㄦ阿绯荤粺
H2chMax  = [30.0; 35.0; 40.0];         % kg/h
H2disMax = [30.0; 35.0; 40.0];         % kg/h
EH2Max   = [40.0; 100.0; 40.0];        % kg
SOC0_h2  = 0.50 * EH2Max;

%% 鍏稿瀷鏃ヨ礋鑽锋洸绾?% 绀惧尯绫诲瀷:
%   1) 浣忓畢鍖?%   2) 宸ヤ笟鍖?%   3) 鍟嗕笟鍖?% 鍋囪: 鍐渚涙殩瀛?
% 鍥哄畾鐢佃礋鑽?MW)
Pload = [ ...
    0.22 0.20 0.28 0.27 0.29 0.38 0.40 0.42 0.50 0.54 0.60 0.58 ...
    0.56 0.55 0.56 0.60 0.68 0.78 0.86 0.92 0.78 0.76 0.42 0.30;   % 绀惧尯1: 浣忓畢鍖?
    0.85 0.82 0.80 0.79 0.82 0.92 1.10 1.32 1.48 1.60 1.68 1.72 ...
    1.74 1.74 1.72 1.70 1.68 1.65 1.58 1.50 1.38 1.22 1.05 0.95;   % 绀惧尯2: 宸ヤ笟鍖?
    0.30 0.28 0.27 0.26 0.28 0.35 0.50 0.82 0.83 0.85 0.98 0.99 ...
    0.96 1.00 0.82 0.78 0.88 0.90 1.12 1.10 0.98 0.86 0.72 0.64];  % 绀惧尯3: 鍟嗕笟鍖?
% Keep the base electric load synchronized.
Pbase = Pload;

% 鏍规嵁鍔熺巼鍥犳暟閲嶆瀯鏃犲姛璐熻嵎
% 浣忓畢鍖? 杈冮珮鍔熺巼鍥犳暟
% 宸ヤ笟鍖? 鍥犵數鏈鸿澶囧姛鐜囧洜鏁拌緝浣?% 鍟嗕笟鍖? 涓珮鍔熺巼鍥犳暟
pfComm = [0.98; 0.93; 0.96];
Qbase = zeros(N,T);
for i = 1:N
    Qbase(i,:) = Pbase(i,:) * tan(acos(pfComm(i)));
end

% 鍥哄畾鐑礋鑽?MW)
Hload = [ ...
   0.625 0.610 0.600 0.590 0.610 0.690 0.780 0.860 0.830 0.750 0.680 0.640 ...
   0.610 0.600 0.610 0.640 0.700 0.790 0.870 0.930 0.950 0.890 0.790 0.690;   % 绀惧尯1: 浣忓畢鍖?
    1.45 1.42 1.40 1.40 1.42 1.48 1.58 1.68 1.76 1.82 1.86 1.88 ...
    1.88 1.86 1.84 1.82 1.80 1.76 1.70 1.62 1.56 1.52 1.48 1.46;   % 绀惧尯2: 宸ヤ笟鍖?
    0.210 0.200 0.190 0.190 0.200 0.240 0.325 0.475 0.640 0.790 0.890 0.950 ...
    0.980 1.000 1.010 0.990 0.940 0.840 0.700 0.550 0.410 0.310 0.250 0.230];  % 绀惧尯3: 鍟嗕笟鍖?
% Hydrogen load: community 2 is the reference; communities 1 and 3 are smaller.
h2Base = [4 4 8 8 9 10 12 14 16 18 20 20 20 20 19 19 18 17 16 14 12 10 9 8];
H2load = zeros(N,T);
H2load(1,:) = 0.35 * h2Base;
H2load(2,:) = h2Base;
H2load(3,:) = 0.55 * h2Base;
if any(H2load(1,:) > H2load(2,:)) || any(H2load(3,:) > H2load(2,:))
    error('Hydrogen load of communities 1 and 3 must not exceed community 2.');
end

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

%% Distribution network operating parameters
Vmin = 0.95 * ones(B,1);
Vmax = 1.05 * ones(B,1);
Vslack = 1.05;
PsubMax = 20.0 * ones(1,T);            % MW, 涓瓑鍥尯瑙勬ā
PijMax  = 12.0 * ones(L,1);            % MW
QijMax  = 8.0 * ones(L,1);             % MVAr
PijMax(1:4)   = 12.0;  QijMax(1:4)   = 8.0;
PijMax(5:17)  = 8.0;   QijMax(5:17)  = 5.5;
PijMax(18:21) = 6.0;   QijMax(18:21) = 4.0;
PijMax(22:24) = 6.0;   QijMax(22:24) = 4.0;
PijMax(25:27) = 5.5;   QijMax(25:27) = 3.5;
PijMax(28:32) = 4.0;   QijMax(28:32) = 2.5;

%% Background distribution network load
PbusBase = zeros(B,T);
QbusBase = zeros(B,T);
for bidx = 2:B
    if ~ismember(bidx, commBus)
        PbusBase(bidx,:) = Pd_nom(bidx) * shape_default;
        QbusBase(bidx,:) = Qd_nom(bidx) * shape_default;
    end
end

%% 鎯╃綒绯绘暟
lambdaPVCurt  = 230 * ones(N,1);        % 鍏?MWh
lambdaWindCurt= 200 * ones(N,1);       % 鍏?MWh
lambdaH2Short = 300 * ones(N,1);      % 鍏?kg
lambdaQpv     = 5.0 * ones(N,1);      % 鍏?(MVAr^2*h)
lambdaQes     = 5.0 * ones(N,1);      % 鍏?(MVAr^2*h)

QcompCoeff = [0.032; 0.033; 0.032];
alphaCompH2 = 0.002 * ones(N,1);       % MW/(kg/h), hydrogen compressor power
QpvMax     = 1.05 * pvCap(:) + 0.08;
QesMax     = 1.10 * PdisMax(:) + 0.08;
PcompFixed = zeros(N,T);         
PcompMax   = max(PcompFixed,[],2) + alphaCompH2(:) .* etaElec(:) .* PelecMax(:);
RampUpComp = 0.60 * PcompMax;
RampDnComp = 0.60 * PcompMax;
cRampComp = 1.0 * ones(N,1);
QinjMax    = max(Qbase,[],2) + QcompCoeff(:).*PcompMax + 0.05;
QinjMin    = min(Qbase,[],2) - QpvMax(:) - QesMax(:) - 0.05;

%% 鎷撴墤杈呭姪缁撴瀯
[bus_has_comm, bus_to_comm, out_lines] = build_network_helpers_struct_hetero(B, branch, commBus, N);

%% 灏佽鍙傛暟
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

% Multi-energy equipment
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
data.RampUpEb = RampUpEb(:);
data.RampDnEb = RampDnEb(:);
data.cRampEb = cRampEb(:);

data.PelecMax = PelecMax(:);
data.etaElec = etaElec(:);
data.RampUpElec = RampUpElec(:);
data.RampDnElec = RampDnElec(:);
data.cRampElec = cRampElec(:);

data.H2fcMax = H2fcMax(:);
data.etaFc = etaFc(:);
data.RampUpFc = RampUpFc(:);
data.RampDnFc = RampDnFc(:);
data.cRampFc = cRampFc(:);

% Electrical storage
data.PchMax = PchMax(:);
data.PdisMax = PdisMax(:);
data.Emax = Emax(:);
data.SOC0_e = SOC0_e(:);
data.etaCh_e = etaCh_e(:);
data.etaDis_e = etaDis_e(:);

% Thermal storage
data.HchMax = HchMax(:);
data.HdisMax = HdisMax(:);
data.EthMax = EthMax(:);
data.SOC0_th = SOC0_th(:);
data.etaCh_th = etaCh_th(:);
data.etaDis_th = etaDis_th(:);

% 鍌ㄦ阿
data.H2chMax = H2chMax(:);
data.H2disMax = H2disMax(:);
data.EH2Max = EH2Max(:);
data.SOC0_h2 = SOC0_h2(:);

% 璐熻嵎
data.Pload = Pload;
data.Hload = Hload;
data.H2load = H2load;

data.PcompFixed = PcompFixed;
data.alphaCompH2 = alphaCompH2(:);
data.PcompMax = PcompMax(:);
data.RampUpComp = RampUpComp(:);
data.RampDnComp = RampDnComp(:);
data.cRampComp = cRampComp(:);
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

% 鍛ㄦ湡鏈鐘舵€佺洰鏍?鏃ュ墠璋冨害)
data.termSOC_e  = data.SOC0_e;
data.termSOC_th = data.SOC0_th;
data.termSOC_h2 = data.SOC0_h2;
data.bus_has_comm = bus_has_comm;
data.bus_to_comm = bus_to_comm;
data.out_lines = out_lines;

% Metadata
data.ieee33_Pd_nom = Pd_nom(:);
data.ieee33_Qd_nom = Qd_nom(:);
data.solarSourceFile = file_ddre_day;
data.ddreMeta = ddreMeta;
data.ddreScenarioId = ddreScenarioId;
data.carbonModelNotes = {'鐢电綉璐數鍜岀噧姘旀秷鑰楃殑绾挎€ф椂鍙樼⒊鎴愭湰'};
end

%% ========================================================================
function [pvProfiles, meta] = build_ddre33_day_pv_profiles_hetero(sourcePath, commBus, scenarioId)
% 浠嶥DRE-33鏁版嵁鏋勫缓鍏変紡鏇茬嚎

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
    error('鏈壘鍒癉DRE-33鍦烘櫙鏂囦欢: %s', scenarioName);
end

tbl = read_ddre33_scenario_table_hetero(scenarioPath);
req = {'node_18_PV','node_33_PV'};
for c = 1:numel(req)
    if ~any(strcmp(tbl.Properties.VariableNames, req{c}))
        error('缂哄皯蹇呴渶鐨凞DRE-33 PV鍒? %s', req{c});
    end
end

pv18_15 = max(0, min(1, double(tbl.node_18_PV(:))));
pv33_15 = max(0, min(1, double(tbl.node_33_PV(:))));
if numel(pv18_15) ~= 96 || numel(pv33_15) ~= 96
    error('DDRE-33 1-day scenario should contain 96 quarter-hour points.');
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
% 浠嶥DRE-33鏁版嵁鏋勫缓椋庣數鏇茬嚎

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
    error('鏈壘鍒癉DRE-33鍦烘櫙鏂囦欢: %s', scenarioName);
end

tbl = read_ddre33_scenario_table_hetero(scenarioPath);
req = {'node_22_wind','node_25_wind'};
for c = 1:numel(req)
    if ~any(strcmp(tbl.Properties.VariableNames, req{c}))
        error('缂哄皯蹇呴渶鐨凞DRE-33椋庣數鍒? %s', req{c});
    end
end

w22_15 = max(0, min(1, double(tbl.node_22_wind(:))));
w25_15 = max(0, min(1, double(tbl.node_25_wind(:))));
if numel(w22_15) ~= 96 || numel(w25_15) ~= 96
    error('DDRE-33 1-day scenario should contain 96 quarter-hour points.');
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
% 瑙ｆ瀽鏈湴鏁版嵁鏂囦欢璺緞

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

error('鏈壘鍒版墍闇€鐨勬暟鎹枃浠?鏂囦欢澶? %s', fileName);
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
% 鏋勫缓缃戠粶杈呭姪缁撴瀯

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
