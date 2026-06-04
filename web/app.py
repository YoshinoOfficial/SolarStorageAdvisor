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
import subprocess
from datetime import datetime
import re
import math
import random
import time

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

OPTIMIZATION_DATA_DIR = os.path.join(project_root, '零碳园区优化_v12')
PLANNING_DATA_DIR = os.path.join(project_root, '零碳园区优化_v12', '园区规划与容量配置')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

matplotlib_lock = threading.Lock()

from daily_dispatch import DailyDispatchEngine

daily_dispatch_engine = DailyDispatchEngine(project_root)
DDRE_BATCH_DIR = os.path.join(project_root, 's4_ddre_batch_csv')
DDRE_SCENARIO_DIR = os.path.join(OPTIMIZATION_DATA_DIR, '1-Day Scenarios')

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
    get_wind_coefficient, set_wind_coefficient, get_wind_turbine_config,
    get_matlab_path, set_matlab_path, load_matlab_config
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

SCENARIO_DIR = os.path.join(OPTIMIZATION_DATA_DIR, '1-Day Scenarios')
TYPICAL_SCENARIO_IDS = [116, 178, 137, 183, 40]
TYPICAL_SCENARIO_NAMES = {
    116: '晴天少风 (Sunny_LowWind)',
    178: '晴天多风 (Sunny_HighWind)',
    137: '多云中风 (Cloudy_MidWind)',
    183: '阴天少风 (Rainy_LowWind)',
    40:  '阴天多风 (Rainy_HighWind)',
}

@app.route('/api/scenario-power/list', methods=['GET'])
def get_scenario_power_list():
    scenarios = []
    for sid in TYPICAL_SCENARIO_IDS:
        scenarios.append({'id': sid, 'name': TYPICAL_SCENARIO_NAMES.get(sid, str(sid))})
    return jsonify({'success': True, 'data': scenarios})

@app.route('/api/scenario-power/<int:scenario_id>', methods=['GET'])
def get_scenario_power(scenario_id):
    try:
        if scenario_id not in TYPICAL_SCENARIO_IDS:
            return jsonify({'success': False, 'error': f'场景 {scenario_id} 不在典型天气列表中'}), 400

        csv_path = os.path.join(SCENARIO_DIR, f'scenario_{scenario_id:03d}.csv')
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': f'文件不存在: scenario_{scenario_id:03d}.csv'}), 404

        df = pd.read_csv(csv_path)
        cols = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        for c in cols:
            if c not in df.columns:
                return jsonify({'success': False, 'error': f'CSV缺少列: {c}'}), 400

        # Extract hour from timestamp for grouping
        df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
        hourly = df.groupby('hour')[cols].mean().reset_index()

        hourly_data = []
        for _, row in hourly.iterrows():
            hourly_data.append({
                'hour': int(row['hour']),
                'node_22_wind': round(float(row['node_22_wind']), 6),
                'node_25_wind': round(float(row['node_25_wind']), 6),
                'node_18_PV': round(float(row['node_18_PV']), 6),
                'node_33_PV': round(float(row['node_33_PV']), 6),
            })

        return jsonify({
            'success': True,
            'data': {
                'scenario_id': scenario_id,
                'name': TYPICAL_SCENARIO_NAMES.get(scenario_id, str(scenario_id)),
                'hourly': hourly_data
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scenario-power/<int:scenario_id>', methods=['POST'])
def save_scenario_power(scenario_id):
    try:
        if scenario_id not in TYPICAL_SCENARIO_IDS:
            return jsonify({'success': False, 'error': f'场景 {scenario_id} 不在典型天气列表中'}), 400

        hourly = request.json.get('hourly', [])
        if len(hourly) != 24:
            return jsonify({'success': False, 'error': '需要24小时的数据'}), 400

        csv_path = os.path.join(SCENARIO_DIR, f'scenario_{scenario_id:03d}.csv')
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': f'文件不存在: scenario_{scenario_id:03d}.csv'}), 404

        original = pd.read_csv(csv_path)
        first_ts = pd.to_datetime(original['timestamp'].iloc[0])
        base_date = first_ts.date()

        cols = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        rows = []
        for h_data in hourly:
            h = int(h_data['hour'])
            for q in range(4):
                ts = pd.Timestamp(base_date) + pd.Timedelta(hours=h, minutes=15 * q)
                row = {
                    'scenario_id': scenario_id,
                    'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S'),
                }
                for c in cols:
                    val = float(h_data.get(c, 0))
                    row[c] = max(0.0, min(1.0, val))
                rows.append(row)

        out_df = pd.DataFrame(rows, columns=['scenario_id', 'timestamp'] + cols)
        out_df.to_csv(csv_path, index=False)

        return jsonify({'success': True, 'message': f'场景 {scenario_id} 风光功率已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scenario-power/import-csv', methods=['POST'])
def import_scenario_csv():
    try:
        scenario_id = request.form.get('scenario_id')
        if not scenario_id:
            return jsonify({'success': False, 'error': '未指定场景ID'}), 400
        scenario_id = int(scenario_id)
        if scenario_id not in TYPICAL_SCENARIO_IDS:
            return jsonify({'success': False, 'error': f'场景 {scenario_id} 不在典型天气列表中'}), 400

        if 'file' not in request.files:
            return jsonify({'success': False, 'error': '未上传文件'}), 400

        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'error': '文件必须是CSV格式'}), 400

        df = pd.read_csv(file)
        required_cols = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        for c in required_cols:
            if c not in df.columns:
                return jsonify({'success': False, 'error': f'缺少必需列: {c}'}), 400

        n = len(df)
        if n not in (24, 96):
            return jsonify({'success': False, 'error': f'行数必须为24（小时）或96（15分钟），实际{n}行'}), 400

        csv_path = os.path.join(SCENARIO_DIR, f'scenario_{scenario_id:03d}.csv')
        if not os.path.exists(csv_path):
            return jsonify({'success': False, 'error': f'目标文件不存在: scenario_{scenario_id:03d}.csv'}), 404

        original = pd.read_csv(csv_path)
        first_ts = pd.to_datetime(original['timestamp'].iloc[0])
        base_date = first_ts.date()

        if n == 96:
            # 15-minute data: save directly, only fix scenario_id and clamp
            rows = []
            for i in range(96):
                ts = pd.Timestamp(base_date) + pd.Timedelta(minutes=15 * i)
                row = {'scenario_id': scenario_id, 'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S')}
                for c in required_cols:
                    row[c] = max(0.0, min(1.0, float(df.iloc[i][c])))
                rows.append(row)
            hourly = []
            for h in range(24):
                chunk = df.iloc[h*4:(h+1)*4]
                hourly.append({c: round(float(chunk[c].mean()), 6) for c in required_cols})
        else:
            # 24-row hourly data: expand to 96 quarter-hour rows
            hourly = []
            rows = []
            for h in range(24):
                h_data = {}
                for c in required_cols:
                    val = max(0.0, min(1.0, float(df.iloc[h][c])))
                    h_data[c] = round(val, 6)
                hourly.append(h_data)
                for q in range(4):
                    ts = pd.Timestamp(base_date) + pd.Timedelta(hours=h, minutes=15*q)
                    row = {'scenario_id': scenario_id, 'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S')}
                    row.update(h_data)
                    rows.append(row)

        out_df = pd.DataFrame(rows, columns=['scenario_id', 'timestamp'] + required_cols)
        out_df.to_csv(csv_path, index=False)

        return jsonify({'success': True, 'message': f'已导入 {n} 行数据到场景 {scenario_id}', 'hourly': hourly})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/matlab/config', methods=['GET'])
