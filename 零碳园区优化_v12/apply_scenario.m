function data = apply_scenario(data, scen)
%APPLY_SCENARIO Apply scenario factors to the base day data.
%
% Important modeling convention in this version:
%   pvScale / windScale are interpreted as renewable capacity/penetration
%   scaling factors, not only weather/output-profile multipliers.
%   Therefore, when PV available active power is scaled, the PV inverter
%   reactive capabilities QpvMax and QwindMax are scaled synchronously.
%   This makes high-renewable scenarios represent larger installed renewable
%   capacity and larger inverter/converter apparent-power capability.
%
% Supported fields in scen:
%   name, name_cn
%   pvScale, windScale
%   loadScale       : scale electric/reactive/heat loads together
%   electricLoadScale, heatLoadScale, h2Scale : optional finer controls
%   days            : representative days for annual weighting
%
% Optional advanced fields:
%   pvCapacityScale, windCapacityScale
%       If provided, these are used for equipment-capacity scaling;
%       otherwise pvScale/windScale are used as capacity scaling factors.
%   pvOutputScale, windOutputScale
%       If provided, these are used for available renewable output scaling;
%       otherwise pvScale/windScale are used as output scaling factors.
%
% Notes:
%   1) The optimization model contains PV and wind reactive support variables
%      Qpv and Qwind, so QpvMax and QwindMax are scaled here.
%   2) Positive Qpv/Qwind denotes reactive support injection in the local
%      convention and reduces the net reactive injection demand Qinj.

if nargin < 2 || isempty(scen)
    return;
end

%% Renewable output and capacity scaling
% PV: scale available active power and inverter reactive capability.
if isfield(scen, 'pvOutputScale')
    pvOutputScale = scen.pvOutputScale;
elseif isfield(scen, 'pvScale')
    pvOutputScale = scen.pvScale;
else
    pvOutputScale = 1.0;
end

if isfield(scen, 'pvCapacityScale')
    pvCapacityScale = scen.pvCapacityScale;
elseif isfield(scen, 'pvScale')
    pvCapacityScale = scen.pvScale;
else
    pvCapacityScale = 1.0;
end

if isfield(data, 'Ppv')
    data.Ppv = data.Ppv * pvOutputScale;
end

if isfield(data, 'QpvMax')
    data.QpvMax = data.QpvMax * pvCapacityScale;
end

% Wind: scale available active power and wind converter reactive capability.
if isfield(scen, 'windOutputScale')
    windOutputScale = scen.windOutputScale;
elseif isfield(scen, 'windScale')
    windOutputScale = scen.windScale;
else
    windOutputScale = 1.0;
end

if isfield(scen, 'windCapacityScale')
    windCapacityScale = scen.windCapacityScale;
elseif isfield(scen, 'windScale')
    windCapacityScale = scen.windScale;
else
    windCapacityScale = 1.0;
end

if isfield(data, 'Pwind')
    data.Pwind = data.Pwind * windOutputScale;
end

% Wind reactive-power model: scale apparent/reactive capability.
if isfield(data, 'QwindMax')
    data.QwindMax = data.QwindMax * windCapacityScale;
end

%% Coarse load scaling: electric + reactive + heat.
if isfield(scen, 'loadScale')
    data.Pbase = data.Pbase * scen.loadScale;
    data.Qbase = data.Qbase * scen.loadScale;
    data.PbusBase = data.PbusBase * scen.loadScale;
    data.QbusBase = data.QbusBase * scen.loadScale;
    data.Pload = data.Pload * scen.loadScale;
    data.Hload = data.Hload * scen.loadScale;
end

%% Optional finer load scaling. These are applied after loadScale.
if isfield(scen, 'electricLoadScale')
    data.Pbase = data.Pbase * scen.electricLoadScale;
    data.Qbase = data.Qbase * scen.electricLoadScale;
    data.PbusBase = data.PbusBase * scen.electricLoadScale;
    data.QbusBase = data.QbusBase * scen.electricLoadScale;
    data.Pload = data.Pload * scen.electricLoadScale;
end

if isfield(scen, 'heatLoadScale')
    data.Hload = data.Hload * scen.heatLoadScale;
end

if isfield(scen, 'h2Scale') && isfield(data, 'H2load')
    data.H2load = data.H2load * scen.h2Scale;
end

%% Refresh feeder reactive-injection bounds after load/PV capability changes.
data = refresh_reactive_injection_bounds(data);

%% Scenario metadata
if isfield(scen, 'name')
    data.scenarioName = matlab.lang.makeValidName(scen.name);
else
    data.scenarioName = 'custom';
end

if isfield(scen, 'name_cn')
    data.scenarioNameCN = scen.name_cn;
end

if isfield(scen, 'days')
    data.representativeDays = scen.days;
end
end

function data = refresh_reactive_injection_bounds(data)
% Recompute conservative community reactive injection bounds used by the
% feeder projection after Qbase, QpvMax, QwindMax or QesMax has changed.
if isfield(data, 'Qbase') && isfield(data, 'QpvMax') && isfield(data, 'QesMax')
    N = size(data.Qbase, 1);

    if isfield(data, 'QcompCoeff') && isfield(data, 'PcompMax')
        qCompMax = data.QcompCoeff(:) .* data.PcompMax(:);
    else
        qCompMax = zeros(N, 1);
    end

    data.QinjMax = max(data.Qbase, [], 2) + qCompMax + 0.05;
    data.QinjMin = min(data.Qbase, [], 2) - data.QpvMax(:) - data.QesMax(:) + 0*qCompMax - 0.05;

    % Wind reactive support reduces net Qinj in the same convention as Qpv.
    if isfield(data, 'QwindMax')
        data.QinjMin = data.QinjMin - data.QwindMax(:);
    end
end
end
