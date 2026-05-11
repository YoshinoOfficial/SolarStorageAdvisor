function p = build_local_params(data, i, zP, zQ, lambdaP_i, lambdaQ_i, rhoPQ, zC, lambdaC_i, rhoC)
if nargin < 8 || isempty(zC)
    zC = zeros(data.N, data.T);
end
if nargin < 9 || isempty(lambdaC_i)
    lambdaC_i = zeros(1, data.T);
end
if nargin < 10 || isempty(rhoC)
    rhoC = rhoPQ;
end

p.idx = i; p.N = data.N; p.T = data.T; p.dt = data.dt;

p.ce = data.ce(i,:);
p.cCarbon = data.cCarbon(i,:);
p.pCO2 = data.pCO2(i,:);
p.Pbase = data.Pbase(i,:);
p.Qbase = data.Qbase(i,:);
p.Ppv   = data.Ppv(i,:);
p.Pwind = data.Pwind(i,:);

% CHP
p.PchpRated = data.PchpRated(i);
p.etaE_chp  = data.etaE_chp(i);
p.etaH_chp  = data.etaH_chp(i);
p.FgasMin   = data.FgasMin(i);
p.FgasMax   = data.FgasMax(i);
p.cGas      = data.cGas;
p.efGas     = data.efGas;
p.enableCarbonQuota = get_data_field(data, 'enableCarbonQuota', get_data_field(data, 'enableCarbonTrading', false));
p.enableCarbonTrading = p.enableCarbonQuota;
p.enableCommunityCarbonTrading = get_data_field(data, 'enableCommunityCarbonTrading', p.enableCarbonQuota);
p.allowCarbonMarketSell = get_data_field(data, 'allowCarbonMarketSell', p.enableCarbonQuota);
p.zetaE = get_data_field(data, 'zetaE', 1080);
p.zetaH = get_data_field(data, 'zetaH', 324);
p.chiE = get_data_field(data, 'chiE', 728);
p.chiH = get_data_field(data, 'chiH', 367.2);
p.ceh = get_data_field(data, 'ceh', 1.6667);
fixedCarbonQuota_kg = get_data_field(data, 'fixedCarbonQuota_kg', []);
if isempty(fixedCarbonQuota_kg)
    p.fixedCarbonQuota_kg = [];
else
    p.fixedCarbonQuota_kg = fixedCarbonQuota_kg(i,:);
end
p.efGrid = data.efGrid(i,:);
p.quotaGridRatio = get_data_field(data, 'quotaGridRatio', 0.80);
p.quotaGasRatio = get_data_field(data, 'quotaGasRatio', 0.80);
p.carbonBuyPrice = get_data_field(data, 'carbonBuyPrice', 200);
p.carbonSellPrice = get_data_field(data, 'carbonSellPrice', 100);

% CHP enhanced operating parameters
p.uChp0       = data.uChp0(i);
p.PchpMin     = data.PchpMin(i);
p.RampUpCHP   = data.RampUpCHP(i);
p.RampDnCHP   = data.RampDnCHP(i);
p.StartUpCHP  = data.StartUpCHP(i);
p.ShutDnCHP   = data.ShutDnCHP(i);
p.MinUpCHP    = data.MinUpCHP(i);
p.MinDnCHP    = data.MinDnCHP(i);
p.cOM_CHP     = data.cOM_CHP(i);
p.cRampCHP    = data.cRampCHP(i);
p.lambdaHdump = data.lambdaHdump(i);
p.minChpHeatShare = get_data_field(data, 'minChpHeatShare', 0);

% Electric boiler
p.PebMax = data.PebMax(i);
p.etaEb  = data.etaEb(i);
p.RampUpEb = get_indexed_field(data, 'RampUpEb', p.PebMax, i);
p.RampDnEb = get_indexed_field(data, 'RampDnEb', p.PebMax, i);
p.cRampEb = get_indexed_field(data, 'cRampEb', 0, i);