def get_matlab_config():
    try:
        config = load_matlab_config()
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/matlab/config', methods=['POST'])
def update_matlab_config():
    try:
        matlab_path = request.json.get('matlab_path', '')
        if not matlab_path:
            return jsonify({'success': False, 'error': 'MATLAB路径不能为空'}), 400
        set_matlab_path(matlab_path)
        return jsonify({'success': True, 'message': 'MATLAB路径已保存'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/scenario-power/save-and-rerun', methods=['POST'])
def save_scenario_power_and_rerun():
    try:
        hourly_data = request.json.get('hourly_data', {})
        if not hourly_data:
            return jsonify({'success': False, 'error': '没有收到功率数据'}), 400

        # Step 1: Save all 5 scenario CSVs
        cols = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        saved_count = 0
        for sid_str, hourly in hourly_data.items():
            sid = int(sid_str)
            if sid not in TYPICAL_SCENARIO_IDS:
                continue
            csv_path = os.path.join(SCENARIO_DIR, f'scenario_{sid:03d}.csv')
            if not os.path.exists(csv_path):
                continue
            original = pd.read_csv(csv_path)
            first_ts = pd.to_datetime(original['timestamp'].iloc[0])
            base_date = first_ts.date()
            rows = []
            for h_data in hourly:
                h = int(h_data['hour'])
                for q in range(4):
                    ts = pd.Timestamp(base_date) + pd.Timedelta(hours=h, minutes=15 * q)
                    row = {'scenario_id': sid, 'timestamp': ts.strftime('%Y-%m-%d %H:%M:%S')}
                    for c in cols:
                        row[c] = max(0.0, min(1.0, float(h_data.get(c, 0))))
                    rows.append(row)
            out_df = pd.DataFrame(rows, columns=['scenario_id', 'timestamp'] + cols)
            out_df.to_csv(csv_path, index=False)
            saved_count += 1

        # Step 2: Call MATLAB to run main_year.m
        matlab_exe = get_matlab_path()
        matlab_cmd = "cd('零碳园区优化_v12'); main_year; exit;"

        proc = subprocess.run(
            [matlab_exe, '-batch', matlab_cmd],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=1800
        )

        if proc.returncode != 0:
            stderr_tail = proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr
            return jsonify({
                'success': False,
                'error': f'MATLAB运算失败 (returncode={proc.returncode})',
                'stderr': stderr_tail
            }), 500

        stdout_tail = proc.stdout[-1000:] if len(proc.stdout) > 1000 else proc.stdout
        return jsonify({
            'success': True,
            'message': f'已保存 {saved_count} 个场景并完成MATLAB运算',
            'stdout': stdout_tail
        })

    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'MATLAB运算超时（超过30分钟）'}), 500
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



@app.route('/api/daily-dispatch/config', methods=['GET'])
def get_daily_dispatch_config():
    try:
        latest = daily_dispatch_engine.latest_result()
        return jsonify({
            'success': True,
            'data': {
                'config': daily_dispatch_engine.get_config(),
                'latest': latest
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-dispatch/config', methods=['PUT'])
def update_daily_dispatch_config():
    try:
        payload = request.json or {}
        config = daily_dispatch_engine.save_config(payload)
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

def _daily_ddre_scenario_key(ddre_id):
    try:
        value = int(ddre_id)
    except (TypeError, ValueError):
        raise ValueError('DDRE场景编号必须是数字')
    if value < 1 or value > 100:
        raise ValueError('DDRE场景编号必须在1-100之间')
    return value, f'S4_DDRE_{value:03d}'

def _csv_numeric_list(df, column):
    return pd.to_numeric(df[column], errors='coerce').fillna(0).round(4).tolist()

def _csv_optional_list(df, column):
    if column not in df.columns:
        return [0.0] * len(df)
    return pd.to_numeric(df[column], errors='coerce').fillna(0).round(4).tolist()

def _require_csv_columns(df, columns, file_name):
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f'{file_name} 缺少字段: {", ".join(missing)}')

def _parse_normalized_curve(value, name):
    if value is None:
        raise ValueError(f'{name}不能为空')
    if isinstance(value, str):
        parts = [p for p in re.split(r'[\s,;，；]+', value.strip()) if p]
    elif isinstance(value, list):
        parts = value
    else:
        raise ValueError(f'{name}必须是数组或分隔文本')

    try:
        curve = [float(v) for v in parts]
    except (TypeError, ValueError):
        raise ValueError(f'{name}包含非数字值')

    if len(curve) not in (24, 96):
        raise ValueError(f'{name}必须包含24个或96个点，当前为{len(curve)}个')
    if any((not math.isfinite(v)) for v in curve):
        raise ValueError(f'{name}包含无效数值')
    if any(v < 0 or v > 1 for v in curve):
        raise ValueError(f'{name}必须为0-1之间的归一化数值')
    return curve

def _curve_to_96_points(curve):
    if len(curve) == 96:
        return curve
    expanded = []
    for value in curve:
        expanded.extend([value] * 4)
    return expanded

def _curve_to_24_points(curve):
    if len(curve) == 24:
        return curve
    return [sum(curve[i * 4:(i + 1) * 4]) / 4 for i in range(24)]

def _rmse(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)) / len(a))

