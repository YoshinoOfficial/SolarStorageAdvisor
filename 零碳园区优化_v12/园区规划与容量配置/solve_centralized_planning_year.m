function res = solve_centralized_planning_year(dataSet, plan)
%SOLVE_CENTRALIZED_PLANNING_YEAR Centralized annual planning model.
% 年尺度“容量-运行”联合优化：
%   - 规划变量：光伏容量、风机容量、电储能容量、热储能容量、储氢容量；
%   - 运行变量：每个典型日单独建立电-热-氢调度变量；
%   - 目标函数：年化投资成本 + 年固定/可变运维成本 + 代表日加权运行成本
%               + lambdaCO2 * 年碳排放量。
%
% 第一版建模约定：
%   1) 储能时长固定：Pmax = Emax / tau；
%   2) 电/热/氢储能采用日内循环 SOC；
%   3) 新能源容量和无功/视在容量同步变化；
%   4) 不加入新能源选址二进制变量；
%   5) CHP、电锅炉、电解槽、燃料电池容量沿用原数据，不做规划。

if nargin < 1 || isempty(dataSet)
    error('dataSet cannot be empty. Use build_planning_dataset first.');
end
if nargin < 2 || isempty(plan)
    plan = configure_planning_params(dataSet{1});
end

yalmip('clear');

S = numel(dataSet);
data0 = dataSet{1};
N = data0.N; T = data0.T; B = data0.B; L = data0.L; dt = data0.dt;

%% Shared capacity planning variables
KpvExisting   = i_get_vec(plan, 'KpvExisting_MW',   zeros(N,1), N);
KwindExisting = i_get_vec(plan, 'KwindExisting_MW', zeros(N,1), N);
EbatExisting  = i_get_vec(plan, 'EbatExisting_MWh', zeros(N,1), N);
EthExisting   = i_get_vec(plan, 'EthExisting_MWh',  zeros(N,1), N);
EH2Existing   = i_get_vec(plan, 'EH2Existing_kg',   zeros(N,1), N);

if isfield(plan, 'fixRenewableCapacity') && plan.fixRenewableCapacity
    KpvNew = zeros(N,1);      % MW
    KwindNew = zeros(N,1);    % MW
else
    KpvNew = sdpvar(N,1);     % MW
    KwindNew = sdpvar(N,1);   % MW
end
EbatNew  = sdpvar(N,1);   % MWh
EthNew   = sdpvar(N,1);   % MWh_th
EH2New   = sdpvar(N,1);   % kg-H2

Kpv   = KpvExisting   + KpvNew;
Kwind = KwindExisting + KwindNew;
Ebat  = EbatExisting  + EbatNew;
Eth   = EthExisting   + EthNew;
EH2   = EH2Existing   + EH2New;

PbatCap = Ebat / plan.tauE_h;
HthCap  = Eth  / plan.tauTh_h;
H2Cap   = EH2  / plan.tauH2_h;
QesCap  = plan.kappaESInv * PbatCap;

F = [];
if ~(isfield(plan, 'fixRenewableCapacity') && plan.fixRenewableCapacity)
    F = [F, max(0, plan.KpvMin_MW(:)   - KpvExisting)   <= KpvNew,   KpvNew   <= max(0, plan.KpvMax_MW(:)   - KpvExisting)];
    F = [F, max(0, plan.KwindMin_MW(:) - KwindExisting) <= KwindNew, KwindNew <= max(0, plan.KwindMax_MW(:) - KwindExisting)];
end
F = [F, max(0, plan.EbatMin_MWh(:) - EbatExisting)  <= EbatNew,  EbatNew  <= max(0, plan.EbatMax_MWh(:) - EbatExisting)];
F = [F, max(0, plan.EthMin_MWh(:)  - EthExisting)   <= EthNew,   EthNew   <= max(0, plan.EthMax_MWh(:)  - EthExisting)];
F = [F, max(0, plan.EH2Min_kg(:)   - EH2Existing)   <= EH2New,   EH2New   <= max(0, plan.EH2Max_kg(:)   - EH2Existing)];

%% Annualized capacity costs
crfPV   = i_crf(plan.discountRate, plan.lifePV);
crfWind = i_crf(plan.discountRate, plan.lifeWind);
crfBat  = i_crf(plan.discountRate, plan.lifeBat);
crfTh   = i_crf(plan.discountRate, plan.lifeTh);
crfH2   = i_crf(plan.discountRate, plan.lifeH2);

invPV   = plan.capexPV_yuan_per_MW   * sum(KpvNew)   * crfPV;
invWind = plan.capexWind_yuan_per_MW * sum(KwindNew) * crfWind;
invBat  = plan.capexBat_yuan_per_MWh * sum(EbatNew)  * crfBat;
invTh   = plan.capexTh_yuan_per_MWh  * sum(EthNew)   * crfTh;
invH2   = plan.capexH2_yuan_per_kg   * sum(EH2New)   * crfH2;

fixOMPV   = plan.fixOMRatePV   * plan.capexPV_yuan_per_MW   * sum(Kpv);
fixOMWind = plan.fixOMRateWind * plan.capexWind_yuan_per_MW * sum(Kwind);
fixOMBat  = plan.fixOMRateBat  * plan.capexBat_yuan_per_MWh * sum(Ebat);
fixOMTh   = plan.fixOMRateTh   * plan.capexTh_yuan_per_MWh  * sum(Eth);
fixOMH2   = plan.fixOMRateH2   * plan.capexH2_yuan_per_kg   * sum(EH2);

annualInvestmentCost = invPV + invWind + invBat + invTh + invH2;
annualFixedOMCost    = fixOMPV + fixOMWind + fixOMBat + fixOMTh + fixOMH2;

