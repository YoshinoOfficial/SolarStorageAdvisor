function out = solve_local_subproblem(varargin)
% Local community subproblem with persistent optimizer cache
% CHP patch included:
%   1) on/off + startup/shutdown binaries
%   2) minimum output + minimum gas input
%   3) ramp constraints + ramp penalty auxiliaries
%   4) thermal dump variable Hdump
%   5) startup / shutdown / O&M / ramp / dump penalties
%
% Backward-compatible with the current build_local_params.m. Missing CHP
% enhancement fields are replaced by default values inside this file.

persistent CACHE
CACHE = local_init_cache(CACHE);

if nargin >= 1 && ischar(varargin{1})
    cmd = lower(varargin{1});
    switch cmd
        case {'reset','clear_cache'}
            CACHE = local_init_cache([]);
            out = [];
            return;
        case 'prebuild'
            if nargin < 2
                error('solve_local_subproblem(''prebuild'', p) requires the parameter struct p.');
            end
            p = varargin{2};
            [~, CACHE] = local_get_or_build_cache(p, CACHE);
            out = [];
            return;
        otherwise
            error('Unknown command: %s', cmd);
    end
end

if nargin ~= 1
    error('solve_local_subproblem expects exactly one struct input p, or a supported command.');
end
p = varargin{1};

[cache, CACHE] = local_get_or_build_cache(p, CACHE);
paramVec = local_pack_parameters(p);

try
    solVec = cache.opt(paramVec);
catch ME
    warning('Local optimizer cache retry for community %d: %s', p.idx, ME.message);
    try, yalmip('clear'); catch, end
    CACHE = local_init_cache([]);
    [cache, CACHE] = local_get_or_build_cache(p, CACHE);
    paramVec = local_pack_parameters(p);
    try
        solVec = cache.opt(paramVec);
    catch ME2
        error('Local optimizer failed for community %d: %s', p.idx, ME2.message);
    end
end

if ~isnumeric(solVec)
    error('Unexpected optimizer output type for community %d.', p.idx);
end

out = local_unpack_solution(solVec, p, cache);
end

function CACHE = local_init_cache(CACHE)
if isempty(CACHE)
    CACHE = containers.Map('KeyType','char','ValueType','any');
end
end

function [cache, CACHE] = local_get_or_build_cache(p, CACHE)
CACHE = local_init_cache(CACHE);
key = local_cache_key(p);
if isKey(CACHE, key)
    cache = CACHE(key);
    return;
end
cache = local_compile_optimizer(p);
CACHE(key) = cache;
end

function key = local_cache_key(p)
%LOCAL_CACHE_KEY
% P2 acceleration: keep only structural/model-form parameters in the cache key.
% Time-series scenario data such as load, renewable output, tariff, compute load,
% and fixed quota are passed through optimizer parameters instead of rebuilding
% the YALMIP model for every scenario.
PchpMin = local_getfield(p,'PchpMin',0.35*p.PchpRated);
uChp0 = local_getfield(p,'uChp0',0);
RampUpCHP = local_getfield(p,'RampUpCHP',0.30*p.PchpRated);
RampDnCHP = local_getfield(p,'RampDnCHP',0.30*p.PchpRated);
StartUpCHP = local_getfield(p,'StartUpCHP',80);
ShutDnCHP  = local_getfield(p,'ShutDnCHP',20);
MinUpCHP   = round(local_getfield(p,'MinUpCHP',2));
MinDnCHP   = round(local_getfield(p,'MinDnCHP',2));
cOM_CHP    = local_getfield(p,'cOM_CHP',8);
cRampCHP   = local_getfield(p,'cRampCHP',2);
lambdaHdump = local_getfield(p,'lambdaHdump',200);
enableCarbonQuota = logical(local_getfield(p,'enableCarbonQuota',local_getfield(p,'enableCarbonTrading',false)));
enableCommunityCarbonTrading = logical(local_getfield(p,'enableCommunityCarbonTrading',enableCarbonQuota));
allowCarbonMarketSell = logical(local_getfield(p,'allowCarbonMarketSell',enableCarbonQuota));
fixedCarbonQuota_kg = local_getfield(p,'fixedCarbonQuota_kg',[]);
hasFixedCarbonQuota = ~isempty(fixedCarbonQuota_kg);
minChpHeatShare = local_getfield(p,'minChpHeatShare',0);
FgasMinEff = max(p.FgasMin, PchpMin / max(p.etaE_chp,1e-6));