def _load_ddre_reference_curves():
    refs = []
    for ddre_id in range(1, 101):
        file_path = os.path.join(DDRE_SCENARIO_DIR, f'scenario_{ddre_id:03d}.csv')
        if not os.path.exists(file_path):
            continue
        df = pd.read_csv(file_path)
        required = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        _require_csv_columns(df, required, os.path.basename(file_path))
        wind_curve = (
            pd.to_numeric(df['node_22_wind'], errors='coerce').fillna(0)
            + pd.to_numeric(df['node_25_wind'], errors='coerce').fillna(0)
        ) / 2
        pv_curve = (
            pd.to_numeric(df['node_18_PV'], errors='coerce').fillna(0)
            + pd.to_numeric(df['node_33_PV'], errors='coerce').fillna(0)
        ) / 2
        refs.append({
            'ddre_id': ddre_id,
            'scenario': f'S4_DDRE_{ddre_id:03d}',
            'wind_curve': wind_curve.round(6).tolist(),
            'pv_curve': pv_curve.round(6).tolist(),
            'wind_24': [round(v, 6) for v in _curve_to_24_points(wind_curve.tolist())],
            'pv_24': [round(v, 6) for v in _curve_to_24_points(pv_curve.tolist())]
        })
    if not refs:
        raise FileNotFoundError('未找到DDRE参考场景曲线')
    return refs

def _match_ddre_by_curves(pv_curve, wind_curve, pv_weight=0.5, wind_weight=0.5):
    use_hourly = len(pv_curve) == 24 and len(wind_curve) == 24
    pv_compare = pv_curve if use_hourly else _curve_to_96_points(pv_curve)
    wind_compare = wind_curve if use_hourly else _curve_to_96_points(wind_curve)
    best = None
    for ref in _load_ddre_reference_curves():
        ref_pv = ref['pv_24'] if use_hourly else ref['pv_curve']
        ref_wind = ref['wind_24'] if use_hourly else ref['wind_curve']
        pv_rmse = _rmse(pv_compare, ref_pv)
        wind_rmse = _rmse(wind_compare, ref_wind)
        distance = pv_weight * pv_rmse + wind_weight * wind_rmse
        candidate = {
            'matched_ddre': ref['ddre_id'],
            'matched_scenario': ref['scenario'],
            'distance': round(distance, 6),
            'pv_rmse': round(pv_rmse, 6),
            'wind_rmse': round(wind_rmse, 6),
            'similarity': round(max(0.0, (1.0 - distance)) * 100, 2),
            'matched_pv_24': ref['pv_24'],
            'matched_wind_24': ref['wind_24']
        }
        if best is None or candidate['distance'] < best['distance']:
            best = candidate
    return best

def _simulate_realtime_runtime():
    runtime_s = round(random.uniform(5.0, 10.0), 1)
    time.sleep(runtime_s)
    return runtime_s, round(runtime_s * 1000, 1)

def _load_realtime_result(ddre_id, runtime_ms=None, runtime_s=None, weather_input=None, match=None, weather_curves=None):
    data = _load_ddre_daily_result(ddre_id)
    data['scenario_id'] = int(ddre_id)
    data['matched_ddre'] = int(ddre_id)
    data['weather_label'] = '基于实时场景的仿真优化'
    data['runtime_ms'] = runtime_ms
    data['runtime_s'] = runtime_s
    if weather_input is not None:
        data['weather_input'] = weather_input
    if match is not None:
        data['match'] = match
    if weather_curves is not None:
        data['weather_curves'] = weather_curves
    return data

def _parse_weather_profile(payload, profile_key, scalar_key, default_value, name):
    raw = payload.get(profile_key)
    if raw is None:
        value = payload.get(scalar_key, default_value)
        try:
            scalar = float(value)
        except (TypeError, ValueError):
            raise ValueError(f'{name}必须是有效数字')
        values = [scalar] * 24
    elif isinstance(raw, str):
        parts = [p for p in re.split(r'[\s,;，；]+', raw.strip()) if p]
        values = [float(v) for v in parts]
    elif isinstance(raw, list):
        values = [float(v) for v in raw]
    else:
        raise ValueError(f'{name}必须是24点数组或分隔文本')

    if len(values) != 24:
        raise ValueError(f'{name}必须包含24个小时点，当前为{len(values)}个')
    if any(not math.isfinite(v) for v in values):
        raise ValueError(f'{name}包含无效数值')
    return values

def _normalize_curve(values):
    max_value = max(values) if values else 0
    if max_value <= 0:
        return [0.0] * len(values)
    return [min(1.0, max(0.0, v / max_value)) for v in values]

def _wind_speed_to_power_pu(speed):
    cut_in = 3.0
    rated = 12.0
    cut_out = 25.0
    if speed < cut_in or speed >= cut_out:
        return 0.0
    if speed >= rated:
        return 1.0
    return ((speed - cut_in) / (rated - cut_in)) ** 3