%% Per-scenario operation variables and costs
op = cell(S,1);
annualOperationCost = 0;
annualCarbonEmission_tCO2 = 0;
annualCarbonTradingCost = 0;
annualRenewableAvailable_MWh = 0;
annualRenewableUse_MWh = 0;
annualRenewableCurt_MWh = 0;

for s = 1:S
    data = dataSet{s};
    days = data.representativeDays;

    % ===== Scenario-specific compatible parameters =====
    uChp0 = i_get_field(data, 'uChp0', zeros(N,1));
    PchpMin = i_get_field(data, 'PchpMin', 0.35 * data.PchpRated(:));
    FgasMinBase = i_get_field(data, 'FgasMin', zeros(N,1));
    FgasMinEff  = max(FgasMinBase(:), PchpMin(:) ./ max(data.etaE_chp(:), 1e-6));
    RampUpCHP = i_get_field(data, 'RampUpCHP', 0.30 * data.PchpRated(:));
    RampDnCHP = i_get_field(data, 'RampDnCHP', 0.30 * data.PchpRated(:));
    StartUpCHP = i_get_field(data, 'StartUpCHP', 80 * ones(N,1));
    ShutDnCHP  = i_get_field(data, 'ShutDnCHP', 20 * ones(N,1));
    MinUpCHP   = round(i_get_field(data, 'MinUpCHP', 2 * ones(N,1)));
    MinDnCHP   = round(i_get_field(data, 'MinDnCHP', 2 * ones(N,1)));
    cOM_CHP    = i_get_field(data, 'cOM_CHP', 8 * ones(N,1));
    cRampCHP   = i_get_field(data, 'cRampCHP', 2 * ones(N,1));
    lambdaHdump = i_get_field(data, 'lambdaHdump', 200 * ones(N,1));
    minChpHeatShare = i_get_field(data, 'minChpHeatShare', 0);

    RampUpEb = i_get_field(data, 'RampUpEb', data.PebMax(:));
    RampDnEb = i_get_field(data, 'RampDnEb', data.PebMax(:));
    cRampEb = i_get_field(data, 'cRampEb', zeros(N,1));
    RampUpElec = i_get_field(data, 'RampUpElec', data.PelecMax(:));
    RampDnElec = i_get_field(data, 'RampDnElec', data.PelecMax(:));
    cRampElec = i_get_field(data, 'cRampElec', zeros(N,1));
    RampUpFc = i_get_field(data, 'RampUpFc', data.etaFc(:).*data.H2fcMax(:));
    RampDnFc = i_get_field(data, 'RampDnFc', data.etaFc(:).*data.H2fcMax(:));
    cRampFc = i_get_field(data, 'cRampFc', zeros(N,1));
    alphaCompH2 = i_get_field(data, 'alphaCompH2', zeros(N,1));
    PcompMax = i_get_field(data, 'PcompMax', max(data.PcompFixed,[],2) + alphaCompH2(:).*data.etaElec(:).*data.PelecMax(:));
    RampUpComp = i_get_field(data, 'RampUpComp', PcompMax(:));
    RampDnComp = i_get_field(data, 'RampDnComp', PcompMax(:));
    cRampComp = i_get_field(data, 'cRampComp', zeros(N,1));

    PloadFixed = i_get_field(data, 'PloadFixed', data.Pload);
    PdrShiftBase = i_get_field(data, 'PdrShiftBase', zeros(N,T));
    PdrShiftMax = i_get_field(data, 'PdrShiftMax', PdrShiftBase);
    PdrCutEmax = i_get_field(data, 'PdrCutEmax', zeros(N,T));
    HdrCutMax = i_get_field(data, 'HdrCutMax', zeros(N,T));
    H2drCutMax = i_get_field(data, 'H2drCutMax', zeros(N,T));
    pfTan = i_get_field(data, 'pfTan', data.Qbase ./ max(data.Pbase, 1e-6));
    cDRShiftE = i_get_field(data, 'cDRShiftE', zeros(N,1));
    cDRCutE = i_get_field(data, 'cDRCutE', zeros(N,1));
    cDRCutH = i_get_field(data, 'cDRCutH', zeros(N,1));
    cDRCutH2 = i_get_field(data, 'cDRCutH2', zeros(N,1));

    zetaE = i_get_field(data, 'zetaE', 1080);
    zetaH = i_get_field(data, 'zetaH', 324);
    chiE  = i_get_field(data, 'chiE', 728);
    chiH  = i_get_field(data, 'chiH', 367.2);
    ceh   = i_get_field(data, 'ceh', 1.6667);

    % ===== Decision variables =====
    Pgrid = sdpvar(N,T,'full');
    Pch   = sdpvar(N,T,'full');
    Pdis  = sdpvar(N,T,'full');
    SOC_e = sdpvar(N,T,'full');
    PpvUse = sdpvar(N,T,'full');
    PpvCurt = sdpvar(N,T,'full');
    PwindUse = sdpvar(N,T,'full');
    PwindCurt = sdpvar(N,T,'full');

    Fgas = sdpvar(N,T,'full');
    Pchp = sdpvar(N,T,'full');
    Hchp = sdpvar(N,T,'full');
    uChp = binvar(N,T,'full');
    vStart = binvar(N,T,'full');
    vStop  = binvar(N,T,'full');
    RupChp = sdpvar(N,T,'full');
    RdnChp = sdpvar(N,T,'full');
    Hdump  = sdpvar(N,T,'full');

    Peb = sdpvar(N,T,'full');
    Heb = sdpvar(N,T,'full');
    RupEb = sdpvar(N,T,'full');
    RdnEb = sdpvar(N,T,'full');

    Pelec = sdpvar(N,T,'full');
    H2prod = sdpvar(N,T,'full');
    RupElec = sdpvar(N,T,'full');
    RdnElec = sdpvar(N,T,'full');

    H2cons_fc = sdpvar(N,T,'full');
    Pfc = sdpvar(N,T,'full');
    RupFc = sdpvar(N,T,'full');
    RdnFc = sdpvar(N,T,'full');

    Pcomp = sdpvar(N,T,'full');
    RupComp = sdpvar(N,T,'full');
    RdnComp = sdpvar(N,T,'full');

    Hch = sdpvar(N,T,'full');
    Hdis = sdpvar(N,T,'full');
    SOC_th = sdpvar(N,T,'full');

    H2ch = sdpvar(N,T,'full');
    H2dis = sdpvar(N,T,'full');
    SOC_h2 = sdpvar(N,T,'full');
    H2short = sdpvar(N,T,'full');

    PdrShift = sdpvar(N,T,'full');
    PdrShiftDev = sdpvar(N,T,'full');
    PdrCutE = sdpvar(N,T,'full');
    HdrCut = sdpvar(N,T,'full');
    H2drCut = sdpvar(N,T,'full');

    Qpv = sdpvar(N,T,'full');
    Qwind = sdpvar(N,T,'full');
    Qes = sdpvar(N,T,'full');
    Pinj = sdpvar(N,T,'full');
    Qinj = sdpvar(N,T,'full');
    Pij = sdpvar(L,T,'full');
    Qij = sdpvar(L,T,'full');
    V   = sdpvar(B,T,'full');

    % Optional simplified carbon-trading variables.
    if plan.includeCarbonTradingCost
        QaBuy = sdpvar(N,T,'full');
        QaSell = sdpvar(N,T,'full');
        F = [F, QaBuy >= 0, QaSell >= 0];
        if ~plan.allowCarbonMarketSell
            F = [F, QaSell == 0];
        end
    else
        QaBuy = [];
        QaSell = [];
    end

    % ===== Basic bounds =====
    F = [F, Pgrid >= 0, Pgrid <= repmat(data.PgridMax(:),1,T)];
    F = [F, Pch >= 0, Pdis >= 0, SOC_e >= plan.socMin*repmat(Ebat,1,T), SOC_e <= plan.socMax*repmat(Ebat,1,T)];
    F = [F, Pch <= repmat(PbatCap,1,T), Pdis <= repmat(PbatCap,1,T)];
    F = [F, PpvUse >= 0, PpvCurt >= 0, PwindUse >= 0, PwindCurt >= 0];
    F = [F, V >= repmat(data.Vmin.^2,1,T), V <= repmat(data.Vmax.^2,1,T)];

    F = [F, Fgas >= 0, Fgas <= repmat(data.FgasMax(:),1,T).*uChp];
    F = [F, Fgas >= repmat(FgasMinEff(:),1,T).*uChp];
    F = [F, 0 <= uChp, uChp <= 1, 0 <= vStart, vStart <= 1, 0 <= vStop, vStop <= 1];
    F = [F, vStart + vStop <= 1, RupChp >= 0, RdnChp >= 0, Hdump >= 0];
    F = [F, Pchp == repmat(data.etaE_chp(:),1,T).*Fgas];
    F = [F, Hchp == repmat(data.etaH_chp(:),1,T).*Fgas];
    F = [F, Pchp <= repmat(data.PchpRated(:),1,T).*uChp];
    F = [F, Pchp >= repmat(PchpMin(:),1,T).*uChp];

    F = [F, Peb >= 0, Peb <= repmat(data.PebMax(:),1,T), RupEb >= 0, RdnEb >= 0];
    F = [F, Heb == repmat(data.etaEb(:),1,T).*Peb];

    F = [F, Pelec >= 0, Pelec <= repmat(data.PelecMax(:),1,T), RupElec >= 0, RdnElec >= 0];
    F = [F, H2prod == repmat(data.etaElec(:),1,T).*Pelec];

    F = [F, H2cons_fc >= 0, H2cons_fc <= repmat(data.H2fcMax(:),1,T), RupFc >= 0, RdnFc >= 0];
    F = [F, Pfc == repmat(data.etaFc(:),1,T).*H2cons_fc];

    F = [F, Pcomp == data.PcompFixed + repmat(alphaCompH2(:),1,T).*H2prod];
    F = [F, Pcomp >= 0, Pcomp <= repmat(PcompMax(:),1,T), RupComp >= 0, RdnComp >= 0];

    F = [F, Hch >= 0, Hdis >= 0, SOC_th >= plan.socMin*repmat(Eth,1,T), SOC_th <= plan.socMax*repmat(Eth,1,T)];
    F = [F, Hch <= repmat(HthCap,1,T), Hdis <= repmat(HthCap,1,T)];

    F = [F, H2ch >= 0, H2dis >= 0, SOC_h2 >= plan.socMin*repmat(EH2,1,T), SOC_h2 <= plan.socMax*repmat(EH2,1,T)];
    F = [F, H2ch <= repmat(H2Cap,1,T), H2dis <= repmat(H2Cap,1,T)];

    F = [F, H2short >= 0, H2short <= data.H2load];

    F = [F, PdrShift >= 0, PdrShift <= PdrShiftMax];
    F = [F, PdrShiftDev >= 0, PdrShiftDev >= PdrShift - PdrShiftBase, PdrShiftDev >= PdrShiftBase - PdrShift];
    F = [F, PdrCutE >= 0, PdrCutE <= PdrCutEmax];
    F = [F, HdrCut >= 0, HdrCut <= HdrCutMax];
    F = [F, H2drCut >= 0, H2drCut <= H2drCutMax];

    % ===== Dynamics, balances, and conic apparent-power constraints =====
    dailyOpCost = 0;
    dailyEmission_kg = 0;
    dailyTradingCost = 0;
    dailyRenAvail = 0;
    dailyRenUse = 0;
    dailyRenCurt = 0;

    pvPU = data.pvProfilePU;
    windPU = data.windProfilePU;

    for i = 1:N
        for t = 1:T
            if t == 1
                F = [F, uChp(i,t) - uChp0(i) == vStart(i,t) - vStop(i,t)];
                F = [F, SOC_e(i,t) == plan.socInitRatio*Ebat(i) + data.etaCh_e(i)*Pch(i,t)*dt - (1/data.etaDis_e(i))*Pdis(i,t)*dt];
                F = [F, SOC_th(i,t) == plan.socInitRatio*Eth(i) + data.etaCh_th(i)*Hch(i,t)*dt - (1/data.etaDis_th(i))*Hdis(i,t)*dt];
                F = [F, SOC_h2(i,t) == plan.socInitRatio*EH2(i) + (H2ch(i,t) - H2dis(i,t))*dt];
            else
                F = [F, uChp(i,t) - uChp(i,t-1) == vStart(i,t) - vStop(i,t)];
                F = [F, Pchp(i,t) - Pchp(i,t-1) <= RampUpCHP(i), Pchp(i,t-1) - Pchp(i,t) <= RampDnCHP(i)];
                F = [F, RupChp(i,t) >= Pchp(i,t) - Pchp(i,t-1), RdnChp(i,t) >= Pchp(i,t-1) - Pchp(i,t)];
                F = [F, Peb(i,t) - Peb(i,t-1) <= RampUpEb(i), Peb(i,t-1) - Peb(i,t) <= RampDnEb(i)];
                F = [F, RupEb(i,t) >= Peb(i,t) - Peb(i,t-1), RdnEb(i,t) >= Peb(i,t-1) - Peb(i,t)];
                F = [F, Pelec(i,t) - Pelec(i,t-1) <= RampUpElec(i), Pelec(i,t-1) - Pelec(i,t) <= RampDnElec(i)];
                F = [F, RupElec(i,t) >= Pelec(i,t) - Pelec(i,t-1), RdnElec(i,t) >= Pelec(i,t-1) - Pelec(i,t)];
                F = [F, Pfc(i,t) - Pfc(i,t-1) <= RampUpFc(i), Pfc(i,t-1) - Pfc(i,t) <= RampDnFc(i)];
                F = [F, RupFc(i,t) >= Pfc(i,t) - Pfc(i,t-1), RdnFc(i,t) >= Pfc(i,t-1) - Pfc(i,t)];
                F = [F, Pcomp(i,t) - Pcomp(i,t-1) <= RampUpComp(i), Pcomp(i,t-1) - Pcomp(i,t) <= RampDnComp(i)];
                F = [F, RupComp(i,t) >= Pcomp(i,t) - Pcomp(i,t-1), RdnComp(i,t) >= Pcomp(i,t-1) - Pcomp(i,t)];

                F = [F, SOC_e(i,t) == SOC_e(i,t-1) + data.etaCh_e(i)*Pch(i,t)*dt - (1/data.etaDis_e(i))*Pdis(i,t)*dt];
                F = [F, SOC_th(i,t) == SOC_th(i,t-1) + data.etaCh_th(i)*Hch(i,t)*dt - (1/data.etaDis_th(i))*Hdis(i,t)*dt];
                F = [F, SOC_h2(i,t) == SOC_h2(i,t-1) + (H2ch(i,t) - H2dis(i,t))*dt];
            end

            % Renewable availability linked to capacity variables.
            F = [F, PpvUse(i,t) + PpvCurt(i,t) == Kpv(i)   * pvPU(i,t)];
            F = [F, PwindUse(i,t) + PwindCurt(i,t) == Kwind(i) * windPU(i,t)];

            % Electrical, hydrogen, thermal balances.
            F = [F, Pgrid(i,t) + PpvUse(i,t) + PwindUse(i,t) + Pchp(i,t) + Pfc(i,t) + Pdis(i,t) ...
                == PloadFixed(i,t) + PdrShift(i,t) - PdrCutE(i,t) + Peb(i,t) + Pelec(i,t) + Pch(i,t) + Pcomp(i,t)];
            F = [F, H2prod(i,t) + H2dis(i,t) + H2short(i,t) == data.H2load(i,t) - H2drCut(i,t) + H2cons_fc(i,t) + H2ch(i,t)];
            F = [F, Hchp(i,t) + Heb(i,t) + Hdis(i,t) == data.Hload(i,t) - HdrCut(i,t) + Hch(i,t) + Hdump(i,t)];

            F = [F, Pinj(i,t) == Pgrid(i,t)];
            F = [F, Qinj(i,t) == pfTan(i)*(PloadFixed(i,t) + PdrShift(i,t) - PdrCutE(i,t)) + data.QcompCoeff(i)*Pcomp(i,t) - Qpv(i,t) - Qwind(i,t) - Qes(i,t)];

            % Apparent-power capability synchronously changes with capacity.
            F = [F, norm([PpvUse(i,t); Qpv(i,t)], 2) <= plan.kappaPVInv*Kpv(i) + 1e-6];
            F = [F, norm([PwindUse(i,t); Qwind(i,t)], 2) <= plan.kappaWindInv*Kwind(i) + 1e-6];
            F = [F, norm([Pdis(i,t)-Pch(i,t); Qes(i,t)], 2) <= QesCap(i) + 1e-6];

            % Optional simplified carbon trading under benchmark quota.
            chpHeatEquivalent_it = ceh*Pchp(i,t) + Hchp(i,t);
            emission_it_kg = zetaE*Pgrid(i,t)*dt + zetaH*chpHeatEquivalent_it*dt;
            quota_it_kg = chiE*Pgrid(i,t)*dt + chiH*chpHeatEquivalent_it*dt;
            if plan.includeCarbonTradingCost
                F = [F, quota_it_kg/1000 + QaBuy(i,t) == emission_it_kg/1000 + QaSell(i,t)];
                dailyTradingCost = dailyTradingCost + plan.carbonBuyPrice*QaBuy(i,t) - plan.carbonSellPrice*QaSell(i,t);
            end
            dailyEmission_kg = dailyEmission_kg + emission_it_kg;

            % Operation cost, excluding annualized investment.
            dailyOpCost = dailyOpCost + data.ce(i,t)*Pgrid(i,t)*dt;
            dailyOpCost = dailyOpCost + data.cGas*Fgas(i,t)*dt;
            dailyOpCost = dailyOpCost + lambdaHdump(i)*Hdump(i,t)*dt;
            dailyOpCost = dailyOpCost + cOM_CHP(i)*Pchp(i,t)*dt;
            dailyOpCost = dailyOpCost + StartUpCHP(i)*vStart(i,t) + ShutDnCHP(i)*vStop(i,t);
            dailyOpCost = dailyOpCost + cRampCHP(i)*(RupChp(i,t) + RdnChp(i,t));
            dailyOpCost = dailyOpCost + cRampEb(i)*(RupEb(i,t) + RdnEb(i,t));
            dailyOpCost = dailyOpCost + cRampElec(i)*(RupElec(i,t) + RdnElec(i,t));
            dailyOpCost = dailyOpCost + cRampFc(i)*(RupFc(i,t) + RdnFc(i,t));
            dailyOpCost = dailyOpCost + cRampComp(i)*(RupComp(i,t) + RdnComp(i,t));
            dailyOpCost = dailyOpCost + data.lambdaPVCurt(i)*PpvCurt(i,t)*dt;
            dailyOpCost = dailyOpCost + data.lambdaWindCurt(i)*PwindCurt(i,t)*dt;
            dailyOpCost = dailyOpCost + data.lambdaH2Short(i)*H2short(i,t)*dt;
            dailyOpCost = dailyOpCost + cDRShiftE(i)*PdrShiftDev(i,t)*dt + cDRCutE(i)*PdrCutE(i,t)*dt;
            dailyOpCost = dailyOpCost + cDRCutH(i)*HdrCut(i,t)*dt + cDRCutH2(i)*H2drCut(i,t)*dt;
            dailyOpCost = dailyOpCost + (data.lambdaQpv(i)*(Qpv(i,t)^2) + data.lambdaQwind(i)*(Qwind(i,t)^2) + data.lambdaQes(i)*(Qes(i,t)^2))*dt;
            dailyOpCost = dailyOpCost + plan.varOMPV_yuan_per_MWh*PpvUse(i,t)*dt;
            dailyOpCost = dailyOpCost + plan.varOMWind_yuan_per_MWh*PwindUse(i,t)*dt;
            dailyOpCost = dailyOpCost + plan.varOMBat_yuan_per_MWh*(Pch(i,t)+Pdis(i,t))*dt;
            dailyOpCost = dailyOpCost + plan.varOMTh_yuan_per_MWh*(Hch(i,t)+Hdis(i,t))*dt;
            dailyOpCost = dailyOpCost + plan.varOMH2_yuan_per_kg*(H2ch(i,t)+H2dis(i,t))*dt;

            dailyRenAvail = dailyRenAvail + (Kpv(i)*pvPU(i,t) + Kwind(i)*windPU(i,t))*dt;
            dailyRenUse   = dailyRenUse   + (PpvUse(i,t) + PwindUse(i,t))*dt;
            dailyRenCurt  = dailyRenCurt  + (PpvCurt(i,t) + PwindCurt(i,t))*dt;
        end

        % Demand response daily energy conservation.
        F = [F, sum(PdrShift(i,:))*dt == sum(PdrShiftBase(i,:))*dt];

        % Optional CHP daily heat lower bound.
        if minChpHeatShare > 0
            F = [F, sum(Hchp(i,:))*dt >= minChpHeatShare * sum(data.Hload(i,:) - HdrCut(i,:))*dt];
        end

        % Minimum up/down time.
        MU = max(1, MinUpCHP(i));
        MD = max(1, MinDnCHP(i));
        for t = MU:T
            F = [F, sum(vStart(i,t-MU+1:t)) <= uChp(i,t)];
        end
        for t = MD:T
            F = [F, sum(vStop(i,t-MD+1:t)) <= 1 - uChp(i,t)];
        end

        % Daily cyclic storage constraints under variable capacities.
        F = [F, SOC_e(i,T)  == plan.socTerminalRatio*Ebat(i)];
        F = [F, SOC_th(i,T) == plan.socTerminalRatio*Eth(i)];
        F = [F, SOC_h2(i,T) == plan.socTerminalRatio*EH2(i)];
    end

    % ===== Network constraints =====
    for t = 1:T
        F = [F, V(data.rootBus,t) == data.Vslack^2];
        for l = 1:L
            from = data.branch(l,1); to = data.branch(l,2);
            Pchild = 0; Qchild = 0;
            child_lines = data.out_lines{to};
            for kk = 1:length(child_lines)
                lp = child_lines(kk);
                Pchild = Pchild + Pij(lp,t);
                Qchild = Qchild + Qij(lp,t);
            end
            Pload_net = data.PbusBase(to,t); Qload_net = data.QbusBase(to,t);
            if data.bus_has_comm(to)
                i = data.bus_to_comm(to);
                Pload_net = Pload_net + Pinj(i,t);
                Qload_net = Qload_net + Qinj(i,t);
            end
            F = [F, Pij(l,t) == Pchild + Pload_net, Qij(l,t) == Qchild + Qload_net];
            F = [F, V(to,t) == V(from,t) - 2*(data.rline(l)*(Pij(l,t)/data.baseMVA) + data.xline(l)*(Qij(l,t)/data.baseMVA))];
            F = [F, -data.PijMax(l) <= Pij(l,t), Pij(l,t) <= data.PijMax(l)];
            F = [F, -data.QijMax(l) <= Qij(l,t), Qij(l,t) <= data.QijMax(l)];
        end
        Psub = 0;
        rootOut = data.out_lines{data.rootBus};
        for kk = 1:length(rootOut)
            Psub = Psub + Pij(rootOut(kk),t);
        end
        F = [F, 0 <= Psub, Psub <= data.PsubMax(t)];
    end

    annualOperationCost = annualOperationCost + days * dailyOpCost;
    annualCarbonEmission_tCO2 = annualCarbonEmission_tCO2 + days * dailyEmission_kg / 1000;
    annualCarbonTradingCost = annualCarbonTradingCost + days * dailyTradingCost;
    annualRenewableAvailable_MWh = annualRenewableAvailable_MWh + days * dailyRenAvail;
    annualRenewableUse_MWh = annualRenewableUse_MWh + days * dailyRenUse;
    annualRenewableCurt_MWh = annualRenewableCurt_MWh + days * dailyRenCurt;

    op{s} = struct('Pgrid',Pgrid,'Pch',Pch,'Pdis',Pdis,'SOC_e',SOC_e, ...
        'PpvUse',PpvUse,'PpvCurt',PpvCurt,'PwindUse',PwindUse,'PwindCurt',PwindCurt, ...
        'Fgas',Fgas,'Pchp',Pchp,'Hchp',Hchp,'uChp',uChp,'vStart',vStart,'vStop',vStop, ...
        'Peb',Peb,'Heb',Heb,'Pelec',Pelec,'H2prod',H2prod,'H2cons_fc',H2cons_fc,'Pfc',Pfc, ...
        'Pcomp',Pcomp,'Hch',Hch,'Hdis',Hdis,'SOC_th',SOC_th, ...
        'H2ch',H2ch,'H2dis',H2dis,'SOC_h2',SOC_h2,'H2short',H2short, ...
        'Hdump',Hdump,'PdrShift',PdrShift,'PdrShiftDev',PdrShiftDev,'PdrCutE',PdrCutE, ...
        'HdrCut',HdrCut,'H2drCut',H2drCut,'Qpv',Qpv,'Qwind',Qwind,'Qes',Qes, ...
        'Pinj',Pinj,'Qinj',Qinj,'Pij',Pij,'Qij',Qij,'V',V, ...
        'dailyOpCost',dailyOpCost,'dailyEmission_tCO2',dailyEmission_kg/1000, ...
        'dailyTradingCost',dailyTradingCost,'dailyRenAvail',dailyRenAvail, ...
        'dailyRenUse',dailyRenUse,'dailyRenCurt',dailyRenCurt, ...
        'QaBuy',QaBuy,'QaSell',QaSell);