key = strjoin({ ...
    sprintf('idx=%d',p.idx), sprintf('T=%d',p.T), sprintf('rhoPQ=%.10g',p.rhoPQ), ...
    sprintf('rhoC=%.10g',p.rhoC), sprintf('carbon=%d',enableCarbonQuota), ...
    sprintf('commCarbon=%d',enableCommunityCarbonTrading), sprintf('sellCarbon=%d',allowCarbonMarketSell), ...
    sprintf('hasFixedQuota=%d',hasFixedCarbonQuota), ...
    sprintf('aCompH2=%.10g',p.alphaCompH2), ...
    sprintf('PchM=%.10g',p.PchMax), sprintf('PdisM=%.10g',p.PdisMax), sprintf('Emax=%.10g',p.Emax), ...
    sprintf('S0e=%.10g',p.SOC0_e), sprintf('eCe=%.10g',p.etaCh_e), sprintf('eDe=%.10g',p.etaDis_e), ...
    sprintf('PchpR=%.10g',p.PchpRated), sprintf('PchpMin=%.10g',PchpMin), sprintf('u0=%.10g',uChp0), ...
    sprintf('eEc=%.10g',p.etaE_chp), sprintf('eHc=%.10g',p.etaH_chp), sprintf('FgMinEff=%.10g',FgasMinEff), ...
    sprintf('FgMax=%.10g',p.FgasMax), sprintf('Rup=%.10g',RampUpCHP), sprintf('Rdn=%.10g',RampDnCHP), ...
    sprintf('SU=%.10g',StartUpCHP), sprintf('SD=%.10g',ShutDnCHP), sprintf('MU=%d',MinUpCHP), sprintf('MD=%d',MinDnCHP), ...
    sprintf('cOM=%.10g',cOM_CHP), sprintf('cRp=%.10g',cRampCHP), sprintf('lHd=%.10g',lambdaHdump), ...
    sprintf('minChpHeatShare=%.10g',minChpHeatShare), ...
    sprintf('cG=%.10g',p.cGas), sprintf('efG=%.10g',p.efGas), sprintf('PebM=%.10g',p.PebMax), ...
    sprintf('eEb=%.10g',p.etaEb), sprintf('RupEb=%.10g',p.RampUpEb), sprintf('RdnEb=%.10g',p.RampDnEb), sprintf('cREb=%.10g',p.cRampEb), ...
    sprintf('PelM=%.10g',p.PelecMax), sprintf('eEl=%.10g',p.etaElec), ...
    sprintf('RupEl=%.10g',p.RampUpElec), sprintf('RdnEl=%.10g',p.RampDnElec), sprintf('cREl=%.10g',p.cRampElec), ...
    sprintf('H2fc=%.10g',p.H2fcMax), sprintf('eFc=%.10g',p.etaFc), ...
    sprintf('RupFc=%.10g',p.RampUpFc), sprintf('RdnFc=%.10g',p.RampDnFc), sprintf('cRFc=%.10g',p.cRampFc), ...
    sprintf('PcompM=%.10g',p.PcompMax), sprintf('RupCmp=%.10g',p.RampUpComp), sprintf('RdnCmp=%.10g',p.RampDnComp), sprintf('cRCmp=%.10g',p.cRampComp), ...
    sprintf('HchM=%.10g',p.HchMax), ...
    sprintf('HdiM=%.10g',p.HdisMax), sprintf('EthM=%.10g',p.EthMax), sprintf('S0th=%.10g',p.SOC0_th), ...
    sprintf('eCt=%.10g',p.etaCh_th), sprintf('eDt=%.10g',p.etaDis_th), sprintf('H2cM=%.10g',p.H2chMax), ...
    sprintf('H2dM=%.10g',p.H2disMax), sprintf('EH2M=%.10g',p.EH2Max), sprintf('S0h2=%.10g',p.SOC0_h2), ...
    sprintf('tSe=%.10g',p.termSOC_e), sprintf('tSth=%.10g',p.termSOC_th), sprintf('tSh2=%.10g',p.termSOC_h2), ...
    sprintf('PgM=%.10g',p.PgridMax), sprintf('lPVC=%.10g',p.lambdaPVCurt), sprintf('lWC=%.10g',p.lambdaWindCurt), ...
    sprintf('lH2=%.10g',p.lambdaH2Short), sprintf('QpvM=%.10g',p.QpvMax), sprintf('QesM=%.10g',p.QesMax), ...
    sprintf('lQp=%.10g',p.lambdaQpv), sprintf('lQe=%.10g',p.lambdaQes), sprintf('Qcomp=%.10g',p.QcompCoeff), ...
    sprintf('zetaE=%.10g',p.zetaE), sprintf('zetaH=%.10g',p.zetaH), ...
    sprintf('chiE=%.10g',p.chiE), sprintf('chiH=%.10g',p.chiH), sprintf('ceh=%.10g',p.ceh), ...
    sprintf('qGr=%.10g',p.quotaGridRatio), sprintf('qGa=%.10g',p.quotaGasRatio), ...
    sprintf('cb=%.10g',p.carbonBuyPrice), sprintf('cs=%.10g',p.carbonSellPrice)}, '|');
