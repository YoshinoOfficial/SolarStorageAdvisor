import time
import cvxpy as cp
import numpy as np
from . import carbon_accounting


def solve(data, time_limit=120, verbose=False):
    N = data['N']
    T = data['T']
    B = data['B']
    L = data['L']
    dt = data['dt']

    df = data
    get = lambda name, default=0: df.get(name, default)
    rep = lambda arr, axis: np.tile(np.asarray(arr)[:, None] if axis == 1 else np.asarray(arr), (1, T))

    # ===== Variables =====
    Pgrid = cp.Variable((N, T), nonneg=True)
    Pch = cp.Variable((N, T), nonneg=True)
    Pdis = cp.Variable((N, T), nonneg=True)
    SOC_e = cp.Variable((N, T))
    PpvUse = cp.Variable((N, T), nonneg=True)
    PpvCurt = cp.Variable((N, T), nonneg=True)
    PwindUse = cp.Variable((N, T), nonneg=True)
    PwindCurt = cp.Variable((N, T), nonneg=True)
    uCh = cp.Variable((N, T))

    Fgas = cp.Variable((N, T), nonneg=True)
    Pchp = cp.Variable((N, T))
    Hchp = cp.Variable((N, T))
    uChp = cp.Variable((N, T), boolean=True)
    vStart = cp.Variable((N, T), boolean=True)
    vStop = cp.Variable((N, T), boolean=True)
    RupChp = cp.Variable((N, T), nonneg=True)
    RdnChp = cp.Variable((N, T), nonneg=True)
    Hdump = cp.Variable((N, T), nonneg=True)

    Peb = cp.Variable((N, T), nonneg=True)
    Heb = cp.Variable((N, T))
    RupEb = cp.Variable((N, T), nonneg=True)
    RdnEb = cp.Variable((N, T), nonneg=True)

    Pelec = cp.Variable((N, T), nonneg=True)
    H2prod = cp.Variable((N, T))
    RupElec = cp.Variable((N, T), nonneg=True)
    RdnElec = cp.Variable((N, T), nonneg=True)

    H2cons_fc = cp.Variable((N, T), nonneg=True)
    Pfc = cp.Variable((N, T))
    RupFc = cp.Variable((N, T), nonneg=True)
    RdnFc = cp.Variable((N, T), nonneg=True)

    Pcomp = cp.Variable((N, T))
    RupComp = cp.Variable((N, T), nonneg=True)
    RdnComp = cp.Variable((N, T), nonneg=True)

    Hch = cp.Variable((N, T), nonneg=True)
    Hdis = cp.Variable((N, T), nonneg=True)
    SOC_th = cp.Variable((N, T))
    uHch = cp.Variable((N, T))

    H2ch = cp.Variable((N, T), nonneg=True)
    H2dis = cp.Variable((N, T), nonneg=True)
    SOC_h2 = cp.Variable((N, T))
    uH2ch = cp.Variable((N, T))

    H2short = cp.Variable((N, T), nonneg=True)

    PdrShift = cp.Variable((N, T), nonneg=True)
    PdrShiftDev = cp.Variable((N, T), nonneg=True)
    PdrCutE = cp.Variable((N, T), nonneg=True)
    HdrCut = cp.Variable((N, T), nonneg=True)
    H2drCut = cp.Variable((N, T), nonneg=True)

    Qpv = cp.Variable((N, T))
    Qwind = cp.Variable((N, T))
    Qes = cp.Variable((N, T))
    Pinj = cp.Variable((N, T))
    Qinj = cp.Variable((N, T))
    Pij = cp.Variable((L, T))
    Qij = cp.Variable((L, T))
    V = cp.Variable((B, T))

    QaBuy = cp.Variable((N, T), nonneg=True)
    QaSell = cp.Variable((N, T), nonneg=True)
    Qtrade = cp.Variable((N, T))
    QaUnused = cp.Variable((N, T), nonneg=True)

    constraints = []

    # ===== Bounds =====
    constraints.append(Pch <= rep(df['PchMax'], 1) * uCh)
    constraints.append(Pdis <= rep(df['PdisMax'], 1) * (1 - uCh))
    constraints.append(SOC_e >= 0.1 * rep(df['Emax'], 1))
    constraints.append(SOC_e <= 0.9 * rep(df['Emax'], 1))
    constraints.append(Pgrid <= rep(df['PgridMax'], 1))
    constraints.append(PpvUse <= df['Ppv'])
    constraints.append(PpvCurt <= df['Ppv'])
    constraints.append(PwindUse <= df['Pwind'])
    constraints.append(PwindCurt <= df['Pwind'])
    constraints.append(V >= rep(df['Vmin'] ** 2, 1))
    constraints.append(V <= rep(df['Vmax'] ** 2, 1))
    constraints.append(Qpv >= -rep(df['QpvMax'], 1))
    constraints.append(Qpv <= rep(df['QpvMax'], 1))
    constraints.append(Qwind >= -rep(df['QwindMax'], 1))
    constraints.append(Qwind <= rep(df['QwindMax'], 1))
    constraints.append(Qes >= -rep(df['QesMax'], 1))
    constraints.append(Qes <= rep(df['QesMax'], 1))

    QtradeMax = get('QtradeMax_tCO2', 1.6)
    if np.isfinite(QtradeMax) and QtradeMax > 0:
        constraints.append(Qtrade >= -QtradeMax)
        constraints.append(Qtrade <= QtradeMax)
    QmarketMax = get('QmarketMax_tCO2', 1e4)
    if np.isfinite(QmarketMax) and QmarketMax > 0:
        constraints.append(QaBuy <= QmarketMax)
        constraints.append(QaSell <= QmarketMax)
        constraints.append(QaUnused <= QmarketMax)

    carbon_enabled = get('enableCarbonQuota', True)
    comm_trading_enabled = get('enableCommunityCarbonTrading', True)
    market_sell_enabled = get('allowCarbonMarketSell', True)
    if not carbon_enabled:
        constraints.append(QaBuy == 0)
        constraints.append(QaSell == 0)
        constraints.append(Qtrade == 0)
        constraints.append(QaUnused == 0)
    else:
        if not comm_trading_enabled:
            constraints.append(Qtrade == 0)
        if not market_sell_enabled:
            constraints.append(QaSell == 0)
        else:
            constraints.append(QaUnused == 0)

    # ===== 0-1 Relaxation Bounds =====
    constraints.append(uCh >= 0)
    constraints.append(uCh <= 1)
    constraints.append(uHch >= 0)
    constraints.append(uHch <= 1)
    constraints.append(uH2ch >= 0)
    constraints.append(uH2ch <= 1)

    # ===== CHP Constraints =====
    constraints.append(uChp >= 0)
    constraints.append(uChp <= 1)
    constraints.append(vStart >= 0)
    constraints.append(vStart <= 1)
    constraints.append(vStop >= 0)
    constraints.append(vStop <= 1)
    constraints.append(vStart + vStop <= 1)

    FgasMinEff = np.maximum(df['FgasMin'], df['PchpMin'] / np.maximum(df['etaE_chp'], 1e-6))
    constraints.append(Fgas <= rep(df['FgasMax'], 1) * uChp)
    constraints.append(Fgas >= rep(FgasMinEff, 1) * uChp)
    constraints.append(Pchp == rep(df['etaE_chp'], 1) * Fgas)
    constraints.append(Hchp == rep(df['etaH_chp'], 1) * Fgas)
    constraints.append(Pchp <= rep(df['PchpRated'], 1) * uChp)
    constraints.append(Pchp >= rep(df['PchpMin'], 1) * uChp)

    # ===== EB =====
    constraints.append(Peb <= rep(df['PebMax'], 1))
    constraints.append(Heb == rep(df['etaEb'], 1) * Peb)

    # ===== Electrolyzer =====
    constraints.append(Pelec <= rep(df['PelecMax'], 1))
    constraints.append(H2prod == rep(df['etaElec'], 1) * Pelec)

    # ===== Fuel Cell =====
    constraints.append(H2cons_fc <= rep(df['H2fcMax'], 1))
    constraints.append(Pfc == rep(df['etaFc'], 1) * H2cons_fc)

    # ===== Compressor =====
    constraints.append(Pcomp == df['PcompFixed'] + rep(df['alphaCompH2'], 1) * H2prod)
    constraints.append(Pcomp <= rep(df['PcompMax'], 1))

    # ===== Thermal Storage =====
    constraints.append(SOC_th >= 0.1 * rep(df['EthMax'], 1))
    constraints.append(SOC_th <= 0.9 * rep(df['EthMax'], 1))
    constraints.append(Hch <= rep(df['HchMax'], 1) * uHch)
    constraints.append(Hdis <= rep(df['HdisMax'], 1) * (1 - uHch))

    # ===== Hydrogen Storage =====
    constraints.append(SOC_h2 >= 0.1 * rep(df['EH2Max'], 1))
    constraints.append(SOC_h2 <= 0.9 * rep(df['EH2Max'], 1))
    constraints.append(H2ch <= rep(df['H2chMax'], 1) * uH2ch)
    constraints.append(H2dis <= rep(df['H2disMax'], 1) * (1 - uH2ch))

    # ===== Hydrogen Shortage =====
    constraints.append(H2short <= df['H2load'])

    # ===== Demand Response =====
    constraints.append(PdrShift <= df['PdrShiftMax'])
    constraints.append(PdrShiftDev >= PdrShift - df['PdrShiftBase'])
    constraints.append(PdrShiftDev >= df['PdrShiftBase'] - PdrShift)
    constraints.append(PdrCutE <= df['PdrCutEmax'])
    constraints.append(HdrCut <= df['HdrCutMax'])
    constraints.append(H2drCut <= df['H2drCutMax'])

    for i in range(N):
        for t in range(T):
            # CHP logic
            if t == 0:
                constraints.append(uChp[i, t] - df['uChp0'][i] == vStart[i, t] - vStop[i, t])
            else:
                constraints.append(uChp[i, t] - uChp[i, t - 1] == vStart[i, t] - vStop[i, t])
                constraints.append(Pchp[i, t] - Pchp[i, t - 1] <= df['RampUpCHP'][i])
                constraints.append(Pchp[i, t - 1] - Pchp[i, t] <= df['RampDnCHP'][i])
                constraints.append(RupChp[i, t] >= Pchp[i, t] - Pchp[i, t - 1])
                constraints.append(RdnChp[i, t] >= Pchp[i, t - 1] - Pchp[i, t])

                constraints.append(Peb[i, t] - Peb[i, t - 1] <= df['RampUpEb'][i])
                constraints.append(Peb[i, t - 1] - Peb[i, t] <= df['RampDnEb'][i])
                constraints.append(RupEb[i, t] >= Peb[i, t] - Peb[i, t - 1])
                constraints.append(RdnEb[i, t] >= Peb[i, t - 1] - Peb[i, t])

                constraints.append(Pelec[i, t] - Pelec[i, t - 1] <= df['RampUpElec'][i])
                constraints.append(Pelec[i, t - 1] - Pelec[i, t] <= df['RampDnElec'][i])
                constraints.append(RupElec[i, t] >= Pelec[i, t] - Pelec[i, t - 1])
                constraints.append(RdnElec[i, t] >= Pelec[i, t - 1] - Pelec[i, t])

                constraints.append(Pfc[i, t] - Pfc[i, t - 1] <= df['RampUpFc'][i])
                constraints.append(Pfc[i, t - 1] - Pfc[i, t] <= df['RampDnFc'][i])
                constraints.append(RupFc[i, t] >= Pfc[i, t] - Pfc[i, t - 1])
                constraints.append(RdnFc[i, t] >= Pfc[i, t - 1] - Pfc[i, t])

                constraints.append(Pcomp[i, t] - Pcomp[i, t - 1] <= df['RampUpComp'][i])
                constraints.append(Pcomp[i, t - 1] - Pcomp[i, t] <= df['RampDnComp'][i])
                constraints.append(RupComp[i, t] >= Pcomp[i, t] - Pcomp[i, t - 1])
                constraints.append(RdnComp[i, t] >= Pcomp[i, t - 1] - Pcomp[i, t])

            # Storage dynamics
            if t == 0:
                constraints.append(SOC_e[i, t] == df['SOC0_e'][i]
                                    + df['etaCh_e'][i] * Pch[i, t] * dt
                                    - (1 / df['etaDis_e'][i]) * Pdis[i, t] * dt)
                constraints.append(SOC_th[i, t] == df['SOC0_th'][i]
                                    + df['etaCh_th'][i] * Hch[i, t] * dt
                                    - (1 / df['etaDis_th'][i]) * Hdis[i, t] * dt)
                constraints.append(SOC_h2[i, t] == df['SOC0_h2'][i]
                                    + (H2ch[i, t] - H2dis[i, t]) * dt)
            else:
                constraints.append(SOC_e[i, t] == SOC_e[i, t - 1]
                                    + df['etaCh_e'][i] * Pch[i, t] * dt
                                    - (1 / df['etaDis_e'][i]) * Pdis[i, t] * dt)
                constraints.append(SOC_th[i, t] == SOC_th[i, t - 1]
                                    + df['etaCh_th'][i] * Hch[i, t] * dt
                                    - (1 / df['etaDis_th'][i]) * Hdis[i, t] * dt)
                constraints.append(SOC_h2[i, t] == SOC_h2[i, t - 1]
                                    + (H2ch[i, t] - H2dis[i, t]) * dt)

            # H2 balance
            constraints.append(H2prod[i, t] + H2dis[i, t] + H2short[i, t]
                               == df['H2load'][i, t] - H2drCut[i, t] + H2cons_fc[i, t] + H2ch[i, t])

            # Power balance
            constraints.append(PpvUse[i, t] + PpvCurt[i, t] == df['Ppv'][i, t])
            constraints.append(PwindUse[i, t] + PwindCurt[i, t] == df['Pwind'][i, t])

            constraints.append(
                Pgrid[i, t] + PpvUse[i, t] + PwindUse[i, t] + Pchp[i, t] + Pfc[i, t] + Pdis[i, t]
                == df['PloadFixed'][i, t] + PdrShift[i, t] - PdrCutE[i, t]
                + Peb[i, t] + Pelec[i, t] + Pch[i, t] + Pcomp[i, t]
            )
            constraints.append(Pinj[i, t] == Pgrid[i, t])

            pf_tan = df['pfTan'][i]
            qcomp = df['QcompCoeff'][i]
            constraints.append(
                Qinj[i, t] == pf_tan * (df['PloadFixed'][i, t] + PdrShift[i, t] - PdrCutE[i, t])
                + qcomp * Pcomp[i, t] - Qpv[i, t] - Qwind[i, t] - Qes[i, t]
            )

            # SOC reactive power constraints
            constraints.append(cp.SOC(df['QpvMax'][i], cp.vstack([PpvUse[i, t], Qpv[i, t]])))
            constraints.append(cp.SOC(df['QwindMax'][i], cp.vstack([PwindUse[i, t], Qwind[i, t]])))
            constraints.append(cp.SOC(df['QesMax'][i], cp.vstack([Pdis[i, t] - Pch[i, t], Qes[i, t]])))

            # Thermal balance
            constraints.append(
                Hchp[i, t] + Heb[i, t] + Hdis[i, t]
                == df['Hload'][i, t] - HdrCut[i, t] + Hch[i, t] + Hdump[i, t]
            )

        # Daily DR energy balance
        constraints.append(cp.sum(PdrShift[i, :]) * dt == cp.sum(df['PdrShiftBase'][i, :]) * dt)

        # Minimum CHP heat share
        min_heat_share = get('minChpHeatShare', 0.0)
        if min_heat_share > 0:
            constraints.append(
                cp.sum(Hchp[i, :]) * dt >= min_heat_share * cp.sum(df['Hload'][i, :] - HdrCut[i, :]) * dt
            )

        # Carbon trading
        if carbon_enabled:
            carbon_mode = get('carbonBalanceMode', 'period')
            fixed_quota = get('fixedCarbonQuota_kg', None)
            zetaE = get('zetaE', 1080)
            zetaH = get('zetaH', 324)
            chiE = get('chiE', 728)
            chiH = get('chiH', 367.2)
            ceh = get('ceh', 1.6667)

            if carbon_mode in ('period', 'hourly'):
                for t in range(T):
                    chp_heat_eq = ceh * Pchp[i, t] + Hchp[i, t]
                    emission_it = zetaE * Pgrid[i, t] * dt + zetaH * chp_heat_eq * dt
                    if fixed_quota is not None:
                        quota_it = fixed_quota[i, t]
                    else:
                        quota_it = chiE * Pgrid[i, t] * dt + chiH * chp_heat_eq * dt
                    constraints.append(
                        quota_it / 1000 + QaBuy[i, t] + Qtrade[i, t]
                        == emission_it / 1000 + QaSell[i, t] + QaUnused[i, t]
                    )
            else:
                emission_day = 0
                quota_day = 0
                for t in range(T):
                    chp_heat_eq = ceh * Pchp[i, t] + Hchp[i, t]
                    emission_day += zetaE * Pgrid[i, t] * dt + zetaH * chp_heat_eq * dt
                    if fixed_quota is not None:
                        quota_day += fixed_quota[i, t]
                    else:
                        quota_day += chiE * Pgrid[i, t] * dt + chiH * chp_heat_eq * dt
                constraints.append(
                    quota_day / 1000 + cp.sum(QaBuy[i, :]) + cp.sum(Qtrade[i, :])
                    == emission_day / 1000 + cp.sum(QaSell[i, :]) + cp.sum(QaUnused[i, :])
                )

        # Minimum up/down time
        MU = max(1, df['MinUpCHP'][i])
        MD = max(1, df['MinDnCHP'][i])
        for t in range(MU, T):
            constraints.append(cp.sum(vStart[i, t - MU + 1:t + 1]) <= uChp[i, t])
        for t in range(MD, T):
            constraints.append(cp.sum(vStop[i, t - MD + 1:t + 1]) <= 1 - uChp[i, t])

    # Cyclic end-of-day storage
    for i in range(N):
        constraints.append(SOC_e[i, T - 1] == df['termSOC_e'][i])
        constraints.append(SOC_th[i, T - 1] == df['termSOC_th'][i])
        constraints.append(SOC_h2[i, T - 1] == df['termSOC_h2'][i])

    if carbon_enabled and comm_trading_enabled:
        for t in range(T):
            constraints.append(cp.sum(Qtrade[:, t]) == 0)

    # ===== DistFlow Network Constraints =====
    branch_0 = df['branch'] - 1
    for t in range(T):
        constraints.append(V[df['rootBus'] - 1, t] == df['Vslack'] ** 2)
        for l in range(L):
            fr = branch_0[l, 0]
            to = branch_0[l, 1]

            Pchild = 0
            Qchild = 0
            for child_line in df['out_lines'][to]:
                Pchild += Pij[child_line, t]
                Qchild += Qij[child_line, t]

            Pload_net = df['PbusBase'][to, t]
            Qload_net = df['QbusBase'][to, t]

            if df['bus_has_comm'][to]:
                comm_i = df['bus_to_comm'][to] - 1
                Pload_net += Pinj[comm_i, t]
                Qload_net += Qinj[comm_i, t]

            constraints.append(Pij[l, t] == Pchild + Pload_net)
            constraints.append(Qij[l, t] == Qchild + Qload_net)

            r = df['rline'][l]
            x = df['xline'][l]
            constraints.append(
                V[to, t] == V[fr, t]
                - 2 * (r * Pij[l, t] / df['baseMVA'] + x * Qij[l, t] / df['baseMVA'])
            )

            constraints.append(Pij[l, t] >= -df['PijMax'][l])
            constraints.append(Pij[l, t] <= df['PijMax'][l])
            constraints.append(Qij[l, t] >= -df['QijMax'][l])
            constraints.append(Qij[l, t] <= df['QijMax'][l])

        Psub = 0
        for child_line in df['out_lines'][df['rootBus'] - 1]:
            Psub += Pij[child_line, t]
        constraints.append(Psub >= 0)
        constraints.append(Psub <= df['PsubMax'][t])

    # ===== Objective Function =====
    Obj = 0
    carbon_buy_price = get('carbonBuyPrice', 200)
    carbon_sell_price = get('carbonSellPrice', 100)

    for i in range(N):
        for t in range(T):
            Obj += df['ce'][i, t] * Pgrid[i, t] * dt
            Obj += df['cGas'] * Fgas[i, t] * dt
            if carbon_enabled:
                Obj += carbon_buy_price * QaBuy[i, t] - carbon_sell_price * QaSell[i, t]
            Obj += df['lambdaHdump'][i] * Hdump[i, t] * dt
            Obj += df['cOM_CHP'][i] * Pchp[i, t] * dt
            Obj += df['StartUpCHP'][i] * vStart[i, t] + df['ShutDnCHP'][i] * vStop[i, t]
            Obj += df['cRampCHP'][i] * (RupChp[i, t] + RdnChp[i, t])
            Obj += df['cRampEb'][i] * (RupEb[i, t] + RdnEb[i, t])
            Obj += df['cRampElec'][i] * (RupElec[i, t] + RdnElec[i, t])
            Obj += df['cRampFc'][i] * (RupFc[i, t] + RdnFc[i, t])
            Obj += df['cRampComp'][i] * (RupComp[i, t] + RdnComp[i, t])
            Obj += df['lambdaPVCurt'][i] * PpvCurt[i, t] * dt
            Obj += df['lambdaWindCurt'][i] * PwindCurt[i, t] * dt
            Obj += df['lambdaH2Short'][i] * H2short[i, t] * dt
            Obj += df['cDRShiftE'][i] * PdrShiftDev[i, t] * dt
            Obj += df['cDRCutE'][i] * PdrCutE[i, t] * dt
            Obj += df['cDRCutH'][i] * HdrCut[i, t] * dt
            Obj += df['cDRCutH2'][i] * H2drCut[i, t] * dt
            Obj += (df['lambdaQpv'][i] * cp.square(Qpv[i, t])
                    + df['lambdaQwind'][i] * cp.square(Qwind[i, t])
                    + df['lambdaQes'][i] * cp.square(Qes[i, t])) * dt

    problem = cp.Problem(cp.Minimize(Obj), constraints)

    solver = cp.GUROBI
    solver_opts = {
        'TimeLimit': time_limit,
        'MIPGap': 0.0001,
        'OutputFlag': int(verbose),
        'Threads': 0,
    }

    t0 = time.time()
    problem.solve(solver=solver, verbose=verbose, **solver_opts)
    solve_time = time.time() - t0

    if problem.status not in ('optimal', 'optimal_inaccurate'):
        raise RuntimeError(f'MILP solve failed: status={problem.status}, value={problem.value}')

    def val(x):
        return x.value if x is not None else 0

    def total(arr):
        return np.sum(arr)

    # ===== Cost Breakdown =====
    grid_cost = np.sum(df['ce'] * val(Pgrid) * dt)
    gas_cost = np.sum(df['cGas'] * val(Fgas) * dt)
    carbon_trading_cost = 0
    if carbon_enabled:
        carbon_trading_cost = np.sum(carbon_buy_price * val(QaBuy) - carbon_sell_price * val(QaSell))
    hdump_cost = np.sum(df['lambdaHdump'][:, None] * val(Hdump) * dt)
    chp_om_cost = np.sum(df['cOM_CHP'][:, None] * val(Pchp) * dt)
    startup_cost = np.sum(df['StartUpCHP'][:, None] * val(vStart))
    shutdown_cost = np.sum(df['ShutDnCHP'][:, None] * val(vStop))
    ramp_cost = np.sum(df['cRampCHP'][:, None] * (val(RupChp) + val(RdnChp))
                       + df['cRampEb'][:, None] * (val(RupEb) + val(RdnEb))
                       + df['cRampElec'][:, None] * (val(RupElec) + val(RdnElec))
                       + df['cRampFc'][:, None] * (val(RupFc) + val(RdnFc))
                       + df['cRampComp'][:, None] * (val(RupComp) + val(RdnComp)))
    pv_curt_cost = np.sum(df['lambdaPVCurt'][:, None] * val(PpvCurt) * dt)
    wind_curt_cost = np.sum(df['lambdaWindCurt'][:, None] * val(PwindCurt) * dt)
    h2_short_cost = np.sum(df['lambdaH2Short'][:, None] * val(H2short) * dt)
    dr_cost = np.sum(df['cDRShiftE'][:, None] * val(PdrShiftDev) * dt
                     + df['cDRCutE'][:, None] * val(PdrCutE) * dt
                     + df['cDRCutH'][:, None] * val(HdrCut) * dt
                     + df['cDRCutH2'][:, None] * val(H2drCut) * dt)
    q_support_cost = np.sum((df['lambdaQpv'][:, None] * np.square(val(Qpv))
                             + df['lambdaQwind'][:, None] * np.square(val(Qwind))
                             + df['lambdaQes'][:, None] * np.square(val(Qes))) * dt)

    total_objective = grid_cost + gas_cost + carbon_trading_cost + hdump_cost + chp_om_cost \
        + startup_cost + shutdown_cost + ramp_cost + pv_curt_cost + wind_curt_cost \
        + h2_short_cost + dr_cost + q_support_cost

    PpvUse_v = val(PpvUse)
    PwindUse_v = val(PwindUse)
    PpvCurt_v = val(PpvCurt)
    PwindCurt_v = val(PwindCurt)
    Pgrid_v = val(Pgrid)
    Pch_v = val(Pch)
    Pdis_v = val(Pdis)
    Pchp_v = val(Pchp)
    Pfc_v = val(Pfc)
    Fgas_v = val(Fgas)

    ren_avail = np.sum(df['Ppv']) + np.sum(df['Pwind'])
    ren_use = np.sum(PpvUse_v) + np.sum(PwindUse_v)
    ren_curt = np.sum(PpvCurt_v) + np.sum(PwindCurt_v)

    carbon = carbon_accounting.compute_carbon(Pgrid_v, Pchp_v, val(Hchp), Fgas_v, df)
    carbon_emission_total = np.sum(carbon['emission'])
    carbon_quota_total = np.sum(carbon['quota'])

    hours = list(range(1, T + 1))

    def to_list(arr):
        return np.round(np.asarray(arr).flatten(), 4).tolist()

    result = {
        'scenario': 'PY_MILP_REALTIME',
        'scenario_id': 'MILP',
        'weather_label': 'MILP 实时优化',
        'runtime_ms': round(solve_time * 1000, 1),
        'solver_status': problem.status,
        'objective': round(problem.value, 4),
        'kpis': {
            'cost': round(total_objective, 0),
            'grid_energy': round(np.sum(Pgrid_v) * dt, 1),
            'carbon_emission': round(carbon_emission_total / 1000, 1),
            'renewable_rate': round(ren_use / max(ren_avail, 1e-9) * 100, 1),
            'carbon_trading_cost': round(carbon_trading_cost, 0),
        },
        'metrics': {
            'cost': round(total_objective, 0),
            'grid_energy': round(np.sum(Pgrid_v) * dt, 1),
            'gas_energy': round(np.sum(Fgas_v) * dt, 1),
            'carbon_emission': round(carbon_emission_total / 1000, 1),
            'carbon_quota': round(carbon_quota_total / 1000, 1),
            'carbon_buy': round(np.sum(val(QaBuy)), 1),
            'carbon_sell': round(np.sum(val(QaSell)), 1),
            'renewable_available': round(ren_avail, 1),
            'renewable_use': round(ren_use, 1),
            'renewable_curtailment': round(ren_curt, 1),
            'renewable_rate': round(ren_use / max(ren_avail, 1e-9) * 100, 1),
            'avg_min_voltage': round(np.mean(np.min(val(V), axis=0)), 4),
            'grid_voltage_deviation': round(np.mean(np.abs(val(V) - 1.0)), 4),
            'h2_shortage': round(np.sum(val(H2short)), 1),
        },
        'cost_breakdown': {
            'grid': round(grid_cost, 4),
            'carbon_trading': round(carbon_trading_cost, 4),
            'gas': round(gas_cost, 4),
            'gas_carbon': 0,
            'pv_curt': round(pv_curt_cost, 4),
            'wind_curt': round(wind_curt_cost, 4),
            'h2_short': round(h2_short_cost, 4),
            'demand_response': round(dr_cost, 4),
            'q_support': round(q_support_cost, 4),
            'total': round(total_objective, 4),
        },
        'energy_summary': {
            'pv': round(np.sum(PpvUse_v) * dt, 4),
            'wind': round(np.sum(PwindUse_v) * dt, 4),
            'grid': round(np.sum(Pgrid_v) * dt, 4),
            'chp': round(np.sum(Pchp_v) * dt, 4),
            'fc': round(np.sum(Pfc_v) * dt, 4),
            'discharge': round(np.sum(Pdis_v) * dt, 4),
        },
        'chart': {
            'supply': {
                'hours': hours,
                'pv': to_list(np.sum(PpvUse_v, axis=0)),
                'wind': to_list(np.sum(PwindUse_v, axis=0)),
                'grid': to_list(np.sum(Pgrid_v, axis=0)),
                'discharge': to_list(np.sum(Pdis_v, axis=0)),
                'chp': to_list(np.sum(Pchp_v, axis=0)),
                'fc': to_list(np.sum(Pfc_v, axis=0)),
            },
            'demand': {
                'hours': hours,
                'load': to_list(np.sum(df['PloadFixed'] + val(PdrShift) - val(PdrCutE), axis=0)),
                'elec': to_list(np.sum(df['PelecMax'][:, None] * 0.5, axis=0)),
                'eb': to_list(np.sum(val(Peb), axis=0)),
                'comp': to_list(np.sum(val(Pcomp), axis=0)),
                'charge': to_list(np.sum(Pch_v, axis=0)),
            },
            'soc': {
                'hours': hours,
                'soc_e': to_list(np.mean(val(SOC_e), axis=0)),
                'soc_th': to_list(np.mean(val(SOC_th), axis=0)),
                'soc_h2': to_list(np.mean(val(SOC_h2), axis=0)),
            },
            'supply_total': to_list(
                np.sum(Pgrid_v, axis=0) + np.sum(PpvUse_v, axis=0) + np.sum(PwindUse_v, axis=0)
                + np.sum(Pchp_v, axis=0) + np.sum(Pfc_v, axis=0) + np.sum(Pdis_v, axis=0)
            ),
            'demand_total': to_list(
                np.sum(df['PloadFixed'] + val(PdrShift) - val(PdrCutE), axis=0)
                + np.sum(val(Peb), axis=0) + np.sum(val(Pelec), axis=0)
                + np.sum(Pch_v, axis=0) + np.sum(val(Pcomp), axis=0)
            ),
        },
        'h2': {
            'hours': hours,
            'load': to_list(np.sum(df['H2load'], axis=0)),
            'production': to_list(np.sum(val(H2prod), axis=0)),
            'storage_discharge': to_list(np.sum(val(H2dis), axis=0)),
            'shortage': to_list(np.sum(val(H2short), axis=0)),
        },
        'dr': {
            'hours': hours,
            'shift_base': to_list(np.sum(df['PdrShiftBase'], axis=0)),
            'shift': to_list(np.sum(val(PdrShift), axis=0)),
            'cut_e': to_list(np.sum(val(PdrCutE), axis=0)),
        },
        'node_voltage': {
            'available': True,
            'hours': hours,
            'nodes': list(range(1, B + 1)),
            'voltage': [to_list(val(V)[b, :]) for b in range(B)],
            'summary': {
                'min': round(float(np.min(val(V))), 6),
                'max': round(float(np.max(val(V))), 6),
                'low_violations': int(np.sum(val(V) < 0.95 ** 2)),
                'high_violations': int(np.sum(val(V) > 1.05 ** 2)),
            },
        },
        'scenario_table': [],
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    return result