end

%% Total objective
annualCarbonPenaltyCost = plan.lambdaCO2_yuan_per_tCO2 * annualCarbonEmission_tCO2;
Obj = annualInvestmentCost + annualFixedOMCost + annualOperationCost + annualCarbonTradingCost + annualCarbonPenaltyCost;

if isfield(plan, 'verbose') && plan.verbose
    fprintf('\n[Planning] S=%d typical days, N=%d communities, T=%d hours.\n', S, N, T);
    fprintf('[Planning] Objective = annualized investment + OM + operation + lambdaCO2*emission.\n');
end

diagnostics = safe_optimize(F, Obj);
if diagnostics.problem ~= 0
    error('Centralized planning problem failed: %s', yalmiperror(diagnostics.problem));
end

%% Pack results
res = struct();
res.method = 'centralized-year-planning-existing-plus-new';
res.solveStatus = 'Solved';
res.diagnostics = diagnostics;
res.obj = value(Obj);
res.plan = plan;

res.capacity = struct();
res.capacity.KpvExisting_MW = KpvExisting;
res.capacity.KwindExisting_MW = KwindExisting;
res.capacity.EbatExisting_MWh = EbatExisting;
res.capacity.PbatExisting_MW = EbatExisting / plan.tauE_h;
res.capacity.EthExisting_MWh = EthExisting;
res.capacity.HthExisting_MW = EthExisting / plan.tauTh_h;
res.capacity.EH2Existing_kg = EH2Existing;
res.capacity.H2PowerExisting_kg_per_h = EH2Existing / plan.tauH2_h;
res.capacity.KpvNew_MW = value(KpvNew);
res.capacity.KwindNew_MW = value(KwindNew);
res.capacity.EbatNew_MWh = value(EbatNew);
res.capacity.PbatNew_MW = value(EbatNew / plan.tauE_h);
res.capacity.EthNew_MWh = value(EthNew);
res.capacity.HthNew_MW = value(EthNew / plan.tauTh_h);
res.capacity.EH2New_kg = value(EH2New);
res.capacity.H2PowerNew_kg_per_h = value(EH2New / plan.tauH2_h);
res.capacity.Kpv_MW = value(Kpv);
res.capacity.Kwind_MW = value(Kwind);
res.capacity.Ebat_MWh = value(Ebat);
res.capacity.Pbat_MW = value(PbatCap);
res.capacity.Eth_MWh = value(Eth);
res.capacity.Hth_MW = value(HthCap);
res.capacity.EH2_kg = value(EH2);
res.capacity.H2Power_kg_per_h = value(H2Cap);
res.capacity.QesMax_Mvar = value(QesCap);
res.capacity.Spv_MVA = plan.kappaPVInv * value(Kpv);
res.capacity.Swind_MVA = plan.kappaWindInv * value(Kwind);