end

function s = local_sig(x)
sz = size(x); x = double(x(:));
if isempty(x), s = sprintf('sz=%s;n=0',mat2str(sz)); return; end
s = sprintf('sz=%s;n=%d;s1=%.16g;s2=%.16g;mn=%.16g;mx=%.16g', ...
    mat2str(sz),numel(x),sum(x),sum(x.^2),min(x),max(x));
end

function cache = local_compile_optimizer(p)
T = p.T;
% P2 acceleration: parameterize all scenario-varying time series.
% Keep these as row vectors to match the 1-by-T decision variables.
cPPar = sdpvar(1,T,'full');
cQPar = sdpvar(1,T,'full');
cCPar = sdpvar(1,T,'full');
PloadPar = sdpvar(1,T,'full');
HloadPar = sdpvar(1,T,'full');
H2loadPar = sdpvar(1,T,'full');
PpvPar = sdpvar(1,T,'full');
PwindPar = sdpvar(1,T,'full');
PcompFixedPar = sdpvar(1,T,'full');
cePar = sdpvar(1,T,'full');
fixedCarbonQuotaPar = sdpvar(1,T,'full');
paramVars = [cPPar(:); cQPar(:); cCPar(:); PloadPar(:); HloadPar(:); H2loadPar(:); ...
             PpvPar(:); PwindPar(:); PcompFixedPar(:); cePar(:); fixedCarbonQuotaPar(:)];

% ===== CHP default-compatible parameters =====
PchpMin = local_getfield(p,'PchpMin',0.35*p.PchpRated);
uChp0 = local_getfield(p,'uChp0',0);
RampUpCHP = local_getfield(p,'RampUpCHP',0.30*p.PchpRated);
RampDnCHP = local_getfield(p,'RampDnCHP',0.30*p.PchpRated);
StartUpCHP = local_getfield(p,'StartUpCHP',80);
ShutDnCHP  = local_getfield(p,'ShutDnCHP',20);
MinUpCHP   = max(1, round(local_getfield(p,'MinUpCHP',2)));
MinDnCHP   = max(1, round(local_getfield(p,'MinDnCHP',2)));
cOM_CHP    = local_getfield(p,'cOM_CHP',8);
cRampCHP   = local_getfield(p,'cRampCHP',2);
lambdaHdump = local_getfield(p,'lambdaHdump',200);
FgasMinEff = max(p.FgasMin, PchpMin / max(p.etaE_chp,1e-6));
minChpHeatShare = local_getfield(p,'minChpHeatShare',0);
hasFixedCarbonQuota = ~isempty(local_getfield(p,'fixedCarbonQuota_kg',[]));
RampUpEb = local_getfield(p,'RampUpEb',p.PebMax);
RampDnEb = local_getfield(p,'RampDnEb',p.PebMax);
cRampEb = local_getfield(p,'cRampEb',0);
RampUpElec = local_getfield(p,'RampUpElec',p.PelecMax);
RampDnElec = local_getfield(p,'RampDnElec',p.PelecMax);
cRampElec = local_getfield(p,'cRampElec',0);
RampUpFc = local_getfield(p,'RampUpFc',p.etaFc*p.H2fcMax);
RampDnFc = local_getfield(p,'RampDnFc',p.etaFc*p.H2fcMax);
cRampFc = local_getfield(p,'cRampFc',0);
PcompMax = local_getfield(p,'PcompMax',max(p.PcompFixed) + p.alphaCompH2*p.etaElec*p.PelecMax);
RampUpComp = local_getfield(p,'RampUpComp',PcompMax);
RampDnComp = local_getfield(p,'RampDnComp',PcompMax);
cRampComp = local_getfield(p,'cRampComp',0);

