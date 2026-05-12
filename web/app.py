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

OPTIMIZATION_DATA_DIR = os.path.join(project_root, '零碳园区优化_v8')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

matplotlib_lock = threading.Lock()

from main import get_simulation_data, calculate_daily_cost, calculate_renewable_revenue
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
        data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
        
        scenario_param = request.args.get('scenario', 'S3')
        scenario_map = {
            'S1': 'S1_Normal_NoStorage_NoCarbon',
            'S2': 'S2_Normal_WithStorage_NoCarbon',
            'S3': 'S3_Normal_WithStorage_Carbon',
            'S4': 'S4_HighRE_WithStorage_Carbon'
        }
        scenario = scenario_map.get(scenario_param, 'S3_Normal_WithStorage_Carbon')
        scenario_name_map = {
            'S1_Normal_NoStorage_NoCarbon': 'S1: 无储能无碳交易',
            'S2_Normal_WithStorage_NoCarbon': 'S2: 有储能无碳交易',
            'S3_Normal_WithStorage_Carbon': 'S3: 有储能有碳交易',
            'S4_HighRE_WithStorage_Carbon': 'S4: 高新能源有储能有碳交易'
        }
        scenario_name = scenario_name_map.get(scenario, 'S3')
        
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
        data_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_plot_data_csv')
        
        scenario_param = request.args.get('scenario', 'S3')
        community_id = request.args.get('community', '1')
        
        scenario_map = {
            'S1': 'S1_Normal_NoStorage_NoCarbon',
            'S2': 'S2_Normal_WithStorage_NoCarbon',
            'S3': 'S3_Normal_WithStorage_Carbon',
            'S4': 'S4_HighRE_WithStorage_Carbon'
        }
        scenario = scenario_map.get(scenario_param, 'S3_Normal_WithStorage_Carbon')
        scenario_name_map = {
            'S1_Normal_NoStorage_NoCarbon': 'S1: 无储能无碳交易',
            'S2_Normal_WithStorage_NoCarbon': 'S2: 有储能无碳交易',
            'S3_Normal_WithStorage_Carbon': 'S3: 有储能有碳交易',
            'S4_HighRE_WithStorage_Carbon': 'S4: 高新能源有储能有碳交易'
        }
        scenario_name = scenario_name_map.get(scenario, 'S3')
        
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
        
        scenarios = ['S1_Normal_NoStorage_NoCarbon', 'S2_Normal_WithStorage_NoCarbon', 
                     'S3_Normal_WithStorage_Carbon', 'S4_HighRE_WithStorage_Carbon']
        scenario_labels = ['S1: 无储能无碳交易', 'S2: 有储能无碳交易', 
                          'S3: 有储能有碳交易', 'S4: 高新能源有储能有碳交易']
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
        
        scenario_param = request.args.get('scenario', 'S3')
        scenario_map = {
            'S1': 'S1_Normal_NoStorage_NoCarbon',
            'S2': 'S2_Normal_WithStorage_NoCarbon',
            'S3': 'S3_Normal_WithStorage_Carbon',
            'S4': 'S4_HighRE_WithStorage_Carbon'
        }
        scenario = scenario_map.get(scenario_param, 'S3_Normal_WithStorage_Carbon')
        scenario_name_map = {
            'S1_Normal_NoStorage_NoCarbon': 'S1: 无储能无碳交易',
            'S2_Normal_WithStorage_NoCarbon': 'S2: 有储能无碳交易',
            'S3_Normal_WithStorage_Carbon': 'S3: 有储能有碳交易',
            'S4_HighRE_WithStorage_Carbon': 'S4: 高新能源有储能有碳交易'
        }
        scenario_name = scenario_name_map.get(scenario, 'S3')
        
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