res.cost = struct();
res.cost.TotalAnnualObjective_Yuan = value(Obj);
res.cost.AnnualInvestmentCost_Yuan = value(annualInvestmentCost);
res.cost.AnnualFixedOMCost_Yuan = value(annualFixedOMCost);
res.cost.AnnualOperationCost_Yuan = value(annualOperationCost);
res.cost.AnnualCarbonTradingCost_Yuan = value(annualCarbonTradingCost);
res.cost.AnnualCarbonPenaltyCost_Yuan = value(annualCarbonPenaltyCost);
res.cost.InvPV_YuanPerYear = value(invPV);
res.cost.InvWind_YuanPerYear = value(invWind);
res.cost.InvBat_YuanPerYear = value(invBat);
res.cost.InvTh_YuanPerYear = value(invTh);
res.cost.InvH2_YuanPerYear = value(invH2);
res.cost.FixOMPV_YuanPerYear = value(fixOMPV);
res.cost.FixOMWind_YuanPerYear = value(fixOMWind);
res.cost.FixOMBat_YuanPerYear = value(fixOMBat);
res.cost.FixOMTh_YuanPerYear = value(fixOMTh);
res.cost.FixOMH2_YuanPerYear = value(fixOMH2);

res.annual = struct();
res.annual.CarbonEmission_tCO2 = value(annualCarbonEmission_tCO2);
res.annual.RenewableAvailable_MWh = value(annualRenewableAvailable_MWh);
res.annual.RenewableUse_MWh = value(annualRenewableUse_MWh);
res.annual.RenewableCurtailment_MWh = value(annualRenewableCurt_MWh);
res.annual.RenewableUseRate_percent = 100 * safe_ratio(res.annual.RenewableUse_MWh, res.annual.RenewableAvailable_MWh);
res.annual.RenewableCurtailmentRate_percent = 100 * safe_ratio(res.annual.RenewableCurtailment_MWh, res.annual.RenewableAvailable_MWh);