% Decision variables
Pgrid=sdpvar(1,T); Pch=sdpvar(1,T); Pdis=sdpvar(1,T); SOC_e=sdpvar(1,T);
PpvUse=sdpvar(1,T); PpvCurt=sdpvar(1,T); PwindUse=sdpvar(1,T); PwindCurt=sdpvar(1,T);
uCh=binvar(1,T);
Fgas=sdpvar(1,T); Pchp=sdpvar(1,T); Hchp=sdpvar(1,T);
uChp=binvar(1,T); vStart=binvar(1,T); vStop=binvar(1,T);
RupChp=sdpvar(1,T); RdnChp=sdpvar(1,T); Hdump=sdpvar(1,T);
Peb=sdpvar(1,T); Heb=sdpvar(1,T); RupEb=sdpvar(1,T); RdnEb=sdpvar(1,T);
Pelec=sdpvar(1,T); H2prod=sdpvar(1,T); RupElec=sdpvar(1,T); RdnElec=sdpvar(1,T);
H2cons_fc=sdpvar(1,T); Pfc=sdpvar(1,T); RupFc=sdpvar(1,T); RdnFc=sdpvar(1,T);
Pcomp=sdpvar(1,T); RupComp=sdpvar(1,T); RdnComp=sdpvar(1,T);
Hch=sdpvar(1,T); Hdis=sdpvar(1,T); SOC_th=sdpvar(1,T);
H2ch=sdpvar(1,T); H2dis=sdpvar(1,T); SOC_h2=sdpvar(1,T);
H2short=sdpvar(1,T);
uHch=binvar(1,T);   % 1: charging heat, 0: discharging heat
uH2ch=binvar(1,T);  % 1: charging hydrogen, 0: discharging hydrogen
    Qpv=sdpvar(1,T); Qes=sdpvar(1,T); QinjLocal=sdpvar(1,T); PinjLocal=sdpvar(1,T);
    QaBuy=sdpvar(1,T); QaSell=sdpvar(1,T); QtradeLocal=sdpvar(1,T); QaUnused=sdpvar(1,T);

F = [];
F = [F, Pgrid>=0, Pch>=0, Pdis>=0, SOC_e>=0.1*p.Emax, PpvUse>=0, PpvCurt>=0];
F = [F, PwindUse>=0, PwindCurt>=0, 0<=uCh, uCh<=1];
F = [F, PpvUse<=PpvPar, PpvCurt<=PpvPar, PwindUse<=PwindPar, PwindCurt<=PwindPar];
F = [F, Pch<=p.PchMax*uCh, Pdis<=p.PdisMax*(1-uCh)];
F = [F, SOC_e<=0.9*p.Emax, Pgrid<=p.PgridMax];

% CHP
F = [F, 0<=uChp, uChp<=1, 0<=vStart, vStart<=1, 0<=vStop, vStop<=1];
F = [F, vStart + vStop <= 1, RupChp>=0, RdnChp>=0, Hdump>=0];
F = [F, Fgas>=0, Fgas<=p.FgasMax*uChp, Fgas>=FgasMinEff*uChp];
F = [F, Pchp==p.etaE_chp*Fgas, Hchp==p.etaH_chp*Fgas];
F = [F, Pchp<=p.PchpRated*uChp, Pchp>=PchpMin*uChp];

