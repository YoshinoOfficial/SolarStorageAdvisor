function out = carbon_accounting(data, Pgrid, Pchp, Hchp, Fgas)
%CARBON_ACCOUNTING Compute carbon emission and free allowance.
% Units:
%   Pgrid, Pchp, Hchp, Fgas: MW or MWh/h over one time step
%   emission/quota outputs: kgCO2 per time step after multiplying by dt

dt = data.dt;
if nargin < 3 || isempty(Pchp)
    Pchp = zeros(size(Pgrid));
end
if nargin < 4 || isempty(Hchp)
    Hchp = zeros(size(Pgrid));
end
if nargin < 5 || isempty(Fgas) %#ok<INUSD>
    Fgas = zeros(size(Pgrid)); %#ok<NASGU>
end

zetaE = get_field(data, 'zetaE', 1080);    % kg/MWh, paper: 1.08 kg/kWh
zetaH = get_field(data, 'zetaH', 324);     % kg/MWh_th, paper: 0.09 t/GJ
chiE = get_field(data, 'chiE', 728);       % kg/MWh, paper: 0.728 kg/kWh
chiH = get_field(data, 'chiH', 367.2);     % kg/MWh_th, paper: 0.102 t/GJ
ceh = get_field(data, 'ceh', 1.6667);

chpHeatEquivalent = ceh .* Pchp + Hchp;

out.gridEmission = zetaE .* Pgrid .* dt;
out.chpEmission = zetaH .* chpHeatEquivalent .* dt;
out.emission = out.gridEmission + out.chpEmission;

out.gridQuota = chiE .* Pgrid .* dt;
out.chpQuota = chiH .* chpHeatEquivalent .* dt;
if isfield(data, 'fixedCarbonQuota_kg') && ~isempty(data.fixedCarbonQuota_kg)
    out.quota = data.fixedCarbonQuota_kg;
    out.gridQuota = zeros(size(out.quota));
    out.chpQuota = out.quota;
else
    out.quota = out.gridQuota + out.chpQuota;
end
out.netAllowanceSurplus = out.quota - out.emission;
end

function val = get_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end