% Electrolyzer
p.PelecMax = data.PelecMax(i);
p.etaElec  = data.etaElec(i);
p.RampUpElec = get_indexed_field(data, 'RampUpElec', p.PelecMax, i);
p.RampDnElec = get_indexed_field(data, 'RampDnElec', p.PelecMax, i);
p.cRampElec = get_indexed_field(data, 'cRampElec', 0, i);

% Fuel cell
p.H2fcMax = data.H2fcMax(i);
p.etaFc   = data.etaFc(i);
p.RampUpFc = get_indexed_field(data, 'RampUpFc', p.etaFc*p.H2fcMax, i);
p.RampDnFc = get_indexed_field(data, 'RampDnFc', p.etaFc*p.H2fcMax, i);
p.cRampFc = get_indexed_field(data, 'cRampFc', 0, i);

% Electrical storage
p.PchMax   = data.PchMax(i);
p.PdisMax  = data.PdisMax(i);
p.Emax     = data.Emax(i);
p.SOC0_e   = data.SOC0_e(i);
p.etaCh_e  = data.etaCh_e(i);
p.etaDis_e = data.etaDis_e(i);

% Thermal storage
p.HchMax    = data.HchMax(i);
p.HdisMax   = data.HdisMax(i);
p.EthMax    = data.EthMax(i);
p.SOC0_th   = data.SOC0_th(i);
p.etaCh_th  = data.etaCh_th(i);
p.etaDis_th = data.etaDis_th(i);

% Hydrogen storage
p.H2chMax  = data.H2chMax(i);
p.H2disMax = data.H2disMax(i);
p.EH2Max   = data.EH2Max(i);
p.SOC0_h2  = data.SOC0_h2(i);

p.termSOC_e  = data.termSOC_e(i);
p.termSOC_th = data.termSOC_th(i);
p.termSOC_h2 = data.termSOC_h2(i);

% Loads
p.Pload  = data.Pload(i,:);
p.Hload  = data.Hload(i,:);
p.H2load = data.H2load(i,:);
p.PcompFixed = data.PcompFixed(i,:);
alphaCompH2 = get_data_field(data, 'alphaCompH2', zeros(data.N,1));
if isscalar(alphaCompH2)
    p.alphaCompH2 = alphaCompH2;
else
    p.alphaCompH2 = alphaCompH2(i);
end
p.PcompMax = get_indexed_field(data, 'PcompMax', max(p.PcompFixed) + p.alphaCompH2*p.etaElec*p.PelecMax, i);
p.RampUpComp = get_indexed_field(data, 'RampUpComp', p.PcompMax, i);
p.RampDnComp = get_indexed_field(data, 'RampDnComp', p.PcompMax, i);
p.cRampComp = get_indexed_field(data, 'cRampComp', 0, i);

% Grid limits
p.PgridMax = data.PgridMax(i);

% Penalties
p.lambdaPVCurt  = data.lambdaPVCurt(i);
p.lambdaWindCurt= data.lambdaWindCurt(i);
p.lambdaH2Short = data.lambdaH2Short(i);

% ADMM consensus
p.zP  = zP(i,:);
p.zQ  = zQ(i,:);
p.lambdaP = lambdaP_i;
p.lambdaQ = lambdaQ_i;
p.rhoPQ = rhoPQ;
p.zC = zC(i,:);
p.lambdaC = lambdaC_i;
p.rhoC = rhoC;

% Reactive power
p.QcompCoeff = data.QcompCoeff(i);
p.QpvMax = data.QpvMax(i);
p.QesMax = data.QesMax(i);
p.lambdaQpv = data.lambdaQpv(i);
p.lambdaQes = data.lambdaQes(i);
end

function val = get_data_field(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end

function val = get_indexed_field(s, name, defaultVal, i)
if isfield(s, name) && ~isempty(s.(name))
    raw = s.(name);
    if isscalar(raw)
        val = raw;
    else
        val = raw(i);
    end
else
    val = defaultVal;
end
end