F = [F, Peb>=0, Peb<=p.PebMax, Heb==p.etaEb*Peb, RupEb>=0, RdnEb>=0];
F = [F, Pelec>=0, Pelec<=p.PelecMax, H2prod==p.etaElec*Pelec, RupElec>=0, RdnElec>=0];
F = [F, H2cons_fc>=0, H2cons_fc<=p.H2fcMax, Pfc==p.etaFc*H2cons_fc, RupFc>=0, RdnFc>=0];
F = [F, Pcomp==PcompFixedPar + p.alphaCompH2*H2prod, Pcomp>=0, Pcomp<=PcompMax, RupComp>=0, RdnComp>=0];

F = [F, Hch>=0, Hdis>=0];
F = [F, SOC_th>=0.1*p.EthMax, SOC_th<=0.9*p.EthMax];
F = [F, Hch<=p.HchMax*uHch, Hdis<=p.HdisMax*(1-uHch)];
F = [F, H2ch>=0, H2dis>=0, SOC_h2>=0.1*p.EH2Max, SOC_h2<=0.9*p.EH2Max];
F = [F, H2ch<=p.H2chMax*uH2ch, H2dis<=p.H2disMax*(1-uH2ch)];
    F = [F, H2short>=0, H2short<=H2loadPar];
    F = [F, -p.QpvMax<=Qpv, Qpv<=p.QpvMax, -p.QesMax<=Qes, Qes<=p.QesMax];
    F = [F, QaBuy>=0, QaSell>=0, QaUnused>=0];
    if ~logical(p.enableCarbonQuota)
        F = [F, QaBuy==0, QaSell==0, QtradeLocal==0, QaUnused==0];
    else
        if ~logical(p.enableCommunityCarbonTrading)
            F = [F, QtradeLocal==0];
        elseif T > 1
            F = [F, QtradeLocal(2:T)==0];
        end
        if ~logical(p.allowCarbonMarketSell)
            F = [F, QaSell==0];
        end
    end

    Obj = 0;
