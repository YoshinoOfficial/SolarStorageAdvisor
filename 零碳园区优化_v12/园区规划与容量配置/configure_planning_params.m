function plan = configure_planning_params(data0)
%CONFIGURE_PLANNING_PARAMS Capacity-planning parameters for first-version model.
% 第一版园区规划参数：固定储能时长 + 年化投资成本 + 年碳排放联合目标。
%
% 输入：
%   data0 - build_case 生成的基础数据，用于读取社区数量和默认容量。
% 输出：
%   plan  - 规划参数结构体。
%
% 重要说明：
%   1) 投资成本已按 CRF 折算为年化成本，目标函数单位为 yuan/year；
%   2) lambdaCO2 的单位为 yuan/tCO2，用于经济性-低碳性的加权单目标；
%   3) 第一版只规划 PV、风机、电储能、热储能、储氢容量；CHP、电锅炉、
%      电解槽、燃料电池容量保持原有固定参数。

if nargin < 1 || isempty(data0)
    data0 = build_case('ieee33_3comm_hetero_real', 1);
end

N = data0.N;

%% Financial parameters
plan.discountRate = 0.06;      % 折现率
plan.currency = 'yuan';

% 设备寿命 / 年
plan.lifePV   = 25;
plan.lifeWind = 20;
plan.lifeBat  = 12;
plan.lifeTh   = 15;
plan.lifeH2   = 20;

% 单位投资成本。
% 单位：PV/风电 yuan/MW；电/热储能 yuan/MWh；储氢 yuan/kg-H2。
% 这些数值用于先跑通模型，后续建议根据论文或工程造价统一修正。
plan.capexPV_yuan_per_MW      = 3.20e6;
plan.capexWind_yuan_per_MW    = 5.80e6;
plan.capexBat_yuan_per_MWh    = 0.80e6;
plan.capexTh_yuan_per_MWh     = 2.50e5;
plan.capexH2_yuan_per_kg      = 2.80e3;

% 固定运维成本：按投资额比例折算为 yuan/year。
plan.fixOMRatePV   = 0.015;
plan.fixOMRateWind = 0.025;
plan.fixOMRateBat  = 0.020;
plan.fixOMRateTh   = 0.015;
plan.fixOMRateH2   = 0.020;

% 可变运维成本。第一版默认较小，避免掩盖容量规划主逻辑。
plan.varOMPV_yuan_per_MWh      = 8;
plan.varOMWind_yuan_per_MWh    = 12;
plan.varOMBat_yuan_per_MWh     = 6;     % 按充放电吞吐量计
plan.varOMTh_yuan_per_MWh      = 3;
plan.varOMH2_yuan_per_kg       = 0.5;

%% Storage duration and SOC ratios
% 固定储能时长：功率容量 = 能量容量 / tau。
plan.tauE_h   = 4.0;     % 电储能 4h
plan.tauTh_h  = 4.0;     % 热储能 4h
plan.tauH2_h  = 8.0;     % 储氢等效 8h，单位 kg/(kg/h)

plan.socMin = 0.10;
plan.socMax = 0.90;
plan.socInitRatio = 0.50;
plan.socTerminalRatio = 0.50;

%% Renewable and inverter reactive capability
plan.kappaPVInv   = 1.05;   % PV 逆变器容量裕度：S_pv = kappa*Kpv
plan.kappaWindInv = 1.05;   % 风机变流器容量裕度
plan.kappaESInv   = 1.10;   % 储能 PCS 容量裕度：S_es = kappa*(E/tau)

%% Capacity bounds
% 第一版建议不要把上限设得过大，否则模型可能用过量新能源挤压购电，
% 但工程可解释性变差。这里按当前三社区规模给一个中等上限。
plan.KpvExisting_MW   = get_field_vec(data0, 'pvCap0', zeros(N,1));
plan.KwindExisting_MW = get_field_vec(data0, 'windCap0', zeros(N,1));
plan.EbatExisting_MWh = get_field_vec(data0, 'Emax', zeros(N,1));
plan.EthExisting_MWh  = get_field_vec(data0, 'EthMax', zeros(N,1));
plan.EH2Existing_kg   = get_field_vec(data0, 'EH2Max', zeros(N,1));
plan.fixRenewableCapacity = true;

plan.KpvMin_MW    = zeros(N,1);
plan.KwindMin_MW  = zeros(N,1);
plan.EbatMin_MWh  = get_field_vec(data0, 'Emax', zeros(N,1));
plan.EthMin_MWh   = zeros(N,1);
plan.EH2Min_kg    = zeros(N,1);

plan.KpvMax_MW    = max([6.0; 7.0; 6.0], 2.5 * get_field_vec(data0, 'pvCap0', ones(N,1)));
plan.KwindMax_MW  = [3.0; 4.0; 3.0];
plan.EbatMax_MWh  = [10.0; 14.0; 10.0];
plan.EthMax_MWh   = [18.0; 18.0; 15.0];
plan.EH2Max_kg    = [220.0; 320.0; 240.0];

% 可选：给部分社区禁建风电时，把对应上限改成 0。
% plan.KwindMax_MW([1 3]) = 0;

%% Carbon objective and carbon trading switch
% lambdaCO2 越大，模型越偏向低碳容量配置。
% 单位：yuan/tCO2。建议后续做 0/100/300/500/800 灵敏度。
plan.lambdaCO2_yuan_per_tCO2 = 300;

% 第一版建议不把碳交易成本纳入目标，只将实际碳排放作为联合目标。
% 若设为 true，则模型会额外加入基准配额下的买/卖碳成本，可能与
% lambdaCO2 出现“双重碳成本”，论文中需要解释。
plan.includeCarbonTradingCost = false;
plan.allowCarbonMarketSell = false;
plan.carbonBuyPrice = 150;
plan.carbonSellPrice = 100;

%% Solver/display
plan.verbose = 1;
plan.saveDispatchDetails = true;

end

function v = get_field_vec(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    tmp = s.(name);
    v = tmp(:);
else
    v = defaultVal(:);
end
end
