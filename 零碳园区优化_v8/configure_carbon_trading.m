function data = configure_carbon_trading(data, opts)
%CONFIGURE_CARBON_TRADING Apply shared carbon quota/trading parameters.
%   This function centralizes the carbon settings used by comparison and
%   annual typical-day studies so both main scripts use the same mechanism.

if nargin < 2 || isempty(opts)
    opts = struct();
end

data.enableCarbonQuota = logical(get_option(opts, 'enableCarbonQuota', ...
    get_field(data, 'enableCarbonQuota', true)));
data.enableCarbonTrading = data.enableCarbonQuota;
data.enableCommunityCarbonTrading = logical(get_option(opts, 'enableCommunityCarbonTrading', ...
    get_field(data, 'enableCommunityCarbonTrading', data.enableCarbonQuota)));
data.allowCarbonMarketSell = logical(get_option(opts, 'allowCarbonMarketSell', ...
    get_field(data, 'allowCarbonMarketSell', data.enableCarbonQuota)));

% Paper benchmark carbon accounting parameters.
data.zetaE = get_option(opts, 'zetaE', 1080);          % kg/MWh, 1.08 kg/kWh
data.zetaH = get_option(opts, 'zetaH', 324);           % kg/MWh_th, 0.09 t/GJ
data.chiE = get_option(opts, 'chiE', 728);             % kg/MWh, 0.728 kg/kWh
data.chiH = get_option(opts, 'chiH', 367.2);           % kg/MWh_th, 0.102 t/GJ
data.ceh = get_option(opts, 'ceh', 1.6667);

% Retained for backward compatibility with older helper code.
data.quotaGridRatio = get_option(opts, 'quotaGridRatio', 1);
data.quotaGasRatio = get_option(opts, 'quotaGasRatio', 1);

data.carbonBuyPrice = get_option(opts, 'carbonBuyPrice', 200);   % yuan/tCO2
data.carbonSellPrice = get_option(opts, 'carbonSellPrice', 100); % yuan/tCO2

% Daily CHP heat floor to avoid shifting most heat to grid-powered boilers.
data.minChpHeatShare = get_option(opts, 'minChpHeatShare', 0.35);
end

function val = get_option(opts, name, defaultVal)
if isstruct(opts) && isfield(opts, name) && ~isempty(opts.(name))
    val = opts.(name);
else
    val = defaultVal;
end
end

function val = get_field(s, name, defaultVal)
if isstruct(s) && isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end
