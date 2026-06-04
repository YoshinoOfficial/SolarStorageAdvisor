import json
import math
import os
import time
from datetime import datetime

import numpy as np
import pandas as pd


DEFAULT_CONFIG = {
    "irradiance_medium": 300.0,
    "irradiance_high": 700.0,
    "wind_medium": 4.0,
    "wind_high": 8.0,
}


class DailyDispatchEngine:
    def __init__(self, project_root):
        self.project_root = project_root
        self.optimization_dir = self._resolve_dir("零碳园区优化_v12")
        self.scenario_dir = os.path.join(self.optimization_dir, "1-Day Scenarios")
        self.output_dir = os.path.join(project_root, "data", "daily_dispatch")
        self.config_path = os.path.join(project_root, "config", "daily_dispatch_config.json")
        self.state_path = os.path.join(self.output_dir, "daily_dispatch_state.json")
        self.latest_path = os.path.join(self.output_dir, "latest_result.json")
        os.makedirs(self.output_dir, exist_ok=True)

    def _resolve_dir(self, name):
        path = os.path.join(self.project_root, name)
        if os.path.isdir(path):
            return path
        raise FileNotFoundError(f"Required directory not found: {path}")

    def get_config(self):
        config = dict(DEFAULT_CONFIG)
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update({k: float(v) for k, v in saved.items() if k in DEFAULT_CONFIG})
        return config

    def save_config(self, payload):
        config = self.get_config()
        for key in DEFAULT_CONFIG:
            if key in payload:
                value = float(payload[key])
                if value < 0:
                    raise ValueError(f"{key} must be non-negative")
                config[key] = value
        if config["irradiance_medium"] >= config["irradiance_high"]:
            raise ValueError("irradiance_medium must be smaller than irradiance_high")
        if config["wind_medium"] >= config["wind_high"]:
            raise ValueError("wind_medium must be smaller than wind_high")
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return config

    def latest_result(self):
        if not os.path.exists(self.latest_path):
            return None
        with open(self.latest_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(self, temperature_c, irradiance_w_m2, wind_speed_m_s):
        start = time.time()
        config = self.get_config()
        env = {
            "temperature_c": float(temperature_c),
            "irradiance_w_m2": float(irradiance_w_m2),
            "wind_speed_m_s": float(wind_speed_m_s),
        }
        if env["irradiance_w_m2"] < 0 or env["wind_speed_m_s"] < 0:
            raise ValueError("Irradiance and wind speed must be non-negative")

        pv_label = self._map_pv_label(env["irradiance_w_m2"], config)
        wind_label = self._map_wind_label(env["wind_speed_m_s"], config)
        scenario_id, exact_match = self._select_scenario(pv_label, wind_label)
        data = self._build_input_profiles(scenario_id)
        result = self._dispatch(data, scenario_id, pv_label, wind_label, env, exact_match)
        result["runtime_ms"] = round((time.time() - start) * 1000, 1)

        self._write_outputs(result)
        with open(self.latest_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        return result

    def _map_pv_label(self, irradiance, config):
        if irradiance >= config["irradiance_high"]:
            return 0
        if irradiance >= config["irradiance_medium"]:
            return 1
        return 2

    def _map_wind_label(self, wind_speed, config):
        if wind_speed >= config["wind_high"]:
            return 2
        if wind_speed >= config["wind_medium"]:
            return 1
        return 0

    def _select_scenario(self, pv_label, wind_label):
        labels_path = os.path.join(self.scenario_dir, "scenario_labels.csv")
        labels = pd.read_csv(labels_path)
        labels = labels[labels["scenario_index"] <= 100].copy()
        exact = labels[(labels["pv_label"] == pv_label) & (labels["wind_label"] == wind_label)]
        exact_match = not exact.empty
        if exact.empty:
            labels["distance"] = (labels["pv_label"] - pv_label).abs() + (labels["wind_label"] - wind_label).abs()
            candidates = labels[labels["distance"] == labels["distance"].min()].copy()
        else:
            candidates = exact.copy()
        candidates = candidates.sort_values("scenario_index")
        ids = [int(v) for v in candidates["scenario_index"].tolist()]

        state = self._load_state()
        key = f"pv{pv_label}_wind{wind_label}"
        cursor = int(state.get("rotation", {}).get(key, 0))
        scenario_id = ids[cursor % len(ids)]
        state.setdefault("rotation", {})[key] = cursor + 1
        self._save_state(state)
        return scenario_id, exact_match

    def _load_state(self):
        if not os.path.exists(self.state_path):
            return {"rotation": {}}
        with open(self.state_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _save_state(self, state):
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _build_input_profiles(self, scenario_id):
        path = os.path.join(self.scenario_dir, f"scenario_{scenario_id:03d}.csv")
        df = pd.read_csv(path)
        hourly = df.groupby(np.arange(len(df)) // 4).mean(numeric_only=True)
        pv18 = hourly["node_18_PV"].clip(0, 1).to_numpy()
        pv33 = hourly["node_33_PV"].clip(0, 1).to_numpy()
        w22 = hourly["node_22_wind"].clip(0, 1).to_numpy()
        w25 = hourly["node_25_wind"].clip(0, 1).to_numpy()

        # Capacities mirror the scaling idea in the MATLAB model.
        pv_cap = np.array([1.60, 2.00, 1.50]) * 5.5
        wind_cap = np.array([0.0, 1.20, 0.0]) * 5.5
        pv_pu = np.vstack([(pv18 + pv33) / 2, pv18, pv33])
        wind_pu = np.vstack([w22, (w22 + w25) / 2, w25])
        ppv = pv_pu * pv_cap[:, None]
        pwind = wind_pu * wind_cap[:, None]

        shape = np.array([
            0.56, 0.54, 0.53, 0.52, 0.54, 0.62, 0.73, 0.83,
            0.90, 0.94, 0.96, 0.97, 0.98, 0.97, 0.96, 0.96,
            0.98, 1.00, 0.98, 0.93, 0.86, 0.78, 0.69, 0.61,
        ])
        electric_peak = np.array([1.65, 1.25, 1.10])
        heat_peak = np.array([1.70, 1.45, 0.95])
        h2_peak = np.array([9.0, 8.2, 7.0])
        pload_fixed = electric_peak[:, None] * shape[None, :]
        pdr_shift_base = 0.10 * pload_fixed
        pdr_shift_max = 0.25 * pload_fixed
        pdr_cut_emax = 0.05 * pload_fixed
        hload = heat_peak[:, None] * (0.72 + 0.28 * shape)[None, :]
        h2load = h2_peak[:, None] * (0.84 + 0.16 * np.roll(shape, 3))[None, :]
        ce = np.array([
            0.40, 0.32, 0.26, 0.21, 0.23, 0.35, 0.55, 0.70,
            0.82, 0.84, 0.80, 0.78, 0.68, 0.57, 0.52, 0.53,
            0.65, 0.85, 0.96, 0.92, 0.87, 0.78, 0.66, 0.48,
        ]) * 1000.0

        return {
            "Ppv": ppv,
            "Pwind": pwind,
            "PloadFixed": pload_fixed,
            "PdrShiftBase": pdr_shift_base,
            "PdrShiftMax": pdr_shift_max,
            "PdrCutEmax": pdr_cut_emax,
            "Hload": hload,
            "H2load": h2load,
            "ce": np.tile(ce, (3, 1)),
        }

    def _dispatch(self, data, scenario_id, pv_label, wind_label, env, exact_match):
        n, t_count = 3, 24
        hours = np.arange(1, t_count + 1)
        p_load_fixed = data["PloadFixed"]
        pdr_base = data["PdrShiftBase"]
        pdr_max = data["PdrShiftMax"]
        pdr_cut_max = data["PdrCutEmax"]
        p_load = p_load_fixed + pdr_base
        h_load = data["Hload"]
        h2_load = data["H2load"]
        ppv = data["Ppv"]
        pwind = data["Pwind"]
        ce = data["ce"]

        arrays = {}
        for name in [
            "Pgrid", "Pch", "Pdis", "SOC_e", "PpvUse", "PpvCurt", "PwindUse", "PwindCurt",
            "Fgas", "Pchp", "Hchp", "Peb", "Heb", "Pelec", "H2prod", "H2cons_fc", "Pfc",
            "Pcomp", "Hch", "Hdis", "SOC_th", "H2ch", "H2dis", "SOC_h2", "H2short", "Hdump",
            "PdrShift", "PdrShiftDev", "PdrCutE", "HdrCut", "H2drCut", "PloadDR", "HloadDR",
            "H2loadDR", "Qpv", "Qwind", "Qes", "QinjLocal", "PinjLocal", "V",
            "CarbonEmission_kg", "CarbonQuota_kg", "CarbonBuyMarket_kg", "CarbonSellMarket_kg",
            "CarbonTradeWithCommunities_kg", "CarbonUnusedAllowance_kg",
        ]:
            arrays[name] = np.zeros((n, t_count), dtype=float)

        emax = np.array([3.6, 5.6, 4.0])
        eth_max = np.array([6.8, 5.8, 3.8])
        eh2_max = np.array([180.0, 160.0, 130.0])
        soc_e = 0.55 * emax
        soc_th = 0.55 * eth_max
        soc_h2 = 0.55 * eh2_max
        p_ch_max = np.array([0.9, 1.4, 1.0])
        p_dis_max = np.array([0.8, 1.2, 0.9])
        h_ch_max = np.array([1.2, 1.0, 0.8])
        h_dis_max = np.array([1.1, 0.9, 0.75])
        h2_ch_max = np.array([18.0, 16.0, 13.0])
        h2_dis_max = np.array([16.0, 14.0, 12.0])
        pchp_rated = np.array([1.15, 1.05, 0.85])
        eta_e_chp = np.array([0.35, 0.35, 0.35])
        eta_h_chp = np.array([0.45, 0.45, 0.45])
        peb_max = np.array([1.5, 1.2, 0.9])
        eta_eb = np.array([0.95, 0.95, 0.95])
        pelec_max = np.array([1.0, 0.9, 0.75])
        eta_elec = np.array([20.0, 20.0, 20.0])
        eta_fc = np.array([0.04, 0.04, 0.04])
        alpha_comp_h2 = np.array([0.018, 0.018, 0.018])

        zeta_e, zeta_h, chi_e, chi_h, ceh = 1080.0, 324.0, 728.0, 367.2, 1.6667
        carbon_buy_price, carbon_sell_price = 150.0, 100.0
        c_gas = 260.0

        for tt in range(t_count):
            high_price = ce[0, tt] >= 780
            low_price = ce[0, tt] <= 420
            for i in range(n):
                p_shift = pdr_base[i, tt] * (0.75 if high_price else 1.08 if low_price else 1.0)
                p_cut = min(pdr_cut_max[i, tt], p_load_fixed[i, tt] * (0.035 if high_price else 0.0))
                p_demand_base = p_load_fixed[i, tt] + p_shift - p_cut

                renewable = ppv[i, tt] + pwind[i, tt]
                usable = min(renewable, p_demand_base)
                pv_share = ppv[i, tt] / renewable if renewable > 1e-9 else 0.0
                arrays["PpvUse"][i, tt] = min(ppv[i, tt], usable * pv_share)
                arrays["PwindUse"][i, tt] = min(pwind[i, tt], usable * (1 - pv_share))
                surplus = max(0.0, renewable - usable)
                deficit = max(0.0, p_demand_base - usable)

                discharge = 0.0
                if high_price and deficit > 0 and soc_e[i] > 0.12 * emax[i]:
                    discharge = min(deficit, p_dis_max[i], max(0.0, soc_e[i] - 0.12 * emax[i]) * 0.92)
                    soc_e[i] -= discharge / 0.92
                    deficit -= discharge
                arrays["Pdis"][i, tt] = discharge

                charge = 0.0
                if surplus > 0 and soc_e[i] < 0.9 * emax[i]:
                    charge = min(surplus, p_ch_max[i], max(0.0, 0.9 * emax[i] - soc_e[i]) / 0.92)
                    soc_e[i] += charge * 0.92
                    surplus -= charge
                elif low_price and soc_e[i] < 0.62 * emax[i]:
                    charge = min(p_ch_max[i] * 0.35, max(0.0, 0.62 * emax[i] - soc_e[i]) / 0.92)
                    soc_e[i] += charge * 0.92
                    deficit += charge
                arrays["Pch"][i, tt] = charge

                h_need = h_load[i, tt]
                chp_heat_target = min(h_need * 0.58, pchp_rated[i] * eta_h_chp[i] / eta_e_chp[i])
                pchp = min(pchp_rated[i], chp_heat_target / max(eta_h_chp[i] / eta_e_chp[i], 1e-6))
                fgas = pchp / eta_e_chp[i]
                hchp = eta_h_chp[i] * fgas
                deficit = max(0.0, deficit - pchp)

                h_remaining = max(0.0, h_need - hchp)
                hdis = min(h_remaining, h_dis_max[i], max(0.0, soc_th[i] - 0.12 * eth_max[i]) * 0.9)
                soc_th[i] -= hdis / 0.9
                h_remaining -= hdis
                peb = min(peb_max[i], h_remaining / eta_eb[i])
                heb = eta_eb[i] * peb
                deficit += peb
                h_remaining -= heb
                hch = 0.0
                if h_remaining < 1e-6 and hchp > h_need and soc_th[i] < 0.9 * eth_max[i]:
                    hch = min(h_ch_max[i], hchp - h_need, (0.9 * eth_max[i] - soc_th[i]) / 0.9)
                    soc_th[i] += hch * 0.9

                h2_need = h2_load[i, tt]
                pelec = 0.0
                if surplus > 0:
                    pelec = min(pelec_max[i], surplus, h2_need / eta_elec[i])
                    surplus -= pelec
                    h2prod = pelec * eta_elec[i]
                else:
                    h2prod = 0.0
                h2_remaining = max(0.0, h2_need - h2prod)
                h2dis = min(h2_remaining, h2_dis_max[i], max(0.0, soc_h2[i] - 0.12 * eh2_max[i]))
                soc_h2[i] -= h2dis
                h2_remaining -= h2dis
                h2short = max(0.0, h2_remaining)
                h2ch = 0.0
                if surplus > 0 and soc_h2[i] < 0.9 * eh2_max[i]:
                    extra_pelec = min(pelec_max[i] - pelec, surplus)
                    extra_h2 = extra_pelec * eta_elec[i]
                    h2ch = min(h2_ch_max[i], extra_h2, 0.9 * eh2_max[i] - soc_h2[i])
                    pelec += h2ch / eta_elec[i]
                    surplus -= h2ch / eta_elec[i]
                    soc_h2[i] += h2ch
                pcomp = alpha_comp_h2[i] * (h2prod + h2ch)
                deficit += pelec + pcomp

                if h2short > 0 and deficit > 0 and soc_h2[i] > 0.18 * eh2_max[i]:
                    h2_fc = min(h2short, 0.35 * h2_dis_max[i], soc_h2[i] - 0.18 * eh2_max[i])
                    pfc = eta_fc[i] * h2_fc
                    soc_h2[i] -= h2_fc
                    h2short -= h2_fc
                    deficit = max(0.0, deficit - pfc)
                else:
                    h2_fc = 0.0
                    pfc = 0.0

                grid = max(0.0, deficit)
                pv_curt = max(0.0, ppv[i, tt] - arrays["PpvUse"][i, tt])
                wind_curt = max(0.0, pwind[i, tt] - arrays["PwindUse"][i, tt])
                if surplus > 0 and renewable > 1e-9:
                    pv_curt = max(0.0, pv_curt - min(pv_curt, surplus * pv_share))
                    wind_curt = max(0.0, wind_curt - min(wind_curt, surplus * (1 - pv_share)))

                arrays["Pgrid"][i, tt] = grid
                arrays["PpvCurt"][i, tt] = pv_curt
                arrays["PwindCurt"][i, tt] = wind_curt
                arrays["Fgas"][i, tt] = fgas
                arrays["Pchp"][i, tt] = pchp
                arrays["Hchp"][i, tt] = hchp
                arrays["Peb"][i, tt] = peb
                arrays["Heb"][i, tt] = heb
                arrays["Pelec"][i, tt] = pelec
                arrays["H2prod"][i, tt] = h2prod
                arrays["H2cons_fc"][i, tt] = h2_fc
                arrays["Pfc"][i, tt] = pfc
                arrays["Pcomp"][i, tt] = pcomp
                arrays["Hdis"][i, tt] = hdis
                arrays["Hch"][i, tt] = hch
                arrays["H2dis"][i, tt] = h2dis + h2_fc
                arrays["H2ch"][i, tt] = h2ch
                arrays["H2short"][i, tt] = h2short
                arrays["PdrShift"][i, tt] = p_shift
                arrays["PdrShiftDev"][i, tt] = abs(p_shift - pdr_base[i, tt])
                arrays["PdrCutE"][i, tt] = p_cut
                arrays["PloadDR"][i, tt] = p_demand_base
                arrays["HloadDR"][i, tt] = h_load[i, tt]
                arrays["H2loadDR"][i, tt] = h2_load[i, tt]
                arrays["SOC_e"][i, tt] = soc_e[i]
                arrays["SOC_th"][i, tt] = soc_th[i]
                arrays["SOC_h2"][i, tt] = soc_h2[i]
                arrays["PinjLocal"][i, tt] = grid
                arrays["QinjLocal"][i, tt] = 0.32 * p_demand_base
                arrays["V"][i, tt] = max(0.94, min(1.04, 1.0 - 0.004 * grid + 0.001 * renewable))

                heat_equiv = ceh * pchp + hchp
                emission = zeta_e * grid + zeta_h * heat_equiv
                quota = chi_e * grid + chi_h * heat_equiv
                diff = emission - quota
                arrays["CarbonEmission_kg"][i, tt] = emission
                arrays["CarbonQuota_kg"][i, tt] = quota
                arrays["CarbonBuyMarket_kg"][i, tt] = max(0.0, diff)
                arrays["CarbonSellMarket_kg"][i, tt] = max(0.0, -diff) * 0.7
                arrays["CarbonUnusedAllowance_kg"][i, tt] = max(0.0, -diff) * 0.3

        self._balance_renewable_use(ppv, pwind, arrays)

        scalars = self._solution_scalars(data, arrays, ce, c_gas, carbon_buy_price, carbon_sell_price)
        aggregate = self._aggregate_table(data, arrays, scenario_id)
        community = self._community_table(data, arrays, scenario_id, emax, eth_max, eh2_max)
        kpis = {
            "cost": round(scalars["Objective_Yuan"], 0),
            "grid_energy": round(float(arrays["Pgrid"].sum()), 1),
            "carbon_emission": round(float(arrays["CarbonEmission_kg"].sum()) / 1000.0, 1),
            "renewable_rate": round(safe_pct(
                float(arrays["PpvUse"].sum() + arrays["PwindUse"].sum()),
                float(ppv.sum() + pwind.sum()),
            ), 1),
            "carbon_trading_cost": round(scalars["Part_carbonTradingCost"], 0),
        }

        return {
            "run_id": datetime.now().strftime("%Y%m%d%H%M%S"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "scenario_id": scenario_id,
            "scenario": f"PY_DDRE_{scenario_id:03d}",
            "pv_label": pv_label,
            "wind_label": wind_label,
            "exact_match": exact_match,
            "weather_label": self._weather_label(pv_label, wind_label),
            "environment": env,
            "kpis": kpis,
            "chart": self._chart_payload(aggregate),
            "h2": self._h2_payload(aggregate),
            "dr": self._dr_payload(aggregate),
            "energy_mix": self._energy_mix(aggregate),
            "aggregate_rows": aggregate.to_dict(orient="records"),
            "community_rows": community.to_dict(orient="records"),
            "scalar_rows": [scalars],
        }

    def _balance_renewable_use(self, ppv, pwind, arrays):
        arrays["PpvUse"] = np.minimum(ppv, arrays["PpvUse"])
        arrays["PwindUse"] = np.minimum(pwind, arrays["PwindUse"])
        arrays["PpvCurt"] = np.maximum(0.0, ppv - arrays["PpvUse"])
        arrays["PwindCurt"] = np.maximum(0.0, pwind - arrays["PwindUse"])

    def _solution_scalars(self, data, arrays, ce, c_gas, carbon_buy_price, carbon_sell_price):
        grid_cost = float((ce * arrays["Pgrid"]).sum())
        gas_cost = float(c_gas * arrays["Fgas"].sum())
        carbon_cost = float(carbon_buy_price * arrays["CarbonBuyMarket_kg"].sum() / 1000.0 -
                            carbon_sell_price * arrays["CarbonSellMarket_kg"].sum() / 1000.0)
        pv_curt_cost = float(60.0 * arrays["PpvCurt"].sum())
        wind_curt_cost = float(200.0 * arrays["PwindCurt"].sum())
        h2_short_cost = float(900.0 * arrays["H2short"].sum())
        dr_cost = float(120.0 * arrays["PdrShiftDev"].sum() + 260.0 * arrays["PdrCutE"].sum())
        objective = grid_cost + gas_cost + carbon_cost + pv_curt_cost + wind_curt_cost + h2_short_cost + dr_cost
        return {
            "Scenario": "PY_DDRE",
            "Method": "python-heuristic",
            "Objective_Yuan": objective,
            "LocalObjective_Yuan": None,
            "Iterations": 1,
            "FinalPrimalResidual": None,
            "FinalDualResidual": None,
            "MaxConsensusP_MW": None,
            "MaxConsensusQ_MVAr": None,
            "MaxConsensusCarbon_kg": None,
            "TotalPVCurt_MWh": float(arrays["PpvCurt"].sum()),
            "TotalWindCurt_MWh": float(arrays["PwindCurt"].sum()),
            "TotalH2Shortage_kg": float(arrays["H2short"].sum()),
            "TotalPdrShiftDeviation_MWh": float(arrays["PdrShiftDev"].sum()),
            "TotalElectricCurtailmentDR_MWh": float(arrays["PdrCutE"].sum()),
            "TotalHeatCurtailmentDR_MWh": float(arrays["HdrCut"].sum()),
            "TotalHydrogenCurtailmentDR_kg": float(arrays["H2drCut"].sum()),
            "Part_gridCost": grid_cost,
            "Part_carbonTradingCost": carbon_cost,
            "Part_gasCost": gas_cost,
            "Part_gasCarbonCost": 0.0,
            "Part_pvCurtCost": pv_curt_cost,
            "Part_windCurtCost": wind_curt_cost,
            "Part_h2ShortCost": h2_short_cost,
            "Part_demandResponseCost": dr_cost,
            "Part_qSupportCost": 0.0,
        }

    def _aggregate_table(self, data, arrays, scenario_id):
        rows = []
        for tt in range(24):
            row = {"Scenario": f"PY_DDRE_{scenario_id:03d}", "Method": "python-heuristic", "TimeSlot": tt + 1}
            for name in [
                "Pload", "PloadFixed", "PdrShiftBase", "PdrShiftMax", "PdrCutEmax",
                "Hload", "HdrCutMax", "H2load", "H2drCutMax", "Ppv", "Pwind", "PcompFixed",
            ]:
                source = {
                    "Pload": data["PloadFixed"] + data["PdrShiftBase"],
                    "HdrCutMax": np.zeros((3, 24)),
                    "H2drCutMax": np.zeros((3, 24)),
                    "PcompFixed": np.zeros((3, 24)),
                }.get(name, data.get(name, np.zeros((3, 24))))
                row[f"DataSum_{name}"] = float(source[:, tt].sum())
            for name, matrix in arrays.items():
                if name in {"SOC_e", "SOC_th", "SOC_h2", "V"}:
                    row[f"Mean_{name}"] = float(matrix[:, tt].mean())
                else:
                    row[f"Sum_{name}"] = float(matrix[:, tt].sum())
            row["TotalRenewableAvailable_MW"] = row["DataSum_Ppv"] + row["DataSum_Pwind"]
            row["TotalRenewableUsed_MW"] = row["Sum_PpvUse"] + row["Sum_PwindUse"]
            row["TotalRenewableCurtailment_MW"] = row["Sum_PpvCurt"] + row["Sum_PwindCurt"]
            rows.append(row)
        return pd.DataFrame(rows)

    def _community_table(self, data, arrays, scenario_id, emax, eth_max, eh2_max):
        rows = []
        for i in range(3):
            for tt in range(24):
                row = {
                    "Scenario": f"PY_DDRE_{scenario_id:03d}",
                    "Method": "python-heuristic",
                    "Community": i + 1,
                    "TimeSlot": tt + 1,
                }
                for name in ["PloadFixed", "PdrShiftBase", "PdrShiftMax", "PdrCutEmax", "Hload", "H2load", "Ppv", "Pwind"]:
                    row[f"Data_{name}"] = float(data[name][i, tt])
                row["Data_Pload"] = row["Data_PloadFixed"] + row["Data_PdrShiftBase"]
                row["Data_HdrCutMax"] = 0.0
                row["Data_H2drCutMax"] = 0.0
                row["Data_PcompFixed"] = 0.0
                for name, matrix in arrays.items():
                    row[name] = float(matrix[i, tt])
                row["Data_Emax"] = float(emax[i])
                row["Data_SOC0_e"] = float(0.55 * emax[i])
                row["Data_EthMax"] = float(eth_max[i])
                row["Data_SOC0_th"] = float(0.55 * eth_max[i])
                row["Data_EH2Max"] = float(eh2_max[i])
                row["Data_SOC0_h2"] = float(0.55 * eh2_max[i])
                rows.append(row)
        return pd.DataFrame(rows)

    def _chart_payload(self, aggregate):
        hours = aggregate["TimeSlot"].tolist()
        supply = {
            "hours": hours,
            "pv": aggregate["Sum_PpvUse"].round(4).tolist(),
            "wind": aggregate["Sum_PwindUse"].round(4).tolist(),
            "grid": aggregate["Sum_Pgrid"].round(4).tolist(),
            "discharge": aggregate["Sum_Pdis"].round(4).tolist(),
            "chp": aggregate["Sum_Pchp"].round(4).tolist(),
            "fc": aggregate["Sum_Pfc"].round(4).tolist(),
        }
        demand = {
            "hours": hours,
            "load": aggregate["Sum_PloadDR"].round(4).tolist(),
            "elec": aggregate["Sum_Pelec"].round(4).tolist(),
            "eb": aggregate["Sum_Peb"].round(4).tolist(),
            "comp": aggregate["Sum_Pcomp"].round(4).tolist(),
            "charge": aggregate["Sum_Pch"].round(4).tolist(),
        }
        soc = {
            "hours": hours,
            "soc_e": aggregate["Mean_SOC_e"].round(4).tolist(),
            "soc_th": aggregate["Mean_SOC_th"].round(4).tolist(),
            "soc_h2": aggregate["Mean_SOC_h2"].round(4).tolist(),
        }
        return {
            "supply": supply,
            "demand": demand,
            "soc": soc,
            "supply_total": (aggregate["Sum_PpvUse"] + aggregate["Sum_PwindUse"] + aggregate["Sum_Pgrid"] +
                             aggregate["Sum_Pdis"] + aggregate["Sum_Pchp"] + aggregate["Sum_Pfc"]).round(4).tolist(),
            "demand_total": (aggregate["Sum_PloadDR"] + aggregate["Sum_Pelec"] + aggregate["Sum_Peb"] +
                             aggregate["Sum_Pcomp"] + aggregate["Sum_Pch"]).round(4).tolist(),
        }

    def _h2_payload(self, aggregate):
        return {
            "hours": aggregate["TimeSlot"].tolist(),
            "load": aggregate["DataSum_H2load"].round(4).tolist(),
            "production": aggregate["Sum_H2prod"].round(4).tolist(),
            "storage_discharge": aggregate["Sum_H2dis"].round(4).tolist(),
            "storage_charge": aggregate["Sum_H2ch"].round(4).tolist(),
            "shortage": aggregate["Sum_H2short"].round(4).tolist(),
        }

    def _dr_payload(self, aggregate):
        return {
            "hours": aggregate["TimeSlot"].tolist(),
            "shift": aggregate["Sum_PdrShift"].round(4).tolist(),
            "shift_base": aggregate["DataSum_PdrShiftBase"].round(4).tolist(),
            "cut_e": aggregate["Sum_PdrCutE"].round(4).tolist(),
        }

    def _energy_mix(self, aggregate):
        values = {
            "pv": float(aggregate["Sum_PpvUse"].sum()),
            "wind": float(aggregate["Sum_PwindUse"].sum()),
            "grid": float(aggregate["Sum_Pgrid"].sum()),
            "chp": float(aggregate["Sum_Pchp"].sum()),
            "fc": float(aggregate["Sum_Pfc"].sum()),
            "discharge": float(aggregate["Sum_Pdis"].sum()),
        }
        values["total"] = sum(values.values())
        return {k: round(v, 3) for k, v in values.items()}

    def _weather_label(self, pv_label, wind_label):
        pv_text = {0: "高光照", 1: "中等光照", 2: "低光照"}[pv_label]
        wind_text = {0: "低风", 1: "中风", 2: "高风"}[wind_label]
        return f"{pv_text} / {wind_text}"

    def _write_outputs(self, result):
        prefix = os.path.join(self.output_dir, f"{result['scenario']}_python_heuristic")
        pd.DataFrame(result["aggregate_rows"]).to_csv(f"{prefix}_hourly_aggregate.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(result["community_rows"]).to_csv(f"{prefix}_community_hourly.csv", index=False, encoding="utf-8-sig")
        pd.DataFrame(result["scalar_rows"]).to_csv(f"{prefix}_solution_scalars.csv", index=False, encoding="utf-8-sig")
        manifest = pd.DataFrame([
            {"Scenario": result["scenario"], "Method": "python-heuristic", "DataType": "hourly_aggregate", "FileName": f"{prefix}_hourly_aggregate.csv"},
            {"Scenario": result["scenario"], "Method": "python-heuristic", "DataType": "community_hourly", "FileName": f"{prefix}_community_hourly.csv"},
            {"Scenario": result["scenario"], "Method": "python-heuristic", "DataType": "solution_scalars", "FileName": f"{prefix}_solution_scalars.csv"},
        ])
        manifest.to_csv(os.path.join(self.output_dir, "plot_data_manifest.csv"), index=False, encoding="utf-8-sig")


def safe_pct(numerator, denominator):
    if abs(denominator) < 1e-9:
        return 0.0
    return numerator / denominator * 100.0