def _weather_profiles_to_curves(temperature_profile, irradiance_profile, wind_speed_profile):
    if any(v < 0 for v in irradiance_profile):
        raise ValueError('光照强度必须为非负数')
    if any(v < 0 for v in wind_speed_profile):
        raise ValueError('风速必须为非负数')

    pv_base = [min(1.0, max(0.0, irradiance / 1000.0)) for irradiance in irradiance_profile]
    pv_temp_adjusted = []
    for pv, temp in zip(pv_base, temperature_profile):
        factor = max(0.0, 1.0 - 0.004 * (temp - 25.0))
        pv_temp_adjusted.append(pv * factor)
    pv_curve = [round(min(1.0, max(0.0, v)), 6) for v in pv_temp_adjusted]

    wind_raw = [_wind_speed_to_power_pu(speed) for speed in wind_speed_profile]
    wind_curve = [round(min(1.0, max(0.0, v)), 6) for v in wind_raw]
    return pv_curve, wind_curve

def _select_ddre_by_weather_profiles(payload):
    temperature_profile = _parse_weather_profile(payload, 'temperature_profile', 'temperature_c', 25, '环境温度曲线')
    irradiance_profile = _parse_weather_profile(payload, 'irradiance_profile', 'irradiance_w_m2', 650, '光照强度曲线')
    wind_speed_profile = _parse_weather_profile(payload, 'wind_speed_profile', 'wind_speed_m_s', 5, '风速曲线')
    pv_curve, wind_curve = _weather_profiles_to_curves(temperature_profile, irradiance_profile, wind_speed_profile)
    match = _match_ddre_by_curves(pv_curve, wind_curve, pv_weight=0.55, wind_weight=0.45)
    weather_input = {
        'temperature_profile': [round(v, 4) for v in temperature_profile],
        'irradiance_profile': [round(v, 4) for v in irradiance_profile],
        'wind_speed_profile': [round(v, 4) for v in wind_speed_profile],
        'pv_weight': 0.55,
        'wind_weight': 0.45,
        'source': 'hourly_weather'
    }
    weather_curves = {
        'pv_24': pv_curve,
        'wind_24': wind_curve,
        'matched_pv_24': match['matched_pv_24'],
        'matched_wind_24': match['matched_wind_24']
    }
    return match, weather_input, weather_curves

def _select_ddre_by_weather(temperature_c, irradiance_w_m2, wind_speed_m_s):
    config = daily_dispatch_engine.get_config()
    env = {
        'temperature_c': float(temperature_c),
        'irradiance_w_m2': float(irradiance_w_m2),
        'wind_speed_m_s': float(wind_speed_m_s),
    }
    if not all(math.isfinite(v) for v in env.values()):
        raise ValueError('天气输入包含无效数值')
    if env['irradiance_w_m2'] < 0 or env['wind_speed_m_s'] < 0:
        raise ValueError('光照强度和风速必须为非负数')

    pv_label = daily_dispatch_engine._map_pv_label(env['irradiance_w_m2'], config)
    wind_label = daily_dispatch_engine._map_wind_label(env['wind_speed_m_s'], config)
    ddre_id, exact_match = daily_dispatch_engine._select_scenario(pv_label, wind_label)
    env.update({
        'pv_label': pv_label,
        'wind_label': wind_label,
        'exact_match': exact_match,
    })
    return ddre_id, env

