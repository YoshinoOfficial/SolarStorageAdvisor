import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import base64
from io import BytesIO
from flask import Flask, render_template, jsonify, request
import sys
import os
import threading

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

OPTIMIZATION_DATA_DIR = os.path.join(project_root, '零碳园区优化_v12')
PLANNING_DATA_DIR = os.path.join(project_root, '零碳园区优化_v12', '园区规划与容量配置')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

matplotlib_lock = threading.Lock()

from main import get_simulation_data, calculate_daily_cost, calculate_renewable_revenue
from Solar.Solar import calculate_all_communities
from Wind.Wind import calculate_all_wind_communities
from config.config_manager import (
    load_electricity_price, save_electricity_price, save_feed_in_price,
    list_available_panels, get_panel_quantities, set_panel_quantities, set_panel_quantity, load_panel_by_id,
    list_available_storages, get_current_storage_id, set_current_storage_id, load_storage_config,
    save_storage_config, create_new_storage_config, delete_storage_config,
    create_new_panel_config, delete_panel_config, save_panel_config,
    list_communities, get_current_community, set_current_community,
    list_wind_communities, get_current_wind_community, set_current_wind_community,
    get_wind_coefficient, set_wind_coefficient, get_wind_turbine_config
)

app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')

def dataframe_to_json(data):
    result = {
        'timestamps': [str(t) for t in data.index],
        'solar': data['Solar'].tolist(),
        'wind': data['Wind'].tolist(),
        'consumption': data['Consumption'].tolist(),
        'energy_balance': data['Energy Balance'].tolist(),
        'storage_power': data['Storage Power'].tolist(),
        'soc': data['SOC'].tolist(),
        'net_load': data['Net Load'].tolist()
    }
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    try:
        panels = list_available_panels()
        storages = list_available_storages()
        communities = list_communities()
        current_community = get_current_community()
        panel_quantities = get_panel_quantities()
        current_storage_id = get_current_storage_id()
        current_storage_config = load_storage_config()
        electricity_price_config = load_electricity_price()
        wind_communities = list_wind_communities()
        current_wind_community = get_current_wind_community()
        
        return jsonify({
            'success': True,
            'data': {
                'panels': panels,
                'storages': storages,
                'communities': communities,
                'current_community': current_community,
                'panel_quantities': panel_quantities,
                'current_storage_id': current_storage_id,
                'current_storage_config': current_storage_config,
                'electricity_price': electricity_price_config['electricity_price'],
                'feed_in_price': electricity_price_config.get('feed_in_price', 0.4),
                'wind_communities': wind_communities,
                'current_wind_community': current_wind_community
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    try:
        community = get_current_community()
        data = get_simulation_data(community=community)
        cost = calculate_daily_cost(data)
        revenue = calculate_renewable_revenue(data)
        chart_data = dataframe_to_json(data)
        
        return jsonify({
            'success': True,
            'data': {
                'chart_data': chart_data,
                'daily_cost': cost,
                'renewable_revenue': revenue,
                'current_community': community
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/panels/<panel_id>', methods=['GET'])
def get_panel_config(panel_id):
    try:
        config = load_panel_by_id(panel_id)
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/panels/quantities', methods=['POST'])
def set_panel_quantities_api():
    try:
        quantities = request.json.get('quantities')
        set_panel_quantities(quantities)
        return jsonify({'success': True, 'message': '已更新光伏板数量配置'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/panels/quantity', methods=['POST'])
def set_panel_quantity_api():
    try:
        panel_id = request.json.get('panel_id')
        quantity = request.json.get('quantity')
        set_panel_quantity(panel_id, quantity)
        return jsonify({'success': True, 'message': f'已设置 {panel_id} 数量为 {quantity}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/panels/create', methods=['POST'])
def create_panel():
    try:
        params = request.json
        new_config = create_new_panel_config(
            panel_id=params['panel_id'],
            name=params['name'],
            description=params.get('description', ''),
            area=params['area'],
            lat=params.get('lat', 39.9),
            lon=params.get('lon', 116.4),
            tz=params.get('tz', 'Asia/Shanghai'),
            altitude=params.get('altitude', 44),
            location_name=params.get('location_name', 'Beijing'),
            surface_tilt=params.get('surface_tilt', 30),
            surface_azimuth=params.get('surface_azimuth', 180)
        )
        return jsonify({'success': True, 'message': f'已创建光伏板: {params["panel_id"]}', 'config': new_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/panels/delete', methods=['POST'])
def delete_panel():
    try:
        panel_id = request.json.get('panel_id')
        delete_panel_config(panel_id)
        return jsonify({'success': True, 'message': f'已删除光伏板: {panel_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/panels/update', methods=['POST'])
def update_panel():
    try:
        params = request.json
        panel_id = params.get('panel_id')
        if not panel_id:
            return jsonify({'success': False, 'error': '缺少 panel_id 参数'}), 400
        save_panel_config(
            panel_id=panel_id,
            area=params.get('area'),
            surface_tilt=params.get('surface_tilt'),
            surface_azimuth=params.get('surface_azimuth'),
            lat=params.get('lat'),
            lon=params.get('lon'),
            tz=params.get('tz'),
            altitude=params.get('altitude'),
            location_name=params.get('location_name'),
            start=params.get('start'),
            end=params.get('end'),
            freq=params.get('freq'),
            temp_air=params.get('temp_air'),
            wind_speed=params.get('wind_speed')
        )
        return jsonify({'success': True, 'message': f'已更新光伏板配置: {panel_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/communities', methods=['GET'])
def get_communities():
    try:
        communities = list_communities()
        current_community = get_current_community()
        return jsonify({
            'success': True,
            'data': {
                'communities': communities,
                'current_community': current_community
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/communities/switch', methods=['POST'])
def switch_community():
    try:
        community_id = request.json.get('community_id')
        set_current_community(community_id)
        return jsonify({'success': True, 'message': f'已切换到社区: {community_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/communities/quantities', methods=['POST'])
def set_community_quantities():
    try:
        data = request.json
        community_id = data.get('community_id')
        quantities = data.get('quantities')
        if community_id:
            set_panel_quantities(quantities, community=community_id)
        else:
            set_panel_quantities(quantities)
        return jsonify({'success': True, 'message': '已更新社区光伏板数量配置'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/community/solar-curve', methods=['GET'])
def get_community_solar_curve():
    try:
        community = request.args.get('community') or get_current_community()

        data_dir = os.path.join(project_root, 'data')
        csv_path = os.path.join(data_dir, f'solar_{community}.csv')

        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': '该社区的光伏数据尚未生成，请先保存配置'}), 404

        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        time_col = df.columns[0]
        times = df[time_col].tolist()

        curves = {}
        for col in df.columns[1:]:
            curves[col] = df[col].tolist()

        return jsonify({
            'success': True,
            'data': {
                'community': community,
                'times': times,
                'curves': curves
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/communities/recalculate-solar', methods=['POST'])
def recalculate_solar():
    try:
        calculate_all_communities()
        return jsonify({'success': True, 'message': '已重新计算所有社区光伏功率曲线'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wind/communities', methods=['GET'])
def get_wind_communities():
    try:
        communities = list_wind_communities()
        current = get_current_wind_community()
        turbine = get_wind_turbine_config()
        return jsonify({
            'success': True,
            'data': {
                'communities': communities,
                'current_wind_community': current,
                'turbine_config': turbine
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/wind/communities/switch', methods=['POST'])
def switch_wind_community():
    try:
        community_id = request.json.get('community_id')
        set_current_wind_community(community_id)
        return jsonify({'success': True, 'message': f'已切换到风电社区: {community_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/wind/coefficient', methods=['POST'])
def update_wind_coefficient():
    try:
        data = request.json
        community_id = data.get('community_id')
        coefficient = data.get('coefficient')
        if community_id:
            set_wind_coefficient(community_id, coefficient)
        else:
            set_wind_coefficient(get_current_wind_community(), coefficient)
        return jsonify({'success': True, 'message': f'已更新风电系数为: {coefficient}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/community/wind-curve', methods=['GET'])
def get_community_wind_curve():
    try:
        community = request.args.get('community') or get_current_wind_community()

        data_dir = os.path.join(project_root, 'data')
        csv_path = os.path.join(data_dir, f'wind_{community}.csv')

        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': '该社区的风电数据尚未生成，请先保存配置'}), 404

        df = pd.read_csv(csv_path, encoding='utf-8-sig')

        time_col = df.columns[0]
        times = df[time_col].tolist()

        curves = {}
        for col in df.columns[1:]:
            curves[col] = df[col].tolist()

        return jsonify({
            'success': True,
            'data': {
                'community': community,
                'times': times,
                'curves': curves
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/communities/recalculate-wind', methods=['POST'])
def recalculate_wind():
    try:
        calculate_all_wind_communities()
        return jsonify({'success': True, 'message': '已重新计算所有社区风电功率曲线'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/storages/switch', methods=['POST'])
def switch_storage():
    try:
        storage_id = request.json.get('storage_id')
        set_current_storage_id(storage_id)
        return jsonify({'success': True, 'message': f'已切换到储能: {storage_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/storages/create', methods=['POST'])
def create_storage():
    try:
        params = request.json
        new_config = create_new_storage_config(
            storage_id=params['storage_id'],
            name=params['name'],
            description=params.get('description', ''),
            capacity=params['capacity'],
            max_charge_power=params['max_charge_power'],
            max_discharge_power=params['max_discharge_power'],
            charge_efficiency=params.get('charge_efficiency', 0.95),
            discharge_efficiency=params.get('discharge_efficiency', 0.95),
            initial_soc=params.get('initial_soc', 0.5),
            min_soc=params.get('min_soc', 0.1),
            max_soc=params.get('max_soc', 0.9)
        )
        return jsonify({'success': True, 'message': f'已创建储能: {params["storage_id"]}', 'config': new_config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/storages/delete', methods=['POST'])
def delete_storage():
    try:
        storage_id = request.json.get('storage_id')
        delete_storage_config(storage_id)
        return jsonify({'success': True, 'message': f'已删除储能: {storage_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/storages/update', methods=['POST'])
def update_storage():
    try:
        params = request.json
        save_storage_config(
            capacity=params.get('capacity'),
            max_charge_power=params.get('max_charge_power'),
            max_discharge_power=params.get('max_discharge_power'),
            charge_efficiency=params.get('charge_efficiency'),
            discharge_efficiency=params.get('discharge_efficiency'),
            initial_soc=params.get('initial_soc'),
            min_soc=params.get('min_soc'),
            max_soc=params.get('max_soc')
        )
        return jsonify({'success': True, 'message': '已更新储能配置'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/electricity-price/update', methods=['POST'])
def update_electricity_price():
    try:
        price = request.json.get('electricity_price')
        save_electricity_price(price)
        return jsonify({'success': True, 'message': f'已更新电价: {price} 元/kWh'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/feed-in-price/update', methods=['POST'])
def update_feed_in_price():
    try:
        price = request.json.get('feed_in_price')
        save_feed_in_price(price)
        return jsonify({'success': True, 'message': f'已更新上网电价: {price} 元/kWh'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/optimization/typical-scenarios', methods=['GET'])
def get_typical_scenarios():
    try:
        settings_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_settings.csv')
        df = pd.read_csv(settings_path)
        
        scenarios = []
        for _, row in df.iterrows():
            scenarios.append({
                'scenario': row['TypicalScenario'],
                'scenario_cn': row['TypicalScenarioCN'],
                'representative_days': int(row['RepresentativeDays']),
                'pv_scale': float(row['PVScaleFinal']),
                'wind_scale': float(row['WindScaleFinal']),
                'load_scale': float(row['LoadScaleFinal']),
                'h2_scale': float(row['H2ScaleFinal']),
                'available_pv': float(row['AvailablePV_MWh']),
                'available_wind': float(row['AvailableWind_MWh']),
                'total_electric_load': float(row['TotalElectricLoad_MWh']),
                'total_heat_load': float(row['TotalHeatLoad_MWh']),
                'total_h2_load': float(row['TotalH2Load_kg'])
            })
        
        return jsonify({'success': True, 'data': scenarios})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/typical-metrics', methods=['GET'])
def get_typical_metrics():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)
        
        metrics = []
        for _, row in df.iterrows():
            metrics.append({
                'scenario': row['TypicalScenario'],
                'scenario_cn': row['TypicalScenarioCN'],
                'representative_days': int(row['RepresentativeDays']),
                'total_objective': float(row['TotalObjective_Yuan']),
                'annual_objective': float(row['AnnualObjective_Yuan']),
                'grid_energy': float(row['GridEnergy_MWh']),
                'annual_grid_energy': float(row['AnnualGridEnergy_MWh']),
                'grid_peak': float(row['GridPeak_MW']),
                'gas_energy': float(row['GasEnergy_MWhth']),
                'annual_gas_energy': float(row['AnnualGasEnergy_MWhth']),
                'carbon_emission': float(row['CarbonEmission_tCO2']),
                'annual_carbon_emission': float(row['AnnualCarbonEmission_tCO2']),
                'carbon_quota': float(row['CarbonQuota_tCO2']),
                'annual_carbon_quota': float(row['AnnualCarbonQuota_tCO2']),
                'carbon_surplus': float(row['CarbonSurplusBeforeTrade_tCO2']),
                'annual_carbon_surplus': float(row['AnnualCarbonSurplusBeforeTrade_tCO2']),
                'carbon_buy': float(row['CarbonBuyMarket_tCO2']),
                'annual_carbon_buy': float(row['AnnualCarbonBuyMarket_tCO2']),
                'carbon_sell': float(row['CarbonSellMarket_tCO2']),
                'annual_carbon_sell': float(row['AnnualCarbonSellMarket_tCO2']),
                'renewable_available': float(row['RenewableAvailable_MWh']),
                'renewable_use': float(row['RenewableUse_MWh']),
                'renewable_curtailment': float(row['RenewableCurtailment_MWh']),
                'renewable_use_rate': float(row['RenewableUseRate_percent']),
                'h2_shortage': float(row['H2Shortage_kg']),
                'annual_h2_shortage': float(row['AnnualH2Shortage_kg']),
                'storage_charge': float(row['StorageCharge_MWh']),
                'storage_discharge': float(row['StorageDischarge_MWh']),
                'storage_soc_swing': float(row['StorageSOCSwing_MWh'])
            })
        
        return jsonify({'success': True, 'data': metrics})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/weather/config', methods=['GET'])
def get_weather_config():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)
        df = df.drop_duplicates(subset=['TypicalScenario'])

        data = []
        for _, row in df.iterrows():
            data.append({
                'scenario': row['TypicalScenario'],
                'name': row['TypicalScenarioCN'],
                'days': int(row['RepresentativeDays'])
            })

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/weather/update', methods=['POST'])
def update_weather_config():
    try:
        days = request.json.get('days', {})

        valid_scenarios = ['Sunny_LowWind', 'Sunny_HighWind', 'Cloudy_MidWind', 'Rainy_LowWind', 'Rainy_HighWind']
        if set(days.keys()) != set(valid_scenarios):
            return jsonify({'success': False, 'error': '天气场景名称不正确'}), 400

        for k, v in days.items():
            if not isinstance(v, int) or v < 0:
                return jsonify({'success': False, 'error': f'{k} 的天数必须为非负整数'}), 400

        total = sum(days.values())
        if total != 365:
            return jsonify({'success': False, 'error': f'总天数必须为365天，当前为{total}天'}), 400

        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)

        annual_cols = [c for c in df.columns if c.startswith('Annual') and c != 'AnnualObjective_Yuan']
        daily_map = {}
        for col in ['TotalObjective_Yuan', 'GridEnergy_MWh', 'GasEnergy_MWhth',
                     'CarbonEmission_tCO2', 'CarbonQuota_tCO2', 'CarbonSurplusBeforeTrade_tCO2',
                     'CarbonBuyMarket_tCO2', 'CarbonSellMarket_tCO2', 'CarbonTradeAbs_tCO2',
                     'CarbonUnusedAllowance_tCO2', 'RenewableCurtailment_MWh', 'H2Shortage_kg']:
            if col in df.columns:
                daily_map[col] = col

        for scenario, new_days in days.items():
            mask = df['TypicalScenario'] == scenario
            df.loc[mask, 'RepresentativeDays'] = new_days

            for daily_col, _ in daily_map.items():
                annual_col = 'Annual' + daily_col.replace('_Yuan', '_Yuan').replace('_MWh', '_MWh').replace('_tCO2', '_tCO2').replace('_kg', '_kg')
                if annual_col in df.columns and daily_col in df.columns:
                    df.loc[mask, annual_col] = df.loc[mask, daily_col] * new_days

            if 'AnnualObjective_Yuan' in df.columns and 'TotalObjective_Yuan' in df.columns:
                df.loc[mask, 'AnnualObjective_Yuan'] = df.loc[mask, 'TotalObjective_Yuan'] * new_days
            if 'AnnualRenewableAvailable_MWh' in df.columns and 'RenewableAvailable_MWh' in df.columns:
                df.loc[mask, 'AnnualRenewableAvailable_MWh'] = df.loc[mask, 'RenewableAvailable_MWh'] * new_days
            if 'AnnualRenewableUse_MWh' in df.columns and 'RenewableUse_MWh' in df.columns:
                df.loc[mask, 'AnnualRenewableUse_MWh'] = df.loc[mask, 'RenewableUse_MWh'] * new_days

        df.to_csv(metrics_path, index=False)

        return jsonify({'success': True, 'message': '天气配置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/annual-summary', methods=['GET'])
def get_annual_summary():
    try:
        summary_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_annual_weighted_summary.csv')
        df = pd.read_csv(summary_path)
        
        results = []
        for _, row in df.iterrows():
            results.append({
                'total_representative_days': int(row['TotalRepresentativeDays']),
                'annual_objective': float(row['AnnualObjective_Yuan']),
                'annual_grid_energy': float(row['AnnualGridEnergy_MWh']),
                'annual_gas_energy': float(row['AnnualGasEnergy_MWhth']),
                'annual_carbon_emission': float(row['AnnualCarbonEmission_tCO2']),
                'annual_carbon_quota': float(row['AnnualCarbonQuota_tCO2']),
                'annual_carbon_buy': float(row['AnnualCarbonBuyMarket_tCO2']),
                'annual_carbon_sell': float(row['AnnualCarbonSellMarket_tCO2']),
                'annual_renewable_available': float(row['AnnualRenewableAvailable_MWh']),
                'annual_renewable_use': float(row['AnnualRenewableUse_MWh']),
                'annual_renewable_curtailment': float(row['AnnualRenewableCurtailment_MWh']),
                'annual_renewable_use_rate': float(row['AnnualRenewableUseRate_percent']),
                'annual_h2_shortage': float(row['AnnualH2Shortage_kg'])
            })
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/s4-annual-kpis', methods=['GET'])
def get_s4_annual_kpis():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)
        df = df.drop_duplicates(subset=['TypicalScenario'])

        annual_cost = float((df['TotalObjective_Yuan'] * df['RepresentativeDays']).sum())
        annual_gen = float((df['RenewableAvailable_MWh'] * df['RepresentativeDays']).sum())
        annual_use = float((df['RenewableUse_MWh'] * df['RepresentativeDays']).sum())
        renewable_rate = annual_use / annual_gen * 100 if annual_gen > 0 else 0

        kpis = {
            'annual_cost': round(annual_cost, 0),
            'annual_renewable_generation_mwh': round(annual_gen, 1),
            'renewable_use_rate': round(renewable_rate, 1)
        }

        return jsonify({'success': True, 'data': kpis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/renewable-utilization', methods=['GET'])
def get_renewable_utilization_chart():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)
        
        unique_scenarios = df.drop_duplicates(subset=['TypicalScenario'])
        
        with matplotlib_lock:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            scenarios = unique_scenarios['TypicalScenarioCN'].tolist()
            available = unique_scenarios['RenewableAvailable_MWh'].tolist()
            used = unique_scenarios['RenewableUse_MWh'].tolist()
            curtailed = unique_scenarios['RenewableCurtailment_MWh'].tolist()
            
            x = range(len(scenarios))
            width = 0.25
            
            ax.bar([i - width for i in x], available, width, label='可利用量', color='#3498db')
            ax.bar(x, used, width, label='实际利用量', color='#2ecc71')
            ax.bar([i + width for i in x], curtailed, width, label='弃能量', color='#e74c3c')
            
            ax.set_xlabel('典型场景')
            ax.set_ylabel('能量 (MWh)')
            ax.set_title('各典型场景可再生能源利用情况')
            ax.set_xticks(x)
            ax.set_xticklabels(scenarios, rotation=15, ha='right')
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
        
        return jsonify({'success': True, 'data': image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/hourly-power-data', methods=['GET'])
def get_hourly_power_data():
    try:
        mode = request.args.get('mode', 'scenario')

        if mode == 'weather':
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'year_plot_data_csv')
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            weather_name_map = {
                'Sunny_LowWind': '晴天少风',
                'Sunny_HighWind': '晴天多风',
                'Cloudy_MidWind': '多云中风',
                'Rainy_LowWind': '阴天少风',
                'Rainy_HighWind': '阴天多风'
            }
            scenario = weather_param
            scenario_name = weather_name_map.get(weather_param, weather_param)
            hourly_file = os.path.join(data_dir, f'{scenario}_admm_hourly_aggregate.csv')
        else:
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
            scenario_param = request.args.get('scenario', 'S4')
            scenario_map = {
                'S1': 'S1_NoCarbon_NoDR',
                'S2': 'S2_Normal_NoCarbon_DR',
                'S3': 'S3_Carbon_NoDR',
                'S4': 'S4_Carbon_DR'
            }
            scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
            scenario_name_map = {
                'S1_NoCarbon_NoDR': 'S1: 无碳交易无需求响应（基准）',
                'S2_Normal_NoCarbon_DR': 'S2: 无碳交易有需求响应',
                'S3_Carbon_NoDR': 'S3: 有碳交易无需求响应',
                'S4_Carbon_DR': 'S4: 有碳交易有需求响应'
            }
            scenario_name = scenario_name_map.get(scenario, 'S4')
            hourly_file = os.path.join(data_dir, f'{scenario}_admm_hourly_aggregate.csv')
        
        if not os.path.exists(hourly_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404
        
        df = pd.read_csv(hourly_file)
        
        supply_data = {
            'hours': list(range(1, 25)),
            'pv': df['Sum_PpvUse'].tolist(),
            'wind': df['Sum_PwindUse'].tolist(),
            'grid': df['Sum_Pgrid'].tolist(),
            'discharge': df['Sum_Pdis'].tolist(),
            'chp': df['Sum_Pchp'].tolist(),
            'fc': df['Sum_Pfc'].tolist()
        }
        
        demand_data = {
            'hours': list(range(1, 25)),
            'load': df['DataSum_Pload'].tolist(),
            'elec': df['Sum_Pelec'].tolist(),
            'eb': df['Sum_Peb'].tolist(),
            'comp': df['Sum_Pcomp'].tolist(),
            'charge': df['Sum_Pch'].tolist()
        }
        
        soc_data = {
            'hours': list(range(1, 25)),
            'soc_e': df['Mean_SOC_e'].tolist(),
            'soc_th': df['Mean_SOC_th'].tolist(),
            'soc_h2': df['Mean_SOC_h2'].tolist()
        }
        
        supply_total = (df['Sum_PpvUse'] + df['Sum_PwindUse'] + df['Sum_Pgrid'] + df['Sum_Pdis'] + df['Sum_Pchp'] + df['Sum_Pfc']).tolist()
        demand_total = (df['DataSum_Pload'] + df['Sum_Pelec'] + df['Sum_Peb'] + df['Sum_Pcomp'] + df['Sum_Pch']).tolist()
        
        return jsonify({
            'success': True,
            'scenario': scenario_name,
            'supply': supply_data,
            'demand': demand_data,
            'soc': soc_data,
            'supply_total': supply_total,
            'demand_total': demand_total
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/community-power-data', methods=['GET'])
def get_community_power_data():
    try:
        mode = request.args.get('mode', 'scenario')
        community_id = request.args.get('community', '1')

        if mode == 'weather':
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'year_plot_data_csv')
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            weather_name_map = {
                'Sunny_LowWind': '晴天少风', 'Sunny_HighWind': '晴天多风',
                'Cloudy_MidWind': '多云中风', 'Rainy_LowWind': '阴天少风',
                'Rainy_HighWind': '阴天多风'
            }
            scenario = weather_param
            scenario_name = weather_name_map.get(weather_param, weather_param)
            community_file = os.path.join(data_dir, f'{scenario}_admm_community_hourly.csv')
        else:
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
            scenario_param = request.args.get('scenario', 'S4')
            scenario_map = {
                'S1': 'S1_NoCarbon_NoDR',
                'S2': 'S2_Normal_NoCarbon_DR',
                'S3': 'S3_Carbon_NoDR',
                'S4': 'S4_Carbon_DR'
            }
            scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
            scenario_name_map = {
                'S1_NoCarbon_NoDR': 'S1: 无碳交易无需求响应（基准）',
                'S2_Normal_NoCarbon_DR': 'S2: 无碳交易有需求响应',
                'S3_Carbon_NoDR': 'S3: 有碳交易无需求响应',
                'S4_Carbon_DR': 'S4: 有碳交易有需求响应'
            }
            scenario_name = scenario_name_map.get(scenario, 'S4')
            community_file = os.path.join(data_dir, f'{scenario}_admm_community_hourly.csv')
        
        if not os.path.exists(community_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404
        
        df = pd.read_csv(community_file)
        df_community = df[df['Community'] == int(community_id)]
        
        supply_data = {
            'hours': list(range(1, 25)),
            'pv': df_community['PpvUse'].tolist(),
            'wind': df_community['PwindUse'].tolist(),
            'grid': df_community['Pgrid'].tolist(),
            'discharge': df_community['Pdis'].tolist(),
            'chp': df_community['Pchp'].tolist(),
            'fc': df_community['Pfc'].tolist()
        }
        
        demand_data = {
            'hours': list(range(1, 25)),
            'load': df_community['Data_Pload'].tolist(),
            'elec': df_community['Pelec'].tolist(),
            'eb': df_community['Peb'].tolist(),
            'comp': df_community['Pcomp'].tolist(),
            'charge': df_community['Pch'].tolist()
        }
        
        soc_data = {
            'hours': list(range(1, 25)),
            'soc_e': df_community['SOC_e'].tolist(),
            'soc_th': df_community['SOC_th'].tolist(),
            'soc_h2': df_community['SOC_h2'].tolist()
        }
        
        supply_total = (df_community['PpvUse'] + df_community['PwindUse'] + df_community['Pgrid'] + df_community['Pdis'] + df_community['Pchp'] + df_community['Pfc']).tolist()
        demand_total = (df_community['Data_Pload'] + df_community['Pelec'] + df_community['Peb'] + df_community['Pcomp'] + df_community['Pch']).tolist()
        
        return jsonify({
            'success': True,
            'scenario': scenario_name,
            'community': community_id,
            'supply': supply_data,
            'demand': demand_data,
            'soc': soc_data,
            'supply_total': supply_total,
            'demand_total': demand_total
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/carbon-analysis', methods=['GET'])
def get_carbon_analysis_chart():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)
        
        unique_scenarios = df.drop_duplicates(subset=['TypicalScenario'])
        
        with matplotlib_lock:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            scenarios = unique_scenarios['TypicalScenarioCN'].tolist()
            emissions = unique_scenarios['CarbonEmission_tCO2'].tolist()
            quotas = unique_scenarios['CarbonQuota_tCO2'].tolist()
            surpluses = unique_scenarios['CarbonSurplusBeforeTrade_tCO2'].tolist()
            
            x = range(len(scenarios))
            width = 0.35
            
            ax1.bar(x, emissions, width, label='碳排放', color='#e74c3c')
            ax1.bar(x, quotas, width, bottom=emissions, label='碳配额', color='#3498db')
            
            ax1.set_xlabel('典型场景')
            ax1.set_ylabel('碳排放量 (tCO2)')
            ax1.set_title('碳排放与配额')
            ax1.set_xticks(x)
            ax1.set_xticklabels(scenarios, rotation=15, ha='right')
            ax1.legend()
            ax1.grid(axis='y', alpha=0.3)
            
            ax2.bar(x, surpluses, color='#2ecc71')
            ax2.set_xlabel('典型场景')
            ax2.set_ylabel('碳配额盈余 (tCO2)')
            ax2.set_title('碳配额盈余')
            ax2.set_xticks(x)
            ax2.set_xticklabels(scenarios, rotation=15, ha='right')
            ax2.grid(axis='y', alpha=0.3)
            
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
        
        return jsonify({'success': True, 'data': image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/economic-comparison', methods=['GET'])
def get_economic_comparison_chart():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)
        
        unique_scenarios = df.drop_duplicates(subset=['TypicalScenario'])
        
        with matplotlib_lock:
            fig, ax = plt.subplots(figsize=(10, 6))
            
            scenarios = unique_scenarios['TypicalScenarioCN'].tolist()
            objectives = unique_scenarios['TotalObjective_Yuan'].tolist()
            
            bars = ax.bar(scenarios, objectives, color=['#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#e74c3c'])
            
            ax.set_xlabel('典型场景')
            ax.set_ylabel('目标函数 (元)')
            ax.set_title('各典型场景日优化成本')
            ax.grid(axis='y', alpha=0.3)
            
            for bar, val in zip(bars, objectives):
                ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 200, 
                       f'{val:.0f}', ha='center', va='bottom', fontsize=9)
            
            plt.xticks(rotation=15, ha='right')
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
        
        return jsonify({'success': True, 'data': image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/admm-convergence', methods=['GET'])
def get_admm_convergence_chart():
    try:
        convergence_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
        
        scenarios = ['S1_NoCarbon_NoDR', 'S2_Normal_NoCarbon_DR',
                     'S3_Carbon_NoDR', 'S4_Carbon_DR']
        scenario_labels = ['S1: 无碳交易无需求响应', 'S2: 无碳交易有需求响应',
                          'S3: 有碳交易无需求响应', 'S4: 有碳交易有需求响应']
        colors = ['#e74c3c', '#3498db', '#2ecc71', '#9b59b6']
        
        with matplotlib_lock:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
            
            for scenario, label, color in zip(scenarios, scenario_labels, colors):
                conv_file = os.path.join(convergence_dir, f'{scenario}_admm_convergence.csv')
                if os.path.exists(conv_file):
                    df = pd.read_csv(conv_file)
                    ax1.semilogy(df['Iteration'], df['PrimalResidual'], 
                                label=label, color=color, linewidth=1.5)
                    ax2.semilogy(df['Iteration'], df['DualResidual'], 
                                label=label, color=color, linewidth=1.5)
            
            ax1.set_xlabel('迭代次数')
            ax1.set_ylabel('原始残差 (对数尺度)')
            ax1.set_title('ADMM原始残差收敛曲线')
            ax1.legend(fontsize=8)
            ax1.grid(True, alpha=0.3)
            
            ax2.set_xlabel('迭代次数')
            ax2.set_ylabel('对偶残差 (对数尺度)')
            ax2.set_title('ADMM对偶残差收敛曲线')
            ax2.legend(fontsize=8)
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
        
        return jsonify({'success': True, 'data': image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/hourly-power', methods=['GET'])
def get_hourly_power_chart():
    try:
        data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
        
        scenario_param = request.args.get('scenario', 'S4')
        scenario_map = {
            'S1': 'S1_NoCarbon_NoDR',
            'S2': 'S2_Normal_NoCarbon_DR',
            'S3': 'S3_Carbon_NoDR',
            'S4': 'S4_Carbon_DR'
        }
        scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
        scenario_name_map = {
            'S1_NoCarbon_NoDR': 'S1: 无碳交易无需求响应（基准）',
            'S2_Normal_NoCarbon_DR': 'S2: 无碳交易有需求响应',
            'S3_Carbon_NoDR': 'S3: 有碳交易无需求响应',
            'S4_Carbon_DR': 'S4: 有碳交易有需求响应'
        }
        scenario_name = scenario_name_map.get(scenario, 'S4')
        
        hourly_file = os.path.join(data_dir, f'{scenario}_admm_hourly_aggregate.csv')
        
        if not os.path.exists(hourly_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404
        
        df = pd.read_csv(hourly_file)
        
        with matplotlib_lock:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
            
            hours = range(1, 25)
            
            supply = df['Sum_PpvUse'].values + df['Sum_PwindUse'].values + df['Sum_Pgrid'].values + df['Sum_Pdis'].values + df['Sum_Pchp'].values + df['Sum_Pfc'].values
            demand = df['DataSum_Pload'].values + df['Sum_Pelec'].values + df['Sum_Peb'].values + df['Sum_Pcomp'].values + df['Sum_Pch'].values
            
            ax1.stackplot(hours, 
                         df['Sum_PpvUse'].values, 
                         df['Sum_PwindUse'].values,
                         df['Sum_Pgrid'].values,
                         df['Sum_Pdis'].values,
                         df['Sum_Pchp'].values,
                         df['Sum_Pfc'].values,
                         labels=['光伏', '风电', '电网', '储能放电', 'CHP', '燃料电池'],
                         colors=['#f1c40f', '#3498db', '#95a5a6', '#2ecc71', '#e74c3c', '#8e44ad'],
                         alpha=0.8)
            ax1.plot(hours, demand, 'k-', linewidth=2.5, label='总用电')
            ax1.set_xlabel('时间 (h)')
            ax1.set_ylabel('功率 (MW)')
            ax1.set_title(f'{scenario_name} 24小时电力平衡 - 供电侧')
            ax1.legend(loc='upper left', fontsize=8, ncol=3)
            ax1.grid(True, alpha=0.3)
            ax1.set_xlim(1, 24)
            ax1.set_ylim(0, max(supply.max(), demand.max()) * 1.1)
            
            ax2.stackplot(hours,
                         df['DataSum_Pload'].values,
                         df['Sum_Pelec'].values,
                         df['Sum_Peb'].values,
                         df['Sum_Pcomp'].values,
                         df['Sum_Pch'].values,
                         labels=['电负荷', '电解槽', '电锅炉', '压缩机', '储能充电'],
                         colors=['#e74c3c', '#9b59b6', '#f39c12', '#1abc9c', '#2ecc71'],
                         alpha=0.8)
            ax2.plot(hours, supply, 'k-', linewidth=2.5, label='总供电')
            ax2.set_xlabel('时间 (h)')
            ax2.set_ylabel('功率 (MW)')
            ax2.set_title(f'{scenario_name} 24小时电力平衡 - 用电侧')
            ax2.legend(loc='upper left', fontsize=8, ncol=3)
            ax2.grid(True, alpha=0.3)
            ax2.set_xlim(1, 24)
            ax2.set_ylim(0, max(supply.max(), demand.max()) * 1.1)
            
            plt.tight_layout()
            
            buffer = BytesIO()
            plt.savefig(buffer, format='png', dpi=100)
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close(fig)
        
        return jsonify({'success': True, 'data': image_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/daily-kpis', methods=['GET'])
def get_daily_kpis():
    try:
        mode = request.args.get('mode', 'scenario')

        if mode == 'weather':
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
            df = pd.read_csv(metrics_path)
            row = df[df['TypicalScenario'] == weather_param]
            if row.empty:
                return jsonify({'success': False, 'error': '未找到天气场景数据'}), 404
            row = row.iloc[0]
            kpis = {
                'cost': round(float(row['TotalObjective_Yuan']), 0),
                'grid_energy': round(float(row['GridEnergy_MWh']), 1),
                'carbon_emission': round(float(row['CarbonEmission_tCO2']), 1),
                'renewable_rate': round(float(row['RenewableUseRate_percent']), 1)
            }
        else:
            scenario_param = request.args.get('scenario', 'S4')
            scenario_map = {
                'S1': 'S1_NoCarbon_NoDR',
                'S2': 'S2_Normal_NoCarbon_DR',
                'S3': 'S3_Carbon_NoDR',
                'S4': 'S4__Carbon_DR'
            }
            scenario = scenario_map.get(scenario_param, 'S4__Carbon_DR')
            metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_metric_table.csv')
            df = pd.read_csv(metrics_path)
            df = df[df['Method'].str.contains('admm')]
            row = df[df['Scenario'] == scenario]
            if row.empty:
                return jsonify({'success': False, 'error': '未找到场景数据'}), 404
            row = row.iloc[0]
            kpis = {
                'cost': round(float(row['TotalObjective_Yuan']), 0),
                'grid_energy': round(float(row['GridEnergy_MWh']), 1),
                'carbon_emission': round(float(row['CarbonEmission_kg']) / 1000, 1),
                'renewable_rate': round(float(row['RenewableUseRate_percent']), 1)
            }

        return jsonify({'success': True, 'data': kpis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/energy-summary', methods=['GET'])
def get_energy_summary():
    try:
        mode = request.args.get('mode', 'scenario')

        if mode == 'weather':
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'year_plot_data_csv')
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            hourly_file = os.path.join(data_dir, f'{weather_param}_admm_hourly_aggregate.csv')

            if not os.path.exists(hourly_file):
                return jsonify({'success': False, 'error': '数据文件不存在'}), 404

            df_hourly = pd.read_csv(hourly_file)

            daily_pv = float(df_hourly['Sum_PpvUse'].sum())
            daily_wind = float(df_hourly['Sum_PwindUse'].sum())
            daily_chp = float(df_hourly['Sum_Pchp'].sum())
            daily_fc = float(df_hourly['Sum_Pfc'].sum())
            daily_discharge = float(df_hourly['Sum_Pdis'].sum())
            daily_grid = float(df_hourly['Sum_Pgrid'].sum())

            total_generation = daily_pv + daily_wind + daily_chp + daily_fc + daily_discharge

            energy_mix = {
                'pv': round(daily_pv, 2),
                'wind': round(daily_wind, 2),
                'chp': round(daily_chp, 2),
                'fc': round(daily_fc, 2),
                'discharge': round(daily_discharge, 2),
                'grid': round(daily_grid, 2),
                'total': round(total_generation, 2)
            }

            if total_generation > 0:
                energy_mix['pv_ratio'] = round(daily_pv / total_generation * 100, 1)
                energy_mix['wind_ratio'] = round(daily_wind / total_generation * 100, 1)
                energy_mix['chp_ratio'] = round(daily_chp / total_generation * 100, 1)
                energy_mix['fc_ratio'] = round(daily_fc / total_generation * 100, 1)
                energy_mix['discharge_ratio'] = round(daily_discharge / total_generation * 100, 1)
            else:
                energy_mix['pv_ratio'] = 0
                energy_mix['wind_ratio'] = 0
                energy_mix['chp_ratio'] = 0
                energy_mix['fc_ratio'] = 0
                energy_mix['discharge_ratio'] = 0

            return jsonify({'success': True, 'data': energy_mix})

        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df_metrics = pd.read_csv(metrics_path)

        unique_scenarios = df_metrics.drop_duplicates(subset=['TypicalScenario'])

        if unique_scenarios.empty:
            return jsonify({'success': False, 'error': '未找到场景数据'}), 404

        scenario_param = request.args.get('scenario', 'S4')
        scenario_map = {
            'S1': 'S1_NoCarbon_NoDR',
            'S2': 'S2_Normal_NoCarbon_DR',
            'S3': 'S3_Carbon_NoDR',
            'S4': 'S4_Carbon_DR'
        }
        scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
        data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
        hourly_file = os.path.join(data_dir, f'{scenario}_admm_hourly_aggregate.csv')

        if not os.path.exists(hourly_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404

        df_hourly = pd.read_csv(hourly_file)

        daily_pv = float(df_hourly['Sum_PpvUse'].sum())
        daily_wind = float(df_hourly['Sum_PwindUse'].sum())
        daily_chp = float(df_hourly['Sum_Pchp'].sum())
        daily_fc = float(df_hourly['Sum_Pfc'].sum())
        daily_discharge = float(df_hourly['Sum_Pdis'].sum())
        daily_grid = float(df_hourly['Sum_Pgrid'].sum())

        annual_pv = 0
        annual_wind = 0
        annual_chp = 0
        annual_fc = 0
        annual_discharge = 0
        annual_grid = 0

        for _, row in unique_scenarios.iterrows():
            days = float(row['RepresentativeDays'])
            renewable_available = float(row['RenewableAvailable_MWh'])
            renewable_use = float(row['RenewableUse_MWh'])

            ratio = renewable_use / renewable_available if renewable_available > 0 else 1

            annual_pv += daily_pv * days * ratio
            annual_wind += daily_wind * days * ratio
            annual_chp += daily_chp * days
            annual_fc += daily_fc * days
            annual_discharge += daily_discharge * days
            annual_grid += daily_grid * days

        total_generation = annual_pv + annual_wind + annual_chp + annual_fc + annual_discharge

        energy_mix = {
            'pv': round(annual_pv, 2),
            'wind': round(annual_wind, 2),
            'chp': round(annual_chp, 2),
            'fc': round(annual_fc, 2),
            'discharge': round(annual_discharge, 2),
            'grid': round(annual_grid, 2),
            'total': round(total_generation, 2)
        }

        if total_generation > 0:
            energy_mix['pv_ratio'] = round(annual_pv / total_generation * 100, 1)
            energy_mix['wind_ratio'] = round(annual_wind / total_generation * 100, 1)
            energy_mix['chp_ratio'] = round(annual_chp / total_generation * 100, 1)
            energy_mix['fc_ratio'] = round(annual_fc / total_generation * 100, 1)
            energy_mix['discharge_ratio'] = round(annual_discharge / total_generation * 100, 1)
        else:
            energy_mix['pv_ratio'] = 0
            energy_mix['wind_ratio'] = 0
            energy_mix['chp_ratio'] = 0
            energy_mix['fc_ratio'] = 0
            energy_mix['discharge_ratio'] = 0

        return jsonify({'success': True, 'data': energy_mix})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/h2-shortage', methods=['GET'])
def get_h2_shortage_chart():
    try:
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'year_typical_scenario_metric_table.csv')
        df = pd.read_csv(metrics_path)

        unique_scenarios = df.drop_duplicates(subset=['TypicalScenario'])

        data = {
            'scenarios': unique_scenarios['TypicalScenarioCN'].tolist(),
            'daily_shortage_kg': [float(v) for v in unique_scenarios['H2Shortage_kg']],
            'annual_shortage_kg': [float(v) for v in unique_scenarios['AnnualH2Shortage_kg']],
        }

        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/optimization/chart/h2-power-data', methods=['GET'])
def get_h2_power_data():
    try:
        mode = request.args.get('mode', 'scenario')

        if mode == 'weather':
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'year_plot_data_csv')
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            hourly_file = os.path.join(data_dir, f'{weather_param}_admm_hourly_aggregate.csv')
        else:
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
            scenario_param = request.args.get('scenario', 'S4')
            scenario_map = {
                'S1': 'S1_NoCarbon_NoDR',
                'S2': 'S2_Normal_NoCarbon_DR',
                'S3': 'S3_Carbon_NoDR',
                'S4': 'S4_Carbon_DR'
            }
            scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
            hourly_file = os.path.join(data_dir, f'{scenario}_admm_hourly_aggregate.csv')

        if not os.path.exists(hourly_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404

        df = pd.read_csv(hourly_file)

        h2_data = {
            'hours': list(range(1, 25)),
            'production': df['Sum_H2prod'].tolist(),
            'storage_discharge': df['Sum_H2dis'].tolist(),
            'fuel_cell': df['Sum_H2cons_fc'].tolist(),
            'storage_charge': df['Sum_H2ch'].tolist(),
            'load': df['DataSum_H2load'].tolist(),
            'shortage': df['Sum_H2short'].tolist(),
            'soc_h2': df['Mean_SOC_h2'].tolist()
        }

        return jsonify({'success': True, 'data': h2_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/optimization/chart/dr-power-data', methods=['GET'])
def get_dr_power_data():
    try:
        mode = request.args.get('mode', 'scenario')

        if mode == 'weather':
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'year_plot_data_csv')
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            hourly_file = os.path.join(data_dir, f'{weather_param}_admm_hourly_aggregate.csv')
            scalars_file = os.path.join(data_dir, f'{weather_param}_admm_solution_scalars.csv')
        else:
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
            scenario_param = request.args.get('scenario', 'S4')
            scenario_map = {
                'S1': 'S1_NoCarbon_NoDR',
                'S2': 'S2_Normal_NoCarbon_DR',
                'S3': 'S3_Carbon_NoDR',
                'S4': 'S4_Carbon_DR'
            }
            scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
            hourly_file = os.path.join(data_dir, f'{scenario}_admm_hourly_aggregate.csv')
            scalars_file = os.path.join(data_dir, f'{scenario}_admm_solution_scalars.csv')

        if not os.path.exists(hourly_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404

        df = pd.read_csv(hourly_file)
        df_s = pd.read_csv(scalars_file)

        dr_data = {
            'hours': list(range(1, 25)),
            'load_original': df['DataSum_Pload'].tolist(),
            'load_after_dr': df['Sum_PloadDR'].tolist(),
            'shift': df['Sum_PdrShift'].tolist(),
            'shift_dev': df['Sum_PdrShiftDev'].tolist(),
            'cut_e': df['Sum_PdrCutE'].tolist(),
            'hdr_cut': df['Sum_HdrCut'].tolist(),
            'h2dr_cut': df['Sum_H2drCut'].tolist(),
            'summary': {
                'total_shift_mwh': float(df_s['TotalPdrShiftDeviation_MWh'].iloc[0]),
                'total_cut_e_mwh': float(df_s['TotalElectricCurtailmentDR_MWh'].iloc[0]),
                'total_cut_h_mwh': float(df_s['TotalHeatCurtailmentDR_MWh'].iloc[0]),
                'total_cut_h2_kg': float(df_s['TotalHydrogenCurtailmentDR_kg'].iloc[0]),
            }
        }

        return jsonify({'success': True, 'data': dr_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/optimization/chart/cost-breakdown', methods=['GET'])
def get_cost_breakdown():
    try:
        data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')

        scenario_param = request.args.get('scenario', 'S4')
        scenario_map = {
            'S1': 'S1_NoCarbon_NoDR',
            'S2': 'S2_Normal_NoCarbon_DR',
            'S3': 'S3_Carbon_NoDR',
            'S4': 'S4_Carbon_DR'
        }
        scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')

        scalars_file = os.path.join(data_dir, f'{scenario}_admm_solution_scalars.csv')

        if not os.path.exists(scalars_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404

        df = pd.read_csv(scalars_file)
        row = df.iloc[0]

        cost_data = {
            'grid': float(row['Part_gridCost']),
            'carbon_trading': float(row['Part_carbonTradingCost']),
            'gas': float(row['Part_gasCost']),
            'gas_carbon': float(row['Part_gasCarbonCost']),
            'pv_curt': float(row['Part_pvCurtCost']),
            'wind_curt': float(row['Part_windCurtCost']),
            'h2_short': float(row['Part_h2ShortCost']),
            'demand_response': float(row['Part_demandResponseCost']),
            'q_support': float(row['Part_qSupportCost']),
            'total': float(row['Objective_Yuan'])
        }

        return jsonify({'success': True, 'data': cost_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/optimization/chart/community-h2-dr-data', methods=['GET'])
def get_community_h2_dr_data():
    try:
        mode = request.args.get('mode', 'scenario')
        community_id = request.args.get('community', '1')

        if mode == 'weather':
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'year_plot_data_csv')
            weather_param = request.args.get('weather', 'Sunny_LowWind')
            community_file = os.path.join(data_dir, f'{weather_param}_admm_community_hourly.csv')
        else:
            data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
            scenario_param = request.args.get('scenario', 'S4')
            scenario_map = {
                'S1': 'S1_NoCarbon_NoDR',
                'S2': 'S2_Normal_NoCarbon_DR',
                'S3': 'S3_Carbon_NoDR',
                'S4': 'S4_Carbon_DR'
            }
            scenario = scenario_map.get(scenario_param, 'S4_Carbon_DR')
            community_file = os.path.join(data_dir, f'{scenario}_admm_community_hourly.csv')

        if not os.path.exists(community_file):
            return jsonify({'success': False, 'error': '数据文件不存在'}), 404

        df = pd.read_csv(community_file)
        df_c = df[df['Community'] == int(community_id)]

        if df_c.empty:
            return jsonify({'success': False, 'error': f'社区 {community_id} 无数据'}), 404

        result = {
            'hours': list(range(1, 25)),
            'h2': {
                'production': df_c['H2prod'].tolist(),
                'fuel_cell': df_c['H2cons_fc'].tolist(),
                'storage_charge': df_c['H2ch'].tolist(),
                'storage_discharge': df_c['H2dis'].tolist(),
                'load': df_c['Data_H2load'].tolist(),
                'shortage': df_c['H2short'].tolist(),
                'soc': df_c['SOC_h2'].tolist()
            },
            'dr': {
                'load_original': df_c['Data_Pload'].tolist(),
                'load_after_dr': df_c['PloadDR'].tolist(),
                'shift': df_c['PdrShift'].tolist(),
                'cut_e': df_c['PdrCutE'].tolist(),
                'hdr_cut': df_c['HdrCut'].tolist()
            }
        }

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/planning/capacity', methods=['GET'])
def get_planning_capacity():
    try:
        capacity_path = os.path.join(PLANNING_DATA_DIR, 'planning_capacity_result.csv')
        if not os.path.exists(capacity_path):
            return jsonify({'success': False, 'error': '容量配置文件不存在'}), 404

        df = pd.read_csv(capacity_path)
        community_map = {1: '工业区', 2: '商业区', 3: '居民区'}

        communities = []
        totals = {'PV_MW': 0, 'Wind_MW': 0, 'BatteryEnergy_MWh': 0, 'BatteryPower_MW': 0,
                  'ThermalStorage_MWh': 0, 'ThermalStoragePower_MW': 0,
                  'HydrogenStorage_kg': 0, 'HydrogenStoragePower_kg_h': 0}

        for _, row in df.iterrows():
            c = {
                'id': int(row['Community']),
                'name': community_map.get(int(row['Community']), f"社区{int(row['Community'])}"),
                'pv_mw': float(row['PV_MW']),
                'pv_new_mw': float(row['PVNew_MW']),
                'wind_mw': float(row['Wind_MW']),
                'wind_new_mw': float(row['WindNew_MW']),
                'battery_mwh': float(row['BatteryEnergy_MWh']),
                'battery_power_mw': float(row['BatteryPower_MW']),
                'thermal_mwh': float(row['ThermalStorage_MWh']),
                'thermal_new_mwh': float(row['ThermalStorageNew_MWh']),
                'thermal_power_mw': float(row['ThermalStoragePower_MW']),
                'h2_kg': float(row['HydrogenStorage_kg']),
                'h2_new_kg': float(row['HydrogenStorageNew_kg']),
                'h2_power_kg_h': float(row['HydrogenStoragePower_kg_h'])
            }
            communities.append(c)
            for key in totals:
                totals[key] += float(row[key])

        return jsonify({'success': True, 'data': {'communities': communities, 'totals': totals}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/planning/annual-cost-breakdown', methods=['GET'])
def get_annual_cost_breakdown():
    try:
        cost_path = os.path.join(PLANNING_DATA_DIR, 'planning_cost_breakdown.csv')
        if not os.path.exists(cost_path):
            return jsonify({'success': False, 'error': '成本分解文件不存在'}), 404

        df = pd.read_csv(cost_path)
        cost_map = dict(zip(df['CostItem'], df['Value_Yuan']))

        cost_data = {
            'total': float(cost_map.get('TotalAnnualObjective_Yuan', 0)),
            'investment': {
                'total': float(cost_map.get('AnnualInvestmentCost_Yuan', 0)),
                'pv': float(cost_map.get('InvPV_YuanPerYear', 0)),
                'wind': float(cost_map.get('InvWind_YuanPerYear', 0)),
                'battery': float(cost_map.get('InvBat_YuanPerYear', 0)),
                'thermal': float(cost_map.get('InvTh_YuanPerYear', 0)),
                'h2': float(cost_map.get('InvH2_YuanPerYear', 0))
            },
            'fixed_om': {
                'total': float(cost_map.get('AnnualFixedOMCost_Yuan', 0)),
                'pv': float(cost_map.get('FixOMPV_YuanPerYear', 0)),
                'wind': float(cost_map.get('FixOMWind_YuanPerYear', 0)),
                'battery': float(cost_map.get('FixOMBat_YuanPerYear', 0)),
                'thermal': float(cost_map.get('FixOMTh_YuanPerYear', 0)),
                'h2': float(cost_map.get('FixOMH2_YuanPerYear', 0))
            },
            'operation': float(cost_map.get('AnnualOperationCost_Yuan', 0)),
            'carbon_trading': float(cost_map.get('AnnualCarbonTradingCost_Yuan', 0)),
            'carbon_penalty': float(cost_map.get('AnnualCarbonPenaltyCost_Yuan', 0))
        }

        return jsonify({'success': True, 'data': cost_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/planning/device-status', methods=['GET'])
def get_device_status():
    try:
        capacity_path = os.path.join(PLANNING_DATA_DIR, 'planning_capacity_result.csv')
        if not os.path.exists(capacity_path):
            return jsonify({'success': False, 'error': '容量配置文件不存在'}), 404

        df = pd.read_csv(capacity_path)

        total_pv = float(df['PV_MW'].sum())
        total_wind = float(df['Wind_MW'].sum())
        total_battery_mwh = float(df['BatteryEnergy_MWh'].sum())
        total_battery_power = float(df['BatteryPower_MW'].sum())
        total_thermal = float(df['ThermalStorage_MWh'].sum())
        total_h2 = float(df['HydrogenStorage_kg'].sum())

        alerts = []
        if total_pv > 0:
            alerts.append({'level': 'info', 'text': f'光伏总装机 {total_pv:.1f} MW', 'time': '运行中'})
        if total_wind > 0:
            alerts.append({'level': 'info', 'text': f'风电总装机 {total_wind:.1f} MW', 'time': '运行中'})
        if total_battery_mwh > 0:
            alerts.append({'level': 'info', 'text': f'电池储能 {total_battery_mwh:.1f} MWh / {total_battery_power:.1f} MW', 'time': '运行中'})
        if total_thermal > 0:
            alerts.append({'level': 'info', 'text': f'热储能总容量 {total_thermal:.1f} MWh', 'time': '运行中'})
        if total_h2 > 0:
            alerts.append({'level': 'info', 'text': f'氢储能总容量 {total_h2:.0f} kg', 'time': '运行中'})

        return jsonify({
            'success': True,
            'data': {
                'pv_mw': total_pv,
                'wind_mw': total_wind,
                'battery_mwh': total_battery_mwh,
                'battery_power_mw': total_battery_power,
                'thermal_mwh': total_thermal,
                'h2_kg': total_h2,
                'alerts': alerts
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/optimization/scenario-metrics', methods=['GET'])
def get_scenario_metrics():
    try:
        frames = []

        # New 4 scenarios (S1-S4: carbon × DR)
        metrics_path = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_metric_table.csv')
        if os.path.exists(metrics_path):
            df = pd.read_csv(metrics_path, encoding='utf-8-sig')
            df = df[df['Method'].str.contains('admm', na=False)]
            frames.append(df)

        if not frames:
            return jsonify({'success': False, 'error': '无场景指标数据'}), 404

        df = pd.concat(frames, ignore_index=True)

        scenario_key_map = {
            'S1_NoCarbon_NoDR': 'S1',
            'S2_Normal_NoCarbon_DR': 'S2',
            'S3_Carbon_NoDR': 'S3',
            'S4__Carbon_DR': 'S4',
            'S4_Carbon_DR': 'S4'
        }

        result = {}
        for _, row in df.iterrows():
            key = scenario_key_map.get(row['Scenario'], row['Scenario'])
            result[key] = {
                'scenario': row['Scenario'],
                'scenario_cn': row.get('ScenarioCN', row['Scenario']),
                'total_objective': float(row['TotalObjective_Yuan']),
                'grid_energy': float(row['GridEnergy_MWh']),
                'gas_energy': float(row['GasEnergy_MWhth']),
                'carbon_emission': float(row['CarbonEmission_kg']),
                'carbon_quota': float(row['CarbonQuota_kg']),
                'carbon_surplus': float(row.get('CarbonSurplusBeforeTrade_kg', 0)),
                'carbon_buy': float(row.get('CarbonBuyMarket_kg', 0)),
                'carbon_sell': float(row.get('CarbonSellMarket_kg', 0)),
                'renewable_available': float(row['RenewableAvailable_MWh']),
                'renewable_use': float(row['RenewableUse_MWh']),
                'renewable_curtailment': float(row['RenewableCurtailment_MWh']),
                'renewable_use_rate': float(row['RenewableUseRate_percent']),
                'avg_voltage': float(row.get('AvgMinimumVoltage_pu', 0)),
                'voltage_deviation': float(row.get('GridVoltageDeviation_pu', 0))
            }

        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
