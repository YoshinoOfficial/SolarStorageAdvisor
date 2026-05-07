function res = solve_centralized(data)
% Centralized zero-carbon campus multi-energy solver
%   - PV + Wind generation
%   - CHP (gas engine), electric boiler, electric chiller
%   - Electrolyzer + fuel cell + H2 storage
%   - Electrical / thermal / hydrogen energy storage
%   - Joint P/Q optimization on IEEE33 feeder
%
% CHP patch included:
%   1) on/off + startup/shutdown binaries
%   2) minimum output + minimum gas input
%   3) ramp constraints + ramp penalty auxiliaries
%   4) thermal dump variable Hdump to avoid forced heat absorption
%   5) startup / shutdown / O&M / ramp / dump penalties
%
% NOTE:
%   This file is backward-compatible. If build_case.m has not yet been
%   extended with the new CHP fields, reasonable defaults are used.

yalmip('clear');

N = data.N; T = data.T; B = data.B; L = data.L; dt = data.dt;

% ===== CHP default-compatible parameters =====
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
enableCarbonQuota = logical(i_get_field(data, 'enableCarbonQuota', i_get_field(data, 'enableCarbonTrading', false)));
enableCommunityCarbonTrading = logical(i_get_field(data, 'enableCommunityCarbonTrading', enableCarbonQuota));
allowCarbonMarketSell = logical(i_get_field(data, 'allowCarbonMarketSell', enableCarbonQuota));
carbonBuyPrice = i_get_field(data, 'carbonBuyPrice', 200);
carbonSellPrice = i_get_field(data, 'carbonSellPrice', 100);
minChpHeatShare = i_get_field(data, 'minChpHeatShare', 0);
zetaE = i_get_field(data, 'zetaE', 1080);
zetaH = i_get_field(data, 'zetaH', 324);
chiE = i_get_field(data, 'chiE', 728);
chiH = i_get_field(data, 'chiH', 367.2);
ceh = i_get_field(data, 'ceh', 1.6667);
fixedCarbonQuota_kg = i_get_field(data, 'fixedCarbonQuota_kg', []);

% Electrical variables
Pgrid = sdpvar(N,T,'full');
Pch   = sdpvar(N,T,'full');
Pdis  = sdpvar(N,T,'full');
SOC_e = sdpvar(N,T,'full');
PpvUse = sdpvar(N,T,'full');
PpvCurt = sdpvar(N,T,'full');
PwindUse = sdpvar(N,T,'full');
PwindCurt = sdpvar(N,T,'full');
uCh = binvar(N,T,'full');

% CHP variables
Fgas = sdpvar(N,T,'full');
Pchp = sdpvar(N,T,'full');
Hchp = sdpvar(N,T,'full');
uChp = binvar(N,T,'full');
vStart = binvar(N,T,'full');
vStop  = binvar(N,T,'full');
RupChp = sdpvar(N,T,'full');
RdnChp = sdpvar(N,T,'full');
Hdump  = sdpvar(N,T,'full');

% Electric boiler
Peb = sdpvar(N,T,'full');
Heb = sdpvar(N,T,'full');

% Electrolyzer
Pelec = sdpvar(N,T,'full');
H2prod = sdpvar(N,T,'full');

% Fuel cell
H2cons_fc = sdpvar(N,T,'full');
Pfc = sdpvar(N,T,'full');

% Thermal storage
Hch = sdpvar(N,T,'full');
Hdis = sdpvar(N,T,'full');
SOC_th = sdpvar(N,T,'full');
uHch = binvar(N,T,'full');   % 1: charging heat, 0: discharging heat

% Hydrogen storage
H2ch = sdpvar(N,T,'full');
H2dis = sdpvar(N,T,'full');
SOC_h2 = sdpvar(N,T,'full');

% Hydrogen shortage (soft constraint)
H2short = sdpvar(N,T,'full');

% Reactive power and network
Qpv = sdpvar(N,T,'full');
Qes = sdpvar(N,T,'full');
Pinj = sdpvar(N,T,'full');
Qinj = sdpvar(N,T,'full');
Pij = sdpvar(L,T,'full');
Qij = sdpvar(L,T,'full');
V   = sdpvar(B,T,'full');