% Scenario dispatch outputs.
scenarioOut = cell(S,1);
for s = 1:S
    data = dataSet{s};
    x = op{s};
    r = struct();
    r.TypicalScenario = string(data.typicalScenarioName);
    r.TypicalScenarioCN = string(data.typicalScenarioNameCN);
    r.RepresentativeDays = data.representativeDays;
    r.dailyOpCost_Yuan = value(x.dailyOpCost);
    r.annualOpCost_Yuan = value(x.dailyOpCost) * data.representativeDays;
    r.dailyEmission_tCO2 = value(x.dailyEmission_tCO2);
    r.annualEmission_tCO2 = value(x.dailyEmission_tCO2) * data.representativeDays;
    r.dailyTradingCost_Yuan = value(x.dailyTradingCost);
    r.annualTradingCost_Yuan = value(x.dailyTradingCost) * data.representativeDays;
    r.dailyRenewableAvailable_MWh = value(x.dailyRenAvail);
    r.dailyRenewableUse_MWh = value(x.dailyRenUse);
    r.dailyRenewableCurtailment_MWh = value(x.dailyRenCurt);
    r.renewableUseRate_percent = 100 * safe_ratio(r.dailyRenewableUse_MWh, r.dailyRenewableAvailable_MWh);
    r.renewableCurtailmentRate_percent = 100 * safe_ratio(r.dailyRenewableCurtailment_MWh, r.dailyRenewableAvailable_MWh);
    r.Pgrid = value(x.Pgrid); r.Pch = value(x.Pch); r.Pdis = value(x.Pdis); r.SOC_e = value(x.SOC_e);
    r.PpvUse = value(x.PpvUse); r.PpvCurt = value(x.PpvCurt);
    r.PwindUse = value(x.PwindUse); r.PwindCurt = value(x.PwindCurt);
    r.Fgas = value(x.Fgas); r.Pchp = value(x.Pchp); r.Hchp = value(x.Hchp);
    r.uChp = value(x.uChp); r.vStart = value(x.vStart); r.vStop = value(x.vStop);
    r.Peb = value(x.Peb); r.Heb = value(x.Heb);
    r.Pelec = value(x.Pelec); r.H2prod = value(x.H2prod);
    r.H2cons_fc = value(x.H2cons_fc); r.Pfc = value(x.Pfc);
    r.Pcomp = value(x.Pcomp);
    r.Hch = value(x.Hch); r.Hdis = value(x.Hdis); r.SOC_th = value(x.SOC_th);
    r.H2ch = value(x.H2ch); r.H2dis = value(x.H2dis); r.SOC_h2 = value(x.SOC_h2);
    r.H2short = value(x.H2short); r.Hdump = value(x.Hdump);
    r.PdrShift = value(x.PdrShift); r.PdrShiftDev = value(x.PdrShiftDev);
    r.PdrCutE = value(x.PdrCutE); r.HdrCut = value(x.HdrCut); r.H2drCut = value(x.H2drCut);
    r.Qpv = value(x.Qpv); r.Qwind = value(x.Qwind); r.Qes = value(x.Qes);
    r.Pinj = value(x.Pinj); r.Qinj = value(x.Qinj); r.Pij = value(x.Pij); r.Qij = value(x.Qij); r.V = value(x.V);
    if ~isempty(x.QaBuy)
        r.QaBuy_tCO2 = value(x.QaBuy);
        r.QaSell_tCO2 = value(x.QaSell);
    else
        r.QaBuy_tCO2 = zeros(N,T);
        r.QaSell_tCO2 = zeros(N,T);
    end
    scenarioOut{s} = r;
