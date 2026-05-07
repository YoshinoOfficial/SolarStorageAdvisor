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

OPTIMIZATION_DATA_DIR = os.path.join(project_root, '零碳园区优化_v6')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

matplotlib_lock = threading.Lock()

from main import get_simulation_data, calculate_daily_cost, calculate_renewable_revenue
from config.config_manager import (
    load_electricity_price, save_electricity_price, save_feed_in_price,
    list_available_panels, get_panel_quantities, set_panel_quantities, set_panel_quantity, load_panel_by_id,
    list_available_storages, get_current_storage_id, set_current_storage_id, load_storage_config,
    save_storage_config, create_new_storage_config, delete_storage_config,
    create_new_panel_config, delete_panel_config, save_panel_config
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
        panel_quantities = get_panel_quantities()
        current_storage_id = get_current_storage_id()
        current_storage_config = load_storage_config()
        electricity_price_config = load_electricity_price()
        
        return jsonify({
            'success': True,
            'data': {
                'panels': panels,
                'storages': storages,
                'panel_quantities': panel_quantities,
                'current_storage_id': current_storage_id,
                'current_storage_config': current_storage_config,
                'electricity_price': electricity_price_config['electricity_price'],
                'feed_in_price': electricity_price_config.get('feed_in_price', 0.4)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    try:
        data = get_simulation_data()
        cost = calculate_daily_cost(data)
        revenue = calculate_renewable_revenue(data)
        chart_data = dataframe_to_json(data)
        
        return jsonify({
            'success': True,
            'data': {
                'chart_data': chart_data,
                'daily_cost': cost,
                'renewable_revenue': revenue
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

@app.route('/api/optimization/comparison/images', methods=['GET'])
def get_comparison_images():
    try:
        comparison_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_submission')
        
        image_files = [f for f in os.listdir(comparison_dir) if f.endswith('.png')]
        
        figure_descriptions = {
            'Fig1': {
                'title': '目标函数对比',
                'description': '展示S1-S4四个场景的总成本对比。S1无储能无碳交易成本最高，S4高新能源有储能有碳交易成本最低。'
            },
            'Fig4': {
                'title': '园区购电功率对比',
                'description': '展示四个场景的日内购电功率曲线。S1购电最多且分布最宽，S4购电最少，说明储能和高新能源显著降低对外部电网的依赖。'
            },
            'Fig5': {
                'title': '可再生能源利用曲线',
                'description': '展示光伏、风电利用情况和弃能量。S1弃能最多，S2/S3储能后弃能减少，S4新能源增加但弃能略有上升。'
            },
            'Fig7a': {
                'title': '电储能SOC曲线',
                'description': '展示电储能充放电状态。S1无储能，S2-S4电储能SOC在10%-90%范围内变化，日末回到50%。'
            },
            'Fig7b': {
                'title': '热储能SOC曲线',
                'description': '展示热储能充放热状态。储能实现热能的跨时段转移，提高能源利用效率。'
            },
            'Fig8': {
                'title': 'CHP出力曲线',
                'description': '展示冷热电联产机组的电、热出力。CHP在新能源不足时提供支撑，实现多能互补。'
            },
            'Fig9': {
                'title': '能量平衡图',
                'description': '展示电、热、氢的能量供需平衡。储能和制氢设备实现能量时空转移。'
            },
            'Fig10': {
                'title': '制氢曲线',
                'description': '展示电解槽制氢功率和氢气储罐状态。制氢消纳富余新能源，提供氢气供应。'
            }
        }
        
        images = []
        for f in sorted(image_files):
            file_path = os.path.join(comparison_dir, f)
            with open(file_path, 'rb') as img_file:
                img_base64 = base64.b64encode(img_file.read()).decode()
                
                fig_num = f.split('_')[0]
                desc_info = figure_descriptions.get(fig_num, {'title': '', 'description': ''})
                
                scenario_info = ''
                if 'NoStorage_NoCarbon' in f:
                    scenario_info = 'S1: 无储能无碳交易'
                elif 'WithStorage_NoCarbon' in f:
                    scenario_info = 'S2: 有储能无碳交易'
                elif 'WithStorage_Carbon' in f:
                    scenario_info = 'S3: 有储能有碳交易'
                elif 'HighRE' in f:
                    scenario_info = 'S4: 高新能源有储能有碳交易'
                
                images.append({
                    'filename': f,
                    'data': img_base64,
                    'figure_num': fig_num,
                    'title': desc_info['title'],
                    'description': desc_info['description'],
                    'scenario': scenario_info
                })
        
        return jsonify({'success': True, 'data': images})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/optimization/comparison/image/<filename>', methods=['GET'])
def get_comparison_image(filename):
    try:
        comparison_dir = os.path.join(OPTIMIZATION_DATA_DIR, 'comparison_submission')
        file_path = os.path.join(comparison_dir, filename)
        
        if not os.path.exists(file_path):
            return jsonify({'success': False, 'error': '文件不存在'}), 404
        
        with open(file_path, 'rb') as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode()
        
        return jsonify({'success': True, 'data': img_base64})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