% Carbon trading
QaBuy = sdpvar(N,T,'full');
QaSell = sdpvar(N,T,'full');
Qtrade = sdpvar(N,T,'full');
QaUnused = sdpvar(N,T,'full');

F = [];
% Bounds
F = [F, Pgrid >= 0, Pch >= 0, Pdis >= 0, SOC_e >= 0.1*repmat(data.Emax,1,T), PpvUse >= 0, PpvCurt >= 0];
F = [F, PwindUse >= 0, PwindCurt >= 0];
F = [F, 0 <= uCh, uCh <= 1];
F = [F, PpvUse <= data.Ppv, PpvCurt <= data.Ppv];
F = [F, PwindUse <= data.Pwind, PwindCurt <= data.Pwind];
F = [F, Pch <= repmat(data.PchMax,1,T).*uCh, Pdis <= repmat(data.PdisMax,1,T).*(1-uCh)];
F = [F, SOC_e <= 0.9*repmat(data.Emax,1,T), Pgrid <= repmat(data.PgridMax,1,T)];
F = [F, V >= repmat(data.Vmin.^2,1,T), V <= repmat(data.Vmax.^2,1,T)];
F = [F, Qpv >= -repmat(data.QpvMax,1,T), Qpv <= repmat(data.QpvMax,1,T)];
F = [F, Qes >= -repmat(data.QesMax,1,T), Qes <= repmat(data.QesMax,1,T)];
F = [F, QaBuy >= 0, QaSell >= 0, QaUnused >= 0];
if ~enableCarbonQuota
    F = [F, QaBuy == 0, QaSell == 0, Qtrade == 0, QaUnused == 0];
else
    if ~enableCommunityCarbonTrading
        F = [F, Qtrade == 0];
    end
    if ~allowCarbonMarketSell
        F = [F, QaSell == 0];
    end
end

% CHP constraints
F = [F, 0 <= uChp, uChp <= 1, 0 <= vStart, vStart <= 1, 0 <= vStop, vStop <= 1];
F = [F, vStart + vStop <= 1];
F = [F, RupChp >= 0, RdnChp >= 0, Hdump >= 0];
F = [F, Fgas >= 0, Fgas <= repmat(data.FgasMax(:),1,T) .* uChp];
F = [F, Fgas >= repmat(FgasMinEff(:),1,T) .* uChp];
F = [F, Pchp == repmat(data.etaE_chp(:),1,T) .* Fgas];
F = [F, Hchp == repmat(data.etaH_chp(:),1,T) .* Fgas];
F = [F, Pchp <= repmat(data.PchpRated(:),1,T) .* uChp];
F = [F, Pchp >= repmat(PchpMin(:),1,T) .* uChp];

% Electric boiler
F = [F, Peb >= 0, Peb <= repmat(data.PebMax,1,T)];
F = [F, Heb == repmat(data.etaEb,1,T) .* Peb];

% Electrolyzer
F = [F, Pelec >= 0, Pelec <= repmat(data.PelecMax,1,T)];
F = [F, H2prod == repmat(data.etaElec,1,T) .* Pelec];

% Fuel cell
F = [F, H2cons_fc >= 0, H2cons_fc <= repmat(data.H2fcMax,1,T)];
F = [F, Pfc == repmat(data.etaFc,1,T) .* H2cons_fc];

% Thermal storage
F = [F, Hch >= 0, Hdis >= 0];
F = [F, SOC_th >= 0.1*repmat(data.EthMax,1,T), SOC_th <= 0.9*repmat(data.EthMax,1,T)];
F = [F, Hch <= repmat(data.HchMax,1,T).*uHch];
F = [F, Hdis <= repmat(data.HdisMax,1,T).*(1-uHch)];

% Hydrogen storage
F = [F, H2ch >= 0, H2dis >= 0, SOC_h2 >= 0.1*repmat(data.EH2Max,1,T), SOC_h2 <= 0.9*repmat(data.EH2Max,1,T)];
F = [F, H2ch <= repmat(data.H2chMax,1,T), H2dis <= repmat(data.H2disMax,1,T)];
% No external hydrogen trucking/trading is modeled here; disable free H2 charge/discharge knobs.
F = [F, H2ch == 0, H2dis == 0];