end
res.scenario = vertcat(scenarioOut{:});

res.capacityTable = make_capacity_table(res.capacity);
res.costTable = make_cost_table(res.cost);
res.scenarioTable = make_scenario_result_table(res.scenario);

end

%% ============================ Helpers ============================
function crf = i_crf(r, y)
if r <= 0
    crf = 1 / y;
else
    crf = r * (1+r)^y / ((1+r)^y - 1);
end
end

function val = i_get_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end

function v = i_get_vec(s, name, defaultVal, n)
if isfield(s, name) && ~isempty(s.(name))
    v = s.(name);
else
    v = defaultVal;
end
v = v(:);
if numel(v) ~= n
    error('Planning parameter %s must have %d entries.', name, n);
end
end

function out = safe_ratio(a, b)
if abs(b) < 1e-9
    out = NaN;
else
    out = a / b;
end
end

function Tcap = make_capacity_table(cap)
N = numel(cap.Kpv_MW);
Community = (1:N)';
Tcap = table(Community, ...
    cap.KpvExisting_MW(:), cap.KpvNew_MW(:), cap.Kpv_MW(:), ...
    cap.KwindExisting_MW(:), cap.KwindNew_MW(:), cap.Kwind_MW(:), ...
    cap.EbatExisting_MWh(:), cap.EbatNew_MWh(:), cap.Ebat_MWh(:), cap.Pbat_MW(:), ...
    cap.EthExisting_MWh(:), cap.EthNew_MWh(:), cap.Eth_MWh(:), cap.Hth_MW(:), ...
    cap.EH2Existing_kg(:), cap.EH2New_kg(:), cap.EH2_kg(:), cap.H2Power_kg_per_h(:), ...
    cap.Spv_MVA(:), cap.Swind_MVA(:), cap.QesMax_Mvar(:), ...
    'VariableNames', {'Community', ...
    'PVExisting_MW','PVNew_MW','PV_MW', ...
    'WindExisting_MW','WindNew_MW','Wind_MW', ...
    'BatteryExisting_MWh','BatteryNew_MWh','BatteryEnergy_MWh','BatteryPower_MW', ...
    'ThermalStorageExisting_MWh','ThermalStorageNew_MWh','ThermalStorage_MWh','ThermalStoragePower_MW', ...
    'HydrogenStorageExisting_kg','HydrogenStorageNew_kg','HydrogenStorage_kg','HydrogenStoragePower_kg_h', ...
    'PVInverter_MVA','WindConverter_MVA','ESReactiveCapability_Mvar'});
