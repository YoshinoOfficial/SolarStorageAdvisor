import os
import numpy as np
import pandas as pd

from . import config


def build_network_helpers():
    B = config.B
    branch = config.branch
    commBus = config.commBus
    N = config.N
    L = config.L

    bus_has_comm = np.zeros(B, dtype=bool)
    bus_to_comm = np.zeros(B, dtype=int)
    for i in range(N):
        bus_has_comm[commBus[i]] = True
        bus_to_comm[commBus[i]] = i + 1

    out_lines = [[] for _ in range(B)]
    for l in range(L):
        fr = branch[l, 0] - 1
        out_lines[fr].append(l)

    return bus_has_comm, bus_to_comm, out_lines


def build_case(ddre_scenario_id=13, pv_curve_24=None, wind_curve_24=None, scenario_dir=None):
    np.random.seed(0)

    if scenario_dir is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        scenario_dir = os.path.join(base, '零碳园区优化_v12', '1-Day Scenarios')

    bus_has_comm, bus_to_comm, out_lines = build_network_helpers()

    ce = np.zeros((config.N, config.T))
    Ppv = np.zeros((config.N, config.T))
    Pwind = np.zeros((config.N, config.T))

    if pv_curve_24 is not None and wind_curve_24 is not None:
        pv_pu = np.clip(np.array(pv_curve_24, dtype=float), 0, 1)
        wind_pu = np.clip(np.array(wind_curve_24, dtype=float), 0, 1)
        for i in range(config.N):
            ce[i, :] = np.maximum(250, config.ce_base + config.priceShift[i])
            Ppv[i, :] = config.pvCap[i] * config.pvScaleFinal * pv_pu
            Pwind[i, :] = config.windCap[i] * config.windScaleFinal * wind_pu
    elif ddre_scenario_id is not None:
        scenario_file = os.path.join(scenario_dir, f'scenario_{ddre_scenario_id:03d}.csv')
        if not os.path.exists(scenario_file):
            raise FileNotFoundError(f'DDRE scenario file not found: {scenario_file}')
        df = pd.read_csv(scenario_file)
        required = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        for col in required:
            if col not in df.columns:
                raise ValueError(f'{scenario_file} missing column: {col}')

        pv18_15 = np.clip(pd.to_numeric(df['node_18_PV'], errors='coerce').fillna(0).values, 0, 1)
        pv33_15 = np.clip(pd.to_numeric(df['node_33_PV'], errors='coerce').fillna(0).values, 0, 1)
        w22_15 = np.clip(pd.to_numeric(df['node_22_wind'], errors='coerce').fillna(0).values, 0, 1)
        w25_15 = np.clip(pd.to_numeric(df['node_25_wind'], errors='coerce').fillna(0).values, 0, 1)

        pv18 = pv18_15.reshape(-1, 4).mean(axis=1)
        pv33 = pv33_15.reshape(-1, 4).mean(axis=1)
        w22 = w22_15.reshape(-1, 4).mean(axis=1)
        w25 = w25_15.reshape(-1, 4).mean(axis=1)

        pv_avg = 0.5 * (pv18 + pv33)
        wind_avg = 0.5 * (w22 + w25)

        for i in range(config.N):
            ce[i, :] = np.maximum(250, config.ce_base + config.priceShift[i])
            Ppv[i, :] = config.pvCap[i] * config.pvScaleFinal * pv_avg
            Pwind[i, :] = config.windCap[i] * config.windScaleFinal * wind_avg
    else:
        raise ValueError('Either ddre_scenario_id or pv_curve_24/wind_curve_24 must be provided')

    loc_carbon_scale = np.array([1.00, 0.97, 1.03])
    efGrid = np.zeros((config.N, config.T))
    pCO2 = np.zeros((config.N, config.T))
    for i in range(config.N):
        efGrid[i, :] = config.efGridBase * loc_carbon_scale[i] * config.carbonShape
        pCO2[i, :] = np.full(config.T, config.pCO2Base)

    data = {
        'N': config.N, 'T': config.T, 'B': config.B, 'L': config.L, 'dt': config.dt,
        'commBus': config.commBus.copy(),
        'rootBus': config.rootBus,
        'branch': config.branch.copy(),
        'branch_ohm': config.branch_ohm.copy(),
        'baseMVA': config.baseMVA,
        'rline': config.rline.copy(),
        'xline': config.xline.copy(),
        'Vslack': config.Vslack,
        'Vmin': config.Vmin.copy(),
        'Vmax': config.Vmax.copy(),
        'PsubMax': config.PsubMax.copy(),
        'PijMax': config.PijMax_arr.copy(),
        'QijMax': config.QijMax_arr.copy(),
        'PbusBase': config.PbusBase.copy(),
        'QbusBase': config.QbusBase.copy(),
        'bus_has_comm': bus_has_comm,
        'bus_to_comm': bus_to_comm,
        'out_lines': out_lines,
        'ce': ce,
        'efGrid': efGrid,
        'pCO2': pCO2,
        'Pbase': config.Pbase.copy(),
        'Qbase': config.Qbase.copy(),
        'pfTan': config.pfTan.copy(),
        'Ppv': Ppv,
        'Pwind': Pwind,
        'PchpRated': config.PchpRated.copy(),
        'etaE_chp': config.etaE_chp.copy(),
        'etaH_chp': config.etaH_chp.copy(),
        'FgasMin': config.FgasMin.copy(),
        'FgasMax': config.FgasMax.copy(),
        'cGas': config.cGas,
        'efGas': config.efGas,
        'uChp0': config.uChp0.copy(),
        'PchpMin': config.PchpMin.copy(),
        'RampUpCHP': config.RampUpCHP.copy(),
        'RampDnCHP': config.RampDnCHP.copy(),
        'StartUpCHP': config.StartUpCHP.copy(),
        'ShutDnCHP': config.ShutDnCHP.copy(),
        'MinUpCHP': config.MinUpCHP.copy().astype(int),
        'MinDnCHP': config.MinDnCHP.copy().astype(int),
        'cOM_CHP': config.cOM_CHP.copy(),
        'cRampCHP': config.cRampCHP.copy(),
        'lambdaHdump': config.lambdaHdump.copy(),
        'PebMax': config.PebMax.copy(),
        'etaEb': config.etaEb.copy(),
        'RampUpEb': config.RampUpEb.copy(),
        'RampDnEb': config.RampDnEb.copy(),
        'cRampEb': config.cRampEb.copy(),
        'PelecMax': config.PelecMax.copy(),
        'etaElec': config.etaElec.copy(),
        'RampUpElec': config.RampUpElec.copy(),
        'RampDnElec': config.RampDnElec.copy(),
        'cRampElec': config.cRampElec.copy(),
        'H2fcMax': config.H2fcMax.copy(),
        'etaFc': config.etaFc.copy(),
        'RampUpFc': config.RampUpFc.copy(),
        'RampDnFc': config.RampDnFc.copy(),
        'cRampFc': config.cRampFc.copy(),
        'PchMax': config.PchMax.copy(),
        'PdisMax': config.PdisMax.copy(),
        'Emax': config.Emax.copy(),
        'SOC0_e': config.SOC0_e.copy(),
        'etaCh_e': config.etaCh_e.copy(),
        'etaDis_e': config.etaDis_e.copy(),
        'HchMax': config.HchMax.copy(),
        'HdisMax': config.HdisMax.copy(),
        'EthMax': config.EthMax.copy(),
        'SOC0_th': config.SOC0_th.copy(),
        'etaCh_th': config.etaCh_th.copy(),
        'etaDis_th': config.etaDis_th.copy(),
        'H2chMax': config.H2chMax.copy(),
        'H2disMax': config.H2disMax.copy(),
        'EH2Max': config.EH2Max.copy(),
        'SOC0_h2': config.SOC0_h2.copy(),
        'Pload': config.Pload.copy(),
        'PloadFixed': config.PloadFixed.copy(),
        'PdrShiftBase': config.PdrShiftBase.copy(),
        'PdrShiftMax': config.PdrShiftMax.copy(),
        'PdrCutEmax': config.PdrCutEmax.copy(),
        'Hload': config.Hload.copy(),
        'HdrCutMax': config.HdrCutMax.copy(),
        'H2load': config.H2load.copy(),
        'H2drCutMax': config.H2drCutMax.copy(),
        'cDRShiftE': config.cDRShiftE.copy(),
        'cDRCutE': config.cDRCutE.copy(),
        'cDRCutH': config.cDRCutH.copy(),
        'cDRCutH2': config.cDRCutH2.copy(),
        'PcompFixed': config.PcompFixed.copy(),
        'alphaCompH2': config.alphaCompH2.copy(),
        'PcompMax': config.PcompMax.copy(),
        'RampUpComp': config.RampUpComp.copy(),
        'RampDnComp': config.RampDnComp.copy(),
        'cRampComp': config.cRampComp.copy(),
        'QcompCoeff': config.QcompCoeff.copy(),
        'PgridMax': config.PgridMax.copy(),
        'lambdaPVCurt': config.lambdaPVCurt.copy(),
        'lambdaWindCurt': config.lambdaWindCurt.copy(),
        'lambdaH2Short': config.lambdaH2Short.copy(),
        'lambdaQpv': config.lambdaQpv.copy(),
        'lambdaQwind': config.lambdaQwind.copy(),
        'lambdaQes': config.lambdaQes.copy(),
        'QpvMax': config.QpvMax.copy(),
        'QwindMax': config.QwindMax.copy(),
        'QesMax': config.QesMax.copy(),
        'QinjMin': config.QinjMin.copy(),
        'QinjMax': config.QinjMax.copy(),
        'termSOC_e': config.SOC0_e.copy(),
        'termSOC_th': config.SOC0_th.copy(),
        'termSOC_h2': config.SOC0_h2.copy(),
        'enableCarbonQuota': True,
        'enableCommunityCarbonTrading': True,
        'allowCarbonMarketSell': True,
        'carbonBuyPrice': 200.0,
        'carbonSellPrice': 100.0,
        'QtradeMax_tCO2': 1.6,
        'QmarketMax_tCO2': 1e4,
        'carbonBalanceMode': 'period',
        'minChpHeatShare': 0.0,
        'zetaE': 1080, 'zetaH': 324, 'chiE': 728, 'chiH': 367.2, 'ceh': 1.6667,
        'PgridMax_sub': config.PsubMax.copy(),
    }

    return data