% Hydrogen shortage
F = [F, H2short >= 0];

for i = 1:N
    for t = 1:T
        % CHP logic
        if t == 1
            F = [F, uChp(i,t) - uChp0(i) == vStart(i,t) - vStop(i,t)];
        else
            F = [F, uChp(i,t) - uChp(i,t-1) == vStart(i,t) - vStop(i,t)];
            F = [F, Pchp(i,t) - Pchp(i,t-1) <= RampUpCHP(i)];
            F = [F, Pchp(i,t-1) - Pchp(i,t) <= RampDnCHP(i)];
            F = [F, RupChp(i,t) >= Pchp(i,t) - Pchp(i,t-1)];
            F = [F, RdnChp(i,t) >= Pchp(i,t-1) - Pchp(i,t)];
        end

        % Electrical storage dynamics
        if t == 1
            F = [F, SOC_e(i,t) == data.SOC0_e(i) + data.etaCh_e(i)*Pch(i,t)*dt - (1/data.etaDis_e(i))*Pdis(i,t)*dt];
        else
            F = [F, SOC_e(i,t) == SOC_e(i,t-1) + data.etaCh_e(i)*Pch(i,t)*dt - (1/data.etaDis_e(i))*Pdis(i,t)*dt];
        end

        % Thermal storage dynamics
        if t == 1
            F = [F, SOC_th(i,t) == data.SOC0_th(i) + data.etaCh_th(i)*Hch(i,t)*dt - (1/data.etaDis_th(i))*Hdis(i,t)*dt];
        else
            F = [F, SOC_th(i,t) == SOC_th(i,t-1) + data.etaCh_th(i)*Hch(i,t)*dt - (1/data.etaDis_th(i))*Hdis(i,t)*dt];
        end

        % Hydrogen storage dynamics
        if t == 1
            F = [F, SOC_h2(i,t) == data.SOC0_h2(i) + (H2prod(i,t) - H2cons_fc(i,t) - data.H2load(i,t) + H2short(i,t))*dt];
        else
            F = [F, SOC_h2(i,t) == SOC_h2(i,t-1) + (H2prod(i,t) - H2cons_fc(i,t) - data.H2load(i,t) + H2short(i,t))*dt];
        end

        % Power balance (electrical)
        Pcomp = data.PcompFixed(i,t);
        F = [F, PpvUse(i,t) + PpvCurt(i,t) == data.Ppv(i,t)];
        F = [F, PwindUse(i,t) + PwindCurt(i,t) == data.Pwind(i,t)];
        F = [F, Pgrid(i,t) + PpvUse(i,t) + PwindUse(i,t) + Pchp(i,t) + Pfc(i,t) + Pdis(i,t) ...
             == data.Pload(i,t) + Peb(i,t) + Pelec(i,t) + Pch(i,t) + Pcomp];
        F = [F, Pinj(i,t) == Pgrid(i,t)];
        F = [F, Qinj(i,t) == data.Qbase(i,t) + data.QcompCoeff(i)*Pcomp - Qpv(i,t) - Qes(i,t)];
        F = [F, PpvUse(i,t)^2 + Qpv(i,t)^2 <= data.QpvMax(i)^2 + 1e-6];
        F = [F, (Pdis(i,t) - Pch(i,t))^2 + Qes(i,t)^2 <= data.QesMax(i)^2 + 1e-6];

        % Thermal balance (with heat dump)
        F = [F, Hchp(i,t) + Heb(i,t) + Hdis(i,t) == data.Hload(i,t) + Hch(i,t) + Hdump(i,t)];

    end

    if minChpHeatShare > 0
        F = [F, sum(Hchp(i,:))*dt >= minChpHeatShare * sum(data.Hload(i,:))*dt];
    end

    if enableCarbonQuota
        emission_day = 0;
        quota_day = 0;
        for t = 1:T
            chpHeatEquivalent_it = ceh*Pchp(i,t) + Hchp(i,t);
            emission_day = emission_day + zetaE*Pgrid(i,t)*dt + zetaH*chpHeatEquivalent_it*dt;
            if isempty(fixedCarbonQuota_kg)
                quota_day = quota_day + chiE*Pgrid(i,t)*dt + chiH*chpHeatEquivalent_it*dt;
            else
                quota_day = quota_day + fixedCarbonQuota_kg(i,t);
            end
        end
        F = [F, quota_day + sum(QaBuy(i,:)) + sum(Qtrade(i,:)) == ...
                emission_day + sum(QaSell(i,:)) + sum(QaUnused(i,:))];
    end

    % Minimum up/down time (simple intra-day version)
    MU = max(1, MinUpCHP(i));
    MD = max(1, MinDnCHP(i));
    for t = MU:T
        F = [F, sum(vStart(i,t-MU+1:t)) <= uChp(i,t)];
    end
    for t = MD:T
        F = [F, sum(vStop(i,t-MD+1:t)) <= 1 - uChp(i,t)];
    end