for t = 1:T
    % CHP logic and ramp
    if t == 1
        F = [F, uChp(t) - uChp0 == vStart(t) - vStop(t)];
    else
        F = [F, uChp(t) - uChp(t-1) == vStart(t) - vStop(t)];
        F = [F, Pchp(t) - Pchp(t-1) <= RampUpCHP];
        F = [F, Pchp(t-1) - Pchp(t) <= RampDnCHP];
        F = [F, RupChp(t) >= Pchp(t) - Pchp(t-1)];
        F = [F, RdnChp(t) >= Pchp(t-1) - Pchp(t)];
        F = [F, Peb(t) - Peb(t-1) <= RampUpEb, Peb(t-1) - Peb(t) <= RampDnEb];
        F = [F, RupEb(t) >= Peb(t) - Peb(t-1), RdnEb(t) >= Peb(t-1) - Peb(t)];
        F = [F, Pelec(t) - Pelec(t-1) <= RampUpElec, Pelec(t-1) - Pelec(t) <= RampDnElec];
        F = [F, RupElec(t) >= Pelec(t) - Pelec(t-1), RdnElec(t) >= Pelec(t-1) - Pelec(t)];
        F = [F, Pfc(t) - Pfc(t-1) <= RampUpFc, Pfc(t-1) - Pfc(t) <= RampDnFc];
        F = [F, RupFc(t) >= Pfc(t) - Pfc(t-1), RdnFc(t) >= Pfc(t-1) - Pfc(t)];
        F = [F, Pcomp(t) - Pcomp(t-1) <= RampUpComp, Pcomp(t-1) - Pcomp(t) <= RampDnComp];
        F = [F, RupComp(t) >= Pcomp(t) - Pcomp(t-1), RdnComp(t) >= Pcomp(t-1) - Pcomp(t)];
    end

    if t==1
        F = [F, SOC_e(t)==p.SOC0_e + p.etaCh_e*Pch(t)*p.dt - (1/p.etaDis_e)*Pdis(t)*p.dt];
        F = [F, SOC_th(t)==p.SOC0_th + p.etaCh_th*Hch(t)*p.dt - (1/p.etaDis_th)*Hdis(t)*p.dt];
        F = [F, SOC_h2(t)==p.SOC0_h2 + (H2ch(t)-H2dis(t))*p.dt];
    else
        F = [F, SOC_e(t)==SOC_e(t-1) + p.etaCh_e*Pch(t)*p.dt - (1/p.etaDis_e)*Pdis(t)*p.dt];
        F = [F, SOC_th(t)==SOC_th(t-1) + p.etaCh_th*Hch(t)*p.dt - (1/p.etaDis_th)*Hdis(t)*p.dt];
        F = [F, SOC_h2(t)==SOC_h2(t-1) + (H2ch(t)-H2dis(t))*p.dt];
    end
    F = [F, H2prod(t)+H2dis(t)+H2short(t)==H2loadPar(t)+H2cons_fc(t)+H2ch(t)];

    F = [F, PpvUse(t)+PpvCurt(t)==PpvPar(t)];
    F = [F, PwindUse(t)+PwindCurt(t)==PwindPar(t)];
    F = [F, Pgrid(t)+PpvUse(t)+PwindUse(t)+Pchp(t)+Pfc(t)+Pdis(t) ...
         == PloadPar(t)+Peb(t)+Pelec(t)+Pch(t)+Pcomp(t)];
    F = [F, PinjLocal(t)==Pgrid(t)];
    F = [F, QinjLocal(t)==p.Qbase(t)+p.QcompCoeff*Pcomp(t)-Qpv(t)-Qes(t)];
    F = [F, PpvUse(t)^2+Qpv(t)^2<=p.QpvMax^2 + 1e-6];
    F = [F, (Pdis(t)-Pch(t))^2+Qes(t)^2<=p.QesMax^2 + 1e-6];

    F = [F, Hchp(t)+Heb(t)+Hdis(t)==HloadPar(t)+Hch(t)+Hdump(t)];

    if logical(p.enableCarbonQuota)
        Obj = Obj + (p.carbonBuyPrice/1000)*QaBuy(t) - (p.carbonSellPrice/1000)*QaSell(t);
    end

    Obj = Obj + cePar(t)*Pgrid(t)*p.dt;
    Obj = Obj + p.cGas*Fgas(t)*p.dt;
    Obj = Obj + lambdaHdump*Hdump(t)*p.dt;
    Obj = Obj + cOM_CHP*Pchp(t)*p.dt;
    Obj = Obj + StartUpCHP*vStart(t) + ShutDnCHP*vStop(t);
    Obj = Obj + cRampCHP*(RupChp(t)+RdnChp(t));
    Obj = Obj + cRampEb*(RupEb(t)+RdnEb(t)) + cRampElec*(RupElec(t)+RdnElec(t)) + ...
        cRampFc*(RupFc(t)+RdnFc(t)) + cRampComp*(RupComp(t)+RdnComp(t));
    Obj = Obj + p.lambdaPVCurt*PpvCurt(t)*p.dt;
    Obj = Obj + p.lambdaWindCurt*PwindCurt(t)*p.dt;
    Obj = Obj + p.lambdaH2Short*H2short(t)*p.dt;
    Obj = Obj + (p.lambdaQpv*Qpv(t)^2 + p.lambdaQes*Qes(t)^2)*p.dt;
end

if minChpHeatShare > 0
    F = [F, sum(Hchp)*p.dt >= minChpHeatShare * sum(HloadPar)*p.dt];
end

if logical(p.enableCarbonQuota)
    emission_day = 0;
    quota_day = 0;
    for t = 1:T
        chpHeatEquivalent_t = p.ceh*Pchp(t) + Hchp(t);
        emission_day = emission_day + p.zetaE*Pgrid(t)*p.dt + p.zetaH*chpHeatEquivalent_t*p.dt;
        if ~hasFixedCarbonQuota
            quota_day = quota_day + p.chiE*Pgrid(t)*p.dt + p.chiH*chpHeatEquivalent_t*p.dt;
        else
            quota_day = quota_day + fixedCarbonQuotaPar(t);
        end
    end
    F = [F, quota_day + sum(QaBuy) + sum(QtradeLocal) == emission_day + sum(QaSell) + sum(QaUnused)];