end

function Tcost = make_cost_table(cost)
Name = string(fieldnames(cost));
Value = zeros(numel(Name),1);
for k = 1:numel(Name)
    Value(k) = cost.(char(Name(k)));
end
Tcost = table(Name, Value, 'VariableNames', {'CostItem','Value_Yuan'});
end

function Tsc = make_scenario_result_table(sc)
S = numel(sc);
TypicalScenario = strings(S,1);
TypicalScenarioCN = strings(S,1);
RepresentativeDays = zeros(S,1);
DailyOpCost_Yuan = zeros(S,1);
AnnualOpCost_Yuan = zeros(S,1);
DailyEmission_tCO2 = zeros(S,1);
AnnualEmission_tCO2 = zeros(S,1);
RenAvail_MWh = zeros(S,1);
RenUse_MWh = zeros(S,1);
RenCurt_MWh = zeros(S,1);
RenUseRate_percent = zeros(S,1);
RenCurtRate_percent = zeros(S,1);
AvgMinVoltage_pu = zeros(S,1);
GridVoltageDeviation_pu = zeros(S,1);
for s = 1:S
    TypicalScenario(s) = sc(s).TypicalScenario;
    TypicalScenarioCN(s) = sc(s).TypicalScenarioCN;
    RepresentativeDays(s) = sc(s).RepresentativeDays;
    DailyOpCost_Yuan(s) = sc(s).dailyOpCost_Yuan;
    AnnualOpCost_Yuan(s) = sc(s).annualOpCost_Yuan;
    DailyEmission_tCO2(s) = sc(s).dailyEmission_tCO2;
    AnnualEmission_tCO2(s) = sc(s).annualEmission_tCO2;
    RenAvail_MWh(s) = sc(s).dailyRenewableAvailable_MWh;
    RenUse_MWh(s) = sc(s).dailyRenewableUse_MWh;
    RenCurt_MWh(s) = sc(s).dailyRenewableCurtailment_MWh;
    RenUseRate_percent(s) = sc(s).renewableUseRate_percent;
    RenCurtRate_percent(s) = sc(s).renewableCurtailmentRate_percent;
    voltagePu = sqrt(max(0, sc(s).V));
    AvgMinVoltage_pu(s) = mean(min(voltagePu,[],1));
    GridVoltageDeviation_pu(s) = mean(abs(voltagePu(:)-1));
end
Tsc = table(TypicalScenario, TypicalScenarioCN, RepresentativeDays, DailyOpCost_Yuan, AnnualOpCost_Yuan, ...
    DailyEmission_tCO2, AnnualEmission_tCO2, RenAvail_MWh, RenUse_MWh, RenCurt_MWh, ...
    RenUseRate_percent, RenCurtRate_percent, AvgMinVoltage_pu, GridVoltageDeviation_pu);
end