end

% Cyclic end-of-day storage constraints to avoid free depletion of initial inventories
for i = 1:N
    F = [F, SOC_e(i,T)==data.termSOC_e(i), SOC_th(i,T)==data.termSOC_th(i), ...
            SOC_h2(i,T)==data.termSOC_h2(i)];
end

if enableCommunityCarbonTrading
    F = [F, sum(Qtrade(:,1)) == 0];
    if T > 1
        F = [F, Qtrade(:,2:T) == 0];
    end
end

% Network constraints
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

% Objective
Obj = 0;
for i = 1:N
    for t = 1:T
        Obj = Obj + data.ce(i,t)*Pgrid(i,t)*dt;
        Obj = Obj + data.cGas*Fgas(i,t)*dt;
        if enableCarbonQuota
            Obj = Obj + (carbonBuyPrice/1000)*QaBuy(i,t) - (carbonSellPrice/1000)*QaSell(i,t);
        end
        Obj = Obj + lambdaHdump(i)*Hdump(i,t)*dt;
        Obj = Obj + cOM_CHP(i)*Pchp(i,t)*dt;
        Obj = Obj + StartUpCHP(i)*vStart(i,t) + ShutDnCHP(i)*vStop(i,t);
        Obj = Obj + cRampCHP(i)*(RupChp(i,t) + RdnChp(i,t));
        Obj = Obj + data.lambdaPVCurt(i)*PpvCurt(i,t)*dt;
        Obj = Obj + data.lambdaWindCurt(i)*PwindCurt(i,t)*dt;
        Obj = Obj + data.lambdaH2Short(i)*H2short(i,t)*dt;
        Obj = Obj + (data.lambdaQpv(i)*(Qpv(i,t)^2) + data.lambdaQes(i)*(Qes(i,t)^2))*dt;
    end
end

diagnostics = safe_optimize(F, Obj);
if diagnostics.problem ~= 0
    error('Multi-energy centralized problem failed: %s', yalmiperror(diagnostics.problem, 'gurobi'));
end

res.method = 'centralized-multi-energy-pq';
res.obj = value(Obj);

% Cost breakdown
gridCost = 0; carbonCost = 0; gasCost = 0; gasCarbonCost = 0;
carbonTradingCost = 0;
hdumpCost = 0; chpOMCost = 0; startupCost = 0; shutdownCost = 0; rampCost = 0;
pvCurtCost = 0; windCurtCost = 0; h2ShortCost = 0; qSupportCost = 0;
for i = 1:N
    for t = 1:T
        gridCost      = gridCost      + data.ce(i,t)*Pgrid(i,t)*dt;
        gasCost      = gasCost      + data.cGas*Fgas(i,t)*dt;
        if enableCarbonQuota
            carbonTradingCost = carbonTradingCost + (carbonBuyPrice/1000)*QaBuy(i,t) - (carbonSellPrice/1000)*QaSell(i,t);
        end
        hdumpCost   = hdumpCost   + lambdaHdump(i)*Hdump(i,t)*dt;
        chpOMCost   = chpOMCost   + cOM_CHP(i)*Pchp(i,t)*dt;
        startupCost = startupCost + StartUpCHP(i)*vStart(i,t);
        shutdownCost= shutdownCost+ ShutDnCHP(i)*vStop(i,t);
        rampCost    = rampCost    + cRampCHP(i)*(RupChp(i,t) + RdnChp(i,t));
        pvCurtCost  = pvCurtCost  + data.lambdaPVCurt(i)*PpvCurt(i,t)*dt;
        windCurtCost = windCurtCost + data.lambdaWindCurt(i)*PwindCurt(i,t)*dt;
        h2ShortCost= h2ShortCost+ data.lambdaH2Short(i)*H2short(i,t)*dt;
        qSupportCost= qSupportCost+ (data.lambdaQpv(i)*Qpv(i,t)^2 + data.lambdaQes(i)*Qes(i,t)^2)*dt;
    end
