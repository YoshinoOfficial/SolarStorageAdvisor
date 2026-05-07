function data = apply_scenario(data, scen)
%APPLY_SCENARIO Apply multiplicative factors to the base day data.
% Supported fields in scen:
%   name, name_cn
%   pvScale, windScale
%   loadScale       : scale electric/reactive/heat loads together
%   electricLoadScale, heatLoadScale, h2Scale : optional finer controls
%   days            : representative days for annual weighting

if nargin < 2 || isempty(scen)
    return;
end

if isfield(scen, 'pvScale')
    data.Ppv = data.Ppv * scen.pvScale;
end

if isfield(scen, 'windScale')
    data.Pwind = data.Pwind * scen.windScale;
end

% Coarse load scaling: electric + reactive + heat.
if isfield(scen, 'loadScale')
    data.Pbase = data.Pbase * scen.loadScale;
    data.Qbase = data.Qbase * scen.loadScale;
    data.PbusBase = data.PbusBase * scen.loadScale;
    data.QbusBase = data.QbusBase * scen.loadScale;
    data.Pload = data.Pload * scen.loadScale;
    data.Hload = data.Hload * scen.loadScale;
end

% Optional finer load scaling. These are applied after loadScale.
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
