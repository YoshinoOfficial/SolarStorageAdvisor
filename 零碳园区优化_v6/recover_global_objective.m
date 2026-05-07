function [obj, parts] = recover_global_objective(data, sol)
% Rebuild the global objective using the same accounting logic as the
% centralized / local models.
%
% Unit convention adopted in this patch:
%   - electricity / gas / curtailment / heat-dump O&M energy terms: Yuan/MWh
%   - gas / grid emission factors: kgCO2/MWh
%   - startup / shutdown: Yuan/start, Yuan/stop
%   - ramp penalty: Yuan/MW-change
%   - hydrogen shortage: Yuan/kg
%   - reactive support penalty: Yuan/(MVAr^2*h)

N  = data.N;
T  = data.T;
dt = data.dt;

% Default-compatible CHP parameters (must match solve_centralized.m / solve_local_subproblem.m)
StartUpCHP  = i_get_field(data, 'StartUpCHP', 80  * ones(N,1));
ShutDnCHP   = i_get_field(data, 'ShutDnCHP',  20  * ones(N,1));
cOM_CHP     = i_get_field(data, 'cOM_CHP',     8  * ones(N,1));
cRampCHP    = i_get_field(data, 'cRampCHP',    2  * ones(N,1));
lambdaHdump = i_get_field(data, 'lambdaHdump', 200 * ones(N,1));
enableCarbonQuota = logical(i_get_field(data, 'enableCarbonQuota', i_get_field(data, 'enableCarbonTrading', false)));
carbonBuyPrice = i_get_field(data, 'carbonBuyPrice', 200);
carbonSellPrice = i_get_field(data, 'carbonSellPrice', 100);

gridCost      = 0;
carbonCost    = 0;
gasCost       = 0;
gasCarbonCost = 0;
hdumpCost     = 0;
chpOMCost     = 0;
startupCost   = 0;
shutdownCost  = 0;
rampCost      = 0;
pvCurtCost    = 0;
windCurtCost  = 0;
h2ShortCost   = 0;
qSupportCost  = 0;
carbonTradingCost = 0;

if iscell(sol)
    for i = 1:N
        si = sol{i};
        for t = 1:T
            gridCost      = gridCost      + data.ce(i,t)      * si.Pgrid(t)    * dt;
            gasCost       = gasCost       + data.cGas         * si.Fgas(t)     * dt;
            if enableCarbonQuota && isfield(si, 'QaBuy') && isfield(si, 'QaSell')
                carbonTradingCost = carbonTradingCost + (carbonBuyPrice/1000)*si.QaBuy(t) - (carbonSellPrice/1000)*si.QaSell(t);
            end
            hdumpCost     = hdumpCost     + lambdaHdump(i)    * si.Hdump(t)    * dt;
            chpOMCost     = chpOMCost     + cOM_CHP(i)        * si.Pchp(t)     * dt;
            startupCost   = startupCost   + StartUpCHP(i)     * si.vStart(t);
            shutdownCost  = shutdownCost  + ShutDnCHP(i)      * si.vStop(t);
            rampCost      = rampCost      + cRampCHP(i)       * (si.RupChp(t) + si.RdnChp(t));
            pvCurtCost    = pvCurtCost    + data.lambdaPVCurt(i)   * si.PpvCurt(t)   * dt;
            windCurtCost  = windCurtCost  + data.lambdaWindCurt(i) * si.PwindCurt(t) * dt;
            h2ShortCost   = h2ShortCost   + data.lambdaH2Short(i)  * si.H2short(t)   * dt;
            qSupportCost  = qSupportCost  + (data.lambdaQpv(i) * si.Qpv(t)^2 + data.lambdaQes(i) * si.Qes(t)^2) * dt;
        end
    end
else
    for i = 1:N
        for t = 1:T
            gridCost      = gridCost      + data.ce(i,t)      * sol.Pgrid(i,t)    * dt;
            gasCost       = gasCost       + data.cGas         * sol.Fgas(i,t)     * dt;
            if enableCarbonQuota && isfield(sol, 'QaBuy') && isfield(sol, 'QaSell')
                carbonTradingCost = carbonTradingCost + (carbonBuyPrice/1000)*sol.QaBuy(i,t) - (carbonSellPrice/1000)*sol.QaSell(i,t);
            end
            hdumpCost     = hdumpCost     + lambdaHdump(i)    * sol.Hdump(i,t)    * dt;
            chpOMCost     = chpOMCost     + cOM_CHP(i)        * sol.Pchp(i,t)     * dt;
            startupCost   = startupCost   + StartUpCHP(i)     * sol.vStart(i,t);
            shutdownCost  = shutdownCost  + ShutDnCHP(i)      * sol.vStop(i,t);
            rampCost      = rampCost      + cRampCHP(i)       * (sol.RupChp(i,t) + sol.RdnChp(i,t));
            pvCurtCost    = pvCurtCost    + data.lambdaPVCurt(i)   * sol.PpvCurt(i,t)   * dt;
            windCurtCost  = windCurtCost  + data.lambdaWindCurt(i) * sol.PwindCurt(i,t) * dt;
            h2ShortCost   = h2ShortCost   + data.lambdaH2Short(i)  * sol.H2short(i,t)   * dt;
            qSupportCost  = qSupportCost  + (data.lambdaQpv(i) * sol.Qpv(i,t)^2 + data.lambdaQes(i) * sol.Qes(i,t)^2) * dt;
        end
    end
end

obj = gridCost + carbonCost + gasCost + gasCarbonCost + carbonTradingCost + hdumpCost + chpOMCost + ...
      startupCost + shutdownCost + rampCost + pvCurtCost + windCurtCost + ...
      h2ShortCost + qSupportCost;

parts = struct(...
    'gridCost',       gridCost, ...
    'carbonCost',     carbonCost, ...
    'gasCost',        gasCost, ...
    'gasCarbonCost',  gasCarbonCost, ...
    'carbonTradingCost', carbonTradingCost, ...
    'hdumpCost',      hdumpCost, ...
    'chpOMCost',      chpOMCost, ...
    'startupCost',    startupCost, ...
    'shutdownCost',   shutdownCost, ...
    'rampCost',       rampCost, ...
    'pvCurtCost',     pvCurtCost, ...
    'windCurtCost',   windCurtCost, ...
    'h2ShortCost',    h2ShortCost, ...
    'qSupportCost',   qSupportCost);
end

function val = i_get_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end