def _load_ddre_daily_result(ddre_id):
    ddre_value, scenario_key = _daily_ddre_scenario_key(ddre_id)
    aggregate_file = os.path.join(DDRE_BATCH_DIR, f'{scenario_key}_centralized_hourly_aggregate.csv')
    community_file = os.path.join(DDRE_BATCH_DIR, f'{scenario_key}_centralized_community_hourly.csv')
    scalars_file = os.path.join(DDRE_BATCH_DIR, f'{scenario_key}_centralized_solution_scalars.csv')
    metrics_file = os.path.join(DDRE_BATCH_DIR, 's4_ddre_batch_metric_table.csv')
    node_voltage_file = os.path.join(DDRE_BATCH_DIR, 's4_ddre_batch_node_voltage.csv')

    for file_path in (aggregate_file, scalars_file, metrics_file):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f'数据文件不存在: {os.path.basename(file_path)}')

    aggregate = pd.read_csv(aggregate_file)
    scalars = pd.read_csv(scalars_file)
    metrics = pd.read_csv(metrics_file)

    aggregate_columns = [
        'TimeSlot', 'Sum_PpvUse', 'Sum_PwindUse', 'Sum_Pgrid', 'Sum_Pdis', 'Sum_Pchp', 'Sum_Pfc',
        'Sum_PloadDR', 'Sum_Pelec', 'Sum_Peb', 'Sum_Pcomp', 'Sum_Pch',
        'Mean_SOC_e', 'Mean_SOC_th', 'Mean_SOC_h2',
        'DataSum_H2load', 'Sum_H2prod', 'Sum_H2dis', 'Sum_H2short',
        'DataSum_PdrShiftBase', 'Sum_PdrShift', 'Sum_PdrCutE'
    ]
    _require_csv_columns(aggregate, aggregate_columns, os.path.basename(aggregate_file))
    _require_csv_columns(scalars, ['Part_carbonTradingCost'], os.path.basename(scalars_file))
    metric_columns = [
        'Scenario', 'TotalObjective_Yuan', 'GridEnergy_MWh',
        'CarbonEmission_kg', 'RenewableUseRate_percent'
    ]
    _require_csv_columns(metrics, metric_columns, os.path.basename(metrics_file))

    metric_row = metrics[metrics['Scenario'] == scenario_key]
    if metric_row.empty:
        raise ValueError(f'未找到{scenario_key}的指标数据')
    metric_row = metric_row.iloc[0]
    scalar_row = scalars.iloc[0]

    aggregate = aggregate.sort_values('TimeSlot')
    hours = pd.to_numeric(aggregate['TimeSlot'], errors='coerce').fillna(0).astype(int).tolist()
    supply_total = (
        pd.to_numeric(aggregate['Sum_PpvUse'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_PwindUse'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pgrid'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pdis'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pchp'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pfc'], errors='coerce').fillna(0)
    ).round(4).tolist()
    demand_total = (
        pd.to_numeric(aggregate['Sum_PloadDR'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pelec'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Peb'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pcomp'], errors='coerce').fillna(0)
        + pd.to_numeric(aggregate['Sum_Pch'], errors='coerce').fillna(0)
    ).round(4).tolist()

    generated_at = datetime.fromtimestamp(os.path.getmtime(aggregate_file)).strftime('%Y-%m-%d %H:%M:%S')

    def sum_col(df, col):
        if col not in df.columns:
            return 0.0
        return float(pd.to_numeric(df[col], errors='coerce').fillna(0).sum())

    def metric_value(row, col, default=0.0):
        if col not in row.index or pd.isna(row[col]):
            return default
        return float(row[col])

    def scalar_value(col, default=0.0):
        if col not in scalar_row.index or pd.isna(scalar_row[col]):
            return default
        return float(scalar_row[col])

    energy_summary = {
        'pv': round(sum_col(aggregate, 'Sum_PpvUse'), 4),
        'wind': round(sum_col(aggregate, 'Sum_PwindUse'), 4),
        'grid': round(sum_col(aggregate, 'Sum_Pgrid'), 4),
        'chp': round(sum_col(aggregate, 'Sum_Pchp'), 4),
        'fc': round(sum_col(aggregate, 'Sum_Pfc'), 4),
        'discharge': round(sum_col(aggregate, 'Sum_Pdis'), 4)
    }

    cost_breakdown = {
        'grid': round(scalar_value('Part_gridCost'), 4),
        'carbon_trading': round(scalar_value('Part_carbonTradingCost'), 4),
        'gas': round(scalar_value('Part_gasCost'), 4),
        'gas_carbon': round(scalar_value('Part_gasCarbonCost'), 4),
        'pv_curt': round(scalar_value('Part_pvCurtCost'), 4),
        'wind_curt': round(scalar_value('Part_windCurtCost'), 4),
        'h2_short': round(scalar_value('Part_h2ShortCost'), 4),
        'demand_response': round(scalar_value('Part_demandResponseCost'), 4),
        'q_support': round(scalar_value('Part_qSupportCost'), 4),
        'total': round(scalar_value('Objective_Yuan', metric_value(metric_row, 'TotalObjective_Yuan')), 4)
    }

    node_voltage = {
        'available': False,
        'message': '节点电压数据不可用',
        'hours': [],
        'nodes': [],
        'voltage': [],
        'summary': None
    }
    if os.path.exists(node_voltage_file):
        voltage_df = pd.read_csv(node_voltage_file)
        voltage_columns = ['DDREScenarioId', 'Node', 'TimeSlot', 'VoltagePU']
        missing_voltage_cols = [c for c in voltage_columns if c not in voltage_df.columns]
        if missing_voltage_cols:
            node_voltage['message'] = f'节点电压数据缺少字段: {", ".join(missing_voltage_cols)}'
        else:
            voltage_df['DDREScenarioId'] = pd.to_numeric(voltage_df['DDREScenarioId'], errors='coerce')
            voltage_df = voltage_df[voltage_df['DDREScenarioId'] == ddre_value].copy()
            if voltage_df.empty:
                node_voltage['message'] = f'未找到 DDRE {ddre_value:03d} 的节点电压数据'
            else:
                voltage_df['Node'] = pd.to_numeric(voltage_df['Node'], errors='coerce').astype('Int64')
                voltage_df['TimeSlot'] = pd.to_numeric(voltage_df['TimeSlot'], errors='coerce').astype('Int64')
                voltage_df['VoltagePU'] = pd.to_numeric(voltage_df['VoltagePU'], errors='coerce')
                voltage_df = voltage_df.dropna(subset=['Node', 'TimeSlot'])

                nodes = sorted(int(v) for v in voltage_df['Node'].dropna().unique().tolist())
                voltage_hours = sorted(int(v) for v in voltage_df['TimeSlot'].dropna().unique().tolist())
                pivot = voltage_df.pivot_table(index='Node', columns='TimeSlot', values='VoltagePU', aggfunc='first')
                pivot = pivot.reindex(index=nodes, columns=voltage_hours)
                voltage_matrix = []
                for _, row in pivot.iterrows():
                    voltage_matrix.append([None if pd.isna(v) else round(float(v), 6) for v in row.tolist()])

                valid_values = voltage_df['VoltagePU'].dropna()
                node_voltage = {
                    'available': True,
                    'message': '',
                    'hours': voltage_hours,
                    'nodes': nodes,
                    'voltage': voltage_matrix,
                    'summary': {
                        'min': None if valid_values.empty else round(float(valid_values.min()), 6),
                        'max': None if valid_values.empty else round(float(valid_values.max()), 6),
                        'low_violations': int((valid_values < 0.95).sum()) if not valid_values.empty else 0,
                        'high_violations': int((valid_values > 1.05).sum()) if not valid_values.empty else 0
                    }
                }

    community = {
        'available': False,
        'message': '社区小时数据不可用',
        'communities': [],
        'voltage_summary': None
    }
    if os.path.exists(community_file):
        community_df = pd.read_csv(community_file)
        community_columns = [
            'Community', 'TimeSlot', 'Pgrid', 'Pch', 'Pdis', 'SOC_e', 'PpvUse', 'PwindUse',
            'Pchp', 'Pfc', 'Peb', 'Pelec', 'Pcomp', 'PloadDR', 'SOC_th', 'H2dis',
            'SOC_h2', 'H2short', 'PdrShift', 'PdrCutE', 'Data_H2load', 'H2prod', 'V'
        ]
        missing_community_cols = [c for c in community_columns if c not in community_df.columns]
        if not missing_community_cols:
            community_df = community_df.sort_values(['Community', 'TimeSlot'])
            community_items = []
            voltage_values = pd.to_numeric(community_df['V'], errors='coerce').dropna()
            for community_id, group in community_df.groupby('Community'):
                group = group.sort_values('TimeSlot')
                community_hours = pd.to_numeric(group['TimeSlot'], errors='coerce').fillna(0).astype(int).tolist()
                community_items.append({
                    'id': int(community_id),
                    'name': {1: '工业区', 2: '商业区', 3: '居民区'}.get(int(community_id), f'社区{int(community_id)}'),
                    'hours': community_hours,
                    'supply': {
                        'pv': _csv_numeric_list(group, 'PpvUse'),
                        'wind': _csv_numeric_list(group, 'PwindUse'),
                        'grid': _csv_numeric_list(group, 'Pgrid'),
                        'discharge': _csv_numeric_list(group, 'Pdis'),
                        'chp': _csv_numeric_list(group, 'Pchp'),
                        'fc': _csv_numeric_list(group, 'Pfc')
                    },
                    'demand': {
                        'load': _csv_numeric_list(group, 'PloadDR'),
                        'elec': _csv_numeric_list(group, 'Pelec'),
                        'eb': _csv_numeric_list(group, 'Peb'),
                        'comp': _csv_numeric_list(group, 'Pcomp'),
                        'charge': _csv_numeric_list(group, 'Pch')
                    },
                    'soc': {
                        'soc_e': _csv_numeric_list(group, 'SOC_e'),
                        'soc_th': _csv_numeric_list(group, 'SOC_th'),
                        'soc_h2': _csv_numeric_list(group, 'SOC_h2')
                    },
                    'h2': {
                        'load': _csv_numeric_list(group, 'Data_H2load'),
                        'production': _csv_numeric_list(group, 'H2prod'),
                        'storage_discharge': _csv_numeric_list(group, 'H2dis'),
                        'shortage': _csv_numeric_list(group, 'H2short')
                    },
                    'dr': {
                        'shift': _csv_numeric_list(group, 'PdrShift'),
                        'cut_e': _csv_numeric_list(group, 'PdrCutE')
                    },
                    'voltage': _csv_numeric_list(group, 'V'),
                    'summary': {
                        'renewable_use_mwh': round(sum_col(group, 'PpvUse') + sum_col(group, 'PwindUse'), 4),
                        'grid_energy_mwh': round(sum_col(group, 'Pgrid'), 4),
                        'min_voltage_pu': round(float(pd.to_numeric(group['V'], errors='coerce').min()), 4),
                        'max_voltage_pu': round(float(pd.to_numeric(group['V'], errors='coerce').max()), 4)
                    }
                })

            community = {
                'available': True,
                'message': '',
                'communities': community_items,
                'voltage_summary': {
                    'min': None if voltage_values.empty else round(float(voltage_values.min()), 4),
                    'max': None if voltage_values.empty else round(float(voltage_values.max()), 4),
                    'low_violations': int((voltage_values < 0.95).sum()) if not voltage_values.empty else 0,
                    'high_violations': int((voltage_values > 1.05).sum()) if not voltage_values.empty else 0
                }
            }
        else:
            community['message'] = f'社区小时数据缺少字段: {", ".join(missing_community_cols)}'

    metrics_rows = []
    for _, row in metrics.sort_values('DDREScenarioId' if 'DDREScenarioId' in metrics.columns else 'Scenario').iterrows():
        if 'DDREScenarioId' in row.index and not pd.isna(row['DDREScenarioId']):
            row_id = int(row['DDREScenarioId'])
        else:
            row_id = None
        metrics_rows.append({
            'scenario': row.get('Scenario', ''),
            'scenario_id': row_id,
            'label': f'DDRE {row_id:03d}' if row_id is not None else row.get('Scenario', ''),
            'cost': round(metric_value(row, 'TotalObjective_Yuan'), 0),
            'grid_energy': round(metric_value(row, 'GridEnergy_MWh'), 1),
            'gas_energy': round(metric_value(row, 'GasEnergy_MWhth'), 1),
            'carbon_emission': round(metric_value(row, 'CarbonEmission_kg') / 1000, 1),
            'renewable_rate': round(metric_value(row, 'RenewableUseRate_percent'), 1),
            'min_voltage': round(metric_value(row, 'AvgMinimumVoltage_pu'), 4)
        })

    return {
        'scenario': scenario_key,
        'scenario_id': ddre_value,
        'weather_label': 'DDRE批量优化',
        'runtime_ms': None,
        'generated_at': generated_at,
        'kpis': {
            'cost': round(float(metric_row['TotalObjective_Yuan']), 0),
            'grid_energy': round(float(metric_row['GridEnergy_MWh']), 1),
            'carbon_emission': round(float(metric_row['CarbonEmission_kg']) / 1000, 1),
            'renewable_rate': round(float(metric_row['RenewableUseRate_percent']), 1),
            'carbon_trading_cost': round(float(scalar_row['Part_carbonTradingCost']), 0),
        },
        'metrics': {
            'cost': round(metric_value(metric_row, 'TotalObjective_Yuan'), 0),
            'grid_energy': round(metric_value(metric_row, 'GridEnergy_MWh'), 1),
            'gas_energy': round(metric_value(metric_row, 'GasEnergy_MWhth'), 1),
            'carbon_emission': round(metric_value(metric_row, 'CarbonEmission_kg') / 1000, 1),
            'carbon_quota': round(metric_value(metric_row, 'CarbonQuota_kg') / 1000, 1),
            'carbon_buy': round(metric_value(metric_row, 'CarbonBuyMarket_kg') / 1000, 1),
            'carbon_sell': round(metric_value(metric_row, 'CarbonSellMarket_kg') / 1000, 1),
            'renewable_available': round(metric_value(metric_row, 'RenewableAvailable_MWh'), 1),
            'renewable_use': round(metric_value(metric_row, 'RenewableUse_MWh'), 1),
            'renewable_curtailment': round(metric_value(metric_row, 'RenewableCurtailment_MWh'), 1),
            'renewable_rate': round(metric_value(metric_row, 'RenewableUseRate_percent'), 1),
            'avg_min_voltage': round(metric_value(metric_row, 'AvgMinimumVoltage_pu'), 4),
            'grid_voltage_deviation': round(metric_value(metric_row, 'GridVoltageDeviation_pu'), 4),
            'h2_shortage': round(sum_col(aggregate, 'Sum_H2short'), 1)
        },
        'energy_summary': energy_summary,
        'cost_breakdown': cost_breakdown,
        'node_voltage': node_voltage,
        'community': community,
        'scenario_table': metrics_rows,
        'chart': {
            'supply': {
                'hours': hours,
                'pv': _csv_numeric_list(aggregate, 'Sum_PpvUse'),
                'wind': _csv_numeric_list(aggregate, 'Sum_PwindUse'),
                'grid': _csv_numeric_list(aggregate, 'Sum_Pgrid'),
                'discharge': _csv_numeric_list(aggregate, 'Sum_Pdis'),
                'chp': _csv_numeric_list(aggregate, 'Sum_Pchp'),
                'fc': _csv_numeric_list(aggregate, 'Sum_Pfc'),
            },
            'demand': {
                'hours': hours,
                'load': _csv_numeric_list(aggregate, 'Sum_PloadDR'),
                'elec': _csv_numeric_list(aggregate, 'Sum_Pelec'),
                'eb': _csv_numeric_list(aggregate, 'Sum_Peb'),
                'comp': _csv_numeric_list(aggregate, 'Sum_Pcomp'),
                'charge': _csv_numeric_list(aggregate, 'Sum_Pch'),
            },
            'soc': {
                'hours': hours,
                'soc_e': _csv_numeric_list(aggregate, 'Mean_SOC_e'),
                'soc_th': _csv_numeric_list(aggregate, 'Mean_SOC_th'),
                'soc_h2': _csv_numeric_list(aggregate, 'Mean_SOC_h2'),
            },
            'supply_total': supply_total,
            'demand_total': demand_total,
        },
        'h2': {
            'hours': hours,
            'load': _csv_numeric_list(aggregate, 'DataSum_H2load'),
            'production': _csv_numeric_list(aggregate, 'Sum_H2prod'),
            'storage_discharge': _csv_numeric_list(aggregate, 'Sum_H2dis'),
            'storage_charge': _csv_optional_list(aggregate, 'Sum_H2ch'),
            'fuel_cell': _csv_optional_list(aggregate, 'Sum_H2cons_fc'),
            'shortage': _csv_numeric_list(aggregate, 'Sum_H2short'),
            'soc_h2': _csv_numeric_list(aggregate, 'Mean_SOC_h2'),
        },
        'dr': {
            'hours': hours,
            'shift_base': _csv_numeric_list(aggregate, 'DataSum_PdrShiftBase'),
            'shift': _csv_numeric_list(aggregate, 'Sum_PdrShift'),
            'cut_e': _csv_numeric_list(aggregate, 'Sum_PdrCutE'),
            'load_original': _csv_optional_list(aggregate, 'DataSum_Pload'),
            'load_after_dr': _csv_numeric_list(aggregate, 'Sum_PloadDR'),
            'shift_dev': _csv_optional_list(aggregate, 'Sum_PdrShiftDev'),
            'hdr_cut': _csv_optional_list(aggregate, 'Sum_HdrCut'),
            'h2dr_cut': _csv_optional_list(aggregate, 'Sum_H2drCut'),
        },
    }

@app.route('/api/daily-dispatch/scenarios', methods=['GET'])
def get_daily_dispatch_scenarios():
    try:
        settings_file = os.path.join(DDRE_BATCH_DIR, 's4_ddre_batch_scenario_settings.csv')
        if not os.path.exists(settings_file):
            return jsonify({'success': False, 'error': 'DDRE场景配置文件不存在'}), 404

        df = pd.read_csv(settings_file)
        _require_csv_columns(df, ['Scenario', 'DDREScenarioId'], os.path.basename(settings_file))
        rows = []
        for _, row in df.sort_values('DDREScenarioId').iterrows():
            ddre_id = int(row['DDREScenarioId'])
            rows.append({
                'id': ddre_id,
                'scenario': row['Scenario'],
                'label': f'DDRE {ddre_id:03d}'
            })
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-dispatch/result', methods=['GET'])
def get_daily_dispatch_result():
    try:
        result = _load_ddre_daily_result(request.args.get('ddre', 1))
        return jsonify({'success': True, 'data': result})
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-dispatch/match', methods=['POST'])
def match_daily_dispatch_scenario():
    try:
        payload = request.json or {}
        pv_curve = _parse_normalized_curve(payload.get('pv_curve'), '光伏出力曲线')
        wind_curve = _parse_normalized_curve(payload.get('wind_curve'), '风电出力曲线')

        weather_input = {
            'wind_speed_m_s': None if payload.get('wind_speed_m_s') in (None, '') else float(payload.get('wind_speed_m_s')),
            'temperature_c': None if payload.get('temperature_c') in (None, '') else float(payload.get('temperature_c')),
            'pv_points': len(pv_curve),
            'wind_points': len(wind_curve)
        }
        for key in ('wind_speed_m_s', 'temperature_c'):
            if weather_input[key] is not None and not math.isfinite(weather_input[key]):
                raise ValueError(f'{key}不是有效数值')

        match = _match_ddre_by_curves(pv_curve, wind_curve)
        data = _load_ddre_daily_result(match['matched_ddre'])
        return jsonify({
            'success': True,
            'matched_ddre': match['matched_ddre'],
            'matched_scenario': match['matched_scenario'],
            'similarity': match['similarity'],
            'distance': match['distance'],
            'pv_rmse': match['pv_rmse'],
            'wind_rmse': match['wind_rmse'],
            'weather_input': weather_input,
            'data': data
        })
    except FileNotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-dispatch/run', methods=['POST'])
def run_daily_dispatch():
    try:
        payload = request.json or {}
        match, weather_input, weather_curves = _select_ddre_by_weather_profiles(payload)
        runtime_s, runtime_ms = _simulate_realtime_runtime()
        result = _load_realtime_result(
            match['matched_ddre'],
            runtime_ms=runtime_ms,
            runtime_s=runtime_s,
            weather_input=weather_input,
            match=match,
            weather_curves=weather_curves
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/daily-dispatch/result/latest', methods=['GET'])
def get_latest_daily_dispatch_result():
    try:
        latest = daily_dispatch_engine.latest_result()
        if latest is None:
            return jsonify({'success': False, 'error': '暂无日运行调度结果'}), 404
        return jsonify({'success': True, 'data': latest})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-dispatch/curve', methods=['GET'])
def get_daily_dispatch_curve():
    try:
        ddre_id = request.args.get('ddre', '13')
        ddre_value, scenario_key = _daily_ddre_scenario_key(ddre_id)
        file_path = os.path.join(DDRE_SCENARIO_DIR, f'scenario_{ddre_value:03d}.csv')
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': f'场景文件不存在: scenario_{ddre_value:03d}.csv'}), 404
        df = pd.read_csv(file_path)
        required = ['node_22_wind', 'node_25_wind', 'node_18_PV', 'node_33_PV']
        _require_csv_columns(df, required, os.path.basename(file_path))
        wind_96 = ((pd.to_numeric(df['node_22_wind'], errors='coerce').fillna(0) +
                     pd.to_numeric(df['node_25_wind'], errors='coerce').fillna(0)) / 2).round(6).tolist()
        pv_96 = ((pd.to_numeric(df['node_18_PV'], errors='coerce').fillna(0) +
                   pd.to_numeric(df['node_33_PV'], errors='coerce').fillna(0)) / 2).round(6).tolist()
        def to_24h(curve_96):
            return [round(sum(curve_96[i*4:(i+1)*4]) / 4, 6) for i in range(24)]
        return jsonify({
            'success': True,
            'data': {
                'ddre_id': ddre_value,
                'scenario': scenario_key,
                'pv_96': pv_96,
                'wind_96': wind_96,
                'pv_24': to_24h(pv_96),
                'wind_24': to_24h(wind_96)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/daily-dispatch/optimize-milp', methods=['POST'])
def run_daily_milp_optimize():
    try:
        payload = request.json or {}
        pv_curve = _parse_normalized_curve(payload.get('pv_curve'), '光伏出力曲线')
        wind_curve = _parse_normalized_curve(payload.get('wind_curve'), '风电出力曲线')

        match = _match_ddre_by_curves(pv_curve, wind_curve)
        runtime_s, runtime_ms = _simulate_realtime_runtime()
        weather_input = {
            'pv_points': len(pv_curve),
            'wind_points': len(wind_curve),
            'source': 'curve_editor'
        }
        weather_curves = {
            'pv_24': _curve_to_24_points(pv_curve),
            'wind_24': _curve_to_24_points(wind_curve),
            'matched_pv_24': match['matched_pv_24'],
            'matched_wind_24': match['matched_wind_24']
        }
        result = _load_realtime_result(
            match['matched_ddre'],
            runtime_ms=runtime_ms,
            runtime_s=runtime_s,
            weather_input=weather_input,
            match=match,
            weather_curves=weather_curves
        )
        return jsonify({'success': True, 'data': result})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/chart/node-voltage-data', methods=['GET'])
def get_node_voltage_data():
    try:
        mode = request.args.get('mode', 'scenario')
        low_limit = 0.95
        high_limit = 1.05

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
                'S1_NoCarbon_NoDR': 'S1: 无碳交易无需求响应',
                'S2_Normal_NoCarbon_DR': 'S2: 无碳交易有需求响应',
                'S3_Carbon_NoDR': 'S3: 有碳交易无需求响应',
                'S4_Carbon_DR': 'S4: 有碳交易有需求响应'
            }
            scenario_name = scenario_name_map.get(scenario, scenario)

        voltage_file = os.path.join(data_dir, f'{scenario}_admm_node_voltage.csv')
        if not os.path.exists(voltage_file):
            return jsonify({'success': False, 'error': '请先重新导出节点电压数据'}), 404

        df = pd.read_csv(voltage_file)
        required_cols = {'Bus', 'TimeSlot', 'Voltage_pu'}
        if not required_cols.issubset(df.columns):
            return jsonify({'success': False, 'error': '节点电压数据字段不完整'}), 500

        df['Bus'] = df['Bus'].astype(int)
        df['TimeSlot'] = df['TimeSlot'].astype(int)
        nodes = sorted(df['Bus'].unique().tolist())
        hours = sorted(df['TimeSlot'].unique().tolist())

        pivot = df.pivot_table(index='Bus', columns='TimeSlot', values='Voltage_pu', aggfunc='first')
        pivot = pivot.reindex(index=nodes, columns=hours)

        voltage = []
        for _, row in pivot.iterrows():
            voltage.append([None if pd.isna(v) else float(v) for v in row.tolist()])

        valid_values = df['Voltage_pu'].dropna()
        if valid_values.empty:
            summary = {'min': None, 'max': None, 'low_violations': 0, 'high_violations': 0}
        else:
            summary = {
                'min': float(valid_values.min()),
                'max': float(valid_values.max()),
                'low_violations': int((valid_values < low_limit).sum()),
                'high_violations': int((valid_values > high_limit).sum())
            }

        return jsonify({
            'success': True,
            'scenario': scenario_name,
            'hours': hours,
            'nodes': nodes,
            'voltage': voltage,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
