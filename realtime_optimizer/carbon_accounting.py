import numpy as np


def compute_carbon(Pgrid, Pchp, Hchp, Fgas, data):
    dt = data['dt']
    zetaE = data.get('zetaE', 1080)
    zetaH = data.get('zetaH', 324)
    chiE = data.get('chiE', 728)
    chiH = data.get('chiH', 367.2)
    ceh = data.get('ceh', 1.6667)

    chp_heat_eq = ceh * Pchp + Hchp

    grid_emission = zetaE * Pgrid * dt
    chp_emission = zetaH * chp_heat_eq * dt
    emission = grid_emission + chp_emission

    grid_quota = chiE * Pgrid * dt
    chp_quota = chiH * chp_heat_eq * dt

    carbon_quota_mode = data.get('carbonQuotaMode', 'baseline-scenario')
    fixed_quota = data.get('fixedCarbonQuota_kg', None)
    use_fixed = (carbon_quota_mode == 'fixed-baseline') and (fixed_quota is not None)

    if use_fixed:
        quota = fixed_quota
    else:
        quota = grid_quota + chp_quota

    net_surplus = quota - emission

    return {
        'gridEmission': grid_emission,
        'chpEmission': chp_emission,
        'emission': emission,
        'gridQuota': grid_quota,
        'chpQuota': chp_quota,
        'quota': quota,
        'netAllowanceSurplus': net_surplus,
    }
