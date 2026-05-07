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
if numel(p.pCO2) > 1
    pco2sig = local_sig(p.pCO2);
else
    pco2sig = sprintf('scalar=%.10g', p.pCO2);
end
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
    minChpHeatShare = local_getfield(p,'minChpHeatShare',0);
    FgasMinEff = max(p.FgasMin, PchpMin / max(p.etaE_chp,1e-6));

    key = strjoin({ ...
        sprintf('idx=%d',p.idx), sprintf('T=%d',p.T), sprintf('rhoPQ=%.10g',p.rhoPQ), ...
        sprintf('rhoC=%.10g',p.rhoC), sprintf('carbon=%d',enableCarbonQuota), ...
        sprintf('commCarbon=%d',enableCommunityCarbonTrading), sprintf('sellCarbon=%d',allowCarbonMarketSell), ...
        ['ce=' local_sig(p.ce)], ['cC=' local_sig(p.cCarbon)], ...
        ['Pld=' local_sig(p.Pload)], ['Hld=' local_sig(p.Hload)], ['H2ld=' local_sig(p.H2load)], ...
        ['Ppv=' local_sig(p.Ppv)], ['Pw=' local_sig(p.Pwind)], ['PcF=' local_sig(p.PcompFixed)], ...
        sprintf('PchM=%.10g',p.PchMax), sprintf('PdisM=%.10g',p.PdisMax), sprintf('Emax=%.10g',p.Emax), ...
        sprintf('S0e=%.10g',p.SOC0_e), sprintf('eCe=%.10g',p.etaCh_e), sprintf('eDe=%.10g',p.etaDis_e), ...
        sprintf('PchpR=%.10g',p.PchpRated), sprintf('PchpMin=%.10g',PchpMin), sprintf('u0=%.10g',uChp0), ...
        sprintf('eEc=%.10g',p.etaE_chp), sprintf('eHc=%.10g',p.etaH_chp), sprintf('FgMinEff=%.10g',FgasMinEff), ...
        sprintf('FgMax=%.10g',p.FgasMax), sprintf('Rup=%.10g',RampUpCHP), sprintf('Rdn=%.10g',RampDnCHP), ...
        sprintf('SU=%.10g',StartUpCHP), sprintf('SD=%.10g',ShutDnCHP), sprintf('MU=%d',MinUpCHP), sprintf('MD=%d',MinDnCHP), ...
        sprintf('cOM=%.10g',cOM_CHP), sprintf('cRp=%.10g',cRampCHP), sprintf('lHd=%.10g',lambdaHdump), ...
        sprintf('minChpHeatShare=%.10g',minChpHeatShare), ...
        sprintf('cG=%.10g',p.cGas), sprintf('efG=%.10g',p.efGas), sprintf('PebM=%.10g',p.PebMax), ...
        sprintf('eEb=%.10g',p.etaEb), sprintf('PelM=%.10g',p.PelecMax), sprintf('eEl=%.10g',p.etaElec), ...
        sprintf('H2fc=%.10g',p.H2fcMax), sprintf('eFc=%.10g',p.etaFc), sprintf('HchM=%.10g',p.HchMax), ...
        sprintf('HdiM=%.10g',p.HdisMax), sprintf('EthM=%.10g',p.EthMax), sprintf('S0th=%.10g',p.SOC0_th), ...
        sprintf('eCt=%.10g',p.etaCh_th), sprintf('eDt=%.10g',p.etaDis_th), sprintf('H2cM=%.10g',p.H2chMax), ...
        sprintf('H2dM=%.10g',p.H2disMax), sprintf('EH2M=%.10g',p.EH2Max), sprintf('S0h2=%.10g',p.SOC0_h2), ...
        sprintf('tSe=%.10g',p.termSOC_e), sprintf('tSth=%.10g',p.termSOC_th), sprintf('tSh2=%.10g',p.termSOC_h2), ...
        sprintf('PgM=%.10g',p.PgridMax), sprintf('lPVC=%.10g',p.lambdaPVCurt), sprintf('lWC=%.10g',p.lambdaWindCurt), ...
        sprintf('lH2=%.10g',p.lambdaH2Short), sprintf('QpvM=%.10g',p.QpvMax), sprintf('QesM=%.10g',p.QesMax), ...
        sprintf('lQp=%.10g',p.lambdaQpv), sprintf('lQe=%.10g',p.lambdaQes), sprintf('Qcomp=%.10g',p.QcompCoeff), ...
        ['pCO2=' pco2sig], sprintf('zetaE=%.10g',p.zetaE), sprintf('zetaH=%.10g',p.zetaH), ...
        sprintf('chiE=%.10g',p.chiE), sprintf('chiH=%.10g',p.chiH), sprintf('ceh=%.10g',p.ceh), ...
        ['fixedQ=' local_sig(fixedCarbonQuota_kg)], ...
        ['efGrid=' local_sig(p.efGrid)], sprintf('qGr=%.10g',p.quotaGridRatio), sprintf('qGa=%.10g',p.quotaGasRatio), ...
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
    paramVars = [sdpvar(T,1,'full'); sdpvar(T,1,'full'); sdpvar(T,1,'full')]; % cPPar, cQPar, cCPar

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
fixedCarbonQuota_kg = local_getfield(p,'fixedCarbonQuota_kg',[]);
minChpHeatShare = local_getfield(p,'minChpHeatShare',0);

% Decision variables
Pgrid=sdpvar(1,T); Pch=sdpvar(1,T); Pdis=sdpvar(1,T); SOC_e=sdpvar(1,T);
PpvUse=sdpvar(1,T); PpvCurt=sdpvar(1,T); PwindUse=sdpvar(1,T); PwindCurt=sdpvar(1,T);
uCh=binvar(1,T);
Fgas=sdpvar(1,T); Pchp=sdpvar(1,T); Hchp=sdpvar(1,T);
uChp=binvar(1,T); vStart=binvar(1,T); vStop=binvar(1,T);
RupChp=sdpvar(1,T); RdnChp=sdpvar(1,T); Hdump=sdpvar(1,T);
Peb=sdpvar(1,T); Heb=sdpvar(1,T);
Pelec=sdpvar(1,T); H2prod=sdpvar(1,T);
H2cons_fc=sdpvar(1,T); Pfc=sdpvar(1,T);
Hch=sdpvar(1,T); Hdis=sdpvar(1,T); SOC_th=sdpvar(1,T);
H2ch=sdpvar(1,T); H2dis=sdpvar(1,T); SOC_h2=sdpvar(1,T);
H2short=sdpvar(1,T);
uHch=binvar(1,T);   % 1: charging heat, 0: discharging heatH2ch=sdpvar(1,T); H2dis=sdpvar(1,T); SOC_h2=sdpvar(1,T);
H2short=sdpvar(1,T);
    Qpv=sdpvar(1,T); Qes=sdpvar(1,T); QinjLocal=sdpvar(1,T); PinjLocal=sdpvar(1,T);
    QaBuy=sdpvar(1,T); QaSell=sdpvar(1,T); QtradeLocal=sdpvar(1,T); QaUnused=sdpvar(1,T);

F = [];
F = [F, Pgrid>=0, Pch>=0, Pdis>=0, SOC_e>=0.1*p.Emax, PpvUse>=0, PpvCurt>=0];
F = [F, PwindUse>=0, PwindCurt>=0, 0<=uCh, uCh<=1];
F = [F, PpvUse<=p.Ppv, PpvCurt<=p.Ppv, PwindUse<=p.Pwind, PwindCurt<=p.Pwind];
F = [F, Pch<=p.PchMax*uCh, Pdis<=p.PdisMax*(1-uCh)];
F = [F, SOC_e<=0.9*p.Emax, Pgrid<=p.PgridMax];

% CHP
F = [F, 0<=uChp, uChp<=1, 0<=vStart, vStart<=1, 0<=vStop, vStop<=1];
F = [F, vStart + vStop <= 1, RupChp>=0, RdnChp>=0, Hdump>=0];
F = [F, Fgas>=0, Fgas<=p.FgasMax*uChp, Fgas>=FgasMinEff*uChp];
F = [F, Pchp==p.etaE_chp*Fgas, Hchp==p.etaH_chp*Fgas];
F = [F, Pchp<=p.PchpRated*uChp, Pchp>=PchpMin*uChp];

F = [F, Peb>=0, Peb<=p.PebMax, Heb==p.etaEb*Peb];
F = [F, Pelec>=0, Pelec<=p.PelecMax, H2prod==p.etaElec*Pelec];
F = [F, H2cons_fc>=0, H2cons_fc<=p.H2fcMax, Pfc==p.etaFc*H2cons_fc];

F = [F, Hch>=0, Hdis>=0];
F = [F, SOC_th>=0.1*p.EthMax, SOC_th<=0.9*p.EthMax];
F = [F, Hch<=p.HchMax*uHch, Hdis<=p.HdisMax*(1-uHch)];
F = [F, H2ch>=0, H2dis>=0, SOC_h2>=0.1*p.EH2Max, SOC_h2<=0.9*p.EH2Max, H2ch<=p.H2chMax, H2dis<=p.H2disMax];

F = [F, H2ch == 0, H2dis == 0];
    F = [F, H2short>=0];
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
    end

    if t==1
        F = [F, SOC_e(t)==p.SOC0_e + p.etaCh_e*Pch(t)*p.dt - (1/p.etaDis_e)*Pdis(t)*p.dt];
        F = [F, SOC_th(t)==p.SOC0_th + p.etaCh_th*Hch(t)*p.dt - (1/p.etaDis_th)*Hdis(t)*p.dt];
        F = [F, SOC_h2(t)==p.SOC0_h2 + (H2prod(t)-H2cons_fc(t)-p.H2load(t)+H2short(t))*p.dt];
    else
        F = [F, SOC_e(t)==SOC_e(t-1) + p.etaCh_e*Pch(t)*p.dt - (1/p.etaDis_e)*Pdis(t)*p.dt];
        F = [F, SOC_th(t)==SOC_th(t-1) + p.etaCh_th*Hch(t)*p.dt - (1/p.etaDis_th)*Hdis(t)*p.dt];
        F = [F, SOC_h2(t)==SOC_h2(t-1) + (H2prod(t)-H2cons_fc(t)-p.H2load(t)+H2short(t))*p.dt];
    end

    Pcomp = p.PcompFixed(t);

    F = [F, PpvUse(t)+PpvCurt(t)==p.Ppv(t)];
    F = [F, PwindUse(t)+PwindCurt(t)==p.Pwind(t)];
    F = [F, Pgrid(t)+PpvUse(t)+PwindUse(t)+Pchp(t)+Pfc(t)+Pdis(t) ...
         == p.Pload(t)+Peb(t)+Pelec(t)+Pch(t)+Pcomp];
    F = [F, PinjLocal(t)==Pgrid(t)];
    F = [F, QinjLocal(t)==p.Qbase(t)+p.QcompCoeff*Pcomp-Qpv(t)-Qes(t)];
    F = [F, PpvUse(t)^2+Qpv(t)^2<=p.QpvMax^2 + 1e-6];
    F = [F, (Pdis(t)-Pch(t))^2+Qes(t)^2<=p.QesMax^2 + 1e-6];

    F = [F, Hchp(t)+Heb(t)+Hdis(t)==p.Hload(t)+Hch(t)+Hdump(t)];

    if logical(p.enableCarbonQuota)
        Obj = Obj + (p.carbonBuyPrice/1000)*QaBuy(t) - (p.carbonSellPrice/1000)*QaSell(t);
    end

    Obj = Obj + p.ce(t)*Pgrid(t)*p.dt;
    Obj = Obj + p.cGas*Fgas(t)*p.dt;
    Obj = Obj + lambdaHdump*Hdump(t)*p.dt;
    Obj = Obj + cOM_CHP*Pchp(t)*p.dt;
    Obj = Obj + StartUpCHP*vStart(t) + ShutDnCHP*vStop(t);
    Obj = Obj + cRampCHP*(RupChp(t)+RdnChp(t));
    Obj = Obj + p.lambdaPVCurt*PpvCurt(t)*p.dt;
    Obj = Obj + p.lambdaWindCurt*PwindCurt(t)*p.dt;
    Obj = Obj + p.lambdaH2Short*H2short(t)*p.dt;
    Obj = Obj + (p.lambdaQpv*Qpv(t)^2 + p.lambdaQes*Qes(t)^2)*p.dt;
end

if minChpHeatShare > 0
    F = [F, sum(Hchp)*p.dt >= minChpHeatShare * sum(p.Hload)*p.dt];
end

if logical(p.enableCarbonQuota)
    emission_day = 0;
    quota_day = 0;
    for t = 1:T
        chpHeatEquivalent_t = p.ceh*Pchp(t) + Hchp(t);
        emission_day = emission_day + p.zetaE*Pgrid(t)*p.dt + p.zetaH*chpHeatEquivalent_t*p.dt;
        if isempty(fixedCarbonQuota_kg)
            quota_day = quota_day + p.chiE*Pgrid(t)*p.dt + p.chiH*chpHeatEquivalent_t*p.dt;
        else
            quota_day = quota_day + fixedCarbonQuota_kg(t);
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
cPPar = paramVars(1:T); cQPar = paramVars(T+1:2*T); cCPar = paramVars(2*T+1:3*T);
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
    Obj_base = Obj_base + p.ce(t)*Pgrid(t)*p.dt;
    Obj_base = Obj_base + p.cGas*Fgas(t)*p.dt;
    Obj_base = Obj_base + lambdaHdump*Hdump(t)*p.dt;
    Obj_base = Obj_base + cOM_CHP*Pchp(t)*p.dt;
    Obj_base = Obj_base + StartUpCHP*vStart(t) + ShutDnCHP*vStop(t);
    Obj_base = Obj_base + cRampCHP*(RupChp(t)+RdnChp(t));
    Obj_base = Obj_base + p.lambdaPVCurt*PpvCurt(t)*p.dt;
    Obj_base = Obj_base + p.lambdaWindCurt*PwindCurt(t)*p.dt;
    Obj_base = Obj_base + p.lambdaH2Short*H2short(t)*p.dt;
    Obj_base = Obj_base + (p.lambdaQpv*Qpv(t)^2 + p.lambdaQes*Qes(t)^2)*p.dt;
end

ops = sdpsettings('solver','gurobi','verbose',0,'warning',0,'cachesolvers',1);
wantedVec = [Pgrid(:);Pch(:);Pdis(:);SOC_e(:);PpvUse(:);PpvCurt(:);PwindUse(:);PwindCurt(:); ...
             uCh(:);Fgas(:);Pchp(:);Hchp(:);uChp(:);vStart(:);vStop(:);RupChp(:);RdnChp(:);Hdump(:); ...
             Peb(:);Heb(:);Pelec(:);H2prod(:);H2cons_fc(:);Pfc(:); ...
             Hch(:);Hdis(:);SOC_th(:);H2ch(:);H2dis(:);SOC_h2(:);H2short(:); ...
             Qpv(:);Qes(:);QinjLocal(:);PinjLocal(:);QaBuy(:);QaSell(:);QtradeLocal(:);QaUnused(:);Obj_base(:)];
cache.opt = optimizer(F, Obj, ops, paramVars, wantedVec);
cache.T = T;
cache.ns = struct('nPgrid',T,'nPch',T,'nPdis',T,'nSOC_e',T,'nPpvUse',T,'nPpvCurt',T, ...
    'nPwindUse',T,'nPwindCurt',T,'nuCh',T,'nFgas',T,'nPchp',T,'nHchp',T, ...
    'nuChp',T,'nvStart',T,'nvStop',T,'nRupChp',T,'nRdnChp',T,'nHdump',T, ...
    'nPeb',T,'nHeb',T,'nPelec',T,'nH2prod',T, ...
    'nH2cons_fc',T,'nPfc',T,'nHch',T,'nHdis',T,'nSOC_th',T, ...
    'nH2ch',T,'nH2dis',T,'nSOC_h2',T, ...
    'nH2short',T,'nQpv',T,'nQes',T,'nQinjLocal',T,'nPinjLocal',T, ...
    'nQaBuy',T,'nQaSell',T,'nQtradeLocal',T,'nQaUnused',T,'nBaseObj',1);
end

function paramVec = local_pack_parameters(p)
T = p.T;
cP = reshape(p.lambdaP(:)-p.rhoPQ*p.zP(:),T,1);
cQ = reshape(p.lambdaQ(:)-p.rhoPQ*p.zQ(:),T,1);
cC = reshape(p.lambdaC(:)-p.rhoC*p.zC(:),T,1);
paramVec = [cP; cQ; cC];
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
[tmp,idx]=local_take(solVec,idx,meta.nPelec); out.Pelec=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2prod); out.H2prod=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nH2cons_fc); out.H2cons_fc=reshape(tmp,1,T);
[tmp,idx]=local_take(solVec,idx,meta.nPfc); out.Pfc=reshape(tmp,1,T);
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