end

for t = MinUpCHP:T
    F = [F, sum(vStart(t-MinUpCHP+1:t)) <= uChp(t)];
end
for t = MinDnCHP:T
    F = [F, sum(vStop(t-MinDnCHP+1:t)) <= 1 - uChp(t)];
end

% Cyclic end-of-day storage constraints
F = [F, SOC_e(T)  == p.termSOC_e];
F = [F, SOC_th(T) == p.termSOC_th];
F = [F, SOC_h2(T) == p.termSOC_h2];

% ADMM augmentation
for t = 1:T
    Obj = Obj + 0.5*p.rhoPQ*(PinjLocal(t)^2) + cPPar(t)*PinjLocal(t);
    Obj = Obj + 0.5*p.rhoPQ*(QinjLocal(t)^2) + cQPar(t)*QinjLocal(t);
    Obj = Obj + 0.5*p.rhoC*(QtradeLocal(t)^2) + cCPar(t)*QtradeLocal(t);
end

Obj_base = 0;
for t = 1:T
    if logical(p.enableCarbonQuota)
        Obj_base = Obj_base + (p.carbonBuyPrice/1000)*QaBuy(t) - (p.carbonSellPrice/1000)*QaSell(t);
    end
    Obj_base = Obj_base + cePar(t)*Pgrid(t)*p.dt;
    Obj_base = Obj_base + p.cGas*Fgas(t)*p.dt;
    Obj_base = Obj_base + lambdaHdump*Hdump(t)*p.dt;
    Obj_base = Obj_base + cOM_CHP*Pchp(t)*p.dt;
    Obj_base = Obj_base + StartUpCHP*vStart(t) + ShutDnCHP*vStop(t);
    Obj_base = Obj_base + cRampCHP*(RupChp(t)+RdnChp(t));
    Obj_base = Obj_base + cRampEb*(RupEb(t)+RdnEb(t)) + cRampElec*(RupElec(t)+RdnElec(t)) + ...
        cRampFc*(RupFc(t)+RdnFc(t)) + cRampComp*(RupComp(t)+RdnComp(t));
    Obj_base = Obj_base + p.lambdaPVCurt*PpvCurt(t)*p.dt;
    Obj_base = Obj_base + p.lambdaWindCurt*PwindCurt(t)*p.dt;
    Obj_base = Obj_base + p.lambdaH2Short*H2short(t)*p.dt;
    Obj_base = Obj_base + (p.lambdaQpv*Qpv(t)^2 + p.lambdaQes*Qes(t)^2)*p.dt;
end

ops = sdpsettings('solver','gurobi','verbose',0,'warning',0,'cachesolvers',1);
wantedVec = [Pgrid(:);Pch(:);Pdis(:);SOC_e(:);PpvUse(:);PpvCurt(:);PwindUse(:);PwindCurt(:); ...
             uCh(:);Fgas(:);Pchp(:);Hchp(:);uChp(:);vStart(:);vStop(:);RupChp(:);RdnChp(:);Hdump(:); ...
             Peb(:);Heb(:);RupEb(:);RdnEb(:);Pelec(:);H2prod(:);RupElec(:);RdnElec(:); ...
             H2cons_fc(:);Pfc(:);RupFc(:);RdnFc(:);Pcomp(:);RupComp(:);RdnComp(:); ...
             Hch(:);Hdis(:);SOC_th(:);H2ch(:);H2dis(:);SOC_h2(:);H2short(:); ...
             Qpv(:);Qes(:);QinjLocal(:);PinjLocal(:);QaBuy(:);QaSell(:);QtradeLocal(:);QaUnused(:);Obj_base(:)];