end
res.parts = struct('gridCost', i_value(gridCost), 'carbonCost', i_value(carbonCost), 'gasCost', i_value(gasCost), ...
    'gasCarbonCost', i_value(gasCarbonCost), 'carbonTradingCost', i_value(carbonTradingCost), ...
    'hdumpCost', i_value(hdumpCost), 'chpOMCost', i_value(chpOMCost), ...
    'startupCost', i_value(startupCost), 'shutdownCost', i_value(shutdownCost), ...
    'rampCost', i_value(rampCost), ...
    'pvCurtCost', i_value(pvCurtCost), 'windCurtCost', i_value(windCurtCost), ...
    'h2ShortCost', i_value(h2ShortCost), 'qSupportCost', i_value(qSupportCost));

res.Pgrid = value(Pgrid); res.Pch = value(Pch); res.Pdis = value(Pdis); res.SOC_e = value(SOC_e);
res.PpvUse = value(PpvUse); res.PpvCurt = value(PpvCurt);
res.PwindUse = value(PwindUse); res.PwindCurt = value(PwindCurt);
res.Fgas = value(Fgas); res.Pchp = value(Pchp); res.Hchp = value(Hchp);
res.uChp = value(uChp); res.vStart = value(vStart); res.vStop = value(vStop);
res.RupChp = value(RupChp); res.RdnChp = value(RdnChp); res.Hdump = value(Hdump);
res.Peb = value(Peb); res.Heb = value(Heb);
res.Pelec = value(Pelec); res.H2prod = value(H2prod);
res.H2cons_fc = value(H2cons_fc); res.Pfc = value(Pfc);
res.Hch = value(Hch); res.Hdis = value(Hdis); res.SOC_th = value(SOC_th);
res.H2ch = value(H2ch); res.H2dis = value(H2dis); res.SOC_h2 = value(SOC_h2);
res.H2short = value(H2short);
res.Qpv = value(Qpv); res.Qes = value(Qes); res.Qinj = value(Qinj);
res.Pinj = value(Pinj); res.Pij = value(Pij); res.Qij = value(Qij); res.V = value(V);
res.QaBuy = value(QaBuy); res.QaSell = value(QaSell); res.Qtrade = value(Qtrade); res.QaUnused = value(QaUnused);
carbon = carbon_accounting(data, res.Pgrid, res.Pchp, res.Hchp, res.Fgas);
res.CarbonEmission_kg = carbon.emission;
res.CarbonQuota_kg = carbon.quota;
res.CarbonAllowanceSurplus_kg = carbon.netAllowanceSurplus;
res.CarbonBuyMarket_kg = res.QaBuy;
res.CarbonSellMarket_kg = res.QaSell;
res.CarbonTradeWithCommunities_kg = res.Qtrade;
res.CarbonUnusedAllowance_kg = res.QaUnused;
res.CarbonTradingCost_Yuan = i_value(carbonTradingCost);
res.TotalObjective_Yuan = res.obj;
res.Iterations = NaN;
res.Status = 'Solved';

res.totalPVCurt = sum(res.PpvCurt(:));
res.totalWindCurt = sum(res.PwindCurt(:));
res.totalPVUse = sum(res.PpvUse(:));
res.totalWindUse = sum(res.PwindUse(:));
res.totalGas = sum(res.Fgas(:));
res.totalH2short = sum(res.H2short(:));
res.totalHdump = sum(res.Hdump(:));
end

function val = i_get_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end

function val = i_value(x)
if isa(x, 'sdpvar')
    val = value(x);
else
    val = x;
end
end
