from flask import Flask, render_template, jsonify, request
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from main import get_simulation_data, calculate_daily_cost
from config.config_manager import (
    load_electricity_price, save_electricity_price,
    list_available_panels, get_current_panel_id, set_current_panel_id, load_panel_by_id,
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
        current_panel_id = get_current_panel_id()
        current_storage_id = get_current_storage_id()
        current_panel_config = load_panel_by_id(current_panel_id)
        current_storage_config = load_storage_config()
        electricity_price = load_electricity_price()
        
        return jsonify({
            'success': True,
            'data': {
                'panels': panels,
                'storages': storages,
                'current_panel_id': current_panel_id,
                'current_storage_id': current_storage_id,
                'current_panel_config': current_panel_config,
                'current_storage_config': current_storage_config,
                'electricity_price': electricity_price['electricity_price']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    try:
        data = get_simulation_data()
        cost = calculate_daily_cost(data)
        chart_data = dataframe_to_json(data)
        
        return jsonify({
            'success': True,
            'data': {
                'chart_data': chart_data,
                'daily_cost': cost
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/panels/switch', methods=['POST'])
def switch_panel():
    try:
        panel_id = request.json.get('panel_id')
        set_current_panel_id(panel_id)
        return jsonify({'success': True, 'message': f'已切换到光伏板: {panel_id}'})
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
        panel_id = params.get('panel_id', get_current_panel_id())
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