cache.opt = optimizer(F, Obj, ops, paramVars, wantedVec);
cache.T = T;
cache.ns = struct('nPgrid',T,'nPch',T,'nPdis',T,'nSOC_e',T,'nPpvUse',T,'nPpvCurt',T, ...
    'nPwindUse',T,'nPwindCurt',T,'nuCh',T,'nFgas',T,'nPchp',T,'nHchp',T, ...
    'nuChp',T,'nvStart',T,'nvStop',T,'nRupChp',T,'nRdnChp',T,'nHdump',T, ...
    'nPeb',T,'nHeb',T,'nRupEb',T,'nRdnEb',T,'nPelec',T,'nH2prod',T,'nRupElec',T,'nRdnElec',T, ...
    'nH2cons_fc',T,'nPfc',T,'nRupFc',T,'nRdnFc',T,'nPcomp',T,'nRupComp',T,'nRdnComp',T, ...
    'nHch',T,'nHdis',T,'nSOC_th',T, ...
    'nH2ch',T,'nH2dis',T,'nSOC_h2',T, ...
    'nH2short',T,'nQpv',T,'nQes',T,'nQinjLocal',T,'nPinjLocal',T, ...
    'nQaBuy',T,'nQaSell',T,'nQtradeLocal',T,'nQaUnused',T,'nBaseObj',1);
end

function paramVec = local_pack_parameters(p)
T = p.T;
cP = reshape(p.lambdaP(:)-p.rhoPQ*p.zP(:),T,1);
cQ = reshape(p.lambdaQ(:)-p.rhoPQ*p.zQ(:),T,1);
cC = reshape(p.lambdaC(:)-p.rhoC*p.zC(:),T,1);
Pload = reshape(p.Pload(:),T,1);
Hload = reshape(p.Hload(:),T,1);
H2load = reshape(p.H2load(:),T,1);
Ppv = reshape(p.Ppv(:),T,1);
Pwind = reshape(p.Pwind(:),T,1);
PcompFixed = reshape(p.PcompFixed(:),T,1);
ce = reshape(p.ce(:),T,1);
fixedCarbonQuota_kg = local_getfield(p,'fixedCarbonQuota_kg',[]);
if isempty(fixedCarbonQuota_kg)
    fixedQuota = zeros(T,1);
else
    fixedQuota = reshape(fixedCarbonQuota_kg(:),T,1);
end
paramVec = [cP; cQ; cC; Pload; Hload; H2load; Ppv; Pwind; PcompFixed; ce; fixedQuota];
end

function [x,idx] = local_take(vec,idx,n)
x=vec(idx:idx+n-1); idx=idx+n;
end

function out = local_unpack_solution(solVec, p, cache)
T = cache.T; meta = cache.ns; idx = 1;
[tmp,idx]=local_take(solVec,idx,meta.nPgrid); out.Pgrid=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPch); out.Pch=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPdis); out.Pdis=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nSOC_e); out.SOC_e=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPpvUse); out.PpvUse=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPpvCurt); out.PpvCurt=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPwindUse); out.PwindUse=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPwindCurt); out.PwindCurt=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nuCh); out.uCh=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nFgas); out.Fgas=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPchp); out.Pchp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nHchp); out.Hchp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nuChp); out.uChp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nvStart); out.vStart=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nvStop); out.vStop=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRupChp); out.RupChp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRdnChp); out.RdnChp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nHdump); out.Hdump=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPeb); out.Peb=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nHeb); out.Heb=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRupEb); out.RupEb=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRdnEb); out.RdnEb=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPelec); out.Pelec=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2prod); out.H2prod=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRupElec); out.RupElec=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRdnElec); out.RdnElec=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2cons_fc); out.H2cons_fc=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPfc); out.Pfc=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRupFc); out.RupFc=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRdnFc); out.RdnFc=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPcomp); out.Pcomp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRupComp); out.RupComp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nRdnComp); out.RdnComp=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nHch); out.Hch=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nHdis); out.Hdis=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nSOC_th); out.SOC_th=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2ch); out.H2ch=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2dis); out.H2dis=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nSOC_h2); out.SOC_h2=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2short); out.H2short=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQpv); out.Qpv=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQes); out.Qes=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQinjLocal); out.QinjLocal=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPinjLocal); out.PinjLocal=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQaBuy); out.QaBuy=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQaSell); out.QaSell=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQtradeLocal); out.QtradeLocal=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nQaUnused); out.QaUnused=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nBaseObj); out.baseObj=tmp(1);
if idx-1~=numel(solVec)
    error('Unexpected packed solution length for community %d.',p.idx);
end
end

function val = local_getfield(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end
